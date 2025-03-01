import asyncio
import logging
import os
import sys
import base64
import uuid
from typing import Dict, Any

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.repositories.document_repository import DocumentRepository
from app.models.knowledge_base import DocumentStatus
from app.worker.tasks import process_document
from app.schemas.document import DocumentCreate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_document_upload_and_processing():
    """
    Test document upload and processing flow.
    
    This test:
    1. Creates a document in the database
    2. Processes the document using the Celery task
    3. Verifies the document status and processed chunks
    """
    try:
        # Create a test document
        document_id = str(uuid.uuid4())
        knowledge_base_id = "test-kb-1"
        user_id = "test-user-1"
        
        # Read a test file
        test_file_path = input("Enter the path to a test file: ")
        if not os.path.exists(test_file_path):
            logger.error(f"File not found: {test_file_path}")
            return
        
        # Determine content type from file extension
        _, ext = os.path.splitext(test_file_path)
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
        with open(test_file_path, 'rb') as f:
            content = f.read()
        
        # Encode content as base64
        content_base64 = base64.b64encode(content).decode('utf-8')
        
        # Create document in database
        document_repo = DocumentRepository()
        document_data = DocumentCreate(
            id=document_id,
            title=os.path.basename(test_file_path),
            description="Test document",
            content=content_base64,
            content_type=content_type,
            knowledge_base_id=knowledge_base_id,
            status=DocumentStatus.PENDING,
            user_id=user_id
        )
        
        document = await document_repo.create(document_data)
        logger.info(f"Document created with ID: {document.id}")
        
        # Process document
        logger.info("Processing document...")
        await process_document(document.id)
        
        # Check document status
        processed_document = await document_repo.get_by_id(document.id)
        logger.info(f"Document status: {processed_document.status}")
        logger.info(f"Processed chunks: {processed_document.processed_chunks}")
        logger.info(f"Summary: {processed_document.summary[:200]}...")
        
        if processed_document.status == DocumentStatus.COMPLETED:
            logger.info("Document processing completed successfully")
        else:
            logger.error(f"Document processing failed: {processed_document.error_message}")
        
    except Exception as e:
        logger.error(f"Error in test: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_document_upload_and_processing()) 