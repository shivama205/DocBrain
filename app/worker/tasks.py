from celery import shared_task
import base64
import logging
from typing import Dict, Any
from celery.exceptions import MaxRetriesExceededError
import asyncio
import google.generativeai as genai

from app.repositories.document_repository import DocumentRepository
from app.services.retriever_factory import RetrieverFactory
from app.models.knowledge_base import DocumentStatus
from app.core.chunking import ChunkingStrategy, DocumentType, chunk_document_multi_level
from app.services.rag_service import RAGService
from app.services.ingestor_factory import IngestorFactory
from app.services.chunker_factory import ChunkerFactory
from app.services.chunker import ChunkSize
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
    """
    Process document content and create chunks.
    
    This task is triggered when a document is uploaded to the system.
    It performs the following steps:
    1. Retrieve the document from the database
    2. Update document status to PROCESSING
    3. Detect document type and extract content
    4. Ingest the document using appropriate ingestor
    5. Chunk the document using appropriate chunker
    6. Store chunks in vector store
    7. Generate document summary
    8. Update document status to COMPLETED
    """
    logger.info(f"Starting document processing task for document_id: {document_id}")
    
    async def _process():
        doc_repo = DocumentRepository()
        
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
                content = base64.b64decode(document.content)
            except Exception as e:
                logger.error(f"Failed to decode document content: {e}")
                raise ValueError(f"Invalid document content: {str(e)}")
            
            # Detect document type
            document_type = _detect_document_type(document.content_type)
            logger.info(f"Detected document type: {document_type}")
            
            # Prepare metadata
            metadata = {
                "document_id": document_id,
                "title": document.title,
                "document_title": document.title,
                "content_type": document.content_type,
                "knowledge_base_id": document.knowledge_base_id,
                "document_type": document_type
            }
            
            # Method 1: Use RAG service for end-to-end processing
            # This is simpler but provides less control over individual steps
            rag_service = RAGService(document.knowledge_base_id)
            result = await rag_service.ingest_document(
                content=content,
                metadata=metadata,
                content_type=document.content_type,
                chunk_size=_get_chunk_size(document_type)
            )
            chunk_count = result["chunk_count"]
            
            # Method 2: Process step by step (alternative approach with more control)
            # Uncomment this section if you need more control over the ingestion process
            """
            # Create ingestor based on content type
            ingestor = IngestorFactory.create_ingestor(document.content_type)
            
            # Ingest document
            ingestion_result = await ingestor.ingest(content, metadata)
            
            # Extract text and enhanced metadata
            text = ingestion_result["text"]
            enhanced_metadata = ingestion_result["metadata"]
            
            # Create chunker based on document type
            chunker = ChunkerFactory.create_chunker_from_metadata(enhanced_metadata)
            
            # Chunk document
            chunks = await chunker.chunk(text, enhanced_metadata, _get_chunk_size(document_type))
            
            # Create retriever
            retriever = RetrieverFactory.create_retriever(document.knowledge_base_id)
            
            # Store chunks in vector store
            await retriever.add_chunks(chunks)
            
            chunk_count = len(chunks)
            """
            
            # Generate document summary
            logger.info(f"Generating summary for document {document_id}")
            summary = await _generate_document_summary(
                base64.b64decode(document.content).decode('utf-8'), 
                document.title
            )
            logger.info(f"Summary generated for document {document_id}")
            
            # Update document with summary and status
            await doc_repo.update(
                document_id,
                {
                    "status": DocumentStatus.COMPLETED,
                    "error_message": None,
                    "processed_chunks": chunk_count,
                    "summary": summary
                }
            )
            
            logger.info(f"Document {document_id} processed successfully with {chunk_count} chunks")
            
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
        from app.repositories.document_repository import DocumentRepository
        
        try:
            logger.info(f"Starting vector deletion for document {document_id}")
            
            # Get the document to find its knowledge base ID
            document = await DocumentRepository.get_by_id(document_id)
            if not document:
                logger.warning(f"Document {document_id} not found, cannot delete vectors")
                return True
                
            knowledge_base_id = document.knowledge_base_id
            logger.info(f"Found document {document_id} in knowledge base {knowledge_base_id}")
            
            # Create RAG service
            rag_service = RAGService(knowledge_base_id)
            
            # Delete document
            success = await rag_service.delete_document(document_id)
            
            if success:
                logger.info(f"Successfully deleted vectors for document {document_id} from knowledge base {knowledge_base_id}")
            else:
                logger.warning(f"Failed to delete vectors for document {document_id}, but continuing")
                
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
        # Create RAG service
        rag_service = RAGService(knowledge_base_id)
        msg_repo = MessageRepository()
        
        try:
            # Process query through RAG pipeline
            response = await rag_service.retrieve(
                query=query,
                top_k=top_k,
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

def _detect_document_type(content_type: str) -> str:
    """
    Detect document type from content type.
    
    Args:
        content_type: MIME type of the document
        
    Returns:
        Document type as a string
    """
    content_type = content_type.lower()
    
    if 'pdf' in content_type:
        return "pdf_with_layout"
    elif any(code_type in content_type for code_type in ['javascript', 'python', 'java', 'typescript']):
        return "code"
    elif content_type in ['text/markdown', 'text/rst']:
        return "technical_docs"
    elif 'legal' in content_type or content_type == 'application/contract':
        return "legal_docs"
    elif content_type in ['text/csv', 'application/csv']:
        return "structured_text"
    elif content_type.startswith('image/'):
        return "image"
    else:
        return "unstructured_text"

def _get_chunk_size(document_type: str) -> ChunkSize:
    """
    Get appropriate chunk size based on document type.
    
    Args:
        document_type: Type of document
        
    Returns:
        ChunkSize enum value
    """
    chunk_sizes = {
        "unstructured_text": ChunkSize.MEDIUM,
        "structured_text": ChunkSize.MEDIUM,
        "technical_docs": ChunkSize.LARGE,
        "code": ChunkSize.SMALL,
        "legal_docs": ChunkSize.SMALL,
        "pdf_with_layout": ChunkSize.MEDIUM,
        "image": ChunkSize.MEDIUM
    }
    
    return chunk_sizes.get(document_type, ChunkSize.MEDIUM) 