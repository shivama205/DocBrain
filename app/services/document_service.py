from typing import List
from fastapi import HTTPException
import base64
import logging
import aiofiles
from celery import Celery
from sqlalchemy.orm import Session

from app.db.models.knowledge_base import Document, DocumentStatus, DocumentType
from app.db.models.user import UserRole
from app.repositories.document_repository import DocumentRepository
from app.schemas.user import UserResponse
from app.services.rag.vector_store import VectorStore
from app.services.knowledge_base_service import KnowledgeBaseService, FileStorage
from app.schemas.document import DocumentResponse, DocumentUpdate, DocumentUpload

# Set up logging
logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_store: VectorStore,
        knowledge_base_service: KnowledgeBaseService,
        file_storage: FileStorage,
        celery_app: Celery,
        db: Session
    ):
        self.document_repository = document_repository
        self.vector_store = vector_store
        self.kb_service = knowledge_base_service
        self.file_storage = file_storage
        self.celery_app = celery_app
        self.db = db

    async def create_document(
        self,
        kb_id: str,
        payload: DocumentUpload,
        current_user: UserResponse
    ) -> DocumentResponse:
        """Create a new document in a knowledge base"""
        # file_path = None
        try:
            # Check knowledge base access
            await self.kb_service.get_knowledge_base(kb_id, current_user)
            
            # Check the number of documents in the knowledge base
            existing_docs = await self.document_repository.list_by_knowledge_base(kb_id, self.db)
            if len(existing_docs) >= 20:
                raise HTTPException(
                    status_code=400,
                    detail="Maximum number of documents (20) reached for this knowledge base"
                )
            
            # # Save file temporarily and get content
            # file_path = await self.file_storage.save_file(payload.title)
            # async with aiofiles.open(file_path, 'rb') as f:
            #     content = await f.read()
            
            # Create document record
            document = await self._create_document_record(
                kb_id=kb_id,
                title=payload.title,
                content_type=self._detect_document_type(payload.content_type),
                content=payload.content,
                user_id=str(current_user.id)
            )
            
            # Queue document processing task
            self.celery_app.send_task(
                'app.worker.tasks.initiate_document_ingestion',
                args=[document.id]
            )
            
            return document
            
        except Exception as e:
            logger.error(f"Failed to create document in service: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        # finally:
        #     if file_path:
        #         self.file_storage.cleanup_file(file_path)

    def _detect_document_type(self, content_type: str) -> DocumentType:
        """Detect document type from content type"""
        content_type = content_type.lower()
        if 'pdf' in content_type:
            return DocumentType.PDF
        if 'image/jpg' in content_type or 'image/jpeg' in content_type:
            return DocumentType.JPG
        if 'image/png' in content_type:
            return DocumentType.PNG
        if 'image/gif' in content_type:
            return DocumentType.GIF
        if 'image/tiff' in content_type:
            return DocumentType.TIFF
        if 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
            return DocumentType.DOCX
        if 'application/msword' in content_type:
            return DocumentType.DOC
        if 'text/plain' in content_type:
            return DocumentType.TXT
        return DocumentType.TXT

    async def _create_document_record(
        self,
        kb_id: str,
        title: str,
        content_type: str,
        content: bytes,
        user_id: str
    ) -> DocumentResponse:
        """Create document record with encoded content"""
        # content_base64 = base64.b64encode(content).decode('utf-8')
        
        document = Document(
            title=title,
            knowledge_base_id=kb_id,
            content_type=content_type,
            content=content,
            size_bytes=len(content),
            user_id=user_id,
            status=DocumentStatus.PENDING
        )
        logger.info(f"Creating document record: {document}")
        return await self.document_repository.create(document, self.db)

    async def get_document(
        self,
        doc_id: str,
        current_user: UserResponse
    ) -> Document:
        """Get document details"""
        try:
            doc = await self.document_repository.get_by_id(doc_id, self.db)
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Check access through knowledge base
            await self.kb_service.get_knowledge_base(doc.knowledge_base_id, current_user)
            
            return doc
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_documents(
        self,
        kb_id: str,
        current_user: UserResponse
    ) -> List[DocumentResponse]:
        """List all documents in a knowledge base"""
        try:
            # Check access
            await self.kb_service.get_knowledge_base(kb_id, current_user)
            return await self.document_repository.list_by_knowledge_base(kb_id, self.db)
        except Exception as e:
            logger.error(f"Failed to list documents for knowledge base {kb_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def update_document(
        self,
        doc_id: str,
        doc_update: DocumentUpdate,
        current_user: UserResponse
    ) -> Document:
        """Update document metadata"""
        try:
            # Get document and check access
            doc = await self.get_document(doc_id, current_user)
            kb = await self.kb_service.get_knowledge_base(doc.knowledge_base_id, current_user)
            
            # Only owner or admin can update
            if current_user.role != UserRole.ADMIN and str(kb.owner_id) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Not enough privileges")
            
            # Update document
            update_data = doc_update.model_dump(exclude_unset=True)
            updated_doc = await self.document_repository.update(doc_id, update_data, self.db)
            if not updated_doc:
                raise HTTPException(status_code=404, detail="Document not found")
            
            logger.info(f"Document {doc_id} updated")
            return updated_doc
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_document(
        self,
        doc_id: str,
        current_user: UserResponse
    ) -> None:
        """Delete a document from a knowledge base"""
        try:
            # Get document and check access
            doc = await self.get_document(doc_id, current_user)
            kb = await self.kb_service.get_knowledge_base(doc.knowledge_base_id, current_user)
            
            if current_user.role != UserRole.ADMIN and str(kb.owner_id) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Not enough privileges")
            
            # Queue vector deletion task
            self.celery_app.send_task(
                'app.worker.tasks.delete_document_vectors',
                args=[doc.id, str(doc.knowledge_base_id)]
            )
            
            # Delete document
            await self.document_repository.delete(doc_id, self.db)
            logger.info(f"Document {doc_id} deleted by user {current_user.id}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e)) 