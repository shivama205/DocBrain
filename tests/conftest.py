"""
Pytest configuration file with shared fixtures.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base
from app.core.config import settings
from app.api.deps import get_db

# Create a test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create a test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create a TestingSessionLocal
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """
    Create a fresh database for each test.
    """
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    
    # Create a new session for the test
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        
    # Drop the database tables
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """
    Create a test client with a database session.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    # Override the get_db dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Create a test client
    with TestClient(app) as client:
        yield client
    
    # Remove the override
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(client, db):
    """
    Create a test user.
    """
    from app.db.models.user import User
    from app.core.security import get_password_hash
    
    # Create a test user
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("password"),
        is_active=True,
    )
    
    # Add the user to the database
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def test_knowledge_base(client, db, test_user):
    """
    Create a test knowledge base.
    """
    from app.db.models.knowledge_base import KnowledgeBase
    
    # Create a test knowledge base
    kb = KnowledgeBase(
        name="Test Knowledge Base",
        description="A test knowledge base",
        user_id=test_user.id,
    )
    
    # Add the knowledge base to the database
    db.add(kb)
    db.commit()
    db.refresh(kb)
    
    return kb
