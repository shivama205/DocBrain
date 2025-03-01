from typing import List
from fastapi import HTTPException
import logging

from app.db.models.conversation import Conversation
from app.db.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.services.knowledge_base_service import KnowledgeBaseService
from app.schemas.conversation import ConversationCreate, ConversationUpdate

# Set up logging
logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(
        self,
        conversation_repository: ConversationRepository,
        knowledge_base_service: KnowledgeBaseService
    ):
        self.repository = conversation_repository
        self.kb_service = knowledge_base_service

    async def create_conversation(
        self,
        conversation_data: ConversationCreate,
        current_user: User
    ) -> Conversation:
        """Create a new conversation"""
        try:
            # Verify knowledge base access
            await self.kb_service.get_knowledge_base(
                conversation_data.knowledge_base_id,
                current_user
            )

            conversation = await self.repository.create(conversation_data, current_user)
            logger.info(f"Conversation {conversation.id} created by user {current_user.id}")
            return conversation
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_conversations(self, current_user: User) -> List[Conversation]:
        """List all conversations for the current user"""
        try:
            conversations = await self.repository.list_by_user(current_user)
            logger.info(f"Retrieved {len(conversations)} conversations for user {current_user.id}")
            return conversations
        except Exception as e:
            logger.error(f"Failed to list conversations for user {current_user.id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_conversation(
        self,
        conversation_id: str,
        current_user: User
    ) -> Conversation:
        """Get conversation details"""
        try:
            conversation = await self.repository.get_by_id(conversation_id, current_user)
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found")
                raise HTTPException(status_code=404, detail="Conversation not found")
            return conversation
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def update_conversation(
        self,
        conversation_id: str,
        conversation_update: ConversationUpdate,
        current_user: User
    ) -> Conversation:
        """Update conversation details"""
        try:
            # Verify ownership
            conversation = await self.get_conversation(conversation_id, current_user)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            # Update conversation
            updated_conversation = await self.repository.update(
                conversation_id,
                conversation_update,
                current_user
            )
            if updated_conversation:
                logger.info(f"Conversation {conversation_id} updated by user {current_user.id}")
                return updated_conversation
            raise HTTPException(status_code=404, detail="Conversation not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update conversation {conversation_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_conversation(
        self,
        conversation_id: str,
        current_user: User
    ) -> None:
        """Delete conversation and all its messages"""
        try:
            # Verify ownership
            conversation = await self.get_conversation(conversation_id, current_user)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

            # Delete conversation (cascade will handle messages)
            if await self.repository.delete(conversation_id, current_user):
                logger.info(f"Conversation {conversation_id} deleted by user {current_user.id}")
            else:
                raise HTTPException(status_code=404, detail="Conversation not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e)) 