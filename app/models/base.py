from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid

class DBModel(BaseModel):
    """Base model class for all database models"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None

    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.utcnow().isoformat()

    class Config:
        from_attributes = True 