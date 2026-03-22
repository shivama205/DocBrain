from typing import List, Any, Dict, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, PostgresDsn, field_validator
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

    # Email Settings (optional)
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    FROM_EMAIL: Optional[str] = os.getenv("FROM_EMAIL", None)

    # Vector Store
    VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "chroma")  # Options: chroma, pinecone
    RETRIEVER_TYPE: str = os.getenv("RETRIEVER_TYPE", "chroma")  # Options: chroma, pinecone

    # ChromaDB (default - local, zero config)
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "docbrain")
    CHROMA_SUMMARY_COLLECTION_NAME: str = os.getenv("CHROMA_SUMMARY_COLLECTION_NAME", "summary")
    CHROMA_QUESTIONS_COLLECTION_NAME: str = os.getenv("CHROMA_QUESTIONS_COLLECTION_NAME", "questions")

    # Pinecone (optional - for production/scale)
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "docbrain")
    PINECONE_SUMMARY_INDEX_NAME: str = os.getenv("PINECONE_SUMMARY_INDEX_NAME", "summary")
    PINECONE_QUESTIONS_INDEX_NAME: str = os.getenv("PINECONE_QUESTIONS_INDEX_NAME", "questions")

    @property
    def SUMMARY_INDEX_NAME(self) -> str:
        if self.VECTOR_STORE_TYPE == "pinecone":
            return self.PINECONE_SUMMARY_INDEX_NAME
        return self.CHROMA_SUMMARY_COLLECTION_NAME

    @property
    def QUESTIONS_INDEX_NAME(self) -> str:
        if self.VECTOR_STORE_TYPE == "pinecone":
            return self.PINECONE_QUESTIONS_INDEX_NAME
        return self.CHROMA_QUESTIONS_COLLECTION_NAME

    # LLM
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Test Emails
    WHITELISTED_EMAILS: str = os.getenv("WHITELISTED_EMAILS", "")

    # RAG
    RAG_TOP_K: int = 3
    RAG_SIMILARITY_THRESHOLD: float = 0.3
    RERANKER_TYPE: str = os.getenv("RERANKER_TYPE", "flag")
    
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

    # Storage
    STORAGE_HOST: str = os.getenv("STORAGE_HOST", "localhost")
    STORAGE_PORT: int = int(os.getenv("STORAGE_PORT", "3306"))
    STORAGE_USER: str = os.getenv("STORAGE_USER", "docbrain")
    STORAGE_PASSWORD: str = os.getenv("STORAGE_PASSWORD", "docbrain")
    STORAGE_DATABASE: str = os.getenv("STORAGE_DATABASE", "storage_docbrain")

    @property
    def STORAGE_URL(self) -> str:
        """Get SQLAlchemy database URL"""
        return f"mysql://{self.STORAGE_USER}:{self.STORAGE_PASSWORD}@{self.STORAGE_HOST}:{self.STORAGE_PORT}/{self.STORAGE_DATABASE}"
    
    @field_validator("BACKEND_CORS_ORIGINS")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v

    # Add these new settings under the existing configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")  # Default to gemini
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DEFAULT_LLM_MODEL: Optional[str] = os.getenv("DEFAULT_LLM_MODEL", None)  # Default model based on provider
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")  # Default embedding model

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 