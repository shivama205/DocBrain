from typing import List, Optional, Dict, Any
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models.question import Question, QuestionStatus
from app.schemas.question import QuestionResponse

logger = logging.getLogger(__name__)

class QuestionRepository:
    """Repository for question operations"""
    
    @staticmethod
    async def create(question: Question, db: Session) -> QuestionResponse:
        """
        Create a new question.
        
        Args:
            question: Question instance
            db: Database session
            
        Returns:
            Created question
        """
        try:
            db.add(question)
            db.commit()
            db.refresh(question)
            return QuestionResponse.model_validate(question)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create question: {e}")
            raise
    
    @staticmethod
    async def get_by_id(question_id: str, db: Session) -> Optional[QuestionResponse]:
        """
        Get a question by ID.
        
        Args:
            question_id: Question ID
            db: Database session
            
        Returns:
            Question if found, None otherwise
        """
        try:
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                return None
            return QuestionResponse.model_validate(question)
        except Exception as e:
            logger.error(f"Failed to get question by ID: {e}")
            raise
    
    @staticmethod
    async def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[QuestionResponse]:
        """
        List all questions.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of questions
        """
        try:
            questions = db.query(Question).offset(skip).limit(limit).all()
            return [QuestionResponse.model_validate(q) for q in questions]
        except Exception as e:
            logger.error(f"Failed to list all questions: {e}")
            raise
    
    @staticmethod
    async def list_by_knowledge_base(
        knowledge_base_id: str,
        db: Session,
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[QuestionResponse]:
        """
        List questions by knowledge base ID.
        
        Args:
            knowledge_base_id: Knowledge base ID
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status
            
        Returns:
            List of questions
        """
        try:
            query = db.query(Question).filter(Question.knowledge_base_id == knowledge_base_id)
            
            if status:
                query = query.filter(Question.status == status)
                
            questions = query.offset(skip).limit(limit).all()
            return [QuestionResponse.model_validate(q) for q in questions]
        except Exception as e:
            logger.error(f"Failed to list questions by knowledge base: {e}")
            raise
    
    @staticmethod
    async def set_ingesting(question_id: str, db: Session) -> Optional[QuestionResponse]:
        """Set question status to INGESTING"""
        try:
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                return None
            
            question.status = QuestionStatus.INGESTING.value
            db.commit()
            db.refresh(question)
            
            return QuestionResponse.model_validate(question)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set question to INGESTING: {e}")
            raise
    
    @staticmethod
    async def set_completed(question_id: str, db: Session) -> Optional[QuestionResponse]:
        """Set question status to COMPLETED"""
        try:
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                return None
            
            question.status = QuestionStatus.COMPLETED.value
            db.commit()
            db.refresh(question)
            
            return QuestionResponse.model_validate(question)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set question to COMPLETED: {e}")
            raise
    
    @staticmethod
    async def set_failed(question_id: str, db: Session) -> Optional[QuestionResponse]:
        """Set question status to FAILED"""
        try:
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                return None
            
            question.status = QuestionStatus.FAILED.value
            db.commit()
            db.refresh(question)
            
            return QuestionResponse.model_validate(question)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set question to FAILED: {e}")
            raise
    
    @staticmethod
    async def update(question_id: str, update_data: Dict[str, Any], db: Session) -> Optional[QuestionResponse]:
        """
        Update a question.
        
        Args:
            question_id: Question ID
            update_data: Data to update
            db: Database session
            
        Returns:
            Updated question
        """
        try:
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                return None
            
            for key, value in update_data.items():
                if hasattr(question, key):
                    setattr(question, key, value)
            
            question.update_timestamp()
            db.commit()
            db.refresh(question)
            
            return QuestionResponse.model_validate(question)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update question: {e}")
            raise
    
    @staticmethod
    async def delete(question_id: str, db: Session) -> bool:
        """
        Delete a question.
        
        Args:
            question_id: Question ID
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                return False
            
            db.delete(question)
            db.commit()
            
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete question: {e}")
            raise 