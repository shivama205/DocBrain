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
    messages = relationship("Message", cascade="all, delete-orphan")
