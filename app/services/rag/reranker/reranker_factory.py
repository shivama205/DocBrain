from typing import Dict, Any
import logging

from app.services.rag.reranker.reranker import (
    Reranker,
    CrossEncoderReranker,
)
from app.services.rag.reranker.pinecone_reranker import (
    PineconeReranker,
    PINECONE_AVAILABLE
)
from app.services.rag.reranker.flag_reranker import (
    FlagEmbeddingReranker,
)

logger = logging.getLogger(__name__)

class RerankerFactory:
    """
    Factory class for creating reranker instances based on configuration.
    
    This factory provides a centralized way to create different types of rerankers
    with appropriate configuration and fallback mechanisms.
    """
    
    @staticmethod
    def create(config: Dict[str, Any]) -> Reranker:
        """
        Create a reranker based on configuration.
        
        Args:
            config: Configuration dictionary with reranker settings
                - type: Type of reranker to create ("pinecone", "cross_encoder", etc.)
                - model_name: Model name for the reranker
                - api_key: API key for services like Pinecone
                
        Returns:
            An instance of a Reranker
            
        Raises:
            ValueError: If required configuration is missing
        """
        reranker_type = config.get("type", "cross_encoder").lower()
        logger.info(f"Creating reranker of type: {reranker_type}")
        
        # Create the appropriate reranker based on type
        if reranker_type == "pinecone":
            return RerankerFactory._create_pinecone_reranker(config)
        elif reranker_type == "cross_encoder":
            return RerankerFactory._create_cross_encoder_reranker(config)
        elif reranker_type == "flag":
            return RerankerFactory._create_flag_embedding_reranker(config)
        else:
            logger.warning(f"Unknown reranker type: {reranker_type}. Falling back to CrossEncoderReranker.")
            return RerankerFactory._create_cross_encoder_reranker(config)
    
    @staticmethod
    def _create_pinecone_reranker(config: Dict[str, Any]) -> Reranker:
        """
        Create a PineconeReranker instance.
        
        Args:
            config: Configuration for the PineconeReranker
            
        Returns:
            A PineconeReranker instance or fallback to CrossEncoderReranker if Pinecone is not available
        """
        if not PINECONE_AVAILABLE:
            logger.warning("Pinecone not installed. Falling back to CrossEncoderReranker.")
            return RerankerFactory._create_cross_encoder_reranker(config)
        
        model_name = config.get("model_name", "cohere-rerank-3.5")
        logger.info(f"Creating PineconeReranker with model: {model_name}")
        
        return PineconeReranker(model_name=model_name)
    
    @staticmethod
    def _create_cross_encoder_reranker(config: Dict[str, Any]) -> Reranker:
        """
        Create a CrossEncoderReranker instance.
        
        Args:
            config: Configuration for the CrossEncoderReranker
            models: 
                - cross-encoder/ms-marco-MiniLM-L-6-v2
                - BAAI/bge-reranker-v2-m3
        Returns:
            A CrossEncoderReranker instance
        """

        model_name = config.get("model_name", "BAAI/bge-reranker-v2-m3")
        logger.info(f"Creating CrossEncoderReranker with model: {model_name}")
        
        return CrossEncoderReranker(model_name=model_name)
    
    @staticmethod
    def _create_flag_embedding_reranker(config: Dict[str, Any]) -> Reranker:
        """
        Create a FlagEmbeddingReranker instance.
        
        Args:
            config: Configuration for the FlagEmbeddingReranker
            models:
                - BAAI/bge-reranker-v2-m3
                - BAAI/bge-reranker-v2-gemma
        Returns:
            A FlagEmbeddingReranker instance
        """
        model_name = config.get("model_name", "BAAI/bge-reranker-v2-m3")
        logger.info(f"Creating FlagEmbeddingReranker with model: {model_name}")
        
        return FlagEmbeddingReranker(model_name=model_name)

# Function for backward compatibility
def create_reranker(config: Dict[str, Any]) -> Reranker:
    """
    Factory function to create a reranker based on configuration.
    
    This function is maintained for backward compatibility.
    New code should use RerankerFactory.create() instead.
    
    Args:
        config: Configuration dictionary with reranker settings
        
    Returns:
        An instance of a Reranker
    """
    logger.info("Using create_reranker (deprecated). Consider using RerankerFactory.create() instead.")
    return RerankerFactory.create(config) 