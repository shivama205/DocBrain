from enum import Enum
from typing import Optional, List
from pydantic import EmailStr, Field

from app.models.base import DBModel

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class User(DBModel):
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