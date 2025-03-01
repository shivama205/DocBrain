from typing import List, Optional
from datetime import datetime
from pydantic import Field
from app.models.base import DBModel

class Conversation(DBModel):
    title: str
    knowledge_base_id: str
    owner_id: str
    created_at: str
    updated_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Discussion about Company Policy",
                "knowledge_base_id": "kb_123",
                "owner_id": "user_123",
                "created_at": "2024-02-24T12:00:00Z",
                "updated_at": "2024-02-24T12:00:00Z"
            }
        } 