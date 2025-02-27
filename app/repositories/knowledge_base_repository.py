from typing import List, Optional
from app.db.database import db
from app.models.knowledge_base import KnowledgeBase, Document
from app.models.conversation import Conversation
from app.models.message import Message
import logging

logger = logging.getLogger(__name__)

class KnowledgeBaseRepository:
    @staticmethod
    async def create(knowledge_base: KnowledgeBase) -> KnowledgeBase:
        """Create a new knowledge base"""
        return db.create("knowledge_bases", knowledge_base)
    
    @staticmethod
    async def get_by_id(kb_id: str) -> Optional[KnowledgeBase]:
        """Get knowledge base by ID"""
        return db.get("knowledge_bases", KnowledgeBase, kb_id)
    
    @staticmethod
    async def list_all() -> List[KnowledgeBase]:
        """List all knowledge bases"""
        return db.list("knowledge_bases", KnowledgeBase)
    
    @staticmethod
    async def list_by_owner(owner_id: str) -> List[KnowledgeBase]:
        """List all knowledge bases owned by a user"""
        return db.list("knowledge_bases", KnowledgeBase, {"owner_id": owner_id})
    
    @staticmethod
    async def update(kb_id: str, update_data: dict) -> Optional[KnowledgeBase]:
        """Update knowledge base"""
        db.update("knowledge_bases", kb_id, update_data)
        return await KnowledgeBaseRepository.get_by_id(kb_id)
    
    @staticmethod
    async def delete(kb_id: str) -> bool:
        """Delete knowledge base and all related data in cascade"""
        try:
            # First delete all messages in conversations
            conversations = db.list("conversations", Conversation, {"knowledge_base_id": kb_id})
            for conv in conversations:
                db.delete_many("messages", {"conversation_id": conv.id})
            
            # Then delete all conversations
            db.delete_many("conversations", {"knowledge_base_id": kb_id})
            
            # Delete all documents
            db.delete_many("documents", {"knowledge_base_id": kb_id})
            
            # Finally delete the knowledge base itself
            return db.delete("knowledge_bases", kb_id)
            
        except Exception as e:
            logger.error(f"Failed to cascade delete knowledge base {kb_id}: {e}")
            raise
    
    @staticmethod
    async def get_documents(kb_id: str) -> List[Document]:
        """Get all documents in a knowledge base"""
        return db.list("documents", Document, {"knowledge_base_id": kb_id})
    
    @staticmethod
    async def list_documents_by_kb(kb_id: str) -> List[Document]:
        """List all documents in a knowledge base"""
        return db.list("documents", Document, {"knowledge_base_id": kb_id}) 