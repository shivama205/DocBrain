from sqlalchemy import Column, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.sql.base import BaseModel

class Message(BaseModel):
    """Message SQLAlchemy model"""
    conversation_id = Column(String(36), ForeignKey('conversation.id'), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)
    sources = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default='completed')

    # Relationships
    conversation = relationship("Conversation", back_populates="messages") 