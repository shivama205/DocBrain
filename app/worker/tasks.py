from typing import Optional
import logging
from celery import shared_task
import base64
import asyncio
from sqlalchemy.orm import Session
from celery.exceptions import MaxRetriesExceededError

from app.db.database import get_db
from app.db.models.message import MessageContentType
from app.services.rag.vector_store import get_vector_store
from app.services.query_router import get_query_router
from app.core.config import settings
from app.repositories.document_repository import DocumentRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.question_repository import QuestionRepository
from app.schemas.document import DocumentResponse
from app.schemas.question import QuestionResponse
from app.services.rag_service import get_rag_service
from app.services.llm.factory import LLMFactory, Message as LLMMessage, Role, CompletionOptions
from app.core.prompts import get_prompt, register_prompt

logger = logging.getLogger(__name__)

# Register prompts
register_prompt("worker", "document_summary", """Create a comprehensive summary of the following document. 
The summary should capture the main topics, key points, and important details.
It should be detailed enough to understand what information is contained in the document.
Focus on factual information rather than opinions.

Document Title: {{ title }}

Document Content:
{{ content }}

Summary:""")

DOCUMENT_REPO = DocumentRepository()
MESSAGE_REPO = MessageRepository()
QUESTION_REPO = QuestionRepository()
RAG_SERVICE = get_rag_service()

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
            
            # Generate document summary
            logger.info(f"Generating summary for document {document_id}")
            summary = await _generate_document_summary(
                document.content, 
                document.title
            )
            logger.info(f"Summary generated for document {document_id}")
            
            # Prepare metadata
            metadata = {
                "document_id": document_id,
                "document_title": document.title,
                "content_type": document.content_type,
                "knowledge_base_id": document.knowledge_base_id,
                "document_type": document.content_type,
            }
            
            # Method 1: Use RAG service for end-to-end processing
            # This is simpler but provides less control over individual steps
            result = await RAG_SERVICE.ingest_document(
                content=document.content,
                metadata=metadata,
                content_type=document.content_type,
            )
            chunk_count = result["chunk_count"]
            
            # Add the summary to the summary index for semantic routing
            logger.info(f"Adding summary to the summary index for document {document_id}")
            await RAG_SERVICE.add_document_summary(
                document_id=document_id,
                knowledge_base_id=document.knowledge_base_id,
                document_title=document.title,
                document_type=document.content_type,
                summary=summary
            )
            
            logger.info(f"Document {document_id} processed successfully with {chunk_count} chunks")
            
            # Update document with summary and status
            await DOCUMENT_REPO.set_processed(
                document_id,
                summary,
                chunk_count,
                db
            )
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

