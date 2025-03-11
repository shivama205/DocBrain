from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.models.knowledge_base import KnowledgeBase, Document
from app.db.models.conversation import Conversation
import logging

from app.schemas.knowledge_base import KnowledgeBaseResponse
from app.db.models.message import Message

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
            # First get all conversations related to the knowledge base
            conversations = db.query(Conversation).filter(Conversation.knowledge_base_id == kb_id).all()
            
            # For each conversation, delete all its messages first
            for conv in conversations:
                # Delete messages associated with this conversation
                db.query(Message).filter(Message.conversation_id == conv.id).delete()
            
            # Commit the message deletions
            db.commit()
            
            # Then delete all conversations
            for conv in conversations:
                db.delete(conv)
            
            # Commit the conversation deletions
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
    
    @staticmethod
    async def is_shared_with_user(kb_id: str, user_id: str, db: Session) -> bool:
        """Check if a knowledge base is shared with a specific user"""
        try:
            from sqlalchemy import text
            query = text("""
                SELECT COUNT(*) FROM knowledge_base_sharing 
                WHERE knowledge_base_id = :kb_id AND user_id = :user_id
            """)
            result = db.execute(query, {"kb_id": kb_id, "user_id": user_id}).scalar()
            return result > 0
        except Exception as e:
            logger.error(f"Failed to check if knowledge base {kb_id} is shared with user {user_id}: {e}")
            raise
    
    @staticmethod
    async def add_user_access(kb_id: str, user_id: str, db: Session) -> bool:
        """Share a knowledge base with a user"""
        try:
            from sqlalchemy import text
            query = text("""
                INSERT INTO knowledge_base_sharing (knowledge_base_id, user_id) 
                VALUES (:kb_id, :user_id)
                ON DUPLICATE KEY UPDATE knowledge_base_id = knowledge_base_id
            """)
            db.execute(query, {"kb_id": kb_id, "user_id": user_id})
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to share knowledge base {kb_id} with user {user_id}: {e}")
            raise
    
    @staticmethod
    async def remove_user_access(kb_id: str, user_id: str, db: Session) -> bool:
        """Remove a user's access to a knowledge base"""
        try:
            from sqlalchemy import text
            query = text("""
                DELETE FROM knowledge_base_sharing 
                WHERE knowledge_base_id = :kb_id AND user_id = :user_id
            """)
            db.execute(query, {"kb_id": kb_id, "user_id": user_id})
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to unshare knowledge base {kb_id} from user {user_id}: {e}")
            raise
    
    @staticmethod
    async def get_shared_users(kb_id: str, db: Session) -> List:
        """Get all users who have access to a knowledge base"""
        try:
            from app.db.models.user import User
            from app.schemas.user import UserResponse
            
            # Get the knowledge base to ensure it exists
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                return []
                
            # Get all users who have access through the shared_with relationship
            shared_users = [UserResponse.model_validate(user) for user in kb.shared_with]
            return shared_users
        except Exception as e:
            logger.error(f"Failed to get shared users for knowledge base {kb_id}: {e}")
            raise
    
    @staticmethod
    async def list_shared_with_user(user_id: str, db: Session) -> List[KnowledgeBaseResponse]:
        """List all knowledge bases shared with a specific user"""
        try:
            
            
            query = text(f"""
                SELECT kb.* FROM knowledge_bases kb
                JOIN knowledge_base_sharing kbs ON kb.id = kbs.knowledge_base_id
                WHERE kbs.user_id = '{user_id}'
            """)

            result = db.execute(query)
            shared_kbs = []
            for row in result:
                shared_kbs.append(KnowledgeBaseResponse.model_validate(row))
                
            return shared_kbs  # This will be an empty list if no shared knowledge bases exist
        except Exception as e:
            logger.error(f"Failed to list knowledge bases shared with user {user_id}: {e}")
            raise 