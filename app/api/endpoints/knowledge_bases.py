from typing import Annotated, List
from fastapi import APIRouter, Body, Depends, UploadFile, File, Path, HTTPException
from fastapi.responses import JSONResponse
from functools import lru_cache
from sqlalchemy.orm import Session
import csv
import io

from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseShareRequest,
    KnowledgeBaseUnshareRequest,
    KnowledgeBaseSharingResponse,
    SharedUserInfo
)
from app.schemas.document import DocumentUpdate, DocumentResponse, DocumentUpload
from app.schemas.question import QuestionResponse, QuestionCreate, QuestionUpdate
from app.api.deps import get_current_user
from app.schemas.user import UserResponse
from app.services.knowledge_base_service import KnowledgeBaseService, LocalFileStorage
from app.services.document_service import DocumentService
from app.services.question_service import QuestionService
from app.repositories.document_repository import DocumentRepository
from app.repositories.question_repository import QuestionRepository
from app.services.rag.vector_store import VectorStore, get_vector_store
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.core.config import settings
from app.worker.celery import celery_app
from app.db.database import get_db
from app.core.permissions import check_permission, Permission

import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@lru_cache()
def get_file_storage() -> LocalFileStorage:
    """Get file storage instance"""
    return LocalFileStorage(upload_dir=settings.UPLOAD_DIR)

def get_knowledge_base_repository() -> KnowledgeBaseRepository:
    """Get knowledge base repository instance"""
    return KnowledgeBaseRepository()

def get_document_repository() -> DocumentRepository:
    """Get document repository instance"""
    return DocumentRepository()

def get_question_repository() -> QuestionRepository:
    return QuestionRepository()

def get_knowledge_base_service(
    repository: KnowledgeBaseRepository = Depends(get_knowledge_base_repository),
    vector_store: VectorStore = Depends(lambda: get_vector_store()),
    file_storage: LocalFileStorage = Depends(get_file_storage),
    db: Session = Depends(get_db)
) -> KnowledgeBaseService:
    """Dependency for KnowledgeBaseService"""
    return KnowledgeBaseService(
        repository=repository,
        vector_store=vector_store,
        file_storage=file_storage,
        celery_app=celery_app,
        db=db
    )

def get_document_service(
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service),
    document_repository: DocumentRepository = Depends(get_document_repository),
    vector_store: VectorStore = Depends(lambda: get_vector_store()),
    file_storage: LocalFileStorage = Depends(get_file_storage),
    db: Session = Depends(get_db)
) -> DocumentService:
    """Dependency for DocumentService"""
    return DocumentService(
        document_repository=document_repository,
        vector_store=vector_store,
        knowledge_base_service=kb_service,
        file_storage=file_storage,
        celery_app=celery_app,
        db=db
    )

def get_question_service(
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service),
    question_repository: QuestionRepository = Depends(get_question_repository),
    vector_store: VectorStore = Depends(lambda: get_vector_store()),
    db: Session = Depends(get_db)
) -> QuestionService:
    return QuestionService(
        question_repository=question_repository,
        vector_store=vector_store,
        knowledge_base_service=kb_service,
        celery_app=celery_app,
        db=db
    )

@router.post("", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    kb: KnowledgeBaseCreate = Body(..., description="Knowledge base details"),
    current_user: UserResponse = Depends(get_current_user),
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
):
    """Create a new knowledge base"""
    return await kb_service.create_knowledge_base(kb, current_user)

@router.get("", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    current_user: UserResponse = Depends(get_current_user),
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service),
    _: UserResponse = Depends(check_permission(Permission.VIEW_KNOWLEDGE_BASES))
):
    """
    List knowledge bases based on role:
    - Admin: All knowledge bases
    - Owner: Only knowledge bases owned by the user
    - User: Empty list (users should use shared-with-me endpoint)
    """
    return await kb_service.list_knowledge_bases(current_user)

