from typing import List, Dict, Any, Optional, Union
import logging
from app.repositories.vector_repository import VectorRepository
from app.services.rag.reranking_service import RerankingService
from app.core.config.reranking_config import RerankingConfig
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class RAGConfig(BaseModel):
    """Configuration for the RAG pipeline."""
    
    # Reranking configuration
    reranking_config: Optional[RerankingConfig] = Field(
        default_factory=RerankingConfig,
        description="Configuration for the reranking service"
    )
    
    # Retrieval configuration
    top_k: int = Field(
        default=10, 
        description="Number of chunks to retrieve initially"
    )
    
    similarity_threshold: float = Field(
        default=0.3, 
        description="Minimum similarity score for chunks to be considered relevant"
    )
    
    # Generation configuration
    max_new_tokens: int = Field(
        default=1024, 
        description="Maximum number of tokens to generate"
    )
    
    temperature: float = Field(
        default=0.7, 
        description="Temperature for generation"
    )
    
    class Config:
        """Pydantic config"""
        extra = "forbid"  # Forbid extra attributes


class RAGPipeline:
    """
    RAG (Retrieval-Augmented Generation) pipeline.
    
    This class orchestrates the RAG pipeline, including:
    1. Retrieval of relevant chunks
    2. Optional reranking of chunks
    3. Generation of answers
    """
    
    def __init__(
        self,
        vector_repository: VectorRepository,
        reranking_service: Optional[RerankingService] = None,
        config: Optional[RAGConfig] = None
    ):
        """
        Initialize the RAG pipeline.
        
        Args:
            vector_repository: Repository for retrieving chunks
            reranking_service: Optional service for reranking chunks
            config: Configuration for the RAG pipeline
        """
        self.vector_repository = vector_repository
        self.reranking_service = reranking_service
        self.config = config or RAGConfig()
        
        logger.info(f"Initialized RAG pipeline with config: {self.config}")
        logger.info(f"Reranking service: {self.reranking_service.__class__.__name__ if self.reranking_service else 'None'}")
    
    async def process_query(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        similarity_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Process a query through the RAG pipeline.
        
        Args:
            query: The query to process
            knowledge_base_id: The ID of the knowledge base to search
            top_k: The number of chunks to retrieve (overrides config if provided)
            metadata_filter: Optional metadata filter to apply
            similarity_threshold: Minimum similarity score (overrides config if provided)
            
        Returns:
            Dictionary containing the answer and relevant chunks
        """
        # Use provided parameters or fall back to config
        top_k_retrieval = top_k or self.config.top_k
        similarity_threshold_value = similarity_threshold or self.config.similarity_threshold
        
        logger.info(f"Processing query: '{query}'")
        logger.info(f"Knowledge base: {knowledge_base_id}")
        logger.info(f"Retrieval parameters: top_k={top_k_retrieval}, similarity_threshold={similarity_threshold_value}")
        
        try:
            # Step 1: Retrieve relevant chunks
            chunks = await self.vector_repository.search_chunks(
                query=query,
                knowledge_base_id=knowledge_base_id,
                top_k=top_k_retrieval,
                metadata_filter=metadata_filter,
                similarity_threshold=similarity_threshold_value
            )
            
            logger.info(f"Retrieved {len(chunks)} chunks from vector repository")
            
            # Step 2: Rerank chunks if reranking service is available
            if self.reranking_service and chunks:
                logger.info("Reranking chunks...")
                chunks = await self.reranking_service.rerank(
                    query=query,
                    chunks=chunks,
                    top_k=top_k
                )
                logger.info(f"After reranking: {len(chunks)} chunks")
            
            # Step 3: Generate answer (placeholder - will be implemented separately)
            # For now, we'll just return the chunks
            
            return {
                "query": query,
                "chunks": chunks,
                "knowledge_base_id": knowledge_base_id,
                "reranked": self.reranking_service is not None
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            raise 