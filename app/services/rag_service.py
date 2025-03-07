from typing import Dict, Any, Optional, List
import logging
from app.db.models.knowledge_base import DocumentType
from app.services.rag.chunker.chunker_factory import ChunkerFactory
from app.services.rag.ingestor.ingestor_factory import IngestorFactory
from app.services.rag.reranker.reranker_factory import RerankerFactory
from app.services.rag.retriever.retriever_factory import RetrieverFactory
from app.services.llm.factory import LLMFactory, Message, Role, CompletionOptions
from app.core.prompts import get_prompt, register_prompt
from app.core.config import settings
from app.services.rag.vector_store import get_vector_store
from functools import lru_cache

logger = logging.getLogger(__name__)

# Register rag_service prompts
register_prompt("rag_service", "generate_answer", """
Based on the given sources, please answer the question.
If you cannot find a relevant answer in the sources, please say so.

Sources:
{{ context }}

Question: {{ query }}

Please provide a clear, direct answer that:
1. Directly addresses the question
2. Uses [Source X] notation to cite the sources
3. Only uses information from the provided sources
4. Maintains a professional and helpful tone
""")

class RAGService:
    """
    Retrieval-Augmented Generation (RAG) service that combines document ingestion,
    chunking, retrieval, reranking, and answer generation.
    """
    
    def __init__(self, use_reranker: bool = True, reranker_model: str = "Cohere/rerank-v3.5", llm_model: str = "gemini-2.0-flash", llm_provider: Optional[str] = None):
        """
        Initialize the RAG service.
        
        Args:
            use_reranker: Whether to use reranking
            reranker_model: Model to use for reranking
            llm_model: Model to use for answer generation
            llm_provider: Provider to use for answer generation (defaults to settings.LLM_PROVIDER)
        """
        try:
            logger.info(f"Initializing RAG service with model {llm_model} from provider {llm_provider or settings.LLM_PROVIDER}")
            self.llm_model = llm_model
            self.llm_provider = llm_provider
            self.use_reranker = use_reranker
            self.reranker_model = reranker_model
            logger.info("RAG service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}", exc_info=True)
            raise
    
    async def ingest_document(
        self,
        content: bytes,
        metadata: Dict[str, Any],
        content_type: DocumentType,
    ) -> Dict[str, Any]:
        """
        Ingest a document into the knowledge base.
        
        Args:
            content: Document content as string or bytes
            metadata: Document metadata
            content_type: MIME type of the document
            
        Returns:
            Dictionary containing:
                - document_id: ID of the ingested document
                - chunk_count: Number of chunks created
        """
        try:
            logger.info(f"Ingesting document of type {content_type}")
            
            # Create ingestor
            ingestor = IngestorFactory.create_ingestor(content_type)
            
            # Ingest document
            ingestion_result = await ingestor.ingest(content, metadata)
            
            # Extract text and enhanced metadata
            text = ingestion_result["text"]
            enhanced_metadata = ingestion_result["metadata"]
            
            # Create chunker
            chunker = ChunkerFactory.create_chunker_from_metadata(enhanced_metadata)
            
            # Chunk document
            chunks = await chunker.chunk(text, enhanced_metadata)
            
            # Use knowledge_base_id from metadata to create retriever
            kb_id = metadata.get("knowledge_base_id")
            retriever = RetrieverFactory.create_retriever(kb_id)
            await retriever.add_chunks(chunks)
            
            logger.info(f"Successfully ingested document with {len(chunks)} chunks")
            
            return {
                "document_id": enhanced_metadata.get("document_id", ""),
                "chunk_count": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest document: {e}", exc_info=True)
            raise
    
    async def delete_document(self, document_id: str, knowledge_base_id: str) -> bool:
        """
        Delete a document from the knowledge base.
        
        Args:
            document_id: ID of the document to delete
            knowledge_base_id: ID of the knowledge base to delete the document from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting document {document_id}")
            
            # Create retriever using the provided knowledge_base_id
            retriever = RetrieverFactory.create_retriever(knowledge_base_id)
            
            # Delete document chunks from vector store
            await retriever.delete_document_chunks(document_id)
            
            logger.info(f"Successfully deleted document {document_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}", exc_info=True)
            return False
    
    async def retrieve_from_storage(
        self,
        knowledge_base_id: str,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant chunks from storage.
        """
        try:
            logger.info(f"Retrieving from storage for query: '{query}'")
            
            # Create retriever using the provided knowledge_base_id
            retriever = RetrieverFactory.create_retriever(knowledge_base_id)

            # TODO: Add Text 2 SQL to convert query to SQL and remove chunks 
            # Retrieve chunks
            chunks = await retriever.search(query, top_k, similarity_threshold)
            return chunks
        except Exception as e:
            logger.error(f"Failed to retrieve from storage: {e}", exc_info=True)
            raise
            

    async def retrieve(
        self,
        knowledge_base_id: str,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant chunks and generate an answer.
        
        Args:
            knowledge_base_id: ID of the knowledge base to use
            query: The query to process
            top_k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity score for chunks
            metadata_filter: Optional filter for retrieval
            
        Returns:
            Dictionary containing:
                - answer: Generated answer
                - sources: List of source chunks
        """
        try:
            logger.info(f"Processing query: '{query}'")
            
            # Create retriever using the provided knowledge_base_id
            retriever = RetrieverFactory.create_retriever(knowledge_base_id)

            # Retrieve chunks
            chunks = await retriever.search(
                query=query,
                top_k=top_k * 2, # always retrive twice to decide whether to rerank
                similarity_threshold=similarity_threshold,
                metadata_filter=metadata_filter
            )
            logger.info(f"Retrieved {len(chunks)} chunks")

            # True if number of chunks is higher than top_k
            should_rerank = True if len(chunks) > top_k else False

            # Rerank chunks if enabled
            if should_rerank and chunks:
                logger.info("Reranking chunks")
                reranker = RerankerFactory.create({"type": settings.RERANKER_TYPE})
                chunks = await reranker.rerank(query, chunks, top_k)
                logger.info(f"Reranked to {len(chunks)} chunks")
            elif len(chunks) > top_k:
                # Limit to top_k if not reranking
                chunks = chunks[:top_k]
            
            # Generate answer using the LLMFactory directly
            if chunks:
                logger.info("Generating answer")
                answer = await self._generate_answer(query, chunks)
            else:
                logger.warning("No chunks found, returning empty answer")
                answer = "I couldn't find any relevant information to answer your question."
            
            # Format sources
            sources = []
            for chunk in chunks:
                source = {
                    "document_id": chunk.get("document_id", ""),
                    "title": chunk.get("title", "Untitled"),
                    "content": chunk.get("content", ""),
                    "chunk_index": chunk.get("chunk_index", 0),
                    "score": chunk.get("score", 0.0)
                }
                sources.append(source)
            
            logger.info(f"Successfully processed query with {len(sources)} sources")
            
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Failed to process query: {e}", exc_info=True)
            return {
                "answer": f"I encountered an error while processing your query: {str(e)}",
                "sources": []
            }
    
    async def _generate_answer(self, query: str, context: List[Dict[str, Any]]) -> str:
        """
        Generate an answer using the LLM Factory.
        
        Args:
            query: The user's query
            context: List of context chunks to use for answering
            
        Returns:
            Generated answer as a string
        """
        try:
            logger.info(f"Generating answer for query: {query}")
            logger.info(f"Using {len(context)} context chunks")
            
            # Format context chunks
            formatted_context = self._format_context(context)
            
            # Get the prompt from the registry
            prompt = get_prompt("rag_service", "generate_answer", 
                               query=query, 
                               context=formatted_context)
            
            # Create the message for the LLM
            messages = [
                Message(role=Role.USER, content=prompt)
            ]
            
            # Set completion options
            options = CompletionOptions(
                temperature=0.3,  # Low temperature for more factual answers
                max_tokens=1000
            )
            
            # Generate response using LLM Factory
            response = await LLMFactory.complete(
                messages=messages,
                provider=self.llm_provider,
                model=self.llm_model,
                options=options
            )
            
            logger.info(f"Generated answer with {len(response.content)} characters")
            
            return response.content
            
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}", exc_info=True)
            return f"I apologize, but I encountered an error while generating an answer: {str(e)}"
    
    def _format_context(self, context: List[Dict[str, Any]]) -> str:
        """
        Format context chunks for the prompt.
        
        Args:
            context: List of context chunks
            
        Returns:
            Formatted context as a string
        """
        formatted_chunks = []
        
        for i, chunk in enumerate(context, 1):
            # Extract metadata
            document_id = chunk.get('document_id', 'unknown')
            title = chunk.get('title', 'Untitled')
            content = chunk.get('content', '')
            score = chunk.get('score', 0.0)
            
            # Format chunk
            formatted_chunk = (
                f"[Source {i}]\n"
                f"Document: {title} (ID: {document_id})\n"
                f"Relevance: {score:.3f}\n"
                f"Content: {content}\n"
            )
            
            formatted_chunks.append(formatted_chunk)
        
        return "\n\n".join(formatted_chunks)

    async def add_document_summary(
        self,
        document_id: str,
        knowledge_base_id: str,
        document_title: str,
        document_type: str,
        summary: str
    ) -> bool:
        """
        Add a document summary to the summary index for semantic routing.
        
        Args:
            document_id: ID of the document
            knowledge_base_id: ID of the knowledge base containing the document
            document_title: Title of the document
            document_type: Type of the document
            summary: Generated summary of the document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Adding summary for document {document_id} to summary index")
            
            # Get the summary vector store
            summary_vector_store = get_vector_store(
                store_type="pinecone", 
                index_name=settings.PINECONE_SUMMARY_INDEX_NAME
            )
            
            # Create a single chunk with the summary
            chunk = {
                "content": summary,
                "metadata": {
                    "document_id": document_id,
                    "knowledge_base_id": knowledge_base_id,
                    "document_title": document_title,
                    "document_type": document_type,
                    "chunk_index": 0,
                    "chunk_size": len(summary),
                    "nearest_header": "Document Summary",
                    "section_path": ["Document Summary"],
                    "is_summary": True
                }
            }
            
            # Add the summary to the summary index
            # We use "summaries" as a special namespace for all document summaries
            await summary_vector_store.add_chunks(chunks=[chunk], knowledge_base_id=knowledge_base_id)
            
            logger.info(f"Successfully added summary for document {document_id} to summary index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document summary to index: {e}", exc_info=True)
            return False 

# Create a singleton instance of RAGService
@lru_cache()
def get_rag_service(
    llm_model: Optional[str] = None, 
    llm_provider: Optional[str] = None
) -> RAGService:
    """
    Get a singleton instance of RAGService.
    
    Args:
        llm_model: Model to use for answer generation (defaults to settings.DEFAULT_LLM_MODEL or provider default)
        llm_provider: Provider to use for answer generation (defaults to settings.LLM_PROVIDER)
        
    Returns:
        RAGService instance
    """
    model = llm_model or settings.DEFAULT_LLM_MODEL or "gemini-2.0-flash"
    provider = llm_provider or settings.LLM_PROVIDER
    
    logger.info(f"Creating RAGService with model={model}, provider={provider}")
    return RAGService(llm_model=model, llm_provider=provider) 