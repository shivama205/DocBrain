from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.sql import func

from app.db.base_class import BaseModel


class Conversation(BaseModel):
    """Conversation SQLAlchemy model"""

    __tablename__ = "conversations"

    title = Column(String(500), nullable=False)
    user_id = Column(String(255), ForeignKey("users.id"))
    knowledge_base_id = Column(String(255), ForeignKey("knowledge_bases.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
