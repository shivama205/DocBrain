from typing import Annotated, Optional
from pydantic import BaseModel, EmailStr, Field
from app.db.models.user import UserRole

class UserBase(BaseModel):
    email: EmailStr = Field(..., alias="email")
    full_name: str = Field(..., alias="full_name")
    role: Optional[UserRole] = Field(default=UserRole.USER)

class UserCreate(UserBase):
    password: str = Field(..., alias="password")

class UserLogin(BaseModel):
    email: EmailStr = Field(..., alias="email")
    password: str = Field(..., alias="password")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(default=None, alias="email")
    full_name: Optional[str] = Field(default=None, alias="full_name")
    password: Optional[str] = Field(default=None, alias="password")
    role: Optional[UserRole] = Field(default=None, alias="role")

class Token(BaseModel):
    access_token: str = Field(..., alias="access_token")
    token_type: str = Field(default="bearer", alias="token_type")

class TokenData(BaseModel):
    email: Optional[str] = Field(default=None, alias="email")
    role: Optional[str] = Field(default=None, alias="role")

class PasswordReset(BaseModel):
    email: EmailStr = Field(..., alias="email")

class PasswordResetConfirm(BaseModel):
    token: str = Field(..., alias="token")
    new_password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    id: str = Field(..., alias="id")
    is_active: bool = Field(..., alias="is_active")
    hashed_password: str = Annotated[str, Field(exclude=True)]

    class Config:
        from_attributes = True 
        