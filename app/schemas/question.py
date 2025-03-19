from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class AnswerType(str, Enum):
    DIRECT = "DIRECT"
    SQL_QUERY = "SQL_QUERY"

class QuestionStatus(str, Enum):
    PENDING = "PENDING"
    INGESTING = "INGESTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class QuestionBase(BaseModel):
    """Base schema for question data"""
    question: str
    answer: str
    answer_type: AnswerType

class QuestionCreate(QuestionBase):
    """Schema for creating a new question"""
    pass

class QuestionUpdate(BaseModel):
    """Schema for updating an existing question"""
    question: Optional[str] = None
    answer: Optional[str] = None
    answer_type: Optional[AnswerType] = None

class QuestionResponse(QuestionBase):
    """Schema for question response"""
    id: str
    status: QuestionStatus
    knowledge_base_id: str
    user_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def model_validate(cls, obj):
        """Custom validation to handle SQLAlchemy model to Pydantic conversion"""
        # Convert string status to enum
        if hasattr(obj, 'status') and isinstance(obj.status, str):
            status = obj.status
            obj.status = QuestionStatus(status)
        
        # Convert string answer_type to enum
        if hasattr(obj, 'answer_type') and isinstance(obj.answer_type, str):
            answer_type = obj.answer_type
            obj.answer_type = AnswerType(answer_type)
            
        return super().model_validate(obj) 