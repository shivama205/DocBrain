from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class Retriever(ABC):
    """
    Abstract base class for retrievers that handle vector storage and retrieval.
    Each retriever is associated with a specific knowledge base.
    """
    
    def __init__(self, knowledge_base_id: str):
        """
        Initialize the retriever with a knowledge base ID.
        
        Args:
            knowledge_base_id: The ID of the knowledge base this retriever will work with
        """
        self.knowledge_base_id = knowledge_base_id
    
    @abstractmethod
    async def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Add document chunks to the vector store.
        
        Args:
            chunks: List of dictionaries containing:
                - content: str
                - metadata: Dict containing document_id, chunk_index, metadata, etc.
        """
        pass
    
    @abstractmethod
    async def delete_document_chunks(self, document_id: str) -> None:
        """
        Delete all chunks for a document from the vector store.
        
        Args:
            document_id: ID of the document to delete
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks in the vector store.
        
        Args:
            query: The search query
            top_k: Maximum number of results to return
            similarity_threshold: Minimum similarity score for results
            metadata_filter: Optional filter to apply to the search
            
        Returns:
            List of dictionaries containing:
                - id: str
                - content: str
                - score: float
                - document_id: str
                - metadata: Dict
        """
        pass
    
    @abstractmethod
    async def get_random_chunks(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get random chunks from the vector store.
        
        Args:
            limit: Maximum number of chunks to return
            
        Returns:
            List of dictionaries containing chunk data
        """
        pass 