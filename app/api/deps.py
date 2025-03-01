from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.user import User
from app.core.config import settings
from app.schemas.user import UserResponse

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserResponse:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
            

        # get db 
        print(f"Getting user {user_id} from db")
        user = db.query(User).filter(User.id == user_id).first()
        print(f"User: {user}")
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        return UserResponse.model_validate(user)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token for a user
    Args:
        user_id: The ID of the user
        expires_delta: Optional expiration time delta. If not provided, defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES
    Returns:
        str: JWT access token
    """
    to_encode = {"sub": user_id}
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM) 