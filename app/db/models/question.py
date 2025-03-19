from enum import Enum
from typing import Optional
from pydantic import Field
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func

from app.db.base_class import BaseModel
from app.db.models.base import DBModel

class AnswerType(str, Enum):
    DIRECT = "DIRECT"
    SQL_QUERY = "SQL_QUERY"

class QuestionStatus(str, Enum):
    PENDING = "PENDING"
    INGESTING = "INGESTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# SQLAlchemy model for database operations
class Question(BaseModel):
    """SQLAlchemy model for questions in a knowledge base"""
    __tablename__ = "questions"
    
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    answer_type = Column(String, nullable=False)
    status = Column(String, default=QuestionStatus.PENDING.value)
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

# Pydantic model for API validation and serialization
class QuestionModel(DBModel):
    """Pydantic model for questions in a knowledge base"""
    question: str
    answer: str
    answer_type: AnswerType
    status: QuestionStatus = Field(default=QuestionStatus.PENDING)
    knowledge_base_id: str
    user_id: str

    class Config:
        from_attributes = True 