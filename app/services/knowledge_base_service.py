from typing import List, Protocol
from fastapi import HTTPException, UploadFile
import logging
from datetime import datetime
import base64
import os
import aiofiles
from celery import Celery
from sqlalchemy.orm import Session

from app.db.models.knowledge_base import KnowledgeBase, Document, DocumentStatus
from app.db.models.user import User, UserRole
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.services.rag.vector_store import VectorStore, get_vector_store
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
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
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
    """Service for knowledge base operations"""
    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        vector_store: VectorStore,
        file_storage: FileStorage,
        celery_app: Celery,
        db: Session
    ):
        self.repository = repository
        self.vector_store = vector_store
        self.file_storage = file_storage
        self.celery_app = celery_app
        self.db = db

    async def create_knowledge_base(
        self, 
        kb_data: KnowledgeBaseCreate,
        current_user: User
    ) -> KnowledgeBase:
        """Create a new knowledge base"""
        try:
            kb = self.repository.create(
                self.db,
                name=kb_data.name,
                description=kb_data.description,
                owner_id=str(current_user.id)
            )
            return kb
        except Exception as e:
            logger.error(f"Error creating knowledge base: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to create knowledge base: {str(e)}")

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
        return await self.repository.create_document(self.db, document)

    async def get_knowledge_base(
        self,
        kb_id: str,
        current_user: User
    ) -> KnowledgeBase:
        """Get a knowledge base by ID"""
        kb = self.repository.get_by_id(self.db, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        # Check if user has access
        if str(kb.owner_id) != str(current_user.id) and current_user.role != UserRole.ADMIN:
            # Check if user is in shared_with
            if not any(str(user.id) == str(current_user.id) for user in kb.shared_with):
                raise HTTPException(status_code=403, detail="You don't have access to this knowledge base")
        
        return kb

    async def get_document(
        self,
        doc_id: str,
        current_user: User
    ) -> Document:
        """Get document details"""
        try:
            doc = await self.repository.get_document_by_id(self.db, doc_id)
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
        """List all knowledge bases accessible to the user"""
        if current_user.role == UserRole.ADMIN:
            return self.repository.list_all(self.db)
        else:
            return self.repository.list_by_owner(self.db, str(current_user.id))

    async def list_documents(
        self,
        kb_id: str,
        current_user: User
    ) -> List[Document]:
        """List all documents in a knowledge base"""
        try:
            # Check access
            await self.get_knowledge_base(kb_id, current_user)
            return await self.repository.list_documents_by_kb(self.db, kb_id)
        except Exception as e:
            logger.error(f"Failed to list documents for knowledge base {kb_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def update_knowledge_base(
        self,
        kb_id: str,
        kb_data: KnowledgeBaseUpdate,
        current_user: User
    ) -> KnowledgeBase:
        """Update a knowledge base"""
        kb = self.repository.get_by_id(self.db, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        # Check if user has permission to update
        if str(kb.owner_id) != str(current_user.id) and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="You don't have permission to update this knowledge base")
        
        try:
            updated_kb = self.repository.update(
                self.db,
                kb_id=kb_id,
                name=kb_data.name,
                description=kb_data.description
            )
            return updated_kb
        except Exception as e:
            logger.error(f"Error updating knowledge base: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to update knowledge base: {str(e)}")

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
            if current_user.role != UserRole.ADMIN and str(kb.owner_id) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Not enough privileges")
            
            # Update document
            update_data = doc_update.model_dump(exclude_unset=True)
            updated_doc = await self.repository.update_document(self.db, doc_id, update_data)
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
        kb = self.repository.get_by_id(self.db, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        # Check if user has permission to delete
        if str(kb.owner_id) != str(current_user.id) and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="You don't have permission to delete this knowledge base")
        
        try:
            # Delete all documents in the knowledge base
            documents = self.repository.get_documents(self.db, kb_id)
            for doc in documents:
                # Delete document vectors
                await self.vector_store.delete_document_chunks(doc.id, kb_id)
                
                # Clean up file if it exists
                if doc.file_path:
                    self.file_storage.cleanup_file(doc.file_path)
            
            # Delete the knowledge base (this will cascade delete documents)
            self.repository.delete(self.db, kb_id)
        except Exception as e:
            logger.error(f"Error deleting knowledge base: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to delete knowledge base: {str(e)}")

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
            
            if str(kb.owner_id) != str(current_user.id) and current_user.role != UserRole.ADMIN:
                raise HTTPException(status_code=403, detail="Not enough privileges")
            
            # Queue vector deletion task
            self.celery_app.send_task(
                'app.worker.tasks.delete_document_vectors',
                args=[doc.id]
            )
            
            # Delete document
            await self.repository.delete_document(self.db, doc_id)
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
        """Share a knowledge base with another user"""
        # Implementation will depend on how sharing is handled in your database model
        # This is a placeholder for the actual implementation
        pass 