@router.get("/shared-with-me", response_model=List[KnowledgeBaseResponse])
async def get_shared_knowledge_bases(
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service),
    current_user: UserResponse = Depends(get_current_user),
    _: UserResponse = Depends(check_permission(Permission.VIEW_KNOWLEDGE_BASES))
):
    """Get all knowledge bases shared with the current user"""
    return await kb_service.list_shared_knowledge_bases(current_user)

@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    current_user: UserResponse = Depends(get_current_user),
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
):
    """Get knowledge base details"""
    return await kb_service.get_knowledge_base(kb_id, current_user)

@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    kb_update: KnowledgeBaseUpdate = Body(..., description="Knowledge base details"),
    current_user: UserResponse = Depends(get_current_user),
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
):
    """Update knowledge base"""
    return await kb_service.update_knowledge_base(kb_id, kb_update, current_user)

@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    current_user: UserResponse = Depends(get_current_user),
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
):
    """Delete knowledge base and all its documents"""
    await kb_service.delete_knowledge_base(kb_id, current_user)
    return JSONResponse(content={"message": "Knowledge base deleted successfully"})

@router.post("/{kb_id}/share", response_model=KnowledgeBaseSharingResponse)
async def share_knowledge_base(
    kb_id: str,
    share_data: KnowledgeBaseShareRequest,
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service),
    current_user: UserResponse = Depends(get_current_user),
    _: UserResponse = Depends(check_permission(Permission.UPDATE_KNOWLEDGE_BASE))
):
    """Share a knowledge base with another user"""
    success = await kb_service.share_knowledge_base(kb_id, share_data.user_id, current_user)
    return KnowledgeBaseSharingResponse(
        success=success,
        message="Knowledge base shared successfully" if success else "Failed to share knowledge base"
    )

@router.post("/{kb_id}/unshare", response_model=KnowledgeBaseSharingResponse)
async def unshare_knowledge_base(
    kb_id: str,
    unshare_data: KnowledgeBaseUnshareRequest,
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service),
    current_user: UserResponse = Depends(get_current_user),
    _: UserResponse = Depends(check_permission(Permission.UPDATE_KNOWLEDGE_BASE))
):
    """Remove a user's access to a knowledge base"""
    success = await kb_service.unshare_knowledge_base(kb_id, unshare_data.user_id, current_user)
    return KnowledgeBaseSharingResponse(
        success=success,
        message="Knowledge base access removed successfully" if success else "Failed to remove knowledge base access"
    )

@router.get("/{kb_id}/shared-users", response_model=List[SharedUserInfo])
async def get_shared_users(
    kb_id: str,
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service),
    current_user: UserResponse = Depends(get_current_user),
    _: UserResponse = Depends(check_permission(Permission.VIEW_KNOWLEDGE_BASES))
):
    """Get all users who have access to a knowledge base"""
    return await kb_service.list_shared_users(kb_id, current_user)

