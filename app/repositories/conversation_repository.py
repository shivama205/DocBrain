from typing import List, Optional
from datetime import datetime
from app.db.models.conversation import Conversation
from app.db.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationUpdate
import logging
from sqlalchemy.orm import Session
logger = logging.getLogger(__name__)

class ConversationRepository:
    @staticmethod
    async def create(conversation: Conversation, db: Session) -> ConversationResponse:
        """Create a new conversation"""
        try:
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            return ConversationResponse.model_validate(conversation)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create conversation: {e}")
            raise


    @staticmethod
    async def get_by_id(conversation_id: str, user: User, db: Session) -> Optional[ConversationResponse]:
        """Get conversation by ID for a specific user"""
        try:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation and conversation.user_id == str(user.id):
                return ConversationResponse.model_validate(conversation)
            return None
        except Exception as e:
            logger.error(f"Failed to get conversation by ID: {e}")
            raise


    @staticmethod
    async def list_by_user(user: User, db: Session) -> List[ConversationResponse]:
        """List all conversations for a user"""
        logger.info(f"Listing conversations for user {user.id}")
        conversations = db.query(Conversation).filter(Conversation.user_id == user.id).all()
        logger.info(f"Found {len(conversations)} conversations for user {user.id}")
        return [ConversationResponse.model_validate(conversation) for conversation in conversations]

    @staticmethod
    async def update(conversation_id: str, conversation_update: ConversationUpdate, user: User, db: Session) -> Optional[ConversationResponse]:
        """Update conversation details"""
        try:
            # First verify ownership
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conversation:
                return None

            # Update the conversation
            update_data = conversation_update.model_dump(exclude_unset=True)
            if update_data:
                db.query(Conversation).update(update_data)
                db.commit()
                db.refresh(conversation)
                return await ConversationRepository.get_by_id(conversation_id, user, db)
        except Exception as e:
            logger.error(f"Failed to update conversation: {e}")
            raise

    @staticmethod
    async def delete(conversation_id: str, user: User, db: Session) -> bool:
        """Delete a conversation and all its messages"""
        try:
            # First verify ownership
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conversation:
                return False

            # Start transaction
            db.execute("BEGIN TRANSACTION")
            try:
                # Delete all messages first
                logger.debug(f"Deleting messages for conversation {conversation_id}")
                db.execute("DELETE FROM messages WHERE conversation_id = ?", [conversation_id])
                
                # Then delete the conversation
                logger.debug(f"Deleting conversation {conversation_id}")
                db.execute("DELETE FROM conversations WHERE id = ?", [conversation_id])
                
                # Commit transaction
                db.execute("COMMIT")
                logger.info(f"Successfully deleted conversation {conversation_id} and its messages")
                return True
            except Exception as e:
                # Rollback on error
                db.execute("ROLLBACK")
                logger.error(f"Failed to delete conversation {conversation_id}: {e}")
                raise
        except Exception as e:
            logger.error(f"Error in delete operation: {e}")
            raise 