from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
import uuid

# Create base class for SQLAlchemy models
Base = declarative_base()

# Define a base model class with common fields
class BaseModel(Base):
    """Base model class with common fields for all SQLAlchemy models"""
    __abstract__ = True
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now()) 