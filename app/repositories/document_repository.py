from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete

from app.db.models.knowledge_base import Document
from app.schemas.document import DocumentCreate
from app.db.database import db

class DocumentRepository:
    """Repository for document operations"""
    
    async def create(self, document_data: DocumentCreate) -> Document:
        """
        Create a new document.
        
        Args:
            document_data: Document data
            
        Returns:
            Created document
        """
        session = db.get_session()
        document = Document(**document_data.dict())
        session.add(document)
        session.commit()
        session.refresh(document)
        return document
    
    async def get_by_id(self, document_id: str) -> Optional[Document]:
        """
        Get a document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        session = db.get_session()
        query = select(Document).where(Document.id == document_id)
        result = await session.execute(query)
        return result.scalars().first()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Document]:
        """
        Get all documents with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of documents
        """
        session = db.get_session()
        query = select(Document).offset(skip).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_by_knowledge_base(
        self, 
        knowledge_base_id: str, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Document]:
        """
        Get documents by knowledge base ID with optional status filter.
        
        Args:
            knowledge_base_id: Knowledge base ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            
        Returns:
            List of documents
        """
        session = db.get_session()
        query = select(Document).where(Document.knowledge_base_id == knowledge_base_id)
            
        if status:
            query = query.where(Document.status == status)
            
        query = query.offset(skip).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def update(self, document_id: str, update_data: Dict[str, Any]) -> Optional[Document]:
        """
        Update a document.
        
        Args:
            document_id: Document ID
            update_data: Data to update
            
        Returns:
            Updated document if found, None otherwise
        """
        session = db.get_session()
        # Update document
        query = update(Document).where(Document.id == document_id).values(**update_data)
        await session.execute(query)
        
        # Get updated document
        get_query = select(Document).where(Document.id == document_id)
        result = await session.execute(get_query)
        document = result.scalars().first()
        
        await session.commit()
        return document
    
    async def delete(self, document_id: str) -> bool:
        """
        Delete a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            True if document was deleted, False otherwise
        """
        session = db.get_session()
        query = delete(Document).where(Document.id == document_id)
        result = await session.execute(query)
        await session.commit()
        return result.rowcount > 0
    
    @classmethod
    async def get_by_id(cls, document_id: str) -> Optional[Document]:
        """
        Class method to get a document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        session = db.get_session()
        query = select(Document).where(Document.id == document_id)
        result = await session.execute(query)
        return result.scalars().first() 