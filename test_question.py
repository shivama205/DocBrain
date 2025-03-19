import asyncio
from fastapi import FastAPI
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.question import Question, QuestionStatus, AnswerType
from app.repositories.question_repository import QuestionRepository
from app.schemas.question import QuestionResponse

async def test_create_question():
    # Get database session
    db_session = next(get_db())
    
    # Create repository
    repo = QuestionRepository()
    
    # Create a test question
    question = Question(
        question="What is the capital of France?",
        answer="The capital of France is Paris.",
        answer_type=AnswerType.DIRECT.value,
        status=QuestionStatus.PENDING.value,
        knowledge_base_id="YOUR_KNOWLEDGE_BASE_ID",  # Replace with a valid KB ID
        user_id="YOUR_USER_ID"  # Replace with a valid user ID
    )
    
    try:
        # Create question
        result = await repo.create(question, db_session)
        print(f"Successfully created question: {result.id}")
        print(f"Status: {result.status}")
        print(f"Answer type: {result.answer_type}")
        
        # Test getting the question
        retrieved = await repo.get_by_id(result.id, db_session)
        print(f"Retrieved question: {retrieved.question}")
        
        # Test setting status
        updated = await repo.set_ingesting(result.id, db_session)
        print(f"Updated status: {updated.status}")
        
        return True
    except Exception as e:
        print(f"Error creating question: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_create_question())
    print(f"Test {'passed' if result else 'failed'}") 