from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class Source(BaseModel):
    """Source document information"""
    score: float = Field(..., description="Relevance score of the source")
    document_id: str = Field(..., description="ID of the source document")
    title: str = Field(..., description="Title of the source document")
    content: str = Field(..., description="Relevant content from the document")
    chunk_index: int = Field(..., description="Index of the chunk in the document")

class MessageBase(BaseModel):
    """Base message attributes"""
    content: str = Field(..., description="Content of the message")
    type: MessageType = Field(..., description="Type of message (user/assistant)")

class MessageCreate(MessageBase):
    """Attributes for creating a new message"""
    top_k: int = Field(5, description="Number of most relevant chunks to return", ge=1, le=20)
    similarity_cutoff: float = Field(0.3, description="Minimum similarity score for results", ge=0, le=1)

class MessageResponse(MessageBase):
    """Response model for messages"""
    id: str = Field(..., description="Unique identifier for the message")
    conversation_id: str = Field(..., description="ID of the conversation this message belongs to")
    sources: Optional[List[Source]] = Field(None, description="Source documents used for assistant's response")
    created_at: datetime = Field(..., description="When the message was created")
    status: str = Field(..., description="Status of the message processing (processing/completed/failed)")

class MessageProcessingResponse(BaseModel):
    """Response for asynchronous message processing"""
    request_id: str = Field(..., description="Unique identifier for the request")
    status: str = Field(..., description="Status of the request (processing/completed/failed)")
    message: str = Field(..., description="Status message or error description") 