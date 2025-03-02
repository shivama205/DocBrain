from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.db.models.knowledge_base import DocumentStatus, DocumentType

class DocumentBase(BaseModel):
    """Base document schema"""
    title: str = Field(..., description="Title of the document")
    content_type: DocumentType = Field(..., description="Content type of the document")
    knowledge_base_id: str = Field(..., description="Knowledge base ID of the document")

class DocumentUpload(DocumentBase):
    """Schema for uploading a document"""
    content: bytes = Field(..., description="Content of the document")

class DocumentUpdate(BaseModel):
    """Schema for updating a document"""
    title: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    processed_chunks: Optional[int] = None
    summary: Optional[str] = None

class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: str = Field(..., description="ID of the document")
    user_id: str = Field(..., description="User ID of the document")
    content: bytes = Field(..., description="Content of the document", exclude=True)
    size_bytes: int = Field(..., description="Size of the document in bytes")
    status: DocumentStatus = Field(..., description="Status of the document")
    error_message: Optional[str] = Field(default=None, description="Error message if the document processing failed")
    processed_chunks: Optional[int] = Field(default=None, description="Number of chunks processed")
    summary: Optional[str] = Field(default=None, description="Summary of the document")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")
    
    class Config:
        from_attributes = True
