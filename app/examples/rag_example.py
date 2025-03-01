import asyncio
import logging
import base64
import os
import sys
from typing import Dict, Any

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.rag_service import RAGService
from app.services.chunker import ChunkSize

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def ingest_document(rag_service: RAGService, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingest a document into the RAG service.
    
    Args:
        rag_service: The RAG service instance
        file_path: Path to the document file
        metadata: Document metadata
        
    Returns:
        Result of ingestion
    """
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
    
    # Ingest document
    result = await rag_service.ingest_document(
        content=content,
        metadata=metadata,
        content_type=content_type,
        chunk_size=ChunkSize.MEDIUM
    )
    
    return result

async def query_rag(rag_service: RAGService, query: str) -> Dict[str, Any]:
    """
    Query the RAG service.
    
    Args:
        rag_service: The RAG service instance
        query: The query to process
        
    Returns:
        Result of the query
    """
    # Process query
    result = await rag_service.retrieve(
        query=query,
        top_k=5,
        similarity_threshold=0.3,
        rerank=True
    )
    
    return result

async def main():
    """Main function to demonstrate RAG service usage"""
    try:
        # Initialize RAG service
        knowledge_base_id = "example-kb-1"
        rag_service = RAGService(
            knowledge_base_id=knowledge_base_id,
            use_reranker=True
        )
        
        # Example document metadata
        document_metadata = {
            "document_id": "doc-1",
            "title": "Example Document",
            "author": "John Doe",
            "document_type": "structured_text"
        }
        
        # Ingest a document (uncomment to run)
        # result = await ingest_document(
        #     rag_service=rag_service,
        #     file_path="path/to/your/document.pdf",
        #     metadata=document_metadata
        # )
        # logger.info(f"Ingestion result: {result}")
        
        # Query the RAG service
        query = "What is the main topic of the document?"
        result = await query_rag(rag_service, query)
        
        # Print the answer
        print("\n" + "="*50)
        print("QUERY:", query)
        print("="*50)
        print("ANSWER:", result["answer"])
        print("="*50)
        print("SOURCES:")
        for i, source in enumerate(result["sources"], 1):
            print(f"Source {i}:")
            print(f"  Document: {source['title']} (ID: {source['document_id']})")
            print(f"  Score: {source['score']:.3f}")
            print(f"  Content: {source['content'][:200]}...")
            print()
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())