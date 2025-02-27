from typing import List, Optional
from fastapi import HTTPException
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate

class UserService:
    def __init__(self):
        self.repository = UserRepository()

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        # Check if email already exists
        if await self.repository.get_by_email(user_data.email):
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user with hashed password
        user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            role=user_data.role or UserRole.USER
        )
        return await self.repository.create(user)

    async def get_user(self, user_id: str) -> User:
        """Get user by ID"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return await self.repository.get_by_email(email)

    async def list_users(self, current_user: User) -> List[User]:
        """List all users (admin only)"""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Not enough privileges")
        return await self.repository.list_all()

    async def update_user(
        self,
        user_id: str,
        user_update: UserUpdate,
        current_user: User
    ) -> User:
        """Update user"""
        # Check permissions
        if current_user.role != UserRole.ADMIN and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Not enough privileges")
        
        # Get existing user
        user = await self.get_user(user_id)
        
        # Prepare update data
        update_data = user_update.model_dump(exclude_unset=True)
        
        # Hash new password if provided
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        # Only admin can update role
        if "role" in update_data and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Not enough privileges to change role")
        
        # Update user
        updated_user = await self.repository.update(user_id, update_data)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return updated_user

    async def delete_user(self, user_id: str, current_user: User) -> None:
        """Delete user (admin only)"""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Not enough privileges")
        
        if not await self.repository.delete(user_id):
            raise HTTPException(status_code=404, detail="User not found")

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password"""
        user = await self.repository.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user 