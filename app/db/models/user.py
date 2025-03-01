from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, String, Boolean, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from pydantic import EmailStr, Field

from app.db.base_class import BaseModel

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

# SQLAlchemy User model
class User(BaseModel):
    """User SQLAlchemy model"""
    __tablename__ = "users"
    
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.USER.value)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    
    # Relationships
    knowledge_bases = relationship("KnowledgeBase", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")

# Pydantic User model for API
class UserModel:
    """Pydantic User model for API"""
    email: EmailStr
    hashed_password: str
    full_name: str
    role: UserRole = UserRole.USER
    is_verified: bool = False
    verification_token: Optional[str] = None
    reset_token: Optional[str] = None
    api_keys: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "role": "user",
                "is_verified": True
            }
        } 