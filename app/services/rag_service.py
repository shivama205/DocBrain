from typing import List, Dict, Any, Optional, Tuple, Union, BinaryIO
import logging
import base64
from app.services.ingestor import Ingestor
from app.services.ingestor_factory import IngestorFactory
from app.services.chunker import Chunker, ChunkSize, DocumentType
from app.services.chunker_factory import ChunkerFactory
from app.services.retriever import Retriever
from app.services.retriever_factory import RetrieverFactory
from app.services.reranker import Reranker, CrossEncoderReranker
from app.services.llm import LLM, GeminiLLM
from app.core.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    """
    Retrieval-Augmented Generation (RAG) service that combines document ingestion,
    chunking, retrieval, reranking, and answer generation.
    """
    
    def __init__(
        self,
        knowledge_base_id: str,
        use_reranker: bool = True,
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        llm_model: str = "gemini-2.0-flash"
    ):
        """
        Initialize the RAG service.
        
        Args:
            knowledge_base_id: ID of the knowledge base to use
            use_reranker: Whether to use reranking
            reranker_model: Name of the reranker model to use
            llm_model: Name of the LLM model to use
        """
        try:
            logger.info(f"Initializing RAG service for knowledge base {knowledge_base_id}")
            
            # Create retriever
            self.retriever = RetrieverFactory.create_retriever(knowledge_base_id)
            
            # Create reranker if enabled
            self.use_reranker = use_reranker
            if use_reranker:
                logger.info(f"Initializing reranker with model {reranker_model}")
                self.reranker = CrossEncoderReranker(reranker_model)
            else:
                self.reranker = None
            
            # Create LLM
            logger.info(f"Initializing LLM with model {llm_model}")
            self.llm = GeminiLLM(llm_model)
            
            logger.info("RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}", exc_info=True)
            raise
    
    async def ingest_document(
        self,
        content: Union[str, bytes],
        metadata: Dict[str, Any],
        content_type: str,
        chunk_size: ChunkSize = ChunkSize.MEDIUM
    ) -> Dict[str, Any]:
        """
        Ingest a document into the knowledge base.
        
        Args:
            content: Document content as string or bytes
            metadata: Document metadata
            content_type: MIME type of the document
            chunk_size: Size of chunks to create
            
        Returns:
            Dictionary containing:
                - document_id: ID of the ingested document
                - chunk_count: Number of chunks created
        """
        try:
            logger.info(f"Ingesting document of type {content_type}")
            
            # Convert string to bytes if needed
            if isinstance(content, str):
                content = content.encode('utf-8')
            
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
            chunks = await chunker.chunk(text, enhanced_metadata, chunk_size)
            
            # Store chunks in vector store
            await self.retriever.add_chunks(chunks)
            
            logger.info(f"Successfully ingested document with {len(chunks)} chunks")
            
            return {
                "document_id": enhanced_metadata.get("document_id", ""),
                "chunk_count": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest document: {e}", exc_info=True)
            raise
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the knowledge base.
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting document {document_id}")
            
            # Delete document chunks from vector store
            await self.retriever.delete_document_chunks(document_id)
            
            logger.info(f"Successfully deleted document {document_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}", exc_info=True)
            return False
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
        rerank: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant chunks and generate an answer.
        
        Args:
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
            
            # Retrieve chunks
            chunks = await self.retriever.search(
                query=query,
                top_k=top_k * 2 if self.use_reranker else top_k,  # Retrieve more if reranking
                similarity_threshold=similarity_threshold,
                metadata_filter=metadata_filter
            )
            
            logger.info(f"Retrieved {len(chunks)} chunks")
            
            # Determine whether to rerank
            should_rerank = rerank if rerank is not None else self.use_reranker
            
            # Rerank chunks if enabled
            if should_rerank and self.reranker and chunks:
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