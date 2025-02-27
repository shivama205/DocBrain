from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import re
import logging

logger = logging.getLogger(__name__)

class DocumentType(str, Enum):
    UNSTRUCTURED_TEXT = "unstructured_text"
    TECHNICAL_DOCS = "technical_docs"
    CODE = "code"
    LEGAL_DOCS = "legal_docs"
    PDF_WITH_LAYOUT = "pdf_with_layout"

class QueryType(str, Enum):
    FACTOID = "factoid"          # Simple fact-based questions
    COMPARISON = "comparison"    # Comparing things
    EXPLANATION = "explanation"  # How and why questions
    LIST = "list"               # Enumerations
    PROCEDURAL = "procedural"   # Step-by-step instructions
    DEFINITION = "definition"   # What is X?
    CAUSE_EFFECT = "cause_effect"  # What causes X? What are effects of X?
    ANALYSIS = "analysis"       # Deep dive into a topic
    UNKNOWN = "unknown"

class ChunkSize(str, Enum):
    SMALL = "small"    # For precise matching (200-300 tokens)
    MEDIUM = "medium"  # For context-aware matching (500-800 tokens)
    LARGE = "large"    # For broad context (1000-1500 tokens)

class ChunkLevel(BaseModel):
    """Configuration for a single chunking level"""
    size: ChunkSize
    chunk_size: int
    chunk_overlap: int

class ChunkingStrategy(BaseModel):
    """Configuration for multi-level chunking strategy"""
    document_type: DocumentType
    levels: List[ChunkLevel]
    preserve_line_breaks: bool = False
    semantic_headers: bool = True  # Whether to include semantic headers

    @classmethod
    def default_strategy(cls, document_type: DocumentType) -> "ChunkingStrategy":
        """Create default multi-level chunking strategy based on document type"""
        if document_type == DocumentType.CODE:
            levels = [
                ChunkLevel(size=ChunkSize.SMALL, chunk_size=300, chunk_overlap=50),   # Function-level
                ChunkLevel(size=ChunkSize.MEDIUM, chunk_size=600, chunk_overlap=100), # Class-level
                ChunkLevel(size=ChunkSize.LARGE, chunk_size=1000, chunk_overlap=200)  # File-level
            ]
        elif document_type == DocumentType.TECHNICAL_DOCS:
            levels = [
                ChunkLevel(size=ChunkSize.SMALL, chunk_size=250, chunk_overlap=50),   # Paragraph-level
                ChunkLevel(size=ChunkSize.MEDIUM, chunk_size=750, chunk_overlap=150), # Section-level
                ChunkLevel(size=ChunkSize.LARGE, chunk_size=1500, chunk_overlap=300)  # Chapter-level
            ]
        else:
            levels = [
                ChunkLevel(size=ChunkSize.SMALL, chunk_size=300, chunk_overlap=50),   # Sentence-level
                ChunkLevel(size=ChunkSize.MEDIUM, chunk_size=600, chunk_overlap=100), # Paragraph-level
                ChunkLevel(size=ChunkSize.LARGE, chunk_size=1000, chunk_overlap=200)  # Multi-paragraph
            ]
        
        return cls(document_type=document_type, levels=levels)

class ChunkMetadata(BaseModel):
    """Enhanced metadata for all chunk types"""
    document_id: str
    document_title: str
    chunk_index: int
    total_chunks: int
    content_type: str
    word_count: int
    title: str
    section_path: List[str]  # Hierarchy of section headers
    nearest_header: str
    document_type: DocumentType
    chunk_size: ChunkSize

def _count_words(text: str) -> int:
    """Simple word count"""
    return len(text.split())

def _split_text(text: str, strategy: ChunkingStrategy) -> List[str]:
    """Split text based on document type"""
    if strategy.document_type == DocumentType.CODE:
        return _split_code(text)
    elif strategy.document_type == DocumentType.TECHNICAL_DOCS:
        return _split_markdown(text)
    else:
        return _split_sentences(text)

def _split_sentences(text: str) -> List[str]:
    """Split text into sentences"""
    # Split on sentence boundaries while preserving punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def _split_markdown(text: str) -> List[str]:
    """Split markdown text into sections"""
    # Split on headers and code blocks
    sections = []
    current_section = []
    
    for line in text.split('\n'):
        if line.startswith('#') or line.startswith('```'):
            if current_section:
                sections.append('\n'.join(current_section))
                current_section = []
        current_section.append(line)
    
    if current_section:
        sections.append('\n'.join(current_section))
    
    return sections

def _split_code(text: str) -> List[str]:
    """Split code into logical blocks"""
    # Split on class and function definitions
    blocks = []
    current_block = []
    
    for line in text.split('\n'):
        if (line.startswith('class ') or 
            line.startswith('def ') or 
            line.startswith('async def ')):
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
        current_block.append(line)
    
    if current_block:
        blocks.append('\n'.join(current_block))
    
    return blocks

def _merge_small_chunks(chunks: List[str], min_size: int = 100) -> List[str]:
    """Merge small chunks with neighbors"""
    if not chunks:
        return []
        
    result = []
    current_chunk = chunks[0]
    
    for chunk in chunks[1:]:
        if len(current_chunk) < min_size:
            current_chunk += " " + chunk
        else:
            result.append(current_chunk)
            current_chunk = chunk
    
    result.append(current_chunk)
    return result

