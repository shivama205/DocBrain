from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.sql.base import BaseModel

class Conversation(BaseModel):
    """Conversation SQLAlchemy model"""
    title = Column(String(255), nullable=False)
    knowledge_base_id = Column(String(36), ForeignKey('knowledgebase.id'), nullable=False)
    owner_id = Column(String(36), ForeignKey('user.id'), nullable=False)

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="conversations")
    owner = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan") 