import asyncio
import logging
import os
import sys
from typing import Dict, Any

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.ingestor import PDFIngestor, ImageIngestor
from app.services.chunker import ChunkSize, MultiLevelChunker
from app.services.rag_service import RAGService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_pdf_ingestor(file_path: str) -> Dict[str, Any]:
    """
    Test the PDF ingestor with docling.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Result of ingestion
    """
    logger.info(f"Testing PDF ingestor with file: {file_path}")
    
    # Read file content
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Create ingestor
    ingestor = PDFIngestor()
    
    # Ingest document
    metadata = {
        "document_id": "test-doc-1",
        "title": os.path.basename(file_path),
        "document_type": "pdf"
    }
    
    result = await ingestor.ingest(content, metadata)
    
    # Print the first 500 characters of the extracted text
    logger.info(f"Extracted text (first 500 chars): {result['text'][:500]}...")
    logger.info(f"Metadata: {result['metadata']}")
    
    return result

async def test_image_ingestor(file_path: str) -> Dict[str, Any]:
    """
    Test the image ingestor with docling OCR.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Result of ingestion
    """
    logger.info(f"Testing image ingestor with file: {file_path}")
    
    # Read file content
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Create ingestor
    ingestor = ImageIngestor()
    
    # Ingest document
    metadata = {
        "document_id": "test-img-1",
        "title": os.path.basename(file_path),
        "document_type": "image"
    }
    
    result = await ingestor.ingest(content, metadata)
    
    # Print the extracted text
    logger.info(f"Extracted text: {result['text']}")
    logger.info(f"Metadata: {result['metadata']}")
    
    return result

async def test_chunking(text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test the chunking process.
    
    Args:
        text: Text to chunk
        metadata: Document metadata
        
    Returns:
        Result of chunking
    """
    logger.info("Testing chunking process")
    
    # Create chunker
    chunker = MultiLevelChunker()
    
    # Chunk text
    chunks = await chunker.chunk(text, metadata, ChunkSize.MEDIUM)
    
    # Print information about chunks
    logger.info(f"Created {len(chunks)} chunks")
    for i, chunk in enumerate(chunks[:3]):  # Print first 3 chunks
        logger.info(f"Chunk {i+1}:")
        logger.info(f"  Content (first 100 chars): {chunk['content'][:100]}...")
        logger.info(f"  Metadata: {chunk['metadata']}")
    
    return {"chunks": chunks}

async def test_full_rag_pipeline(file_path: str) -> Dict[str, Any]:
    """
    Test the full RAG pipeline.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Result of the RAG pipeline
    """
    logger.info(f"Testing full RAG pipeline with file: {file_path}")
    
    # Determine content type from file extension
    _, ext = os.path.splitext(file_path)
    content_type = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.csv': 'text/csv',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png'
    }.get(ext.lower(), 'text/plain')
    
    # Read file content
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Create RAG service
    knowledge_base_id = "test-kb-1"
    rag_service = RAGService(
        knowledge_base_id=knowledge_base_id,
        use_reranker=True
    )
    
    # Prepare metadata
    metadata = {
        "document_id": "test-doc-1",
        "title": os.path.basename(file_path),
        "document_type": "structured_text",
        "knowledge_base_id": knowledge_base_id
    }
    
    # Ingest document
    ingest_result = await rag_service.ingest_document(
        content=content,
        metadata=metadata,
        content_type=content_type,
        chunk_size=ChunkSize.MEDIUM
    )
    
    logger.info(f"Ingestion result: {ingest_result}")
    
    # Test query
    query = "What is the main topic of the document?"
    query_result = await rag_service.retrieve(
        query=query,
        top_k=5,
        similarity_threshold=0.3,
        rerank=True
    )
    
    # Print the answer
    logger.info(f"Query: {query}")
    logger.info(f"Answer: {query_result['answer']}")
    logger.info(f"Sources: {len(query_result['sources'])}")
    
    return {
        "ingest_result": ingest_result,
        "query_result": query_result
    }

async def main():
    """Main function to run tests"""
    try:
        # Get file path from command line argument or use default
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
        else:
            # Default test file path
            file_path = input("Enter the path to a PDF or image file to test: ")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return
        
        # Determine file type
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext in ['.pdf']:
            # Test PDF ingestor
            pdf_result = await test_pdf_ingestor(file_path)
            
            # Test chunking with the extracted text
            chunk_result = await test_chunking(pdf_result['text'], pdf_result['metadata'])
            
            # Test full RAG pipeline
            rag_result = await test_full_rag_pipeline(file_path)
            
        elif ext in ['.jpg', '.jpeg', '.png']:
            # Test image ingestor
            img_result = await test_image_ingestor(file_path)
            
            # Test chunking with the extracted text
            chunk_result = await test_chunking(img_result['text'], img_result['metadata'])
            
            # Test full RAG pipeline
            rag_result = await test_full_rag_pipeline(file_path)
            
        else:
            logger.error(f"Unsupported file type: {ext}")
            return
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 