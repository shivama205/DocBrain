from typing import List, Optional
from fastapi import HTTPException
import logging

from sqlalchemy.orm import Session
from app.db.models.conversation import Conversation
from app.db.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.services.knowledge_base_service import KnowledgeBaseService
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationUpdate

# Set up logging
logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(
        self,
        conversation_repository: ConversationRepository,
        knowledge_base_service: KnowledgeBaseService,
        db: Session
    ):
        self.repository = conversation_repository
        self.kb_service = knowledge_base_service
        self.db = db

    async def create_conversation(
        self,
        conversation_data: ConversationCreate,
        current_user: User
    ) -> ConversationResponse:
        """Create a new conversation"""
        try:
            # Verify knowledge base access
            await self.kb_service.get_knowledge_base(
                conversation_data.knowledge_base_id,
                current_user
            )
            conversation = Conversation(
                title=conversation_data.title,
                knowledge_base_id=conversation_data.knowledge_base_id,
                user_id=current_user.id
            )
            conversation: ConversationResponse = await self.repository.create(conversation, self.db)
            logger.info(f"Conversation {conversation.id} created by user {current_user.id}")
            return conversation
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_conversations(self, current_user: User) -> List[ConversationResponse]:
        """List all conversations for the current user"""
        try:
            logger.info(f"Listing conversations for user {current_user.id}")
            conversations: List[ConversationResponse] = await self.repository.list_by_user(current_user, self.db)
            logger.info(f"Retrieved {len(conversations)} conversations for user {current_user.id}")
            return conversations
        except Exception as e:
            logger.error(f"Failed to list conversations for user {current_user.id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_conversation(
        self,
        conversation_id: str,
        current_user: User
    ) -> ConversationResponse:
        """Get conversation details"""
        try:
            conversation: Optional[ConversationResponse] = await self.repository.get_by_id(conversation_id, current_user, self.db)
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
    ) -> ConversationResponse:
        """Update conversation details"""
        try:
            # Verify ownership
            conversation: ConversationResponse = await self.get_conversation(conversation_id, current_user)
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
            conversation: ConversationResponse = await self.get_conversation(conversation_id, current_user)
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