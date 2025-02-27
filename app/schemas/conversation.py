from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from .message import MessageResponse

class ConversationBase(BaseModel):
    """Base conversation attributes"""
    title: str = Field(..., description="Title of the conversation")
    knowledge_base_id: str = Field(..., description="ID of the knowledge base this conversation is linked to")

class ConversationCreate(ConversationBase):
    """Attributes for creating a new conversation"""
    pass

class ConversationUpdate(BaseModel):
    """Attributes that can be updated"""
    title: Optional[str] = Field(None, description="New title for the conversation")

class ConversationResponse(ConversationBase):
    """Response model for conversations"""
    id: str = Field(..., description="Unique identifier for the conversation")
    owner_id: str = Field(..., description="ID of the user who created the conversation")
    created_at: datetime = Field(..., description="When the conversation was created")
    updated_at: datetime = Field(..., description="When the conversation was last updated") 