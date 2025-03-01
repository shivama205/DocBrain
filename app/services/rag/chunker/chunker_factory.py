from typing import Dict, Any
import logging

from app.services.rag.chunker.chunker import Chunker, DocumentType, MultiLevelChunker, SingleChunker

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
            logger.info(f"Creating chunker for document type: {document_type}")
            
            # Normalize document type
            document_type = document_type.lower()
            
            # Map document types to chunkers
            if document_type in [DocumentType.STRUCTURED_TEXT, 'structured_text', 'structured']:
                logger.info("Creating MultiLevelChunker for structured text")
                return MultiLevelChunker()
            
            elif document_type in [DocumentType.CODE, 'code']:
                logger.info("Creating MultiLevelChunker for code")
                return MultiLevelChunker()
            
            elif document_type in [DocumentType.LEGAL_DOCS, 'legal_docs', 'legal']:
                logger.info("Creating MultiLevelChunker for legal documents")
                return MultiLevelChunker()
            
            elif document_type in [DocumentType.SCIENTIFIC, 'scientific']:
                logger.info("Creating MultiLevelChunker for scientific documents")
                return MultiLevelChunker()
            
            elif document_type in [DocumentType.TECHNICAL, 'technical']:
                logger.info("Creating MultiLevelChunker for technical documents")
                return MultiLevelChunker()
            
            else:
                # Default to single chunker for unstructured text
                logger.info("Creating SingleChunker for unstructured text")
                return SingleChunker()
                
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