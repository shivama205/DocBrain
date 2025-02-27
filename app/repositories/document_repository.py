from typing import List, Optional, Dict, Any
from app.db.database import db
from app.models.knowledge_base import Document

class DocumentRepository:
    @staticmethod
    async def create(document: Document) -> Document:
        """Create a new document"""
        return db.create("documents", document)
    
    @staticmethod
    async def get_by_id(doc_id: str) -> Optional[Document]:
        """Get document by ID"""
        return db.get("documents", Document, doc_id)
    
    @staticmethod
    async def list_by_knowledge_base(kb_id: str) -> List[Document]:
        """List all documents in a knowledge base"""
        return db.list("documents", Document, {"knowledge_base_id": kb_id})
    
    @staticmethod
    async def get_by_knowledge_base(knowledge_base_id: str, limit: int = 20, status: Optional[str] = None) -> List[Document]:
        """
        Get documents from a knowledge base with optional filtering by status and limit
        
        Args:
            knowledge_base_id: The ID of the knowledge base
            limit: Maximum number of documents to retrieve
            status: Optional status filter (e.g., "COMPLETED")
            
        Returns:
            List of Document objects
        """
        query: Dict[str, Any] = {"knowledge_base_id": knowledge_base_id}
        
        # Add status filter if provided
        if status:
            query["status"] = status
            
        # Get documents with filter
        documents = db.list("documents", Document, query, limit=limit)
        
        return documents
    
    @staticmethod
    async def update(doc_id: str, update_data: dict) -> Optional[Document]:
        """Update document"""
        db.update("documents", doc_id, update_data)
        return await DocumentRepository.get_by_id(doc_id)
    
    @staticmethod
    async def delete(doc_id: str) -> bool:
        """Delete document"""
        return db.delete("documents", doc_id)
    
    @staticmethod
    async def bulk_delete(kb_id: str) -> None:
        """Delete all documents in a knowledge base"""
        documents = await DocumentRepository.list_by_knowledge_base(kb_id)
        for doc in documents:
            await DocumentRepository.delete(doc.id) 