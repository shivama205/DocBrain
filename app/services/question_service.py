from typing import List, Optional
import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session
from celery import Celery

from app.db.models.question import Question, QuestionStatus, AnswerType
from app.repositories.question_repository import QuestionRepository
from app.services.rag.vector_store import VectorStore
from app.services.knowledge_base_service import KnowledgeBaseService
from app.schemas.question import QuestionResponse, QuestionCreate, QuestionUpdate
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

class QuestionService:
    def __init__(
        self,
        question_repository: QuestionRepository,
        vector_store: VectorStore,
        knowledge_base_service: KnowledgeBaseService,
        celery_app: Celery,
        db: Session
    ):
        self.question_repository = question_repository
        self.vector_store = vector_store
        self.kb_service = knowledge_base_service
        self.celery_app = celery_app
        self.db = db

    async def create_question(
        self,
        kb_id: str,
        payload: QuestionCreate,
        current_user: UserResponse
    ) -> QuestionResponse:
        """Create a new question in a knowledge base"""
        try:
            # Check knowledge base access
            await self.kb_service.get_knowledge_base(kb_id, current_user)
            
            # Create question record
            question = Question(
                question=payload.question,
                answer=payload.answer,
                answer_type=payload.answer_type.value,  # Use .value for enum
                status=QuestionStatus.PENDING.value,    # Use .value for enum
                knowledge_base_id=kb_id,
                user_id=str(current_user.id)
            )
            
            # Save to database
            created_question = await self.question_repository.create(question, self.db)
            
            # Queue question ingestion task
            self.celery_app.send_task(
                'app.worker.tasks.initiate_question_ingestion',
                args=[created_question.id]
            )
            
            return created_question
            
        except Exception as e:
            logger.error(f"Failed to create question in service: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_question(
        self,
        question_id: str,
        current_user: UserResponse
    ) -> QuestionResponse:
        """Get a question by ID"""
        question = await self.question_repository.get_by_id(question_id, self.db)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Check knowledge base access
        await self.kb_service.get_knowledge_base(question.knowledge_base_id, current_user)
        
        return question

    async def list_questions(
        self,
        kb_id: str,
        current_user: UserResponse,
        skip: int = 0,
        limit: int = 100
    ) -> List[QuestionResponse]:
        """List all questions for a knowledge base"""
        # Check knowledge base access
        await self.kb_service.get_knowledge_base(kb_id, current_user)
        
        questions = await self.question_repository.list_by_knowledge_base(
            kb_id, self.db, skip, limit
        )
        return questions

    async def update_question(
        self,
        question_id: str,
        question_update: QuestionUpdate,
        current_user: UserResponse
    ) -> QuestionResponse:
        """Update a question"""
        # Get existing question
        question = await self.question_repository.get_by_id(question_id, self.db)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Check knowledge base access
        await self.kb_service.get_knowledge_base(question.knowledge_base_id, current_user)
        
        # Update question
        update_data = question_update.model_dump(exclude_unset=True)
        
        # If content changes, set status back to PENDING for re-ingestion
        if "question" in update_data or "answer" in update_data:
            update_data["status"] = QuestionStatus.PENDING.value
        
        updated_question = await self.question_repository.update(
            question_id, update_data, self.db
        )
        
        # If content changed, queue re-ingestion
        if "question" in update_data or "answer" in update_data:
            self.celery_app.send_task(
                'app.worker.tasks.initiate_question_ingestion',
                args=[question_id]
            )
        
        return updated_question

    async def delete_question(
        self,
        question_id: str,
        current_user: UserResponse
    ) -> None:
        """Delete a question"""
        # Get existing question
        question = await self.question_repository.get_by_id(question_id, self.db)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Check knowledge base access
        await self.kb_service.get_knowledge_base(question.knowledge_base_id, current_user)
        
        # Delete question from vector store
        self.celery_app.send_task(
            'app.worker.tasks.initiate_question_vector_deletion',
            args=[question_id, question.knowledge_base_id]
        )
        
        # Delete question from database
        await self.question_repository.delete(question_id, self.db)

    async def get_question_status(
        self,
        question_id: str,
        current_user: UserResponse
    ) -> QuestionStatus:
        """Get the status of a question"""
        question = await self.question_repository.get_by_id(question_id, self.db)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Check knowledge base access
        await self.kb_service.get_knowledge_base(question.knowledge_base_id, current_user)
        
        return question.status 