from typing import List, Optional
import logging
from sqlalchemy.orm import Session
from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse

logger = logging.getLogger(__name__)

class UserRepository:
    @staticmethod
    async def create(user_data: User, db: Session) -> UserResponse:
        """Create a new user"""
        try:
            # Add user to session and commit
            db.add(user_data)
            db.commit()
            db.refresh(user_data)
            
            # Convert to response model
            return UserResponse.model_validate(user_data)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create user: {e}")
            raise
    
    @staticmethod
    async def get_by_id(user_id: str, db: Session) -> Optional[UserResponse]:
        """Get user by ID"""
        try:
            db_user = db.query(User).filter(User.id == user_id).first()
            if db_user is None:
                return None
            return UserResponse.model_validate(db_user)
        except Exception as e:
            logger.error(f"Failed to get user by ID {user_id}: {e}")
            raise
    
    @staticmethod
    async def get_by_email(email: str, db: Session) -> Optional[UserResponse]:
        """Get user by email"""
        try:
            db_user = db.query(User).filter(User.email == email).first()
            if db_user is None:
                return None
            return UserResponse.model_validate(db_user)
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise
    
    @staticmethod
    async def list_all(db: Session) -> List[UserResponse]:
        """List all users"""
        try:
            db_users = db.query(User).all()
            return [UserResponse.model_validate(user) for user in db_users]
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            raise
    
    @staticmethod
    async def update(user_id: str, update_data: UserUpdate, db: Session) -> Optional[UserResponse]:
        """Update user"""
        try:
            # Get the user
            db_user = db.query(User).filter(User.id == user_id).first()
            if db_user is None:
                return None
            
            # Update user attributes
            update_dict = update_data.model_dump(exclude_unset=True)
            for key, value in update_dict.items():
                setattr(db_user, key, value)
            
            # Commit changes
            db.commit()
            db.refresh(db_user)
            
            return UserResponse.model_validate(db_user)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update user {user_id}: {e}")
            raise
    
    @staticmethod
    async def delete(user_id: str, db: Session) -> bool:
        """Delete user"""
        try:
            db_user = db.query(User).filter(User.id == user_id).first()
            if db_user is None:
                return False
            
            db.delete(db_user)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete user {user_id}: {e}")
            raise 