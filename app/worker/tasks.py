from celery import shared_task
import base64
import logging
from typing import Dict, Any
from celery.exceptions import MaxRetriesExceededError
import asyncio
import google.generativeai as genai

from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository
from app.models.knowledge_base import DocumentStatus
from app.core.chunking import ChunkingStrategy, DocumentType, chunk_document_multi_level
from app.services.rag_service import RAGService
from app.repositories.message_repository import MessageRepository
from app.core.config import settings

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True
)
def process_document(self, document_id: str) -> None:
    """Process document content and create chunks"""
    logger.info(f"Starting document processing task for document_id: {document_id}")
    
    async def _process():
        doc_repo = DocumentRepository()
        vector_repo = VectorRepository()
        
        try:
            # Get document
            logger.info(f"Fetching document {document_id} from repository")
            document = await doc_repo.get_by_id(document_id)
            if not document:
                logger.error(f"Document {document_id} not found")
                return
            
            logger.info(f"Processing document: {document.title} (type: {document.content_type})")
            
            # Update status to processing
            logger.info(f"Updating document {document_id} status to PROCESSING")
            await doc_repo.update(document_id, {
                "status": DocumentStatus.PROCESSING,
                "error_message": None
            })
            
            # Decode content
            try:
                logger.debug(f"Decoding content for document {document_id}")
                content = base64.b64decode(document.content).decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to decode document content: {e}")
                raise ValueError(f"Invalid document content: {str(e)}")
            
            # Generate document summary
            logger.info(f"Generating summary for document {document_id}")
            summary = await _generate_document_summary(content, document.title)
            logger.info(f"Summary generated for document {document_id}")
            
            # Update document with summary
            await doc_repo.update(document_id, {"summary": summary})
            logger.info(f"Updated document {document_id} with summary")
            
            # Detect document type and get chunk size once
            doc_type = _detect_document_type(document.content_type)
            chunk_size = _get_chunk_size_for_type(doc_type)
            logger.info(f"Document type detected as {doc_type} with chunk size {chunk_size}")
            
            # Create chunking strategy
            strategy = ChunkingStrategy.default_strategy(doc_type)
            
            # Chunk document
            logger.info(f"Starting document chunking for {document_id}")
            chunks = await chunk_document_multi_level(
                content=content,
                document_id=document_id,
                document_title=document.title,
                strategy=strategy
            )
            
            if not chunks:
                logger.error(f"No chunks generated for document {document_id}")
                raise ValueError("No chunks were generated from the document")
            
            # Log chunk size distribution
            chunk_sizes = {}
            for chunk in chunks:
                size = chunk['metadata']['chunk_size']
                chunk_sizes[size] = chunk_sizes.get(size, 0) + 1
            logger.info(f"Generated chunks by size: {chunk_sizes}")
            logger.info(f"Total chunks generated: {len(chunks)}")
            
            # Store chunks in vector store
            logger.info(f"Storing {len(chunks)} chunks in vector store for document {document_id}")
            await vector_repo.add_chunks(chunks, document.knowledge_base_id)
            logger.info(f"Successfully stored chunks in vector store for document {document_id}")
            
            # Update document status
            logger.info(f"Updating document {document_id} status to COMPLETED")
            await doc_repo.update(
                document_id,
                {
                    "status": DocumentStatus.COMPLETED,
                    "error_message": None,
                    "processed_chunks": len(chunks)
                }
            )
            
            logger.info(f"Document {document_id} processed successfully with {len(chunks)} chunks")
            
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for document {document_id}")
            await doc_repo.update(
                document_id,
                {
                    "status": DocumentStatus.FAILED,
                    "error_message": "Processing failed after maximum retries"
                }
            )
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}", exc_info=True)
            await doc_repo.update(
                document_id,
                {
                    "status": DocumentStatus.FAILED,
                    "error_message": str(e)
                }
            )
            raise  # Let Celery handle the retry

    # Run the async function using asyncio.run()
    try:
        return asyncio.run(_process())
    except Exception as e:
        logger.error(f"Failed to run async process for document {document_id}: {e}", exc_info=True)
        raise

