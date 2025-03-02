from typing import Dict, Any
import logging

from app.db.models.knowledge_base import DocumentType
from app.services.rag.chunker.chunker import Chunker, MultiLevelChunker, SingleChunker

logger = logging.getLogger(__name__)

class ChunkerFactory:
    """
    Factory for creating chunkers based on document type.
    """
    
    @staticmethod
    def create_chunker(document_type: str) -> Chunker:
        """
        Create a chunker based on document type.
        
        Args:
            document_type: Type of document to chunk
            
        Returns:
            Chunker instance
        """
        try:
            # TODO: Implement chunker factory based on document type
            return MultiLevelChunker()
        except Exception as e:
            logger.error(f"Failed to create chunker: {e}", exc_info=True)
            raise
    
    @staticmethod
    def create_chunker_from_metadata(metadata: Dict[str, Any]) -> Chunker:
        """
        Create a chunker based on document metadata.
        
        Args:
            metadata: Document metadata
            
        Returns:
            Chunker instance
        """
        try:
            logger.info("Creating chunker from metadata")
            
            # Extract document type from metadata
            document_type = metadata.get('document_type', DocumentType.UNSTRUCTURED_TEXT)
            
            # Create chunker based on document type
            return ChunkerFactory.create_chunker(document_type)
            
        except Exception as e:
            logger.error(f"Failed to create chunker from metadata: {e}", exc_info=True)
            raise 