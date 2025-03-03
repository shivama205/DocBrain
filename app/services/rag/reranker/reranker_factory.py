from typing import Dict, Any, Optional
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
    
    It uses a singleton pattern to ensure models are only initialized once,
    which helps prevent segmentation faults in multiprocessing environments.
    """
    
    # Singleton instances for each reranker type
    _pinecone_instance: Optional[Reranker] = None
    _cross_encoder_instance: Optional[Reranker] = None
    _flag_embedding_instance: Optional[Reranker] = None
    
    @staticmethod
    def create(config: Dict[str, Any]) -> Reranker:
        """
        Create or return a singleton reranker based on configuration.
        
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
        logger.info(f"Getting reranker of type: {reranker_type}")
        
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
        Create a PineconeReranker instance or return existing singleton.
        
        Args:
            config: Configuration for the PineconeReranker
            
        Returns:
            A PineconeReranker instance or fallback to CrossEncoderReranker if Pinecone is not available
        """
        # Return existing instance if available
        if RerankerFactory._pinecone_instance is not None:
            logger.info("Returning existing PineconeReranker instance")
            return RerankerFactory._pinecone_instance
            
        if not PINECONE_AVAILABLE:
            logger.warning("Pinecone not installed. Falling back to CrossEncoderReranker.")
            return RerankerFactory._create_cross_encoder_reranker(config)
        
        model_name = config.get("model_name", "cohere-rerank-3.5")
        logger.info(f"Creating new PineconeReranker with model: {model_name}")
        
        # Create and store the instance
        RerankerFactory._pinecone_instance = PineconeReranker(model_name=model_name)
        return RerankerFactory._pinecone_instance
    
    @staticmethod
    def _create_cross_encoder_reranker(config: Dict[str, Any]) -> Reranker:
        """
        Create a CrossEncoderReranker instance or return existing singleton.
        
        Args:
            config: Configuration for the CrossEncoderReranker
            models: 
                - cross-encoder/ms-marco-MiniLM-L-6-v2
                - BAAI/bge-reranker-v2-m3
        Returns:
            A CrossEncoderReranker instance
        """
        # Return existing instance if available
        if RerankerFactory._cross_encoder_instance is not None:
            logger.info("Returning existing CrossEncoderReranker instance")
            return RerankerFactory._cross_encoder_instance

        model_name = config.get("model_name", "BAAI/bge-reranker-v2-m3")
        logger.info(f"Creating new CrossEncoderReranker with model: {model_name}")
        
        # Create and store the instance
        RerankerFactory._cross_encoder_instance = CrossEncoderReranker(model_name=model_name)
        return RerankerFactory._cross_encoder_instance
    
    @staticmethod
    def _create_flag_embedding_reranker(config: Dict[str, Any]) -> Reranker:
        """
        Create a FlagEmbeddingReranker instance or return existing singleton.
        
        Args:
            config: Configuration for the FlagEmbeddingReranker
            models:
                - BAAI/bge-reranker-v2-m3
                - BAAI/bge-reranker-v2-gemma
        Returns:
            A FlagEmbeddingReranker instance
        """
        # Return existing instance if available
        if RerankerFactory._flag_embedding_instance is not None:
            logger.info("Returning existing FlagEmbeddingReranker instance")
            return RerankerFactory._flag_embedding_instance
            
        model_name = config.get("model_name", "BAAI/bge-reranker-v2-m3")
        logger.info(f"Creating new FlagEmbeddingReranker with model: {model_name}")
        
        # Create and store the instance
        RerankerFactory._flag_embedding_instance = FlagEmbeddingReranker(model_name=model_name)
        return RerankerFactory._flag_embedding_instance

    @staticmethod
    def initialize_models(config: Dict[str, Any] = None) -> None:
        """
        Pre-initialize all reranker models at startup.
        
        This method should be called during application or worker startup
        to ensure models are initialized in the main process before any
        forking occurs.
        
        Args:
            config: Optional configuration dictionary
        """
        if config is None:
            config = {}
            
        logger.info("Pre-initializing reranker models...")
        
        # Initialize the default reranker (usually flag or cross-encoder)
        default_type = config.get("type", "flag")
        if default_type == "flag":
            RerankerFactory._create_flag_embedding_reranker(config)
        else:
            RerankerFactory._create_cross_encoder_reranker(config)
            
        logger.info("Reranker models pre-initialized successfully")

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