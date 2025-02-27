from typing import Optional
import logging
from app.repositories.vector_repository import VectorRepository
from app.services.rag.pipeline import RAGPipeline, RAGConfig
from app.services.rag.retrieval_service import VectorRetrievalService, RetrievalConfig
from app.services.rag.reranking_service import CrossEncoderRerankingService
from app.services.rag.generation_service import GeminiGenerationService, GenerationConfig
from app.core.config.reranking_config import RerankingConfig

logger = logging.getLogger(__name__)

class RAGFactory:
    """Factory for creating RAG pipeline instances."""
    
    @staticmethod
    async def create_pipeline(
        vector_repository: VectorRepository,
        config: Optional[RAGConfig] = None
    ) -> RAGPipeline:
        """
        Create a RAG pipeline with all necessary components.
        
        Args:
            vector_repository: Repository for retrieving chunks
            config: Configuration for the RAG pipeline
            
        Returns:
            Configured RAG pipeline
        """
        # Use provided config or create a default one
        rag_config = config or RAGConfig()
        logger.info(f"Creating RAG pipeline with config: {rag_config}")
        
        # Create retrieval service
        retrieval_config = RetrievalConfig(
            top_k=rag_config.top_k,
            similarity_threshold=rag_config.similarity_threshold
        )
        retrieval_service = VectorRetrievalService(
            vector_repository=vector_repository,
            config=retrieval_config
        )
        logger.info(f"Created retrieval service: {retrieval_service.__class__.__name__}")
        
        # Create reranking service if enabled
        reranking_service = None
        if rag_config.reranking_config.enabled:
            try:
                reranking_service = CrossEncoderRerankingService(
                    config=rag_config.reranking_config
                )
                logger.info(f"Created reranking service: {reranking_service.__class__.__name__}")
            except Exception as e:
                logger.error(f"Failed to create reranking service: {e}", exc_info=True)
                logger.warning("Continuing without reranking service")
        
        # Create generation service
        generation_config = GenerationConfig(
            max_new_tokens=rag_config.max_new_tokens,
            temperature=rag_config.temperature
        )
        generation_service = GeminiGenerationService(
            config=generation_config
        )
        logger.info(f"Created generation service: {generation_service.__class__.__name__}")
        
        # Create and return the pipeline
        pipeline = RAGPipeline(
            vector_repository=vector_repository,
            reranking_service=reranking_service,
            config=rag_config
        )
        logger.info(f"Created RAG pipeline with components: retrieval, generation, reranking={reranking_service is not None}")
        
        return pipeline 