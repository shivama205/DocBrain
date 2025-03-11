from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserWithPermissions
from app.services.user_service import UserService
from app.api.deps import get_current_user
from app.db.database import get_db
from app.core.permissions import get_permissions_for_role, Permission, check_permission

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
    db: Session = Depends(get_db),
    _: User = Depends(check_permission(Permission.VIEW_USERS))
):
    """
    List all users (admin and owner roles).
    """
    user_service = UserService(db)
    return await user_service.list_users(current_user)

@router.get("/me", response_model=UserWithPermissions)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information with permissions.
    Returns detailed information about the current user, including their role and permissions.
    """
    user_service = UserService(db)
    user = await user_service.get_user(str(current_user.id))
    
    # Get permissions for the user's role
    permissions = [perm.value for perm in get_permissions_for_role(user.role)]
    
    # Create a UserWithPermissions response
    return {
        **user.dict(),
        "permissions": permissions
    }

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