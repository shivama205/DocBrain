from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.base_class import BaseModel

class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    """Message SQLAlchemy model"""
    __tablename__ = "messages"
    
    content = Column(Text, nullable=False)
    role = Column(String, nullable=False, default=MessageRole.USER.value)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Optional fields for tracking sources
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=True)
    