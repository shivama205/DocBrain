from typing import List, Optional
from app.db.database import db
from app.db.models.knowledge_base import KnowledgeBase, Document
from app.db.models.conversation import Conversation
import logging

logger = logging.getLogger(__name__)

class KnowledgeBaseRepository:
    @staticmethod
    async def create(knowledge_base: KnowledgeBase) -> KnowledgeBase:
        """Create a new knowledge base"""
        session = db.get_session()
        session.add(knowledge_base)
        session.commit()
        session.refresh(knowledge_base)
        return knowledge_base
    
    @staticmethod
    async def get_by_id(kb_id: str) -> Optional[KnowledgeBase]:
        """Get knowledge base by ID"""
        session = db.get_session()
        return session.get(KnowledgeBase, kb_id)
    
    @staticmethod
    async def list_all() -> List[KnowledgeBase]:
        """List all knowledge bases"""
        session = db.get_session()
        knowledge_bases = session.query(KnowledgeBase).all()
        for knowledge_base in knowledge_bases:
            session.refresh(knowledge_base)
        return knowledge_bases
    
    @staticmethod
    async def list_by_owner(owner_id: str) -> List[KnowledgeBase]:
        """List all knowledge bases owned by a user"""
        session = db.get_session()
        return session.query(KnowledgeBase).filter(KnowledgeBase.owner_id == owner_id).all()
    
    @staticmethod
    async def update(kb_id: str, update_data: dict) -> Optional[KnowledgeBase]:
        """Update knowledge base"""
        session = db.get_session()
        session.update(kb_id, update_data)
        session.commit()
        session.refresh(kb_id)
        return await KnowledgeBaseRepository.get_by_id(kb_id)
    
    @staticmethod
    async def delete(kb_id: str) -> bool:
        """Delete knowledge base and all related data in cascade"""
        try:
            # First delete all messages in conversations
            session = db.get_session()
            conversations = session.query(Conversation).filter(Conversation.knowledge_base_id == kb_id).all()
            for conv in conversations:
                session.delete(conv)
            
            # Then delete all conversations
            session.commit()
            
            # Delete all documents
            documents = session.query(Document).filter(Document.knowledge_base_id == kb_id).all()
            for doc in documents:
                session.delete(doc)
            session.commit()
            
            # Finally delete the knowledge base itself
            session.delete(kb_id)
            session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to cascade delete knowledge base {kb_id}: {e}")
            raise
    
    @staticmethod
    async def get_documents(kb_id: str) -> List[Document]:
        """Get all documents in a knowledge base"""
        session = db.get_session()
        return session.query(Document).filter(Document.knowledge_base_id == kb_id).all()
    
    @staticmethod
    async def list_documents_by_kb(kb_id: str) -> List[Document]:
        """List all documents in a knowledge base"""
        session = db.get_session()
        return session.query(Document).filter(Document.knowledge_base_id == kb_id).all() 