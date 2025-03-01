from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class DocumentBase(BaseModel):
    """Base document schema"""
    title: str
    description: Optional[str] = ""
    content_type: str
    knowledge_base_id: str

class DocumentCreate(DocumentBase):
    """Schema for creating a document"""
    content: str  # Base64 encoded content
    status: str = "PENDING"
    user_id: str

class DocumentUpdate(BaseModel):
    """Schema for updating a document"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    processed_chunks: Optional[int] = None
    summary: Optional[str] = None

class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: str
    status: str
    error_message: Optional[str] = None
    processed_chunks: Optional[int] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: str
    
    class Config:
        orm_mode = True 