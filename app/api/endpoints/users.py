from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService
from app.api.deps import get_current_user
from app.db.database import get_db

router = APIRouter()

@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user.
    """
    user_service = UserService(db)
    return await user_service.create_user(user_data)

@router.get("", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only).
    """
    user_service = UserService(db)
    return await user_service.list_users(current_user)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information.
    """
    user_service = UserService(db)
    return await user_service.get_user(str(current_user.id))

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user by ID.
    """
    user_service = UserService(db)
    return await user_service.get_user(user_id)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user.
    """
    user_service = UserService(db)
    return await user_service.update_user(user_id, user_update, current_user)

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user (admin only).
    """
    user_service = UserService(db)
    await user_service.delete_user(user_id, current_user)
    return {"message": "User deleted successfully"} 