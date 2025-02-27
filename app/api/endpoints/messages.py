from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from functools import lru_cache

from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse
from app.api.deps import get_current_user
from app.services.message_service import MessageService
from app.repositories.message_repository import MessageRepository
from app.api.endpoints.conversations import get_conversation_service

router = APIRouter()

@lru_cache()
def get_message_repository() -> MessageRepository:
    """Get message repository instance"""
    return MessageRepository()

def get_message_service(
    message_repository: MessageRepository = Depends(get_message_repository),
    conversation_service = Depends(get_conversation_service)
) -> MessageService:
    """Get message service instance"""
    return MessageService(
        message_repository=message_repository,
        conversation_service=conversation_service
    )

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def create_message(
    conversation_id: str,
    message: MessageCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Create a new message in a conversation"""
    return await message_service.create_message(
        conversation_id,
        message,
        current_user,
        background_tasks
    )

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """List all messages in a conversation"""
    return await message_service.list_messages(conversation_id, current_user)

@router.get("/{conversation_id}/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    conversation_id: str,
    message_id: str,
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Get message details"""
    return await message_service.get_message(conversation_id, message_id, current_user) 