@router.post("/{kb_id}/documents", response_model=DocumentResponse)
async def create_document(
    kb_id: str = Path(..., description="Knowledge base ID"),
    file: UploadFile = Annotated[..., File(..., description="Document to upload")],
    current_user: UserResponse = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """Upload a new document to a knowledge base"""
    logger.info(f"Uploading document {file.filename} to knowledge base {kb_id}")
    payload = DocumentUpload(title=file.filename, content=file.file.read(), knowledge_base_id=kb_id, content_type=file.content_type)
    return await doc_service.create_document(kb_id, payload, current_user)

@router.get("/{kb_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    kb_id: str = Path(..., description="Knowledge base ID"),
    current_user: UserResponse = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """List all documents in a knowledge base"""
    return await doc_service.list_documents(kb_id, current_user)

@router.get("/{kb_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    kb_id: str,
    doc_id: str,
    current_user: UserResponse = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """Get document details"""
    return await doc_service.get_document(doc_id, current_user)

@router.put("/{kb_id}/documents/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    doc_update: DocumentUpdate = Body(..., description="Document details"),
    current_user: UserResponse = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """Update document details"""
    return await doc_service.update_document(doc_id, doc_update, current_user)

@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(
    kb_id: str,
    doc_id: str,
    current_user: UserResponse = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """Delete a document"""
    await doc_service.delete_document(doc_id, current_user)
    return JSONResponse(content={"message": "Document deleted successfully"})

@router.post("/{kb_id}/documents/{doc_id}/retry", response_model=DocumentResponse)
async def retry_document(
    kb_id: str = Path(..., description="Knowledge base ID"),
    doc_id: str = Path(..., description="Document ID"),
    current_user: UserResponse = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Retry processing a failed document.
    
    This endpoint allows you to retry processing a document that failed during the initial ingestion.
    It can only be used on documents with a FAILED status.
    """
    return await doc_service.retry_failed_document(kb_id, doc_id, current_user)

# Question endpoints

@router.get("/{kb_id}/questions", response_model=List[QuestionResponse])
async def list_questions(
    kb_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = Depends(get_current_user),
    question_service: QuestionService = Depends(get_question_service)
):
    """List all questions for a knowledge base"""
    return await question_service.list_questions(kb_id, current_user, skip, limit)

@router.get("/{kb_id}/questions/{question_id}", response_model=QuestionResponse)
async def get_question(
    kb_id: str,
    question_id: str,
    current_user: UserResponse = Depends(get_current_user),
    question_service: QuestionService = Depends(get_question_service)
):
    """Get a specific question by ID"""
    return await question_service.get_question(question_id, current_user)

@router.post("/{kb_id}/questions", response_model=QuestionResponse)
async def create_question(
    kb_id: str,
    question: QuestionCreate,
    current_user: UserResponse = Depends(get_current_user),
    question_service: QuestionService = Depends(get_question_service)
):
    """Create a new question in a knowledge base"""
    return await question_service.create_question(kb_id, question, current_user)

@router.put("/{kb_id}/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    kb_id: str,
    question_id: str,
    question_update: QuestionUpdate,
    current_user: UserResponse = Depends(get_current_user),
    question_service: QuestionService = Depends(get_question_service)
):
    """Update a question"""
    return await question_service.update_question(question_id, question_update, current_user)

@router.delete("/{kb_id}/questions/{question_id}")
async def delete_question(
    kb_id: str,
    question_id: str,
    current_user: UserResponse = Depends(get_current_user),
    question_service: QuestionService = Depends(get_question_service)
):
    """Delete a question"""
    await question_service.delete_question(question_id, current_user)
    return {"message": "Question deleted successfully"}

@router.get("/{kb_id}/questions/{question_id}/status")
async def get_question_status(
    kb_id: str,
    question_id: str,
    current_user: UserResponse = Depends(get_current_user),
    question_service: QuestionService = Depends(get_question_service)
):
    """Get the status of a question"""
    return await question_service.get_question_status(question_id, current_user)

@router.post("/{kb_id}/questions/bulk-upload")
async def bulk_upload_questions(
    kb_id: str,
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
    question_service: QuestionService = Depends(get_question_service)
):
    """Bulk upload questions from a CSV file"""
    # Check file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Read CSV file
    contents = await file.read()
    csv_data = contents.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_data))
    
    # Validate required fields
    required_fields = ['question', 'answer', 'answer_type']
    if not all(field in csv_reader.fieldnames for field in required_fields):
        raise HTTPException(
            status_code=400, 
            detail=f"CSV must contain the following columns: {', '.join(required_fields)}"
        )
    
    # Process questions
    results = {
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    for row_idx, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header row
        try:
            # Create question model
            question_data = QuestionCreate(
                question=row['question'].strip(),
                answer=row['answer'].strip(),
                answer_type=row['answer_type'].strip().upper()
            )
            
            # Create question
            await question_service.create_question(kb_id, question_data, current_user)
            results["success"] += 1
            
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Row {row_idx}: {str(e)}")
    
    return results 