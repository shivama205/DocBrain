from typing import Optional
import logging
from app.services.retriever import Retriever
from app.services.pinecone_retriever import PineconeRetriever
from app.core.config import settings

logger = logging.getLogger(__name__)

class RetrieverFactory:
    """
    Factory for creating retrievers based on configuration.
    """
    
    @staticmethod
    def create_retriever(knowledge_base_id: str, retriever_type: Optional[str] = None) -> Retriever:
        """
        Create a retriever based on configuration.
        
        Args:
            knowledge_base_id: ID of the knowledge base to retrieve from
            retriever_type: Type of retriever to create (defaults to configured type)
            
        Returns:
            Retriever instance
            
        Raises:
            ValueError: If no retriever is available for the specified type
        """
        try:
            # If no type specified, use the configured type
            if retriever_type is None:
                retriever_type = settings.RETRIEVER_TYPE if hasattr(settings, 'RETRIEVER_TYPE') else "pinecone"
            
            logger.info(f"Creating retriever of type '{retriever_type}' for knowledge base {knowledge_base_id}")
            
            # Create retriever based on type
            if retriever_type.lower() == "pinecone":
                logger.info(f"Creating PineconeRetriever for knowledge base {knowledge_base_id}")
                return PineconeRetriever(knowledge_base_id)
            
            # Add more retriever types here as needed
            
            else:
                logger.warning(f"Unknown retriever type '{retriever_type}', falling back to PineconeRetriever")
                return PineconeRetriever(knowledge_base_id)
                
        except Exception as e:
            logger.error(f"Failed to create retriever: {e}", exc_info=True)
            raise 