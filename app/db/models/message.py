from sqlalchemy import Column, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
import enum

from app.db.base_class import BaseModel

class MessageKind(str, enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"

class MessageContentType(str, enum.Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"

class MessageStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class Message(BaseModel):
    """Message SQLAlchemy model"""
    __tablename__ = "messages"
    
    content = Column(Text, nullable=False)
    content_type = Column(String, nullable=False, default=MessageContentType.TEXT.value)
    kind = Column(String, nullable=False, default=MessageKind.USER.value)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    sources = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Optional fields for tracking sources
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"))
    