from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from app.repositories.vector_repository import VectorRepository
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class RetrievalConfig(BaseModel):
    """Configuration for the retrieval service."""
    
    # Number of chunks to retrieve
    top_k: int = Field(
        default=10, 
        description="Number of chunks to retrieve"
    )
    
    # Minimum similarity score for chunks to be considered relevant
    similarity_threshold: float = Field(
        default=0.3, 
        description="Minimum similarity score for chunks to be considered relevant"
    )
    
    class Config:
        """Pydantic config"""
        extra = "forbid"  # Forbid extra attributes


class RetrievalService(ABC):
    """Interface for retrieval services."""
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: The query to process
            knowledge_base_id: The ID of the knowledge base to search
            top_k: The number of chunks to retrieve
            metadata_filter: Optional metadata filter to apply
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of relevant chunks
        """
        pass


class VectorRetrievalService(RetrievalService):
    """Retrieval service using a vector repository."""
    
    def __init__(
        self,
        vector_repository: VectorRepository,
        config: Optional[RetrievalConfig] = None
    ):
        """
        Initialize the vector retrieval service.
        
        Args:
            vector_repository: Repository for retrieving chunks
            config: Configuration for the retrieval service
        """
        self.vector_repository = vector_repository
        self.config = config or RetrievalConfig()
        
        logger.info(f"Initialized VectorRetrievalService with config: {self.config}")
        logger.info(f"Top-k: {self.config.top_k}, Similarity threshold: {self.config.similarity_threshold}")
    
    async def retrieve(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks using the vector repository.
        
        Args:
            query: The query to process
            knowledge_base_id: The ID of the knowledge base to search
            top_k: The number of chunks to retrieve (overrides config if provided)
            metadata_filter: Optional metadata filter to apply
            similarity_threshold: Minimum similarity score (overrides config if provided)
            
        Returns:
            List of relevant chunks
        """
        try:
            # Use provided parameters or fall back to config
            top_k_value = top_k or self.config.top_k
            similarity_threshold_value = similarity_threshold or self.config.similarity_threshold
            
            logger.info(f"Retrieving chunks for query: '{query}'")
            logger.info(f"Knowledge base: {knowledge_base_id}")
            logger.info(f"Retrieval parameters: top_k={top_k_value}, similarity_threshold={similarity_threshold_value}")
            
            if metadata_filter:
                logger.info(f"Applying metadata filter: {metadata_filter}")
            
            # Retrieve chunks from the vector repository
            chunks = await self.vector_repository.search_chunks(
                query=query,
                knowledge_base_id=knowledge_base_id,
                top_k=top_k_value,
                metadata_filter=metadata_filter,
                similarity_threshold=similarity_threshold_value
            )
            
            logger.info(f"Retrieved {len(chunks)} chunks from vector repository")
            
            if chunks:
                # Log score range
                scores = [chunk.get('score', 0.0) for chunk in chunks]
                logger.info(f"Score range: {min(scores):.3f} - {max(scores):.3f}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}", exc_info=True)
            raise 