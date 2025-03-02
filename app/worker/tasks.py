from typing import Optional
from celery import shared_task
import base64
import logging
from celery.exceptions import MaxRetriesExceededError
import asyncio
from fastapi import Depends
import google.generativeai as genai

from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.message import MessageContentType, MessageStatus
from app.repositories.document_repository import DocumentRepository
from app.db.models.knowledge_base import DocumentStatus, DocumentType
from app.schemas.document import DocumentResponse
from app.schemas.message import ProcessedMessageSchema
from app.services.rag.chunker.chunker import ChunkSize
from app.services.rag_service import RAGService
from app.repositories.message_repository import MessageRepository
from app.services.rag.vector_store import get_vector_store
from app.core.config import settings

logger = logging.getLogger(__name__)

DOCUMENT_REPO = DocumentRepository()
MESSAGE_REPO = MessageRepository()
RAG_SERVICE = RAGService()

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True
)
def initiate_document_ingestion(self, document_id: str) -> None:
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
    
    async def _ingest(db: Session):
        try:
            # Get document
            logger.info(f"Fetching document {document_id} from repository")
            document: Optional[DocumentResponse] = await DOCUMENT_REPO.get_by_id(document_id, db)
            if not document:
                logger.error(f"Document {document_id} not found")
                raise ValueError(f"Document {document_id} not found")
            
            logger.info(f"Processing document: {document.title} (type: {document.content_type})")
            
            # Update status to processing
            logger.info(f"Updating document {document_id} status to PROCESSING")
            await DOCUMENT_REPO.set_processing(document_id, db)
            
            # Prepare metadata
            metadata = {
                "document_id": document_id,
                "title": document.title,
                "document_title": document.title,
                "content_type": document.content_type,
                "knowledge_base_id": document.knowledge_base_id,
                "document_type": document.content_type
            }
            
            # Method 1: Use RAG service for end-to-end processing
            # This is simpler but provides less control over individual steps
            result = await RAG_SERVICE.ingest_document(
                content=document.content,
                metadata=metadata,
                content_type=document.content_type,
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
            await DOCUMENT_REPO.set_processed(
                document_id,
                summary,
                chunk_count,
                db
            )
            
            logger.info(f"Document {document_id} processed successfully with {chunk_count} chunks")
            
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for document {document_id}")
            await DOCUMENT_REPO.set_failed(
                document_id,
                "Processing failed after maximum retries",
                db
            )
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}", exc_info=True)
            await DOCUMENT_REPO.set_failed(
                document_id,
                str(e),
                db
            )
            raise  # Let Celery handle the retry

    # Run the async function using asyncio.run()
    try:
        return asyncio.run(_ingest(get_db().__next__()))
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
def delete_document_vectors(self, document_id: str, knowledge_base_id: str = None) -> None:
    """Delete document vectors from vector store"""
    async def _process():
        from app.repositories.document_repository import DocumentRepository
        
        try:
            logger.info(f"Starting vector deletion for document {document_id}")
            
            # If knowledge_base_id is not provided, get it from the document
            if not knowledge_base_id:
                # Get the document to find its knowledge base ID
                document = await DocumentRepository.get_by_id(document_id)
                if not document:
                    logger.warning(f"Document {document_id} not found, cannot delete vectors")
                    return True
                    
                knowledge_base_id = document.knowledge_base_id
                logger.info(f"Found document {document_id} in knowledge base {knowledge_base_id}")
            
            # Use RAG service for deletion (which uses VectorStore internally)
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
def initiate_rag_retrieval(
    self,
    user_message_id: str,
    assistant_message_id: str
) -> None:
    """Initiate RAG retrieval for a given user message and update the corresponding assistant message.
    This implementation fetches the user message (content, content_type, knowledge_base_id), uses a cached RAGService instance,
    applies system config for top_k and similarity_threshold, and then updates the assistant message with the retrieved answer,
    content_type, sources, and status. No services or repositories are newly instantiated here, ensuring efficiency.
    """

    async def _retrieve(db: Session):
        try:
            # Fetch user message using the cached repository instance
            user_msg = await MESSAGE_REPO.get_by_id(user_message_id, db)
            if not user_msg:
                error_message = f"User message {user_message_id} not found"
                logger.error(error_message)
                await MESSAGE_REPO.set_failed(assistant_message_id, error_message, db)
                return

            # Retrieve system configs for top_k and similarity threshold
            top_k = settings.RAG_TOP_K
            similarity_threshold = settings.RAG_SIMILARITY_THRESHOLD

            # Use the content from the user message as the query
            query = user_msg.content

            # Process query through the RAG pipeline
            response = await RAG_SERVICE.retrieve(
                knowledge_base_id=user_msg.knowledge_base_id,
                query=query,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )

            # Prepare update data based on response
            data = ProcessedMessageSchema(
                content=response.get("answer", ""),
                content_type=MessageContentType.TEXT,
                sources=response.get("sources", []),
            )
            await MESSAGE_REPO.set_completed(assistant_message_id, data, db)

        except MaxRetriesExceededError:
            err_msg = f"Max retries exceeded for message {assistant_message_id}"
            logger.error(err_msg)
            await MESSAGE_REPO.set_failed(assistant_message_id, err_msg, db)
        except Exception as e:
            logger.error(f"Failed to process RAG response for message {assistant_message_id}: {e}", exc_info=True)
            await MESSAGE_REPO.set_failed(assistant_message_id, str(e), db)
            raise

    return asyncio.run(_retrieve(get_db().__next__()))
