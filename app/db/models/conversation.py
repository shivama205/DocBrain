from sqlalchemy import Column, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.db.base_class import BaseModel

class Conversation(BaseModel):
    """Conversation SQLAlchemy model"""
    __tablename__ = "conversations"
    
    title = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    knowledge_base = relationship("KnowledgeBase", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

# Add the relationship to User model
from app.db.models.user import User
User.conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

# Add the relationship to KnowledgeBase model
from app.db.models.knowledge_base import KnowledgeBase
KnowledgeBase.conversations = relationship("Conversation", back_populates="knowledge_base") 