async def _generate_document_summary(content: bytes, title: str) -> str:
    """Generate a summary of the document content using the LLM factory"""
    try:
        # Convert bytes to base64 string
        content_str = base64.b64encode(content).decode('utf-8')

        # Truncate content if it's too long
        max_content_length = 10000  # Adjust based on model limits
        truncated_content = content_str[:max_content_length] + "..." if len(content_str) > max_content_length else content_str
        
        # Get the prompt from the registry
        prompt = get_prompt("worker", "document_summary", 
                           title=title, 
                           content=truncated_content)
        
        # Create a message for the LLM
        messages = [
            LLMMessage(role=Role.USER, content=prompt)
        ]
        
        # Set completion options
        options = CompletionOptions(
            temperature=0.3,  # Lower temperature for more factual summarization
            max_tokens=1000
        )
        
        # Generate summary using LLM Factory
        response = await LLMFactory.complete(
            messages=messages,
            options=options
        )
        
        summary = response.content.strip()
        
        # Ensure summary isn't too long for database storage
        max_summary_length = 5000  # Adjust based on database field size
        if len(summary) > max_summary_length:
            summary = summary[:max_summary_length - 3] + "..."
            
        return summary
    except Exception as e:
        logger.error(f"Error generating document summary: {e}", exc_info=True)
        return f"Summary generation failed: {str(e)}"

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def initiate_document_vector_deletion(self, document_id: str) -> None:
    """Delete document vectors from vector store"""
    async def _delete_vectors(db: Session):
        
        try:
            logger.info(f"Starting vector deletion for document {document_id}")
            
            # Get the document to find its knowledge base ID
            document = await DOCUMENT_REPO.get_by_id(document_id, db)
            if not document:
                logger.warning(f"Document {document_id} not found, cannot delete vectors")
                return True
                
            knowledge_base_id = document.knowledge_base_id
            logger.info(f"Found document {document_id} in knowledge base {knowledge_base_id}")
            
            # Delete document
            success = await RAG_SERVICE.delete_document(document_id, knowledge_base_id)
            
            # Also delete document summary from the summary index
            logger.info(f"Deleting document summary from summary index for document {document_id}")
            summary_vector_store = get_vector_store(
                store_type="pinecone", 
                index_name=settings.PINECONE_SUMMARY_INDEX_NAME
            )
            await summary_vector_store.delete_document_chunks(document_id, "summaries")
            
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
                
                # Check specifically for the Serverless/Starter tier error
                if "Serverless and Starter indexes do not support deleting with metadata filtering" in error_msg:
                    logger.warning("This error is expected with Pinecone Serverless/Starter tiers")
                    logger.warning("The vector_store.py and pinecone_retriever.py have been updated to handle this case")
                    logger.warning("Please retry the document deletion")
                    # We'll raise the exception to trigger a retry, as our updated code should handle it
                    raise
                else:
                    logger.warning("This may be due to an invalid filter format or the document not existing in the index")
                    # We'll consider this a "success" since we can't do anything about it
                    logger.info(f"Marking document {document_id} vector deletion as complete despite error")
                    return True
            
            raise

    try:
        return asyncio.run(_delete_vectors(get_db().__next__()))
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
    """Initiate query processing for a given user message and update the corresponding assistant message.
    This implementation first uses the QueryRouter to determine which service to use (RAG or TAG),
    then explicitly calls the appropriate service based on that decision.
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
            knowledge_base_id = user_msg.knowledge_base_id
            
            # Get the query router - this is a singleton
            query_router = get_query_router()
            
            # Use the full route_and_dispatch method to handle questions index and proper routing
            logger.info(f"Calling query router to route and dispatch query: '{query}'")
            
            metadata_filter = {"knowledge_base_id": knowledge_base_id} if knowledge_base_id else {}
            
            # This will check questions index first, then route if needed
            response = await query_router.route_and_dispatch(
                query=query,
                metadata_filter=metadata_filter,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            # Log which service was used
            service = response.get("service", "unknown")
            routing_info = response.get("routing_info", {})
            logger.info(f"Successfully processed query using {service} service")
            
            # Add routing metadata to the response sources and ensure all required fields are present
            sources = response.get("sources", [])
            for i, source in enumerate(sources):
                # Ensure all required fields are present in each source
                if "score" not in source:
                    source["score"] = 1.0 if service == "tag" else source.get("similarity", 0.8)
                
                if "content" not in source:
                    if service == "tag":
                        source["content"] = f"Table data from {source.get('title', 'database')}"
                    else:
                        source["content"] = source.get("text", "No content available")
                
                # Handle the source differently based on the service
                if service == "questions":
                    # For questions service, use question-specific fields
                    if "question_id" not in source:
                        metadata = source.get("metadata", {})
                        source["question_id"] = metadata.get("question_id", f"question_{i}")
                    
                    if "question" not in source:
                        source["question"] = source.get("content", "")
                    
                    # Add answer field from metadata if not present
                    if "answer" not in source:
                        metadata = source.get("metadata", {})
                        source["answer"] = metadata.get("answer", "")
                    
                    if "answer_type" not in source:
                        metadata = source.get("metadata", {})
                        source["answer_type"] = metadata.get("answer_type", "DIRECT")
                        
                    # Make document_id optional
                    if "document_id" not in source:
                        source["document_id"] = source.get("question_id", f"question_{i}")
                else:
                    # For document-based services (RAG/TAG)
                    if "chunk_index" not in source:
                        source["chunk_index"] = i
                    
                    # Ensure document_id field is present
                    if "document_id" not in source:
                        metadata = source.get("metadata", {})
                        source["document_id"] = metadata.get("document_id", f"doc_{i}")
                    
                    # Ensure title field is present
                    if "title" not in source:
                        metadata = source.get("metadata", {})
                        source["title"] = metadata.get("doc_title", "Untitled Document")
                
                # Add routing information to each source
                source["routing"] = {
                    "service": service,
                    "confidence": routing_info.get("confidence", 0),
                    "reasoning": routing_info.get("reasoning", "No reasoning provided")
                }
                
                # If TAG service was used, add SQL information to the source
                if service == "tag" and response.get("sql"):
                    source["sql_query"] = response.get("sql")

            # Prepare update data based on response
            # Both RAG and TAG services provide an "answer" field
            metadata = {"routing": routing_info}
            if service == "tag" and response.get("sql"):
                metadata["sql_query"] = response.get("sql")
                if response.get("results"):
                    metadata["sql_results"] = response.get("results")[:5]  # Limit to first 5 results to avoid huge payload
            
            # Check if sources have all required fields before calling set_processed
            logger.info(f"Checking sources for required fields: {sources}")
            
            await MESSAGE_REPO.set_processed(
                message_id=assistant_message_id,
                content=response.get("answer", ""),
                content_type=MessageContentType.TEXT,
                sources=sources,
                metadata=metadata,
                db=db
            )

        except MaxRetriesExceededError:
            err_msg = f"Max retries exceeded for message {assistant_message_id}"
            logger.error(err_msg)
            await MESSAGE_REPO.set_failed(assistant_message_id, err_msg, db)
        except Exception as e:
            logger.error(f"Failed to process response for message {assistant_message_id}: {e}", exc_info=True)
            await MESSAGE_REPO.set_failed(assistant_message_id, str(e), db)
            raise

    return asyncio.run(_retrieve(get_db().__next__()))

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True
)
def initiate_question_ingestion(self, question_id: str) -> None:
    """
    Process question and add it to the vector store.
    
    This task is triggered when a question is created or updated.
    It performs the following steps:
    1. Retrieve the question from the database
    2. Update question status to INGESTING
    3. Format the question and answer
    4. Store in vector store
    5. Update question status to COMPLETED
    """
    logger.info(f"Starting question ingestion task for question_id: {question_id}")
    
    async def _ingest(db: Session):
        try:
            # Get question
            logger.info(f"Fetching question {question_id} from repository")
            question: Optional[QuestionResponse] = await QUESTION_REPO.get_by_id(question_id, db)
            if not question:
                logger.error(f"Question {question_id} not found")
                raise ValueError(f"Question {question_id} not found")
            
            logger.info(f"Processing question: {question.question} (type: {question.answer_type})")
            
            # Update status to ingesting
            logger.info(f"Updating question {question_id} status to INGESTING")
            await QUESTION_REPO.set_ingesting(question_id, db)
            
            try:
                # Get vector store instance
                vector_store = get_vector_store(
                    store_type="pinecone",
                    index_name=settings.PINECONE_QUESTIONS_INDEX_NAME
                )
                
                # Create metadata with question-specific fields only
                metadata = {
                    "question_id": question_id,
                    "knowledge_base_id": question.knowledge_base_id,
                    "answer_type": str(question.answer_type),
                    "question": question.question,  # Store the actual question for retrieval
                    "answer": question.answer,      # Store the answer in metadata as well
                    "user_id": str(question.user_id),
                }
                
                # Format content for vector store - include both question and answer in content
                formatted_content = f"Question: {question.question}\nAnswer: {question.answer}"
                
                # Store in vector store using knowledge_base_id as namespace
                # Use the specialized add_questions method for questions
                await vector_store.add_questions(
                    texts=[formatted_content],
                    metadatas=[metadata],
                    ids=[f"question:{question_id}"],
                    collection_name=question.knowledge_base_id
                )
                
                logger.info(f"Question {question_id} successfully ingested into questions index")
                await QUESTION_REPO.set_completed(question_id, db)
                
            except Exception as e:
                # Update status to failed
                logger.error(f"Failed to ingest question {question_id}: {e}", exc_info=True)
                await QUESTION_REPO.set_failed(question_id, db)
                raise
                
        except Exception as e:
            logger.error(f"Failed to ingest question: {e}", exc_info=True)
            raise
    
    loop = asyncio.get_event_loop()
    try:
        for db in get_db():
            loop.run_until_complete(_ingest(db))
            break
    except Exception as e:
        logger.error(f"Error in question ingestion: {e}", exc_info=True)
        self.retry(exc=e)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def initiate_question_vector_deletion(self, question_id: str, knowledge_base_id: str) -> None:
    """
    Delete question vectors from vector store.
    
    This task is triggered when a question is deleted.
    """
    logger.info(f"Starting question vector deletion task for question_id: {question_id}")
    
    async def _delete_vectors(db: Session):
        try:
            # Get vector store instance for questions index
            vector_store = get_vector_store(
                store_type="pinecone",
                index_name=settings.PINECONE_QUESTIONS_INDEX_NAME
            )
            
            # Delete from vector store using knowledge_base_id as namespace
            await vector_store.delete_document_chunks(
                document_id=f"question:{question_id}",
                knowledge_base_id=knowledge_base_id
            )
            
            logger.info(f"Successfully deleted question {question_id} vectors from questions index")
            
        except Exception as e:
            logger.error(f"Failed to delete question vectors: {e}", exc_info=True)
            raise
    
    loop = asyncio.get_event_loop()
    try:
        for db in get_db():
            loop.run_until_complete(_delete_vectors(db))
            break
    except Exception as e:
        logger.error(f"Error in question vector deletion: {e}", exc_info=True)
        self.retry(exc=e)
