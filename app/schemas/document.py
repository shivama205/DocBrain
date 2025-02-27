from typing import List, Optional
from pydantic import BaseModel

class DocumentBase(BaseModel):
    title: str

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: str
    knowledge_base_id: str
    file_name: str
    content_type: str
    vector_ids: List[str]
    status: str
    summary: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True 