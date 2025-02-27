from typing import List
from pydantic_settings import BaseSettings
from pydantic import EmailStr
import os

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "DocBrain"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Email Settings
    SENDGRID_API_KEY: str
    FROM_EMAIL: EmailStr

    # Vector Store
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str
    PINECONE_INDEX_NAME: str = "docbrain"

    # LLM
    GEMINI_API_KEY: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Test Emails
    WHITELISTED_EMAILS: str
    
    @property
    def WHITELISTED_EMAIL_LIST(self) -> List[str]:
        return [email.strip() for email in self.WHITELISTED_EMAILS.split(",")]

    # File Upload
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "/data/uploads"

    # Database settings
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "docbrain")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "docbrain")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "docbrain")
    
    @property
    def DATABASE_URL(self) -> str:
        """Get SQLAlchemy database URL"""
        return f"mysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 