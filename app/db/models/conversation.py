from sqlalchemy import Column, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import BaseModel

class Conversation(BaseModel):
    """Conversation SQLAlchemy model"""
    __tablename__ = "conversations"
    
    title = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    messages = relationship("Message", cascade="all, delete-orphan")
