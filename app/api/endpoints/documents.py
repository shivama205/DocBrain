from fastapi import APIRouter, Body, Depends, UploadFile, File, Form
import logging
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.user import UserResponse
from app.services.document_service import DocumentService
from app.services.knowledge_base_service import KnowledgeBaseService, LocalFileStorage
from app.repositories.document_repository import DocumentRepository
from app.services.rag.vector_store import VectorStore, get_vector_store
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.worker.celery import celery_app
from app.api.deps import get_current_user
from app.schemas.document import DocumentResponse, DocumentUpdate, DocumentUpload
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependencies
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
    vector_store: VectorStore = Depends(get_vector_store),
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
    vector_store: VectorStore = Depends(get_vector_store),
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

# @router.post("/upload", response_model=DocumentResponse)
# async def upload_document(
#     file: UploadFile = File(...),
#     knowledge_base_id: str = Form(...),
#     current_user: UserResponse = Depends(get_current_user),
#     doc_service: DocumentService = Depends(get_document_service)
# ):
#     """
#     Upload a document to a knowledge base.
    
#     This endpoint:
#     1. Reads and validates the uploaded file
#     2. Creates a document entry in the database
#     3. Triggers a Celery task to process the document
#     """
#     payload = DocumentUpload(title=file.filename, content=file.file.read(), knowledge_base_id=knowledge_base_id, content_type=file.content_type)
#     return await doc_service.create_document(knowledge_base_id, payload, current_user)

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Get document details by ID.
    """
    return await doc_service.get_document(document_id, current_user)

# @router.get("/", response_model=List[DocumentResponse])
# async def list_documents(
#     knowledge_base_id: str,
#     current_user: User = Depends(get_current_user),
#     doc_service: DocumentService = Depends(get_document_service)
# ):
#     """
#     List all documents in a knowledge base.
#     """
#     return await doc_service.list_documents(knowledge_base_id, current_user)

@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    doc_update: DocumentUpdate = Body(..., description="Document details"),
    current_user: UserResponse = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Update document details.
    """
    return await doc_service.update_document(document_id, doc_update, current_user)

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Delete a document.
    """
    await doc_service.delete_document(document_id, current_user)
    return {"message": "Document deleted successfully"} 