async def _generate_document_summary(content: str, title: str) -> str:
    """Generate a summary of the document content using Gemini"""
    try:
        # Initialize Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Truncate content if it's too long
        max_content_length = 10000  # Adjust based on model limits
        truncated_content = content[:max_content_length] + "..." if len(content) > max_content_length else content
        
        prompt = f"""Create a comprehensive summary of the following document. 
The summary should capture the main topics, key points, and important details.
It should be detailed enough to understand what information is contained in the document.
Focus on factual information rather than opinions.

Document Title: {title}

Document Content:
{truncated_content}

Summary:"""

        response = model.generate_content(prompt)
        summary = response.text.strip()
        
        # Ensure summary isn't too long for database storage
        max_summary_length = 5000  # Adjust based on database field size
        if len(summary) > max_summary_length:
            summary = summary[:max_summary_length] + "..."
            
        logger.info(f"Generated summary of length {len(summary)} characters")
        return summary
        
    except Exception as e:
        logger.error(f"Failed to generate document summary: {e}", exc_info=True)
        return f"Summary generation failed: {str(e)}"

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def delete_document_vectors(self, document_id: str) -> None:
    """Delete document vectors from vector store"""
    async def _process():
        vector_repo = VectorRepository()
        
        try:
            logger.info(f"Starting vector deletion for document {document_id}")
            await vector_repo.delete_document_chunks(document_id)
            logger.info(f"Successfully deleted vectors for document {document_id}")
            return True
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to delete vectors for document {document_id}: {error_msg}", exc_info=True)
            
            # Check if this is a Pinecone API error
            if "400" in error_msg and "Bad Request" in error_msg:
                logger.warning(f"Pinecone API error (400 Bad Request) for document {document_id}")
                logger.warning("This may be due to an invalid filter format or the document not existing in the index")
                
                # We'll consider this a "success" since the document doesn't exist in Pinecone
                # This prevents endless retries for a document that might not be in the index
                logger.info(f"Marking document {document_id} vector deletion as complete despite error")
                return True
            
            # For other errors, let Celery handle the retry
            raise

    try:
        return asyncio.run(_process())
    except Exception as e:
        logger.error(f"Failed to run async process for document vector deletion {document_id}: {e}", exc_info=True)
        # Check retry count and provide more context
        retry_count = self.request.retries
        max_retries = self.max_retries
        logger.info(f"Current retry count: {retry_count}/{max_retries}")
        
        if retry_count >= max_retries:
            logger.warning(f"Max retries ({max_retries}) exceeded for document {document_id} vector deletion")
            # We'll consider this a "success" to prevent the task from being stuck in the queue
            logger.info(f"Marking document {document_id} vector deletion as complete despite errors")
            return True
        
        raise

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def process_rag_response(
    self,
    message_id: str,
    query: str,
    knowledge_base_id: str,
    top_k: int = 5,
    similarity_threshold: float = 0.3
) -> None:
    """Process RAG response for a message"""
    async def _process():
        rag_service = RAGService(VectorRepository())
        msg_repo = MessageRepository()
        
        try:
            # Process query through RAG pipeline
            response = await rag_service.process_query(
                query=query,
                knowledge_base_id=knowledge_base_id,
                top_k=top_k,
                metadata_filter=None,  # No metadata filter needed
                similarity_threshold=similarity_threshold
            )
            
            if not response.get("sources", []):
                await msg_repo.update_with_sources(
                    message_id,
                    "I could not find any relevant information to answer your question.",
                    []
                )
                return
            
            # Update message with response
            await msg_repo.update_with_sources(
                message_id,
                response.get("answer", ""),
                response.get("sources", [])
            )
            
            logger.info(f"Processed RAG response for message {message_id} with {len(response.get('sources', []))} sources")
            
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for message {message_id}")
            await msg_repo.update_with_sources(
                message_id,
                "I apologize, but I encountered an error while processing your query.",
                []
            )
        except Exception as e:
            logger.error(f"Failed to process RAG response for message {message_id}: {e}")
            await msg_repo.update_with_sources(
                message_id,
                "I apologize, but I encountered an error while processing your query.",
                []
            )
            raise  # Let Celery handle the retry

    # Run the async function using asyncio.run()
    return asyncio.run(_process())

def _detect_document_type(content_type: str) -> DocumentType:
    """Detect document type from content type"""
    content_type = content_type.lower()
    
    if 'pdf' in content_type:
        return DocumentType.PDF_WITH_LAYOUT
    elif any(code_type in content_type for code_type in ['javascript', 'python', 'java', 'typescript']):
        return DocumentType.CODE
    elif content_type in ['text/markdown', 'text/rst']:
        return DocumentType.TECHNICAL_DOCS
    elif 'legal' in content_type or content_type == 'application/contract':
        return DocumentType.LEGAL_DOCS
    else:
        return DocumentType.UNSTRUCTURED_TEXT

def _get_chunk_size_for_type(doc_type: DocumentType) -> int:
    """Get appropriate chunk size based on document type"""
    chunk_sizes = {
        DocumentType.UNSTRUCTURED_TEXT: 512,
        DocumentType.TECHNICAL_DOCS: 1024,
        DocumentType.CODE: 300,
        DocumentType.LEGAL_DOCS: 256,
        DocumentType.PDF_WITH_LAYOUT: 512
    }
    
    return chunk_sizes.get(doc_type, 512) 