from typing import List, Optional
import logging
from app.db.database import db
from app.models.user import User

logger = logging.getLogger(__name__)

class UserRepository:
    @staticmethod
    async def create(user: User) -> User:
        """Create a new user"""
        try:
            return db.create("users", user)
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    @staticmethod
    async def get_by_id(user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            return db.get("users", User, user_id)
        except Exception as e:
            logger.error(f"Failed to get user by ID {user_id}: {e}")
            raise
    
    @staticmethod
    async def get_by_email(email: str) -> Optional[User]:
        """Get user by email"""
        try:
            # Use filter_dict to query by email (DuckDB will use the UNIQUE index)
            users = db.list("users", User, {"email": email})
            return users[0] if users else None
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise
    
    @staticmethod
    async def list_all() -> List[User]:
        """List all users"""
        try:
            return db.list("users", User)
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            raise
    
    @staticmethod
    async def update(user_id: str, update_data: dict) -> Optional[User]:
        """Update user"""
        try:
            if db.update("users", user_id, update_data):
                return await UserRepository.get_by_id(user_id)
            return None
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            raise
    
    @staticmethod
    async def delete(user_id: str) -> bool:
        """Delete user"""
        try:
            return db.delete("users", user_id)
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            raise 