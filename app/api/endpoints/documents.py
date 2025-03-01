from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import List, Optional
import logging
import base64
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.knowledge_base import DocumentStatus
from app.repositories.document_repository import DocumentRepository
from app.worker.tasks import process_document
from app.api.deps import get_current_user
from app.schemas.document import DocumentCreate, DocumentResponse

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    knowledge_base_id: str = Form(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Upload a document to a knowledge base.
    
    This endpoint:
    1. Reads and validates the uploaded file
    2. Creates a document entry in the database
    3. Triggers a Celery task to process the document
    
    Args:
        file: The document file to upload
        title: Document title
        knowledge_base_id: ID of the knowledge base to add the document to
        description: Optional document description
        
    Returns:
        The created document
    """
    try:
        logger.info(f"Uploading document: {title} to knowledge base: {knowledge_base_id}")
        
        # Read file content
        content = await file.read()
        
        # Encode content as base64
        content_base64 = base64.b64encode(content).decode('utf-8')
        
        # Create document in database
        document_repo = DocumentRepository()
        document_data = DocumentCreate(
            title=title,
            description=description or "",
            content=content_base64,
            content_type=file.content_type,
            knowledge_base_id=knowledge_base_id,
            status=DocumentStatus.PENDING,
            user_id=current_user.id
        )
        
        document = await document_repo.create(document_data)
        logger.info(f"Document created with ID: {document.id}")
        
        # Trigger Celery task to process document
        process_document.delay(document.id)
        logger.info(f"Document processing task triggered for document: {document.id}")
        
        return document
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a document by ID"""
    document_repo = DocumentRepository()
    document = await document_repo.get_by_id(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    knowledge_base_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List documents, optionally filtered by knowledge base"""
    document_repo = DocumentRepository()
    
    if knowledge_base_id:
        documents = await document_repo.get_by_knowledge_base(knowledge_base_id, skip, limit)
    else:
        documents = await document_repo.get_all(skip, limit)
    
    return documents

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete a document.
    
    This endpoint:
    1. Deletes the document from the database
    2. Triggers a Celery task to delete document vectors
    """
    from app.worker.tasks import delete_document_vectors
    
    document_repo = DocumentRepository()
    document = await document_repo.get_by_id(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete document vectors in background
    delete_document_vectors.delay(document_id)
    
    # Delete document from database
    await document_repo.delete(document_id)
    
    return {"message": "Document deleted successfully"} 