from typing import Dict, Any, Optional, Union
import logging
from app.db.models.knowledge_base import DocumentType
from app.services.rag.chunker.chunker import ChunkSize
from app.services.rag.chunker.chunker_factory import ChunkerFactory
from app.services.rag.ingestor.ingestor_factory import IngestorFactory
from app.services.rag.reranker import CrossEncoderReranker
from app.services.rag.retriever.retriever_factory import RetrieverFactory
from app.services.rag.llm import GeminiLLM

logger = logging.getLogger(__name__)

class RAGService:
    """
    Retrieval-Augmented Generation (RAG) service that combines document ingestion,
    chunking, retrieval, reranking, and answer generation.
    """
    
    def __init__(self, use_reranker: bool = True, reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", llm_model: str = "gemini-2.0-flash"):
        """Initialize the RAG service. All methods now receive knowledge_base_id as a parameter where needed."""
        try:
            logger.info("Initializing RAG service")

            self.use_reranker = use_reranker
            if use_reranker:
                logger.info(f"Initializing reranker with model {reranker_model}")
                self.reranker = CrossEncoderReranker(reranker_model)
            else:
                self.reranker = None

            logger.info(f"Initializing LLM with model {llm_model}")
            self.llm = GeminiLLM(llm_model)

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
    
    async def retrieve(
        self,
        knowledge_base_id: str,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
        rerank: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant chunks and generate an answer.
        
        Args:
            knowledge_base_id: ID of the knowledge base to use
            query: The query to process
            top_k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity score for chunks
            metadata_filter: Optional filter for retrieval
            rerank: Whether to use reranking (overrides instance setting)
            
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
                top_k=top_k * 2 if self.use_reranker else top_k,  # Retrieve more if reranking
                similarity_threshold=similarity_threshold,
                metadata_filter=metadata_filter
            )
            
            logger.info(f"Retrieved {len(chunks)} chunks")
            
            # Determine whether to rerank
            should_rerank = False
            
            # Rerank chunks if enabled
            if should_rerank and chunks:
                logger.info("Reranking chunks")
                chunks = await self.reranker.rerank(query, chunks, top_k)
                logger.info(f"Reranked to {len(chunks)} chunks")
            elif len(chunks) > top_k:
                # Limit to top_k if not reranking
                chunks = chunks[:top_k]
            
            # Generate answer
            if chunks:
                logger.info("Generating answer")
                answer = await self.llm.generate_answer(query, chunks)
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