from enum import Enum
from typing import List, Optional

from pydantic import EmailStr, Field
from sqlalchemy import Boolean, Column, String

from app.db.base_class import BaseModel


class UserRole(str, Enum):
    ADMIN = "admin"
    OWNER = "owner"
    USER = "user"


# SQLAlchemy User model
class User(BaseModel):
    """User SQLAlchemy model"""

    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.USER.value)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    reset_token = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)


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
                "is_verified": True,
            }
        }
