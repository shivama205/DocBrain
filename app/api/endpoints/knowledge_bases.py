from typing import Annotated, List
from fastapi import APIRouter, Body, Depends, Form, UploadFile, File, Path
from fastapi.responses import JSONResponse
from functools import lru_cache
from sqlalchemy.orm import Session

from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse
)
from app.schemas.document import DocumentUpdate, DocumentResponse, DocumentUpload
from app.api.deps import get_current_user
from app.schemas.user import UserResponse
from app.services.knowledge_base_service import KnowledgeBaseService, LocalFileStorage
from app.services.document_service import DocumentService
from app.repositories.document_repository import DocumentRepository
from app.services.rag.vector_store import VectorStore, get_vector_store
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.core.config import settings
from app.worker.celery import celery_app
from app.db.database import get_db

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
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
):
    """List all knowledge bases accessible to the user"""
    return await kb_service.list_knowledge_bases(current_user)

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

@router.post("/{kb_id}/share/{user_id}")
async def share_knowledge_base(
    kb_id: str,
    user_id: str,
    current_user: UserResponse = Depends(get_current_user),
    kb_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
):
    """Share knowledge base with another user"""
    await kb_service.share_knowledge_base(kb_id, user_id, current_user)
    return JSONResponse(content={"message": "Knowledge base shared successfully"})

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