def _extract_semantic_headers(text: str, document_type: DocumentType) -> List[Dict[str, Any]]:
    """Extract semantic headers and their positions from text"""
    headers = []
    current_position = 0
    
    if document_type == DocumentType.TECHNICAL_DOCS:
        # Process markdown-style headers
        lines = text.split('\n')
        current_section_level = 0
        
        for i, line in enumerate(lines):
            if line.startswith('#'):
                # Count header level
                level = len(line.strip().split()[0])
                header_text = line.lstrip('#').strip()
                
                headers.append({
                    'text': header_text,
                    'level': level,
                    'position': current_position,
                    'line_number': i
                })
            current_position += len(line) + 1  # +1 for newline
            
    elif document_type == DocumentType.CODE:
        # Process code structure (class/function definitions)
        lines = text.split('\n')
        current_indent = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('class ', 'def ', 'async def ')):
                # Calculate indentation level
                indent = len(line) - len(stripped)
                level = indent // 4  # Assuming 4 spaces per indent level
                
                # Extract class/function name
                name = stripped.split()[1].split('(')[0]
                
                headers.append({
                    'text': name,
                    'level': level,
                    'position': current_position,
                    'line_number': i
                })
            current_position += len(line) + 1
            
    return headers

def _get_chunk_metadata(
    chunk_start: int,
    chunk_end: int,
    headers: List[Dict[str, Any]],
    document_title: str,
    document_type: DocumentType,
    chunk_size: ChunkSize
) -> Dict[str, Any]:
    """Get metadata about chunk's location in document hierarchy"""
    # Find headers that appear before this chunk
    relevant_headers = [h for h in headers if h['position'] <= chunk_start]
    
    # Default metadata
    metadata = {
        'title': document_title,
        'section_path': [],
        'nearest_header': "",
        'document_type': document_type,
        'chunk_size': chunk_size
    }
    
    if relevant_headers:
        # Get nearest header (most recent one before chunk)
        metadata['nearest_header'] = relevant_headers[-1]['text']
        
        # Build section path from header hierarchy
        current_level = relevant_headers[-1]['level']
        section_path = []
        for header in reversed(relevant_headers[:-1]):
            if header['level'] < current_level:
                section_path.insert(0, header['text'])
                current_level = header['level']
        metadata['section_path'] = section_path
    
    return metadata

async def chunk_document(
    content: str,
    document_id: str,
    document_title: str,
    strategy: ChunkingStrategy
) -> List[dict]:
    """Chunk document based on type and strategy"""
    try:
        # Extract semantic headers
        headers = _extract_semantic_headers(content, strategy.document_type)
        
        # Split content based on document type
        raw_chunks = _split_text(content, strategy)
        
        # Merge small chunks
        chunks = _merge_small_chunks(raw_chunks)
        
        # Create chunk records
        chunk_records = []
        total_chunks = len(chunks)
        current_pos = 0
        
        for i, chunk_content in enumerate(chunks):
            chunk_size = len(chunk_content)
            
            # Get chunk metadata
            metadata_dict = _get_chunk_metadata(
                current_pos,
                current_pos + chunk_size,
                headers,
                document_title,
                strategy.document_type,
                ChunkSize.MEDIUM  # Default to MEDIUM for single-level chunking
            )
            
            # Create chunk metadata
            metadata = ChunkMetadata(
                document_id=document_id,
                document_title=document_title,
                chunk_index=i,
                total_chunks=total_chunks,
                content_type=strategy.document_type,
                word_count=_count_words(chunk_content),
                **metadata_dict  # Unpack all metadata fields
            )
            
            # Create chunk record
            chunk_records.append({
                'content': chunk_content,
                'metadata': metadata.model_dump()
            })
            
            current_pos += chunk_size
        
        return chunk_records
        
    except Exception as e:
        logger.error(f"Failed to chunk document {document_id}: {e}")
        raise

async def chunk_document_multi_level(
    content: str,
    document_id: str,
    document_title: str,
    strategy: ChunkingStrategy
) -> List[Dict[str, Any]]:
    """Chunk document into multiple levels with metadata."""
    try:
        # Extract headers for document structure
        headers = _extract_semantic_headers(content, strategy.document_type)
        all_chunks = []
        
        # Process each chunking level
        for level in strategy.levels:
            current_pos = 0
            current_chunks = []
            remaining_text = content
            
            while remaining_text:
                # Calculate chunk boundaries
                chunk_end = min(level.chunk_size, len(remaining_text))
                if chunk_end < len(remaining_text):
                    # Try to break at a natural boundary
                    for i in range(min(50, chunk_end), 0, -1):
                        if remaining_text[chunk_end - i] in '.!?\n':
                            chunk_end = chunk_end - i + 1
                            break
                
                chunk_content = remaining_text[:chunk_end]
                
                # Get chunk metadata
                metadata_dict = _get_chunk_metadata(
                    current_pos,
                    current_pos + len(chunk_content),
                    headers,
                    document_title,
                    strategy.document_type,
                    level.size
                )
                
                # Create chunk metadata
                metadata = ChunkMetadata(
                    document_id=document_id,
                    document_title=document_title,
                    chunk_index=len(current_chunks),
                    total_chunks=-1,  # Will update after all chunks are created
                    content_type=strategy.document_type,
                    word_count=_count_words(chunk_content),
                    **metadata_dict  # Unpack all metadata fields
                )
                
                # Create chunk record
                current_chunks.append({
                    'content': chunk_content,
                    'metadata': metadata.model_dump()
                })
                
                # Move position and handle overlap
                current_pos += len(chunk_content)
                overlap_size = min(level.chunk_overlap, len(remaining_text) - chunk_end)
                remaining_text = remaining_text[chunk_end - overlap_size:]
            
            # Update total_chunks in metadata
            for chunk in current_chunks:
                chunk['metadata']['total_chunks'] = len(current_chunks)
            
            all_chunks.extend(current_chunks)
        
        return all_chunks
        
    except Exception as e:
        logger.error(f"Failed to chunk document {document_id}: {e}")
        raise 