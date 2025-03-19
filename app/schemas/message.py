from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from enum import Enum
import json

from app.db.models.message import MessageContentType, MessageKind, MessageStatus

class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageSource(BaseModel):
    """Source document or question information"""
    score: float = Field(..., description="Relevance score of the source")
    content: str = Field(..., description="Relevant content from the document or question")
    
    # Document-specific fields (optional for questions)
    document_id: Optional[str] = Field(None, description="ID of the source document")
    title: Optional[str] = Field(None, description="Title of the source document")
    chunk_index: Optional[int] = Field(None, description="Index of the chunk in the document")
    
    # Question-specific fields (optional for documents)
    question_id: Optional[str] = Field(None, description="ID of the source question")
    question: Optional[str] = Field(None, description="The question that was matched")
    answer: Optional[str] = Field(None, description="The answer for the matched question")
    answer_type: Optional[str] = Field(None, description="Type of answer (DIRECT, SQL_QUERY, etc.)")

class MessageBase(BaseModel):
    """Base message attributes"""
    content: str = Field(..., description="Content of the message")
    content_type: MessageContentType = Field(..., description="Type of message (TEXT/IMAGE/AUDIO/VIDEO/DOCUMENT)")

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
    message_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata including routing information")
    status: MessageStatus = Field(..., description="Status of the message (RECEIVED/PROCESSING/SENT/FAILED)")
    created_at: datetime = Field(..., description="When the message was created")
    updated_at: datetime = Field(..., description="When the message was last updated")

    @model_validator(mode='after')
    def parse_message_metadata(self) -> 'MessageResponse':
        """Parse message_metadata if it's a string"""
        if self.message_metadata and isinstance(self.message_metadata, str):
            try:
                self.message_metadata = json.loads(self.message_metadata)
            except json.JSONDecodeError:
                # If we can't parse it as JSON, set it to None
                self.message_metadata = None
        return self

    class Config:
        from_attributes = True

class MessageProcessingResponse(BaseModel):
    """Response for asynchronous message processing"""
    request_id: str = Field(..., description="Unique identifier for the request")
    status: str = Field(..., description="Status of the request (processing/completed/failed)")
    message: str = Field(..., description="Status message or error description") 