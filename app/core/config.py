from typing import List, Any, Dict, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import EmailStr, AnyHttpUrl, PostgresDsn, field_validator
import os

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "DocBrain"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Email Settings
    SENDGRID_API_KEY: str
    FROM_EMAIL: EmailStr

    # Vector Store
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "docbrain")
    RETRIEVER_TYPE: str = os.getenv("RETRIEVER_TYPE", "pinecone")

    # LLM
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Test Emails
    WHITELISTED_EMAILS: str

    # RAG
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.3
    
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

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @field_validator("BACKEND_CORS_ORIGINS")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 