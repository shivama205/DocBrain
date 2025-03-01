from typing import List, Optional
import json
from app.db.models.message import Message
from app.db.models.conversation import Conversation
from app.db.models.user import User
from app.schemas.message import MessageCreate, MessageResponse, MessageType
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class MessageRepository:
    @staticmethod
    async def create(message: Message, db: Session) -> Message:
        """Create a new message"""
        try:
            db.add(message)
            db.commit()
            db.refresh(message)
            return message
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create message: {e}")
            raise

    @staticmethod
    async def get_by_id(message_id: str, db: Session) -> Optional[MessageResponse]:
        """Get message by ID with ownership verification"""
        # First get the message
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            return None

        return MessageResponse.model_validate(message)

    @staticmethod
    async def list_by_conversation(conversation_id: str, db: Session) -> List[MessageResponse]:
        """List all messages in a conversation"""
        return [MessageResponse.model_validate(message) 
                for message in db.query(Message).filter(Message.conversation_id == conversation_id).all()]  

    @staticmethod
    async def update_with_sources(message_id: str, content: str, sources: List[dict], db: Session) -> Optional[MessageResponse]:
        """Update message with response and sources"""
        update_data = {
            "content": content,
            "sources": json.dumps(sources) if sources is not None else None,
            "status": "completed"
        }
        db.query(Message).filter(Message.id == message_id).update(update_data)
        db.commit()
        db.refresh(message_id)
        return MessageResponse.model_validate(message_id) 