from typing import List
from fastapi import HTTPException, UploadFile
import base64
import logging
import aiofiles
from celery import Celery
from sqlalchemy.orm import Session

from app.db.models.knowledge_base import Document, DocumentStatus
from app.db.models.user import User, UserRole
from app.repositories.document_repository import DocumentRepository
from app.services.rag.vector_store import VectorStore, get_vector_store
from app.services.rag.chunker.chunker import DocumentType
from app.services.knowledge_base_service import KnowledgeBaseService, FileStorage
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate

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
        doc_data: DocumentCreate,
        file: UploadFile,
        current_user: User
    ) -> Document:
        """Create a new document in a knowledge base"""
        file_path = None
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
            
            # Save file temporarily and get content
            file_path = await self.file_storage.save_file(file)
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            # Create document record
            document = await self._create_document_record(
                kb_id=kb_id,
                title=doc_data.title,
                file_name=file.filename,
                content_type=file.content_type,
                content=content,
                user_id=str(current_user.id)
            )
            
            # Queue document processing task
            self.celery_app.send_task(
                'app.worker.tasks.process_document',
                args=[document.id]
            )
            
            return document
            
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if file_path:
                self.file_storage.cleanup_file(file_path)

    async def _create_document_record(
        self,
        kb_id: str,
        title: str,
        file_name: str,
        content_type: str,
        content: bytes,
        user_id: str
    ) -> Document:
        """Create document record with encoded content"""
        content_base64 = base64.b64encode(content).decode('utf-8')
        
        document = Document(
            title=title,
            knowledge_base_id=kb_id,
            file_name=file_name,
            content_type=content_type,
            content=content_base64,
            size_bytes=len(content),
            status=DocumentStatus.PENDING,
            uploaded_by=user_id
        )
        return await self.document_repository.create(document, self.db)

    def _detect_document_type(self, content_type: str) -> DocumentType:
        """Detect document type from content type"""
        content_type = content_type.lower()
        
        if 'pdf' in content_type:
            return DocumentType.PDF_WITH_LAYOUT
        elif any(code_type in content_type for code_type in ['javascript', 'python', 'java', 'typescript']):
            return DocumentType.CODE
        elif content_type in ['text/markdown', 'text/rst']:
            return DocumentType.TECHNICAL_DOCS
        elif 'legal' in content_type or content_type == 'application/contract':
            return DocumentType.LEGAL_DOCS
        else:
            return DocumentType.UNSTRUCTURED_TEXT

    def _get_chunk_size_for_type(self, content_type: str) -> int:
        """Get appropriate chunk size based on document type"""
        doc_type = self._detect_document_type(content_type)
        
        chunk_sizes = {
            DocumentType.UNSTRUCTURED_TEXT: 512,
            DocumentType.TECHNICAL_DOCS: 1024,
            DocumentType.CODE: 300,
            DocumentType.LEGAL_DOCS: 256,
            DocumentType.PDF_WITH_LAYOUT: 512
        }
        
        return chunk_sizes.get(doc_type, 512)

    async def get_document(
        self,
        doc_id: str,
        current_user: User
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
        current_user: User
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
        current_user: User
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
        current_user: User
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