from enum import Enum
from typing import List, Optional
from pydantic import Field

from app.models.base import DBModel

class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Document(DBModel):
    title: str
    knowledge_base_id: str
    file_name: str
    content_type: str
    content: Optional[str] = None
    size_bytes: int = 0
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: Optional[str] = None
    vector_ids: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    uploaded_by: str

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Company Policy.pdf",
                "file_name": "policy.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
                "status": "completed",
                "vector_ids": ["vec1", "vec2"],
                "summary": "This is a summary of the document",
                "uploaded_by": "user123"
            }
        }

class KnowledgeBase(DBModel):
    name: str
    description: str
    owner_id: str
    shared_with: List[str] = Field(default_factory=list)
    document_count: int = 0
    total_size_bytes: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Company Policies",
                "description": "All company policy documents",
                "document_count": 5,
                "total_size_bytes": 5242880
            }
        } 