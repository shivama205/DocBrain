from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)

class ChunkSize(str, Enum):
    """Enum for chunk sizes"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class DocumentType(str, Enum):
    """Enum for document types"""
    UNSTRUCTURED_TEXT = "unstructured_text"
    STRUCTURED_TEXT = "structured_text"
    CODE = "code"
    LEGAL_DOCS = "legal_docs"
    SCIENTIFIC = "scientific"
    TECHNICAL = "technical"

class Chunker(ABC):
    """
    Abstract base class for chunkers that split documents into chunks.
    """
    
    @abstractmethod
    async def chunk(
        self,
        text: str,
        metadata: Dict[str, Any],
        chunk_size: ChunkSize = ChunkSize.MEDIUM
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks with metadata.
        
        Args:
            text: The text to chunk
            metadata: Metadata about the document
            chunk_size: Size of chunks to create
            
        Returns:
            List of dictionaries containing:
                - content: The chunk text
                - metadata: Enhanced metadata for the chunk
        """
        pass

class SingleChunker(Chunker):
    """
    Simple chunker that splits text into chunks of roughly equal size.
    """
    
    async def chunk(
        self,
        text: str,
        metadata: Dict[str, Any],
        chunk_size: ChunkSize = ChunkSize.MEDIUM
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks of roughly equal size.
        
        Args:
            text: The text to chunk
            metadata: Metadata about the document
            chunk_size: Size of chunks to create
            
        Returns:
            List of dictionaries containing:
                - content: The chunk text
                - metadata: Enhanced metadata for the chunk
        """
        try:
            logger.info(f"Chunking text with SingleChunker, chunk_size={chunk_size}")
            
            # Determine chunk size in characters
            size_map = {
                ChunkSize.SMALL: 1000,
                ChunkSize.MEDIUM: 2000,
                ChunkSize.LARGE: 4000
            }
            target_size = size_map.get(chunk_size, 2000)
            
            # Split text into paragraphs
            paragraphs = re.split(r'\n\s*\n', text)
            
            # Create chunks
            chunks = []
            current_chunk = ""
            current_size = 0
            chunk_index = 0
            
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                
                # If adding this paragraph would exceed the target size, start a new chunk
                if current_size + len(paragraph) > target_size and current_chunk:
                    # Create chunk
                    chunk_metadata = {
                        **metadata,
                        "chunk_index": chunk_index,
                        "chunk_size": chunk_size,
                        "nearest_header": "",
                        "section_path": []
                    }
                    
                    chunks.append({
                        "content": current_chunk.strip(),
                        "metadata": chunk_metadata
                    })
                    
                    # Reset for next chunk
                    current_chunk = ""
                    current_size = 0
                    chunk_index += 1
                
                # Add paragraph to current chunk
                current_chunk += paragraph + "\n\n"
                current_size += len(paragraph)
            
            # Add the last chunk if it's not empty
            if current_chunk:
                chunk_metadata = {
                    **metadata,
                    "chunk_index": chunk_index,
                    "chunk_size": chunk_size,
                    "nearest_header": "",
                    "section_path": []
                }
                
                chunks.append({
                    "content": current_chunk.strip(),
                    "metadata": chunk_metadata
                })
            
            logger.info(f"Created {len(chunks)} chunks with SingleChunker")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to chunk text with SingleChunker: {e}", exc_info=True)
            raise

class MultiLevelChunker(Chunker):
    """
    Advanced chunker that splits text into chunks based on document structure.
    Preserves section hierarchy and headers in metadata.
    """
    
    async def chunk(
        self,
        text: str,
        metadata: Dict[str, Any],
        chunk_size: ChunkSize = ChunkSize.MEDIUM
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks based on document structure.
        
        Args:
            text: The text to chunk
            metadata: Metadata about the document
            chunk_size: Size of chunks to create
            
        Returns:
            List of dictionaries containing:
                - content: The chunk text
                - metadata: Enhanced metadata for the chunk
        """
        try:
            logger.info(f"Chunking text with MultiLevelChunker, chunk_size={chunk_size}")
            
            # Determine chunk size in characters
            size_map = {
                ChunkSize.SMALL: 1000,
                ChunkSize.MEDIUM: 2000,
                ChunkSize.LARGE: 4000
            }
            target_size = size_map.get(chunk_size, 2000)
            
            # Extract headers and sections
            sections = self._extract_sections(text)
            
            # Create chunks
            chunks = []
            chunk_index = 0
            
            for section in sections:
                section_text = section["text"]
                section_path = section["path"]
                section_header = section["header"]
                
                # Skip empty sections
                if not section_text.strip():
                    continue
                
                # Split section into paragraphs
                paragraphs = re.split(r'\n\s*\n', section_text)
                
                # Create chunks from paragraphs
                current_chunk = ""
                current_size = 0
                
                for paragraph in paragraphs:
                    paragraph = paragraph.strip()
                    if not paragraph:
                        continue
                    
                    # If adding this paragraph would exceed the target size, start a new chunk
                    if current_size + len(paragraph) > target_size and current_chunk:
                        # Create chunk
                        chunk_metadata = {
                            **metadata,
                            "chunk_index": chunk_index,
                            "chunk_size": chunk_size,
                            "nearest_header": section_header,
                            "section_path": section_path
                        }
                        
                        chunks.append({
                            "content": current_chunk.strip(),
                            "metadata": chunk_metadata
                        })
                        
                        # Reset for next chunk
                        current_chunk = ""
                        current_size = 0
                        chunk_index += 1
                    
                    # Add paragraph to current chunk
                    current_chunk += paragraph + "\n\n"
                    current_size += len(paragraph)
                
                # Add the last chunk if it's not empty
                if current_chunk:
                    chunk_metadata = {
                        **metadata,
                        "chunk_index": chunk_index,
                        "chunk_size": chunk_size,
                        "nearest_header": section_header,
                        "section_path": section_path
                    }
                    
                    chunks.append({
                        "content": current_chunk.strip(),
                        "metadata": chunk_metadata
                    })
                    
                    chunk_index += 1
            
            logger.info(f"Created {len(chunks)} chunks with MultiLevelChunker")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to chunk text with MultiLevelChunker: {e}", exc_info=True)
            raise
    
    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract sections and headers from text.
        
        Args:
            text: The text to extract sections from
            
        Returns:
            List of dictionaries containing:
                - header: The section header
                - text: The section text
                - path: The section path (list of parent headers)
        """
        # Split text into lines
        lines = text.split('\n')
        
        # Find headers (lines starting with #)
        headers = []
        for i, line in enumerate(lines):
            if re.match(r'^#+\s', line):
                level = len(re.match(r'^#+', line).group(0))
                header_text = line.lstrip('#').strip()
                headers.append({
                    "level": level,
                    "text": header_text,
                    "line": i
                })
        
        # If no headers found, return the entire text as one section
        if not headers:
            return [{
                "header": "",
                "text": text,
                "path": []
            }]
        
        # Extract sections
        sections = []
        for i, header in enumerate(headers):
            # Determine section start and end
            start_line = header["line"] + 1
            end_line = len(lines)
            
            if i < len(headers) - 1:
                end_line = headers[i + 1]["line"]
            
            # Extract section text
            section_text = '\n'.join(lines[start_line:end_line])
            
            # Determine section path
            path = []
            for prev_header in headers[:i]:
                if prev_header["level"] < header["level"]:
                    path.append(prev_header["text"])
            
            sections.append({
                "header": header["text"],
                "text": section_text,
                "path": path
            })
        
        return sections 