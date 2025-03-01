from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models.knowledge_base import KnowledgeBase, Document
from app.db.models.conversation import Conversation
import logging

from app.schemas.knowledge_base import KnowledgeBaseResponse

logger = logging.getLogger(__name__)

class KnowledgeBaseRepository:
    @staticmethod
    async def create(knowledge_base: KnowledgeBase, db: Session) -> KnowledgeBaseResponse:
        """Create a new knowledge base"""
        try:
            db.add(knowledge_base)
            db.commit()
            db.refresh(knowledge_base)
            return KnowledgeBaseResponse.model_validate(knowledge_base)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create knowledge base: {e}")
            raise
    
    @staticmethod
    async def get_by_id(kb_id: str, db: Session) -> Optional[KnowledgeBaseResponse]:
        """Get knowledge base by ID"""
        try:
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                return None
            return KnowledgeBaseResponse.model_validate(kb)
        except Exception as e:
            logger.error(f"Failed to get knowledge base by ID {kb_id}: {e}")
            raise
    
    @staticmethod
    async def list_all(db: Session) -> List[KnowledgeBaseResponse]:
        """List all knowledge bases"""
        try:
            knowledge_bases = db.query(KnowledgeBase).all()
            return [KnowledgeBaseResponse.model_validate(kb) for kb in knowledge_bases]
        except Exception as e:
            logger.error(f"Failed to list knowledge bases: {e}")
            raise
    
    @staticmethod
    async def list_by_owner(owner_id: str, db: Session) -> List[KnowledgeBaseResponse]:
        """List all knowledge bases owned by a user"""
        try:
            knowledge_bases = db.query(KnowledgeBase).filter(KnowledgeBase.user_id == owner_id).all()
            return [KnowledgeBaseResponse.model_validate(kb) for kb in knowledge_bases]
        except Exception as e:
            logger.error(f"Failed to list knowledge bases by owner {owner_id}: {e}")
            raise
    
    @staticmethod
    async def update(kb_id: str, update_data: dict, db: Session) -> Optional[KnowledgeBaseResponse]:
        """Update knowledge base"""
        try:
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                return None
                
            # Update attributes
            for key, value in update_data.items():
                setattr(kb, key, value)
                
            db.commit()
            db.refresh(kb)
            return KnowledgeBaseResponse.model_validate(kb)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update knowledge base {kb_id}: {e}")
            raise
    
    @staticmethod
    async def delete(kb_id: str, db: Session) -> bool:
        """Delete knowledge base and all related data in cascade"""
        try:
            # First delete all messages in conversations
            conversations = db.query(Conversation).filter(Conversation.knowledge_base_id == kb_id).all()
            for conv in conversations:
                db.delete(conv)
            
            # Then delete all conversations
            db.commit()
            
            # Delete all documents
            documents = db.query(Document).filter(Document.knowledge_base_id == kb_id).all()
            for doc in documents:
                db.delete(doc)
            db.commit()
            
            # Finally delete the knowledge base itself
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                return False
                
            db.delete(kb)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cascade delete knowledge base {kb_id}: {e}")
            raise
    
    @staticmethod
    async def get_documents(kb_id: str, db: Session) -> List[Document]:
        """Get all documents in a knowledge base"""
        try:
            return db.query(Document).filter(Document.knowledge_base_id == kb_id).all()
        except Exception as e:
            logger.error(f"Failed to get documents for knowledge base {kb_id}: {e}")
            raise
    
    @staticmethod
    async def list_documents_by_kb(kb_id: str, db: Session) -> List[Document]:
        """List all documents in a knowledge base"""
        try:
            return db.query(Document).filter(Document.knowledge_base_id == kb_id).all()
        except Exception as e:
            logger.error(f"Failed to list documents for knowledge base {kb_id}: {e}")
            raise 