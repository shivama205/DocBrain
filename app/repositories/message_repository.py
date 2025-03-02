from typing import List, Optional
import json

from app.db.models.message import Message, MessageContentType, MessageStatus
from app.schemas.message import MessageResponse
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
        messages = db.query(Message).filter(Message.conversation_id == conversation_id).all()
        return [MessageResponse.model_validate(message) for message in messages]

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
    
    @staticmethod
    async def set_processed(message_id: str, content: str, content_type: MessageContentType, sources: List[dict], db: Session) -> Optional[MessageResponse]:
        """Set message as processed"""
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if not message:
                raise ValueError(f"Message {message_id} not found")
            message.content = content
            message.content_type = content_type
            message.sources = sources
            message.status = MessageStatus.PROCESSED
            db.commit()
            db.refresh(message)
            return MessageResponse.model_validate(message)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set message as processed: {e}")
            raise
    
    @staticmethod
    async def set_failed(message_id: str, error_message: str, db: Session) -> Optional[MessageResponse]:
        """Set message as failed"""
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if not message:
                raise ValueError(f"Message {message_id} not found")
            message.content = error_message
            message.content_type = MessageContentType.TEXT
            message.sources = []
            message.status = MessageStatus.FAILED
            db.commit()
            db.refresh(message)
            return MessageResponse.model_validate(message)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set message as failed: {e}")
            raise