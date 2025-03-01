from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, BinaryIO
import logging
import base64
import io
import PyPDF2
import csv
import markdown
from PIL import Image
import pytesseract
import docling
from docling.document import Document as DoclingDocument
from docling.extractors import PDFExtractor, ImageExtractor

logger = logging.getLogger(__name__)

class Ingestor(ABC):
    """
    Abstract base class for document ingestors that extract text and metadata from documents.
    """
    
    @abstractmethod
    async def ingest(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text and metadata from a document.
        
        Args:
            content: Raw document content as bytes
            metadata: Additional metadata about the document
            
        Returns:
            Dictionary containing:
                - text: Extracted text
                - metadata: Enhanced metadata
        """
        pass

class PDFIngestor(Ingestor):
    """
    Ingestor for PDF documents using docling for better text extraction and structure preservation.
    """
    
    async def ingest(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text and metadata from a PDF document using docling.
        
        Args:
            content: Raw PDF content as bytes
            metadata: Additional metadata about the document
            
        Returns:
            Dictionary containing:
                - text: Extracted text (in markdown format)
                - metadata: Enhanced metadata
        """
        try:
            logger.info("Ingesting PDF document with docling")
            
            # Create a file-like object from bytes
            pdf_file = io.BytesIO(content)
            
            # Use docling for PDF extraction
            extractor = PDFExtractor()
            doc = extractor.extract(pdf_file)
            
            # Get markdown representation
            markdown_text = doc.to_markdown()
            
            # Extract metadata from docling document
            docling_metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "creation_date": doc.metadata.get("creation_date", ""),
                "modification_date": doc.metadata.get("modification_date", ""),
                "page_count": len(doc.pages)
            }
            
            # Extract text from each page for additional processing if needed
            page_texts = []
            for page in doc.pages:
                page_texts.append(page.text)
            
            # Combine with provided metadata
            enhanced_metadata = {
                **metadata,
                "page_count": len(doc.pages),
                "pdf_metadata": docling_metadata,
                "document_type": "pdf"
            }
            
            logger.info(f"Successfully ingested PDF with {len(doc.pages)} pages using docling")
            
            return {
                "text": markdown_text,
                "metadata": enhanced_metadata,
                "page_texts": page_texts
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest PDF with docling: {e}", exc_info=True)
            
            # Fallback to PyPDF2 if docling fails
            logger.info("Falling back to PyPDF2 for PDF ingestion")
            try:
                # Create a file-like object from bytes
                pdf_file = io.BytesIO(content)
                
                # Open the PDF file
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                # Extract text from each page
                text = ""
                page_texts = []
                for i, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        page_texts.append(page_text)
                        text += f"\n\n--- Page {i+1} ---\n\n{page_text}"
                
                # Extract metadata
                pdf_metadata = {}
                if pdf_reader.metadata:
                    for key, value in pdf_reader.metadata.items():
                        if key.startswith('/'):
                            pdf_metadata[key[1:]] = value
                
                # Combine with provided metadata
                enhanced_metadata = {
                    **metadata,
                    "page_count": len(pdf_reader.pages),
                    "pdf_metadata": pdf_metadata,
                    "document_type": "pdf"
                }
                
                logger.info(f"Successfully ingested PDF with {len(pdf_reader.pages)} pages using PyPDF2 fallback")
                
                return {
                    "text": text,
                    "metadata": enhanced_metadata,
                    "page_texts": page_texts
                }
                
            except Exception as fallback_error:
                logger.error(f"Fallback PDF ingestion also failed: {fallback_error}", exc_info=True)
                raise

class CSVIngestor(Ingestor):
    """
    Ingestor for CSV documents.
    """
    
    async def ingest(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text and metadata from a CSV document.
        
        Args:
            content: Raw CSV content as bytes
            metadata: Additional metadata about the document
            
        Returns:
            Dictionary containing:
                - text: Extracted text
                - metadata: Enhanced metadata
        """
        try:
            logger.info("Ingesting CSV document")
            
            # Create a file-like object from bytes
            csv_file = io.StringIO(content.decode('utf-8'))
            
            # Read CSV
            csv_reader = csv.reader(csv_file)
            rows = list(csv_reader)
            
            # Extract headers if available
            headers = rows[0] if rows else []
            
            # Convert to text
            text = ""
            if headers:
                text += "Headers: " + ", ".join(headers) + "\n\n"
            
            for i, row in enumerate(rows[1:], 1):
                text += f"Row {i}: " + ", ".join(row) + "\n"
            
            # Enhance metadata
            enhanced_metadata = {
                **metadata,
                "row_count": len(rows) - 1 if rows else 0,
                "column_count": len(headers),
                "headers": headers,
                "document_type": "csv"
            }
            
            logger.info(f"Successfully ingested CSV with {enhanced_metadata['row_count']} rows and {enhanced_metadata['column_count']} columns")
            
            return {
                "text": text,
                "metadata": enhanced_metadata,
                "rows": rows
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest CSV: {e}", exc_info=True)
            raise

class MarkdownIngestor(Ingestor):
    """
    Ingestor for Markdown documents.
    """
    
    async def ingest(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text and metadata from a Markdown document.
        
        Args:
            content: Raw Markdown content as bytes
            metadata: Additional metadata about the document
            
        Returns:
            Dictionary containing:
                - text: Extracted text
                - metadata: Enhanced metadata
        """
        try:
            logger.info("Ingesting Markdown document")
            
            # Decode bytes to string
            md_text = content.decode('utf-8')
            
            # Convert to HTML (for metadata extraction)
            html = markdown.markdown(md_text)
            
            # Extract headers
            headers = []
            for line in md_text.split('\n'):
                if line.startswith('#'):
                    # Count the number of # to determine header level
                    level = 0
                    for char in line:
                        if char == '#':
                            level += 1
                        else:
                            break
                    
                    header_text = line[level:].strip()
                    headers.append({
                        "level": level,
                        "text": header_text
                    })
            
            # Enhance metadata
            enhanced_metadata = {
                **metadata,
                "headers": headers,
                "document_type": "markdown"
            }
            
            logger.info(f"Successfully ingested Markdown with {len(headers)} headers")
            
            return {
                "text": md_text,
                "metadata": enhanced_metadata,
                "html": html
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest Markdown: {e}", exc_info=True)
            raise

class ImageIngestor(Ingestor):
    """
    Ingestor for image documents using docling for better OCR.
    """
    
    async def ingest(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text and metadata from an image using docling OCR.
        
        Args:
            content: Raw image content as bytes
            metadata: Additional metadata about the document
            
        Returns:
            Dictionary containing:
                - text: Extracted text
                - metadata: Enhanced metadata
        """
        try:
            logger.info("Ingesting image document with docling OCR")
            
            # Create a file-like object from bytes
            image_file = io.BytesIO(content)
            
            # Use docling for image extraction
            extractor = ImageExtractor()
            doc = extractor.extract(image_file)
            
            # Get text from docling document
            text = doc.text
            
            # Extract image metadata
            image = Image.open(io.BytesIO(content))
            image_metadata = {
                "format": image.format,
                "size": image.size,
                "mode": image.mode
            }
            
            # Enhance metadata
            enhanced_metadata = {
                **metadata,
                "image_metadata": image_metadata,
                "document_type": "image"
            }
            
            logger.info(f"Successfully ingested image with docling OCR, extracted {len(text)} characters")
            
            return {
                "text": text,
                "metadata": enhanced_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest image with docling: {e}", exc_info=True)
            
            # Fallback to pytesseract if docling fails
            logger.info("Falling back to pytesseract for image OCR")
            try:
                # Create a file-like object from bytes
                image_file = io.BytesIO(content)
                
                # Open the image
                image = Image.open(image_file)
                
                # Extract image metadata
                image_metadata = {
                    "format": image.format,
                    "size": image.size,
                    "mode": image.mode
                }
                
                # Perform OCR
                text = pytesseract.image_to_string(image)
                
                # Enhance metadata
                enhanced_metadata = {
                    **metadata,
                    "image_metadata": image_metadata,
                    "document_type": "image"
                }
                
                logger.info(f"Successfully ingested image with pytesseract fallback, extracted {len(text)} characters")
                
                return {
                    "text": text,
                    "metadata": enhanced_metadata
                }
                
            except Exception as fallback_error:
                logger.error(f"Fallback image OCR also failed: {fallback_error}", exc_info=True)
                raise

class TextIngestor(Ingestor):
    """
    Ingestor for plain text documents.
    """
    
    async def ingest(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text and metadata from a plain text document.
        
        Args:
            content: Raw text content as bytes
            metadata: Additional metadata about the document
            
        Returns:
            Dictionary containing:
                - text: Extracted text
                - metadata: Enhanced metadata
        """
        try:
            logger.info("Ingesting plain text document")
            
            # Decode bytes to string
            text = content.decode('utf-8')
            
            # Count lines and words
            lines = text.split('\n')
            words = text.split()
            
            # Enhance metadata
            enhanced_metadata = {
                **metadata,
                "line_count": len(lines),
                "word_count": len(words),
                "document_type": "text"
            }
            
            logger.info(f"Successfully ingested text with {enhanced_metadata['line_count']} lines and {enhanced_metadata['word_count']} words")
            
            return {
                "text": text,
                "metadata": enhanced_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest text: {e}", exc_info=True)
            raise