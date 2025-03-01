from typing import Dict, Any, Optional
import logging
import mimetypes
from app.services.ingestor import (
    Ingestor,
    PDFIngestor,
    CSVIngestor,
    MarkdownIngestor,
    ImageIngestor,
    TextIngestor
)

logger = logging.getLogger(__name__)

class IngestorFactory:
    """
    Factory for creating ingestors based on document type.
    """
    
    @staticmethod
    def create_ingestor(content_type: str) -> Ingestor:
        """
        Create an ingestor based on content type.
        
        Args:
            content_type: MIME type of the document
            
        Returns:
            Ingestor instance
            
        Raises:
            ValueError: If no ingestor is available for the content type
        """
        try:
            logger.info(f"Creating ingestor for content type: {content_type}")
            
            # Normalize content type
            content_type = content_type.lower()
            
            # Map content types to ingestors
            if content_type in ['application/pdf', 'pdf']:
                logger.info("Creating PDFIngestor")
                return PDFIngestor()
            
            elif content_type in ['text/csv', 'application/csv', 'csv']:
                logger.info("Creating CSVIngestor")
                return CSVIngestor()
            
            elif content_type in ['text/markdown', 'markdown', 'md']:
                logger.info("Creating MarkdownIngestor")
                return MarkdownIngestor()
            
            elif content_type.startswith('image/'):
                logger.info("Creating ImageIngestor")
                return ImageIngestor()
            
            elif content_type.startswith('text/'):
                logger.info("Creating TextIngestor")
                return TextIngestor()
            
            else:
                # Default to text ingestor
                logger.warning(f"No specific ingestor for content type {content_type}, using TextIngestor")
                return TextIngestor()
                
        except Exception as e:
            logger.error(f"Failed to create ingestor: {e}", exc_info=True)
            raise
    
    @staticmethod
    def create_ingestor_from_filename(filename: str) -> Ingestor:
        """
        Create an ingestor based on filename extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            Ingestor instance
        """
        try:
            logger.info(f"Creating ingestor for file: {filename}")
            
            # Guess content type from filename
            content_type, _ = mimetypes.guess_type(filename)
            
            if not content_type:
                # Try to determine from extension
                extension = filename.split('.')[-1].lower() if '.' in filename else ''
                
                if extension == 'pdf':
                    content_type = 'application/pdf'
                elif extension == 'csv':
                    content_type = 'text/csv'
                elif extension in ['md', 'markdown']:
                    content_type = 'text/markdown'
                elif extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                    content_type = f'image/{extension}'
                elif extension in ['txt', 'text']:
                    content_type = 'text/plain'
                else:
                    content_type = 'text/plain'  # Default
            
            logger.info(f"Determined content type: {content_type}")
            
            # Create ingestor based on content type
            return IngestorFactory.create_ingestor(content_type)
            
        except Exception as e:
            logger.error(f"Failed to create ingestor from filename: {e}", exc_info=True)
            raise 