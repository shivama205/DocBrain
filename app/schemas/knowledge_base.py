from typing import Annotated, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.db.models.knowledge_base import DocumentStatus
from app.schemas.user import UserResponse

class KnowledgeBaseBase(BaseModel):
    name: str = Field(..., alias="name")
    description: str = Field(..., alias="description")

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class SharedUserInfo(BaseModel):
    id: str
    email: str
    full_name: str

    class Config:
        from_attributes = True

class KnowledgeBaseResponse(KnowledgeBaseBase):
    id: str
    user_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user: Optional[UserResponse] = Annotated[None, Field(exclude=True)]

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
    created_at: datetime
    updated_at: Optional[datetime] = None

class DocumentUploadResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    message: str = "Document upload initiated"

class KnowledgeBaseShareRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user to share the knowledge base with")

class KnowledgeBaseUnshareRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user to remove access for")

class KnowledgeBaseSharingResponse(BaseModel):
    success: bool
    message: str 