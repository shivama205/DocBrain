from typing import List, Dict, Any
from fastapi import APIRouter, Body, Depends, Path
from functools import lru_cache
from sqlalchemy.orm import Session

from app.schemas.message import MessageCreate, MessageResponse
from app.api.deps import get_current_user
from app.schemas.user import UserResponse
from app.services.message_service import MessageService
from app.repositories.message_repository import MessageRepository
from app.api.endpoints.conversations import get_conversation_service
from app.db.database import get_db
from app.services.query_router import get_query_router

router = APIRouter()

@lru_cache()
def get_message_repository() -> MessageRepository:
    """Get message repository instance"""
    return MessageRepository()

def get_message_service(
    message_repository: MessageRepository = Depends(get_message_repository),
    conversation_service = Depends(get_conversation_service),
    db: Session = Depends(get_db)
) -> MessageService:
    """Get message service instance"""
    return MessageService(
        message_repository=message_repository,
        conversation_service=conversation_service,
        db=db
    )

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def create_message(
    conversation_id: str = Path(..., description="ID of the conversation this message belongs to"),
    payload: MessageCreate = Body(..., description="Message details"),
    current_user: UserResponse = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Create a new message in a conversation"""
    return await message_service.create_message(
        conversation_id,
        payload,
        current_user,
    )

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """List all messages in a conversation"""
    return await message_service.list_messages(conversation_id, current_user)

@router.get("/{conversation_id}/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    conversation_id: str,
    message_id: str,
    current_user: UserResponse = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Get a message by ID"""
    return await message_service.get_message(conversation_id, message_id, current_user)
