from typing import List
from fastapi import HTTPException
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models.message import Message
from app.repositories.message_repository import MessageRepository
from app.schemas.user import UserResponse
from app.services.conversation_service import ConversationService
from app.worker.celery import celery_app
from app.schemas.message import MessageCreate, MessageType

# Set up logging
logger = logging.getLogger(__name__)

class MessageService:
    def __init__(
        self,
        message_repository: MessageRepository,
        conversation_service: ConversationService,
        db: Session
    ):
        self.repository = message_repository
        self.conversation_service = conversation_service
        self.db = db

    async def create_message(
        self,
        conversation_id: str,
        message_data: MessageCreate,
        current_user: UserResponse,
    ) -> Message:
        """Create a new message in a conversation"""
        try:
            # Check conversation access
            conversation = await self.conversation_service.get_conversation(
                conversation_id,
                current_user
            )

            # Create user message
            message = Message(
                conversation_id=conversation_id,
                content=message_data.content,
                type=MessageType.USER,
                user_id=current_user.id
            )
            user_message = await self.repository.create(
                message,
                self.db
            )
            logger.info(f"User message {user_message.id} created in conversation {conversation_id}")

            # Create assistant message
            response_message = Message(
                conversation_id=conversation_id,
                content="",
                type=MessageType.ASSISTANT,
                user_id=current_user.id
            )
            assistant_message_data = MessageCreate(
                content="",
                type=MessageType.ASSISTANT,
                top_k=message_data.top_k,
                similarity_cutoff=message_data.similarity_cutoff
            )
            assistant_message = await self.repository.create(
                response_message,
                self.db
            )
            logger.info(f"Assistant message {assistant_message.id} created in conversation {conversation_id}")

            # Queue RAG processing task
            celery_app.send_task(
                'app.worker.tasks.process_rag_response',
                args=[
                    assistant_message.id,
                    message_data.content,
                    conversation.knowledge_base_id,
                    message_data.top_k,
                    message_data.similarity_cutoff
                ]
            )

            return user_message

        except Exception as e:
            logger.error(f"Failed to create message in conversation {conversation_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_message(
        self,
        conversation_id: str,
        message_id: str,
        current_user: UserResponse
    ) -> Message:
        """Get message details"""
        try:
            # Check conversation access first
            await self.conversation_service.get_conversation(conversation_id, current_user)

            message = await self.repository.get_by_id(message_id, self.db)
            if not message:
                logger.warning(f"Message {message_id} not found in conversation {conversation_id}")
                raise HTTPException(status_code=404, detail="Message not found")

            return message
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_messages(
        self,
        conversation_id: str,
        current_user: UserResponse
    ) -> List[Message]:
        """List all messages in a conversation"""
        try:
            # Check conversation access first
            await self.conversation_service.get_conversation(conversation_id, current_user)

            messages = await self.repository.list_by_conversation(conversation_id, self.db)
            logger.info(f"Retrieved {len(messages)} messages from conversation {conversation_id}")
            return messages
        except Exception as e:
            logger.error(f"Failed to list messages for conversation {conversation_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e)) 