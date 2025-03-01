from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.base_class import BaseModel

class DocumentStatus(str, enum.Enum):
    """Document processing status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Document(BaseModel):
    """Document model"""
    __tablename__ = "documents"
    
    title = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False)
    content = Column(Text, nullable=False)  # Base64 encoded content
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, default=DocumentStatus.PENDING.value)
    error_message = Column(Text, nullable=True)
    processed_chunks = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Company Policy.pdf",
                "file_name": "policy.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
                "status": "completed",
                "vector_ids": ["vec1", "vec2"],
                "summary": "This is a summary of the document",
                "uploaded_by": "user123"
            }
        } 

class KnowledgeBase(BaseModel):
    """Knowledge base model"""
    __tablename__ = "knowledge_bases"
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    