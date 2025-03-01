from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from functools import lru_cache

from app.db.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse
from app.api.deps import get_current_user
from app.services.conversation_service import ConversationService
from app.repositories.conversation_repository import ConversationRepository
from app.services.knowledge_base_service import KnowledgeBaseService
from app.api.endpoints.knowledge_bases import get_knowledge_base_service

router = APIRouter()

@lru_cache()
def get_conversation_repository() -> ConversationRepository:
    """Get conversation repository instance"""
    return ConversationRepository()

def get_conversation_service(
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
    knowledge_base_service: KnowledgeBaseService = Depends(get_knowledge_base_service)
) -> ConversationService:
    """Get conversation service instance"""
    return ConversationService(
        conversation_repository=conversation_repository,
        knowledge_base_service=knowledge_base_service
    )

@router.post("", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Create a new conversation"""
    return await conversation_service.create_conversation(conversation, current_user)

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """List all conversations for the current user"""
    return await conversation_service.list_conversations(current_user)

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Get conversation details including messages"""
    return await conversation_service.get_conversation(conversation_id, current_user)

@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    conversation_update: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Update conversation details"""
    return await conversation_service.update_conversation(conversation_id, conversation_update, current_user)

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """Delete a conversation and all its messages"""
    await conversation_service.delete_conversation(conversation_id, current_user)
    return JSONResponse(content={"message": "Conversation deleted successfully"}) 