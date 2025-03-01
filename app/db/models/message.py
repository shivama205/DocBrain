from sqlalchemy import Column, String, Text, ForeignKey, Boolean, Integer
from sqlalchemy.orm import relationship
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
    
    # Optional fields for tracking sources
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", back_populates="messages")
    knowledge_base = relationship("KnowledgeBase", back_populates="messages")
    document = relationship("Document", back_populates="messages")

# Add the relationship to User model
from app.db.models.user import User
User.messages = relationship("Message", back_populates="user")

# Add the relationship to KnowledgeBase model
from app.db.models.knowledge_base import KnowledgeBase
KnowledgeBase.messages = relationship("Message", back_populates="knowledge_base")

# Add the relationship to Document model
from app.db.models.knowledge_base import Document
Document.messages = relationship("Message", back_populates="document") 