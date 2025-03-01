from typing import Optional, List, Type, TypeVar
from datetime import datetime
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from pydantic import BaseModel
from app.core.config import settings

# Import the base class and models
from app.db.base_class import Base
from app.db.models.user import User
from app.db.models.knowledge_base import KnowledgeBase, Document
from app.db.models.conversation import Conversation
from app.db.models.message import Message

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

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

class Database:
    def __init__(self):
        """Initialize database connection"""
        self.engine = engine
        self.SessionLocal = SessionLocal
        self._initialize_db()

    def _initialize_db(self):
        """Initialize the database with required tables"""
        try:
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @contextmanager
    def get_session(self):
        """Get a database session using context manager"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def create(self, table: str, model: BaseModel) -> BaseModel:
        """Create a new record"""
        try:
            with self.get_session() as session:
                db_model = self._convert_to_db_model(table, model)
                session.add(db_model)
                session.commit()
                session.refresh(db_model)
                return self._convert_to_pydantic(db_model, type(model))
        except Exception as e:
            logger.error(f"Failed to create record in {table}: {e}")
            raise

    def get(self, table: str, model_class: Type[T], id: str) -> Optional[T]:
        """Get a single record by ID"""
        try:
            with self.get_session() as session:
                db_model = self._get_db_model_class(table)
                result = session.query(db_model).filter(db_model.id == id).first()
                if not result:
                    return None
                return self._convert_to_pydantic(result, model_class)
        except Exception as e:
            logger.error(f"Failed to get record from {table}: {e}")
            raise

    def list(self, table: str, model_class: Type[T], filter_dict: Optional[dict] = None, limit: Optional[int] = None) -> List[T]:
        """
        List records with optional filtering and limit
        
        Args:
            table: The table name
            model_class: The Pydantic model class
            filter_dict: Optional dictionary of filters
            limit: Optional maximum number of records to return
            
        Returns:
            List of model instances
        """
        try:
            with self.get_session() as session:
                db_model = self._get_db_model_class(table)
                query = session.query(db_model)
                
                if filter_dict:
                    for key, value in filter_dict.items():
                        query = query.filter(getattr(db_model, key) == value)
                
                # Apply limit if provided
                if limit is not None:
                    query = query.limit(limit)
                
                results = query.all()
                return [self._convert_to_pydantic(result, model_class) for result in results]
        except Exception as e:
            logger.error(f"Failed to list records from {table}: {e}")
            raise

    def update(self, table: str, id: str, update_data: dict) -> bool:
        """Update a record"""
        try:
            with self.get_session() as session:
                db_model = self._get_db_model_class(table)
                result = session.query(db_model).filter(db_model.id == id)
                if not result.first():
                    return False
                result.update(update_data)
                return True
        except Exception as e:
            logger.error(f"Failed to update record in {table}: {e}")
            raise

    def delete(self, table: str, id: str) -> bool:
        """Delete a record"""
        try:
            with self.get_session() as session:
                db_model = self._get_db_model_class(table)
                result = session.query(db_model).filter(db_model.id == id).first()
                if not result:
                    return False
                session.delete(result)
                return True
        except Exception as e:
            logger.error(f"Failed to delete record from {table}: {e}")
            raise

    def delete_many(self, table: str, filter_dict: dict) -> bool:
        """Delete multiple records based on filter criteria"""
        try:
            with self.get_session() as session:
                db_model = self._get_db_model_class(table)
                query = session.query(db_model)
                for key, value in filter_dict.items():
                    query = query.filter(getattr(db_model, key) == value)
                query.delete()
                return True
        except Exception as e:
            logger.error(f"Failed to delete records from {table}: {e}")
            raise

    def _get_db_model_class(self, table: str):
        """Get the SQLAlchemy model class for a table"""
        models = {
            'users': User,
            'knowledge_bases': KnowledgeBase,
            'documents': Document,
            'conversations': Conversation,
            'messages': Message
        }
        return models[table]

    def _convert_to_db_model(self, table: str, pydantic_model: BaseModel):
        """Convert a Pydantic model to a SQLAlchemy model"""
        db_model_class = self._get_db_model_class(table)
        return db_model_class(**pydantic_model.model_dump())

    def _convert_to_pydantic(self, db_model, pydantic_class: Type[T]) -> T:
        """Convert a SQLAlchemy model to a Pydantic model"""
        # Convert SQLAlchemy model to dict, handling datetime conversion
        data = {}
        for column in db_model.__table__.columns:
            value = getattr(db_model, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            data[column.name] = value
        return pydantic_class(**data)

# Create global database instance
db = Database() 