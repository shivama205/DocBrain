from typing import List, Protocol
from fastapi import HTTPException, UploadFile
import logging
from datetime import datetime
import os
import aiofiles
from celery import Celery
from sqlalchemy.orm import Session

from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.user import UserRole
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.user import UserResponse
from app.services.rag.vector_store import VectorStore
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseResponse, KnowledgeBaseUpdate

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
        file_storage: LocalFileStorage,
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
        current_user: UserResponse
    ) -> KnowledgeBase:
        """Create a new knowledge base"""
        try:
            knowledge_base = KnowledgeBase(
                name=kb_data.name,
                description=kb_data.description,
                user_id=current_user.id
            )
            kb = await self.repository.create(
                knowledge_base,
                self.db
            )
            return kb
        except Exception as e:
            logger.error(f"Error creating knowledge base: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to create knowledge base: {str(e)}")

    async def get_knowledge_base(
        self,
        kb_id: str,
        current_user: UserResponse
    ) -> KnowledgeBaseResponse:
        """Get a knowledge base by ID"""
        kb =  await self.repository.get_by_id(kb_id, self.db)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        # Check if user has access
        if str(kb.user_id) != str(current_user.id):
            # Check if user is in shared_with
            if not any(str(user.id) == str(current_user.id) for user in kb.shared_with):
                raise HTTPException(status_code=403, detail="You don't have access to this knowledge base")
        
        return kb

    async def list_knowledge_bases(
        self,
        current_user: UserResponse
    ) -> List[KnowledgeBase]:
        """List all knowledge bases accessible to the user"""
        if current_user.role == UserRole.ADMIN:
            return await self.repository.list_all(self.db)
        else:
            return await self.repository.list_by_owner(current_user.id, self.db)

    async def update_knowledge_base(
        self,
        kb_id: str,
        kb_data: KnowledgeBaseUpdate,
        current_user: UserResponse
    ) -> KnowledgeBase:
        """Update a knowledge base"""
        kb = await self.repository.get_by_id(kb_id, self.db)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        # Check if user has permission to update
        if str(kb.owner_id) != str(current_user.id) and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="You don't have permission to update this knowledge base")
        
        try:
            updated_kb = await self.repository.update(
                self.db,
                kb_id=kb_id,
                name=kb_data.name,
                description=kb_data.description
            )
            return updated_kb
        except Exception as e:
            logger.error(f"Error updating knowledge base: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to update knowledge base: {str(e)}")

    async def delete_knowledge_base(
        self,
        kb_id: str,
        current_user: UserResponse
    ) -> None:
        """Delete a knowledge base and all its documents"""
        kb = await self.repository.get_by_id(kb_id, self.db)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
        
        # Check if user has permission to delete
        if str(kb.owner_id) != str(current_user.id) and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="You don't have permission to delete this knowledge base")
        
        try:
            # Delete all documents in the knowledge base
            documents = await self.repository.get_documents(kb_id, self.db)
            for doc in documents:
                # Delete document vectors
                await self.vector_store.delete_document_chunks(doc.id, kb_id)
                
                # Clean up file if it exists
                if doc.file_path:
                    self.file_storage.cleanup_file(doc.file_path)
            
            # Delete the knowledge base (this will cascade delete documents)
            await self.repository.delete(kb_id, self.db)
        except Exception as e:
            logger.error(f"Error deleting knowledge base: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to delete knowledge base: {str(e)}")

    async def share_knowledge_base(
        self,
        kb_id: str,
        user_id: str,
        current_user: UserResponse
    ) -> None:
        """Share a knowledge base with another user"""
        # Implementation will depend on how sharing is handled in your database model
        # This is a placeholder for the actual implementation
        pass 