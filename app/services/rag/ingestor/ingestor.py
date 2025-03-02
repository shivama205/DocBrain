from abc import ABC, abstractmethod
import base64
from typing import Dict, Any
import logging
import io
import os  # Added for environment variables
import multiprocessing
import PyPDF2
import csv
import markdown
from PIL import Image
import pytesseract

# Configure multiprocessing to use 'spawn' instead of 'fork'
# This can help prevent segmentation faults in multiprocessing environments
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    # If already set, this will raise a RuntimeError
    pass

# Disable GPU acceleration to avoid segfaults with MPS on macOS
# This prevents the SIGSEGV (signal 11) crashes that occur when docling tries to use
# the Metal Performance Shaders (MPS) backend on macOS, especially in multiprocessing environments.
# Setting these environment variables forces CPU-only operation which is more stable.
os.environ["DOCLING_DEVICE"] = "cpu"  # Try to force docling to use CPU
os.environ["MPS_VISIBLE_DEVICES"] = ""  # Disable MPS for PyTorch if used
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Disable CUDA if present
os.environ["PYTORCH_MPS_ENABLE_WORKSTREAM_WATCHDOG"] = "0"  # Disable MPS watchdog

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentStream

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
            logger.info("Ingesting PDF document with docling v2")
            
            # Configure pipeline options
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True
            pipeline_options.do_table_structure = True
            pipeline_options.table_structure_options.do_cell_matching = True
            
            # Set up the document converter with PDF format options
            doc_converter = DocumentConverter(
                allowed_formats=[InputFormat.PDF],
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )

            # Convert bytes to DocumentStream
            content_stream = DocumentStream(
                name=metadata.get("title", "temp.pdf"),
                stream=io.BytesIO(content)
            )

            # Convert the PDF content
            conv_result = doc_converter.convert(source=content_stream)
            
            # Get markdown representation
            markdown_text = conv_result.document.export_to_markdown()
            
            # Extract metadata from docling document
            docling_metadata = conv_result.document.metadata.model_dump() if hasattr(conv_result.document, 'metadata') else {}
            
            # Extract text from each page for additional processing if needed
            page_texts = []
            for page in conv_result.document.pages:
                page_text = page.export_to_text() if hasattr(page, 'export_to_text') else ""
                page_texts.append(page_text)
            
            # Combine with provided metadata
            enhanced_metadata = {
                **metadata,
                "page_count": len(conv_result.document.pages),
                "pdf_metadata": docling_metadata,
                "document_type": "pdf"
            }
            
            logger.info(f"Successfully ingested PDF with {len(conv_result.document.pages)} pages using docling v2")
            
            return {
                "text": markdown_text,
                "metadata": enhanced_metadata,
                "page_texts": page_texts
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest PDF with docling v2: {e}", exc_info=True)
            
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
    Ingestor for image documents using docling v2 for better OCR.
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
            logger.info("Ingesting image document with docling v2 OCR")
            
            # Create a file-like object from bytes
            image_file = io.BytesIO(content)
            
            # Set up the document converter with IMAGE format options
            doc_converter = DocumentConverter(
                allowed_formats=[InputFormat.IMAGE]
            )
            
            # Convert the image file
            conv_result = doc_converter.convert(image_file)
            
            # Get text from docling document
            text = conv_result.document.export_to_text()
            
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
            
            logger.info(f"Successfully ingested image with docling v2 OCR, extracted {len(text)} characters")
            
            return {
                "text": text,
                "metadata": enhanced_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest image with docling v2: {e}", exc_info=True)
            
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

class DocxIngestor(Ingestor):
    """
    Ingestor for DOCX documents using docling v2.
    """
    
    async def ingest(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text and metadata from a DOCX document using docling.
        
        Args:
            content: Raw DOCX content as bytes
            metadata: Additional metadata about the document
            
        Returns:
            Dictionary containing:
                - text: Extracted text
                - metadata: Enhanced metadata
        """
        try:
            logger.info("Ingesting DOCX document with docling v2")
            
            # Create a file-like object from bytes
            docx_file = io.BytesIO(content)
            
            # Set up the document converter with DOCX format options
            doc_converter = DocumentConverter(
                allowed_formats=[InputFormat.DOCX]
            )
            
            # Convert the DOCX file
            conv_result = doc_converter.convert(docx_file)
            
            # Get text and markdown representation
            text = conv_result.document.export_to_text()
            markdown_text = conv_result.document.export_to_markdown()
            
            # Extract metadata from docling document
            docling_metadata = conv_result.document.metadata.model_dump() if hasattr(conv_result.document, 'metadata') else {}
            
            # Enhance metadata
            enhanced_metadata = {
                **metadata,
                "docx_metadata": docling_metadata,
                "document_type": "docx"
            }
            
            logger.info(f"Successfully ingested DOCX document using docling v2")
            
            return {
                "text": text,
                "markdown": markdown_text,
                "metadata": enhanced_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest DOCX with docling v2: {e}", exc_info=True)
            raise

class PptxIngestor(Ingestor):
    """
    Ingestor for PPTX documents using docling v2.
    """
    
    async def ingest(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text and metadata from a PPTX document using docling.
        
        Args:
            content: Raw PPTX content as bytes
            metadata: Additional metadata about the document
            
        Returns:
            Dictionary containing:
                - text: Extracted text
                - metadata: Enhanced metadata
        """
        try:
            logger.info("Ingesting PPTX document with docling v2")
            
            # Create a file-like object from bytes
            pptx_file = io.BytesIO(content)
            
            # Set up the document converter with PPTX format options
            doc_converter = DocumentConverter(
                allowed_formats=[InputFormat.PPTX]
            )
            
            # Convert the PPTX file
            conv_result = doc_converter.convert(pptx_file)
            
            # Get text and markdown representation
            text = conv_result.document.export_to_text()
            markdown_text = conv_result.document.export_to_markdown()
            
            # Extract metadata from docling document
            docling_metadata = conv_result.document.metadata.model_dump() if hasattr(conv_result.document, 'metadata') else {}
            
            # Extract slide count if available
            slide_count = len(conv_result.document.pages) if hasattr(conv_result.document, 'pages') else 0
            
            # Enhance metadata
            enhanced_metadata = {
                **metadata,
                "slide_count": slide_count,
                "pptx_metadata": docling_metadata,
                "document_type": "pptx"
            }
            
            logger.info(f"Successfully ingested PPTX document with {slide_count} slides using docling v2")
            
            return {
                "text": text,
                "markdown": markdown_text,
                "metadata": enhanced_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest PPTX with docling v2: {e}", exc_info=True)
            raise

class HTMLIngestor(Ingestor):
    """
    Ingestor for HTML documents using docling v2.
    """
    
    async def ingest(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text and metadata from an HTML document using docling.
        
        Args:
            content: Raw HTML content as bytes
            metadata: Additional metadata about the document
            
        Returns:
            Dictionary containing:
                - text: Extracted text
                - metadata: Enhanced metadata
        """
        try:
            logger.info("Ingesting HTML document with docling v2")
            
            # Create a file-like object from bytes
            html_file = io.BytesIO(content)
            
            # Set up the document converter with HTML format options
            doc_converter = DocumentConverter(
                allowed_formats=[InputFormat.HTML]
            )
            
            # Convert the HTML file
            conv_result = doc_converter.convert(html_file)
            
            # Get text and markdown representation
            text = conv_result.document.export_to_text()
            markdown_text = conv_result.document.export_to_markdown()
            
            # Extract metadata from docling document
            docling_metadata = conv_result.document.metadata.model_dump() if hasattr(conv_result.document, 'metadata') else {}
            
            # Enhance metadata
            enhanced_metadata = {
                **metadata,
                "html_metadata": docling_metadata,
                "document_type": "html"
            }
            
            logger.info(f"Successfully ingested HTML document using docling v2")
            
            return {
                "text": text,
                "markdown": markdown_text,
                "metadata": enhanced_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest HTML with docling v2: {e}", exc_info=True)
            
            # Fallback to simple HTML parsing if docling fails
            logger.info("Falling back to simple HTML parsing")
            try:
                # Decode bytes to string
                html_text = content.decode('utf-8')
                
                # Convert to markdown
                md_text = html_to_markdown(html_text)
                
                # Enhance metadata
                enhanced_metadata = {
                    **metadata,
                    "document_type": "html"
                }
                
                logger.info(f"Successfully ingested HTML with fallback method")
                
                return {
                    "text": md_text,
                    "markdown": md_text,
                    "metadata": enhanced_metadata
                }
                
            except Exception as fallback_error:
                logger.error(f"Fallback HTML ingestion also failed: {fallback_error}", exc_info=True)
                raise

def html_to_markdown(html_text):
    """
    Simple function to convert HTML to markdown.
    This is a fallback method when docling fails.
    """
    # This is a very simple implementation
    # In a real-world scenario, you might want to use a more robust library
    # like html2text or markdownify
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # Extract text
    text = soup.get_text(separator='\n\n')
    
    # Try to preserve some structure
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        level = int(heading.name[1])
        heading_text = heading.get_text().strip()
        heading_md = '#' * level + ' ' + heading_text
        text = text.replace(heading_text, heading_md)
    
    return text

class MultiFormatIngestor(Ingestor):
    """
    Unified ingestor that can handle multiple document formats using docling v2.
    Supports PDF, DOCX, PPTX, HTML, and images.
    """
    
    async def ingest(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text and metadata from a document using docling v2.
        
        Args:
            content: Raw document content as bytes
            metadata: Additional metadata about the document, including 'file_extension'
            
        Returns:
            Dictionary containing:
                - text: Extracted text
                - metadata: Enhanced metadata
        """
        # Determine the input format based on file extension
        file_extension = metadata.get('file_extension', '').lower()
        
        # Map file extensions to docling InputFormat
        format_mapping = {
            'pdf': InputFormat.PDF,
            'docx': InputFormat.DOCX,
            'doc': InputFormat.DOCX,  # Treat .doc as .docx (may not work perfectly)
            'pptx': InputFormat.PPTX,
            'ppt': InputFormat.PPTX,  # Treat .ppt as .pptx (may not work perfectly)
            'html': InputFormat.HTML,
            'htm': InputFormat.HTML,
            'png': InputFormat.IMAGE,
            'jpg': InputFormat.IMAGE,
            'jpeg': InputFormat.IMAGE,
            'gif': InputFormat.IMAGE,
            'bmp': InputFormat.IMAGE,
            'tiff': InputFormat.IMAGE,
            'tif': InputFormat.IMAGE,
        }
        
        input_format = format_mapping.get(file_extension)
        
        if not input_format:
            logger.warning(f"Unsupported file extension: {file_extension}")
            # Fall back to text ingestor for unsupported formats
            text_ingestor = TextIngestor()
            return await text_ingestor.ingest(content, metadata)
        
        try:
            logger.info(f"Ingesting {file_extension.upper()} document with docling v2")
            
            # Create a file-like object from bytes
            file_obj = io.BytesIO(content)
            
            # Configure pipeline options for PDF
            pipeline_options = None
            if input_format == InputFormat.PDF:
                pipeline_options = PdfPipelineOptions()
                pipeline_options.do_ocr = True
                pipeline_options.do_table_structure = True
                pipeline_options.table_structure_options.do_cell_matching = True
            
            # Set up the document converter with appropriate format options
            format_options = {}
            if input_format == InputFormat.PDF and pipeline_options:
                format_options = {
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            
            # Create the document converter
            doc_converter = DocumentConverter(
                allowed_formats=[input_format],
                format_options=format_options
            )
            
            # Convert the file
            conv_result = doc_converter.convert(file_obj)
            
            # Get text and markdown representation
            text = conv_result.document.export_to_text()
            markdown_text = conv_result.document.export_to_markdown()
            
            # Extract metadata from docling document
            docling_metadata = conv_result.document.metadata.model_dump() if hasattr(conv_result.document, 'metadata') else {}
            
            # Extract page/slide count if available
            page_count = len(conv_result.document.pages) if hasattr(conv_result.document, 'pages') else 0
            
            # Extract page texts for PDF
            page_texts = []
            if input_format == InputFormat.PDF and hasattr(conv_result.document, 'pages'):
                for page in conv_result.document.pages:
                    page_text = page.export_to_text() if hasattr(page, 'export_to_text') else ""
                    page_texts.append(page_text)
            
            # Combine with provided metadata
            enhanced_metadata = {
                **metadata,
                "docling_metadata": docling_metadata,
                "document_type": file_extension,
            }
            
            # Add format-specific metadata
            if input_format == InputFormat.PDF:
                enhanced_metadata["page_count"] = page_count
                enhanced_metadata["pdf_metadata"] = docling_metadata
            elif input_format == InputFormat.PPTX:
                enhanced_metadata["slide_count"] = page_count
                enhanced_metadata["pptx_metadata"] = docling_metadata
            elif input_format == InputFormat.DOCX:
                enhanced_metadata["docx_metadata"] = docling_metadata
            elif input_format == InputFormat.HTML:
                enhanced_metadata["html_metadata"] = docling_metadata
            elif input_format == InputFormat.IMAGE:
                # Add image-specific metadata
                try:
                    image = Image.open(io.BytesIO(content))
                    enhanced_metadata["image_metadata"] = {
                        "format": image.format,
                        "size": image.size,
                        "mode": image.mode
                    }
                except Exception as img_error:
                    logger.warning(f"Failed to extract image metadata: {img_error}")
            
            logger.info(f"Successfully ingested {file_extension.upper()} document using docling v2")
            
            result = {
                "text": text,
                "markdown": markdown_text,
                "metadata": enhanced_metadata
            }
            
            # Add page_texts for PDF
            if input_format == InputFormat.PDF:
                result["page_texts"] = page_texts
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to ingest document with docling v2: {e}", exc_info=True)
            
            # Fall back to specific ingestors based on format
            try:
                logger.info(f"Falling back to specific ingestor for {file_extension}")
                
                if input_format == InputFormat.PDF:
                    pdf_ingestor = PDFIngestor()
                    return await pdf_ingestor.ingest(content, metadata)
                elif input_format == InputFormat.IMAGE:
                    image_ingestor = ImageIngestor()
                    return await image_ingestor.ingest(content, metadata)
                elif input_format == InputFormat.HTML:
                    # Use the fallback method directly
                    html_text = content.decode('utf-8')
                    md_text = html_to_markdown(html_text)
                    return {
                        "text": md_text,
                        "markdown": md_text,
                        "metadata": {**metadata, "document_type": "html"}
                    }
                else:
                    # For other formats, fall back to text ingestor
                    text_ingestor = TextIngestor()
                    return await text_ingestor.ingest(content, metadata)
                
            except Exception as fallback_error:
                logger.error(f"Fallback ingestion also failed: {fallback_error}", exc_info=True)
                
                # Last resort: try to extract as plain text
                try:
                    text = content.decode('utf-8', errors='replace')
                    return {
                        "text": text,
                        "metadata": {**metadata, "document_type": "text", "extraction_method": "fallback_text"}
                    }
                except:
                    # If all else fails, return an error
                    raise Exception(f"Failed to ingest document with any available method")