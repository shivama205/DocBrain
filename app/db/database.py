from typing import Generator
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Import the base class
from app.db.base_class import Base

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True,  # Enable connection health checks
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    """Initialize the database with required tables"""
    try:
        # Import all models here to ensure they are registered with the Base metadata
        # This is important for creating tables
        from app.db.models.user import User
        from app.db.models.knowledge_base import KnowledgeBase, Document
        from app.db.models.conversation import Conversation
        from app.db.models.message import Message
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.
    
    This function is used as a dependency in FastAPI endpoints to get a database session.
    It yields a session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 