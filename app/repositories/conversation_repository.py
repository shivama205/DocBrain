from typing import List, Optional
from datetime import datetime
from app.db.database import db
from app.db.models.conversation import Conversation
from app.db.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationUpdate
import logging

logger = logging.getLogger(__name__)

class ConversationRepository:
    @staticmethod
    async def create(conversation: ConversationCreate, owner: User) -> Conversation:
        """Create a new conversation"""
        current_time = datetime.utcnow().isoformat()
        conversation_dict = {
            "title": conversation.title,
            "knowledge_base_id": conversation.knowledge_base_id,
            "owner_id": str(owner.id),
            "created_at": current_time,
            "updated_at": current_time
        }
        conversation_model = Conversation(**conversation_dict)
        session = db.get_session()
        session.add(conversation_model)
        session.commit()
        session.refresh(conversation_model)
        return conversation_model

    @staticmethod
    async def get_by_id(conversation_id: str, user: User) -> Optional[Conversation]:
        """Get conversation by ID for a specific user"""
        session = db.get_session()
        conversation = session.get(Conversation, conversation_id)
        if conversation and conversation.owner_id == str(user.id):
            return conversation
        return None

    @staticmethod
    async def list_by_user(user: User) -> List[Conversation]:
        """List all conversations for a user"""
        session = db.get_session()
        return session.query(Conversation).filter(Conversation.owner_id == str(user.id)).all()

    @staticmethod
    async def update(conversation_id: str, conversation_update: ConversationUpdate, user: User) -> Optional[Conversation]:
        """Update conversation details"""
        # First verify ownership
        session = db.get_session()
        conversation = session.get(Conversation, conversation_id)
        if not conversation:
            return None

        # Update the conversation
        update_data = conversation_update.model_dump(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()
            session.update(conversation_id, update_data)
            session.commit()
            session.refresh(conversation_id)
            return await ConversationRepository.get_by_id(conversation_id, user)
        return conversation

    @staticmethod
    async def delete(conversation_id: str, user: User) -> bool:
        """Delete a conversation and all its messages"""
        try:
            # First verify ownership
            session = db.get_session()
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                return False

            # Start transaction
            session.execute("BEGIN TRANSACTION")
            try:
                # Delete all messages first
                logger.debug(f"Deleting messages for conversation {conversation_id}")
                session.execute("DELETE FROM messages WHERE conversation_id = ?", [conversation_id])
                
                # Then delete the conversation
                logger.debug(f"Deleting conversation {conversation_id}")
                session.execute("DELETE FROM conversations WHERE id = ?", [conversation_id])
                
                # Commit transaction
                session.execute("COMMIT")
                logger.info(f"Successfully deleted conversation {conversation_id} and its messages")
                return True
            except Exception as e:
                # Rollback on error
                session.execute("ROLLBACK")
                logger.error(f"Failed to delete conversation {conversation_id}: {e}")
                raise
        except Exception as e:
            logger.error(f"Error in delete operation: {e}")
            raise 