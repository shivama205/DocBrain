from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from app.db.models.message import MessageContentType, MessageKind, MessageStatus

class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageSource(BaseModel):
    """Source document information"""
    score: float = Field(..., description="Relevance score of the source")
    document_id: str = Field(..., description="ID of the source document")
    title: str = Field(..., description="Title of the source document")
    content: str = Field(..., description="Relevant content from the document")
    chunk_index: int = Field(..., description="Index of the chunk in the document")

class MessageBase(BaseModel):
    """Base message attributes"""
    content: str = Field(..., description="Content of the message")
    content_type: MessageContentType = Field(..., description="Type of message (TEXT/IMAGE/AUDIO/VIDEO/DOCUMENT)")

class ProcessedMessageSchema(BaseModel):
    """Processed message attributes"""
    content: str
    content_type: MessageContentType
    sources: List[MessageSource]

class MessageCreate(MessageBase):
    """Attributes for creating a new message"""
    pass

class MessageResponse(MessageBase):
    """Response model for messages"""
    id: str = Field(..., description="Unique identifier for the message")
    kind: MessageKind = Field(..., description="Kind of message (USER/ASSISTANT/SYSTEM)")
    user_id: str = Field(..., description="ID of the user who created the message")
    conversation_id: str = Field(..., description="ID of the conversation this message belongs to")
    knowledge_base_id: str = Field(..., description="ID of the knowledge base this message belongs to")
    sources: Optional[List[MessageSource]] = Field(None, description="Source documents used for assistant's response")
    status: MessageStatus = Field(..., description="Status of the message (RECEIVED/PROCESSING/SENT/FAILED)")
    created_at: datetime = Field(..., description="When the message was created")
    updated_at: datetime = Field(..., description="When the message was last updated")

    class Config:
        from_attributes = True

class MessageProcessingResponse(BaseModel):
    """Response for asynchronous message processing"""
    request_id: str = Field(..., description="Unique identifier for the request")
    status: str = Field(..., description="Status of the request (processing/completed/failed)")
    message: str = Field(..., description="Status message or error description") 