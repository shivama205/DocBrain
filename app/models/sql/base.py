from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declared_attr
from app.db.database import Base

class BaseModel(Base):
    """Base SQLAlchemy model with common fields"""
    __abstract__ = True

    id = Column(String(36), primary_key=True, index=True)  # UUID length is 36 characters
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower() 