from sqlalchemy import Column, LargeBinary, String, Text, ForeignKey, DateTime, Integer, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.base_class import BaseModel

class DocumentStatus(str, enum.Enum):
    """Document processing status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class DocumentType(str, enum.Enum):
    """Document type"""
    PDF = "application/pdf"
    JPG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    TIFF = "image/tiff"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    DOC = "application/msword"
    CSV = "text/csv"
    EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    MARKDOWN = "text/markdown"
    MD = "text/markdown"
    TXT = "text/plain"
    HTML = "text/html"

class Document(BaseModel):
    """Document model"""
    __tablename__ = "documents"
    
    title = Column(String, nullable=False)
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False)
    content = Column(LargeBinary, nullable=False)  # Base64 encoded content
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
                "knowledge_base_id": "kb123",
                "user_id": "user123",
                "content": "base64 encoded content",
                "content_type": "application/pdf",
                "size_bytes": 1024,
                "status": "completed",
                "summary": "This is a summary of the document",
            }
        } 

# Knowledge base sharing association table
knowledge_base_sharing = Table(
    "knowledge_base_sharing",
    BaseModel.metadata,
    Column("knowledge_base_id", String, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=func.now()),
)

class KnowledgeBase(BaseModel):
    """Knowledge base model"""
    __tablename__ = "knowledge_bases"
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Define relationship to users that this knowledge base is shared with
    shared_with = relationship("User", secondary=knowledge_base_sharing, lazy="joined", backref="shared_knowledge_bases")
    