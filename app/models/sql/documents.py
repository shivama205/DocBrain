from sqlalchemy import Column, String, Integer, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.sql.base import BaseModel

class Document(BaseModel):
    """Document SQLAlchemy model"""
    title = Column(String(255), nullable=False)
    knowledge_base_id = Column(String(36), ForeignKey('knowledgebase.id'), nullable=False)
    file_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    content = Column(Text, nullable=True)
    size_bytes = Column(Integer, default=0)
    status = Column(String(50), nullable=False)
    error_message = Column(String(500), nullable=True)
    vector_ids = Column(JSON, nullable=True, default=list)
    processed_chunks = Column(Integer, default=0)
    summary = Column(Text, nullable=True)
    uploaded_by = Column(String(36), ForeignKey('user.id'), nullable=False)

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    uploader = relationship("User", back_populates="uploaded_documents") 