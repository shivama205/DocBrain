from typing import List, Optional
from pydantic import Field, field_validator
from app.models.base import DBModel
from app.schemas.message import MessageType
import json

class Message(DBModel):
    conversation_id: str
    content: str
    type: MessageType
    sources: Optional[List[dict]] = Field(default=None)
    status: str = "completed"

    @field_validator('sources', mode='before')
    @classmethod
    def validate_sources(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv_123",
                "content": "What is this document about?",
                "type": "user",
                "sources": None,
                "status": "completed"
            }
        } 