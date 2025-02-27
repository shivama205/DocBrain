from typing import List, Optional
from pydantic import BaseModel

from app.models.knowledge_base import DocumentStatus

class KnowledgeBaseBase(BaseModel):
    name: str
    description: str

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class KnowledgeBaseResponse(KnowledgeBaseBase):
    id: str
    owner_id: str
    shared_with: List[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    size_bytes: int
    status: DocumentStatus
    error_message: Optional[str] = None
    knowledge_base_id: str
    uploaded_by: str
    created_at: str
    updated_at: Optional[str] = None

class DocumentUploadResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    message: str = "Document upload initiated" 