from typing import Dict, Any, Optional
import logging
import mimetypes

from app.db.models.knowledge_base import DocumentType
from app.services.rag.ingestor.ingestor import CSVIngestor, ImageIngestor, Ingestor, MarkdownIngestor, PDFIngestor, TextIngestor


logger = logging.getLogger(__name__)

class IngestorFactory:
    """
    Factory for creating ingestors based on document type.
    
    Uses a singleton pattern to ensure ingestors are only initialized once,
    which helps prevent issues in multiprocessing environments.
    """
    
    # Singleton instances for each ingestor type
    _pdf_ingestor: Optional[Ingestor] = None
    _csv_ingestor: Optional[Ingestor] = None
    _markdown_ingestor: Optional[Ingestor] = None
    _image_ingestor: Optional[Ingestor] = None
    _text_ingestor: Optional[Ingestor] = None
    
    @staticmethod
    def create_ingestor(content_type: DocumentType) -> Ingestor:
        """
        Create or return a singleton ingestor based on content type.
        
        Args:
            content_type: MIME type of the document
            
        Returns:
            Ingestor instance
            
        Raises:
            ValueError: If no ingestor is available for the content type
        """
        try:
            logger.info(f"Getting ingestor for content type: {content_type}")
            
            # Normalize content type
            content_type = content_type.lower()
            
            # Map content types to ingestors
            if content_type == DocumentType.PDF:
                if IngestorFactory._pdf_ingestor is None:
                    logger.info("Creating new PDFIngestor")
                    IngestorFactory._pdf_ingestor = PDFIngestor()
                else:
                    logger.info("Returning existing PDFIngestor")
                return IngestorFactory._pdf_ingestor
            
            elif content_type in [DocumentType.CSV, DocumentType.EXCEL]:
                if IngestorFactory._csv_ingestor is None:
                    logger.info("Creating new CSVIngestor")
                    IngestorFactory._csv_ingestor = CSVIngestor()
                else:
                    logger.info("Returning existing CSVIngestor")
                return IngestorFactory._csv_ingestor
            
            elif content_type in [DocumentType.MARKDOWN, DocumentType.MD]:
                if IngestorFactory._markdown_ingestor is None:
                    logger.info("Creating new MarkdownIngestor")
                    IngestorFactory._markdown_ingestor = MarkdownIngestor()
                else:
                    logger.info("Returning existing MarkdownIngestor")
                return IngestorFactory._markdown_ingestor
            
            elif content_type in [DocumentType.JPG, DocumentType.PNG, DocumentType.GIF, DocumentType.TIFF]:
                if IngestorFactory._image_ingestor is None:
                    logger.info("Creating new ImageIngestor")
                    IngestorFactory._image_ingestor = ImageIngestor()
                else:
                    logger.info("Returning existing ImageIngestor")
                return IngestorFactory._image_ingestor
            
            elif content_type in [DocumentType.TXT, DocumentType.DOC, DocumentType.DOCX]:
                if IngestorFactory._text_ingestor is None:
                    logger.info("Creating new TextIngestor")
                    IngestorFactory._text_ingestor = TextIngestor()
                else:
                    logger.info("Returning existing TextIngestor")
                return IngestorFactory._text_ingestor
            
            else:
                # Default to text ingestor
                if IngestorFactory._text_ingestor is None:
                    logger.warning(f"No specific ingestor for content type {content_type}, creating new TextIngestor")
                    IngestorFactory._text_ingestor = TextIngestor()
                else:
                    logger.warning(f"No specific ingestor for content type {content_type}, returning existing TextIngestor")
                return IngestorFactory._text_ingestor
                
        except Exception as e:
            logger.error(f"Failed to create ingestor: {e}", exc_info=True)
            raise
    
    @staticmethod
    def create_ingestor_from_filename(filename: str) -> Ingestor:
        """
        Create or return a singleton ingestor based on filename extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            Ingestor instance
        """
        try:
            logger.info(f"Getting ingestor for file: {filename}")
            
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
            
    @staticmethod
    def initialize_ingestors() -> None:
        """
        Pre-initialize all ingestor types at startup.
        
        This method should be called during application or worker startup
        to ensure ingestors are initialized in the main process before any
        forking occurs.
        """
        logger.info("Pre-initializing ingestors...")
        
        # Initialize all ingestor types
        IngestorFactory.create_ingestor(DocumentType.PDF)
        IngestorFactory.create_ingestor(DocumentType.CSV)
        IngestorFactory.create_ingestor(DocumentType.MARKDOWN)
        IngestorFactory.create_ingestor(DocumentType.JPG)
        IngestorFactory.create_ingestor(DocumentType.TXT)
        
        logger.info("Ingestors pre-initialized successfully") 