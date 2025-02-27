from sqlalchemy import Column, String, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.sql.base import BaseModel

class KnowledgeBase(BaseModel):
    """KnowledgeBase SQLAlchemy model"""
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    owner_id = Column(String(36), ForeignKey('user.id'), nullable=False)
    shared_with = Column(JSON, nullable=True, default=list)  # Store as JSON array
    document_count = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)

    # Relationships
    owner = relationship("User", back_populates="knowledge_bases")
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="knowledge_base", cascade="all, delete-orphan") 