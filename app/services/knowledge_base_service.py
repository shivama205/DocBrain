from typing import List, Protocol
from fastapi import HTTPException, UploadFile
import logging
from datetime import datetime
import base64
import os
import aiofiles
from celery import Celery

from app.db.models.knowledge_base import KnowledgeBase, Document, DocumentStatus
from app.db.models.user import User, UserRole
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.repositories.vector_repository import VectorRepository
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.schemas.document import DocumentCreate, DocumentUpdate

# Set up logging
logger = logging.getLogger(__name__)

class FileStorage(Protocol):
    """Protocol for file storage operations"""
    async def save_file(self, file: UploadFile) -> str:
        """Save a file and return its path"""
        ...
    
    def cleanup_file(self, file_path: str) -> None:
        """Clean up a saved file"""
        ...

class LocalFileStorage:
    """Local filesystem implementation of FileStorage"""
    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir
    
    async def save_file(self, file: UploadFile) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(self.upload_dir, safe_filename)
        
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
            
        return file_path
    
    def cleanup_file(self, file_path: str) -> None:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {e}")

class KnowledgeBaseService:
    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        vector_repository: VectorRepository,
        file_storage: FileStorage,
        celery_app: Celery
    ):
        self.repository = repository
        self.vector_repository = vector_repository
        self.file_storage = file_storage
        self.celery_app = celery_app

    async def create_knowledge_base(
        self, 
        kb_data: KnowledgeBaseCreate,
        current_user: User
    ) -> KnowledgeBase:
        """Create a new knowledge base"""
        try:
            knowledge_base = KnowledgeBase(
                name=kb_data.name,
                description=kb_data.description,
                owner_id=current_user.id
            )
            kb = await self.repository.create(knowledge_base)
            logger.info(f"Knowledge base {kb.id} created by user {current_user.id}")
            return kb
        except Exception as e:
            logger.error(f"Failed to create knowledge base: {e}")
            raise HTTPException(status_code=500, detail=str(e))

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
            kb = await self.get_knowledge_base(kb_id, current_user)
            
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
                user_id=current_user.id
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
        return await self.repository.create_document(document)

    async def get_knowledge_base(
        self,
        kb_id: str,
        current_user: User
    ) -> KnowledgeBase:
        """Get knowledge base details"""
        try:
            kb = await self.repository.get_by_id(kb_id)
            if not kb:
                raise HTTPException(status_code=404, detail="Knowledge base not found")
            
            # Check access
            if current_user.role != UserRole.ADMIN and kb.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")
            
            return kb
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get knowledge base {kb_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_document(
        self,
        doc_id: str,
        current_user: User
    ) -> Document:
        """Get document details"""
        try:
            doc = await self.repository.get_document_by_id(doc_id)
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Check access through knowledge base
            await self.get_knowledge_base(doc.knowledge_base_id, current_user)
            
            return doc
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_knowledge_bases(
        self,
        current_user: User
    ) -> List[KnowledgeBase]:
        """List all knowledge bases accessible by user"""
        try:
            if current_user.role == UserRole.ADMIN:
                return await self.repository.list_all()
            else:
                return await self.repository.list_by_owner(current_user.id)
        except Exception as e:
            logger.error(f"Failed to list knowledge bases: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_documents(
        self,
        kb_id: str,
        current_user: User
    ) -> List[Document]:
        """List all documents in a knowledge base"""
        try:
            # Check access
            await self.get_knowledge_base(kb_id, current_user)
            return await self.repository.list_documents_by_kb(kb_id)
        except Exception as e:
            logger.error(f"Failed to list documents for knowledge base {kb_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def update_knowledge_base(
        self,
        kb_id: str,
        kb_data: KnowledgeBaseUpdate,
        current_user: User
    ) -> KnowledgeBase:
        """Update knowledge base"""
        try:
            kb = await self.get_knowledge_base(kb_id, current_user)
            
            if current_user.role != UserRole.ADMIN and kb.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not enough privileges")
            
            update_data = kb_data.model_dump(exclude_unset=True)
            updated_kb = await self.repository.update(kb_id, update_data)
            if not updated_kb:
                raise HTTPException(status_code=404, detail="Knowledge base not found")
            
            logger.info(f"Knowledge base {kb_id} updated by user {current_user.id}")
            return updated_kb
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update knowledge base {kb_id}: {e}")
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
            kb = await self.get_knowledge_base(doc.knowledge_base_id, current_user)
            
            # Only owner or admin can update
            if current_user.role != UserRole.ADMIN and kb.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not enough privileges")
            
            # Update document
            update_data = doc_update.model_dump(exclude_unset=True)
            updated_doc = await self.repository.update_document(doc_id, update_data)
            if not updated_doc:
                raise HTTPException(status_code=404, detail="Document not found")
            
            logger.info(f"Document {doc_id} updated")
            return updated_doc
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_knowledge_base(
        self,
        kb_id: str,
        current_user: User
    ) -> None:
        """Delete a knowledge base and all its documents"""
        try:
            # Check access
            kb = await self.get_knowledge_base(kb_id, current_user)
            
            if current_user.role != UserRole.ADMIN and kb.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not enough privileges")
            
            # Get all documents to delete their vectors
            documents = await self.repository.list_documents_by_kb(kb_id)
            for doc in documents:
                # Queue vector deletion task
                self.celery_app.send_task(
                    'app.worker.tasks.delete_document_vectors',
                    args=[doc.id]
                )
            
            # Delete knowledge base (cascades to documents)
            await self.repository.delete(kb_id)
            logger.info(f"Knowledge base {kb_id} deleted by user {current_user.id}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete knowledge base {kb_id}: {e}")
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
            kb = await self.get_knowledge_base(doc.knowledge_base_id, current_user)
            
            if current_user.role != UserRole.ADMIN and kb.owner_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not enough privileges")
            
            # Queue vector deletion task
            self.celery_app.send_task(
                'app.worker.tasks.delete_document_vectors',
                args=[doc.id]
            )
            
            # Delete document
            await self.repository.delete_document(doc_id)
            logger.info(f"Document {doc_id} deleted by user {current_user.id}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def share_knowledge_base(
        self,
        kb_id: str,
        user_id: str,
        current_user: User
    ) -> None:
        """Share knowledge base with another user"""
        try:
            kb = await self.get_knowledge_base(kb_id, current_user)
            
            if current_user.role != UserRole.ADMIN and kb.owner_id != current_user.id:
                logger.warning(f"User {current_user.id} denied share access to knowledge base {kb_id}")
                raise HTTPException(status_code=403, detail="Access denied")
            
            if user_id not in kb.shared_with:
                kb.shared_with.append(user_id)
                await self.repository.update(kb_id, {"shared_with": kb.shared_with})
                logger.info(f"Knowledge base {kb_id} shared with user {user_id} by {current_user.id}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to share knowledge base {kb_id} with user {user_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e)) 