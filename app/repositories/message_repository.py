from typing import List, Optional
import json
from app.db.database import db
from app.db.models.message import Message
from app.db.models.conversation import Conversation
from app.db.models.user import User
from app.schemas.message import MessageCreate, MessageType

class MessageRepository:
    @staticmethod
    async def create(conversation_id: str, message: MessageCreate, user_message: bool = True) -> Message:
        """Create a new message"""
        message_dict = {
            "conversation_id": conversation_id,
            "content": message.content,
            "type": MessageType.USER if user_message else MessageType.ASSISTANT,
            "sources": None,
            "status": "completed" if user_message else "processing"
        }
        message_model = Message(**message_dict)
        session = db.get_session()
        session.add(message_model)
        session.commit()
        session.refresh(message_model)
        return message_model

    @staticmethod
    async def get_by_id(conversation_id: str, message_id: str, user: User) -> Optional[Message]:
        """Get message by ID with ownership verification"""
        # First get the message
        session = db.get_session()
        message = session.get(Message, message_id)
        if not message or message.conversation_id != conversation_id:
            return None

        # Then verify conversation ownership
        conversation = session.get(Conversation, conversation_id)
        if not conversation or conversation.owner_id != str(user.id):
            return None

        return message

    @staticmethod
    async def list_by_conversation(conversation_id: str, user: User) -> List[Message]:
        """List all messages in a conversation"""
        # First verify conversation ownership
        session = db.get_session()
        conversation = session.get(Conversation, conversation_id)
        if not conversation or conversation.owner_id != str(user.id):
            return []

        # Then get all messages
        return session.query(Message).filter(Message.conversation_id == conversation_id).all()

    @staticmethod
    async def update_with_sources(message_id: str, content: str, sources: List[dict]) -> Optional[Message]:
        """Update message with response and sources"""
        update_data = {
            "content": content,
            "sources": json.dumps(sources) if sources is not None else None,
            "status": "completed"
        }
        session = db.get_session()
        session.update(message_id, update_data)
        session.commit()
        session.refresh(message_id)
        return session.get(Message, message_id) 