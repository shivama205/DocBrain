from sqlalchemy import Column, String, Boolean, JSON
from sqlalchemy.orm import relationship
from app.models.sql.base import BaseModel

class User(BaseModel):
    """User SQLAlchemy model"""
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    reset_token = Column(String(255), nullable=True)
    api_keys = Column(JSON, nullable=True, default=list)  # Store as JSON array

    # Relationships
    knowledge_bases = relationship("KnowledgeBase", back_populates="owner")
    uploaded_documents = relationship("Document", back_populates="uploader")
    conversations = relationship("Conversation", back_populates="owner") 