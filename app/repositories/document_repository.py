from typing import List, Optional, Dict, Any
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models.knowledge_base import Document, DocumentStatus
from app.schemas.document import DocumentResponse

logger = logging.getLogger(__name__)

class DocumentRepository:
    """Repository for document operations"""
    
    @staticmethod
    async def create(document: Document, db: Session) -> DocumentResponse:
        """
        Create a new document.
        
        Args:
            document: Document instance
            db: Database session
            
        Returns:
            Created document
        """
        try:
            db.add(document)
            db.commit()
            db.refresh(document)
            return DocumentResponse.model_validate(document)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create document: {e}")
            raise
    
    @staticmethod
    async def get_by_id(document_id: str, db: Session) -> Optional[DocumentResponse]:
        """
        Get a document by ID.
        
        Args:
            document_id: Document ID
            db: Database session
            
        Returns:
            Document if found, None otherwise
        """
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return None
            return DocumentResponse.model_validate(document)
        except Exception as e:
            logger.error(f"Failed to get document by ID {document_id}: {e}")
            raise
    
    @staticmethod
    async def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[DocumentResponse]:
        """
        Get all documents with pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of documents
        """
        try:
            documents = db.query(Document).offset(skip).limit(limit).all()
            return [DocumentResponse.model_validate(doc) for doc in documents]
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise
    
    @staticmethod
    async def list_by_knowledge_base(
        knowledge_base_id: str,
        db: Session,
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[DocumentResponse]:
        """
        Get documents by knowledge base ID with optional status filter.
        
        Args:
            knowledge_base_id: Knowledge base ID
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            
        Returns:
            List of documents
        """
        try:
            query = db.query(Document).filter(Document.knowledge_base_id == knowledge_base_id)
                
            if status:
                query = query.filter(Document.status == status)
                
            return [DocumentResponse.model_validate(doc) for doc in query.offset(skip).limit(limit).all()]
        except Exception as e:
            logger.error(f"Failed to list documents for knowledge base {knowledge_base_id}: {e}")
            raise

    @staticmethod
    async def set_processing(document_id: str, db: Session) -> Optional[DocumentResponse]:
        """
        Set a document as processing.
        """
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return None
            document.status = DocumentStatus.PROCESSING
            db.commit()
            db.refresh(document)
            return DocumentResponse.model_validate(document)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set document {document_id} as processing: {e}")
            raise

    @staticmethod
    async def set_processed(document_id: str, summary: Optional[str], processed_chunks: int, db: Session) -> Optional[DocumentResponse]:
        """
        Set a document as processed.
        """
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return None
            document.status = DocumentStatus.PROCESSED
            document.summary = summary
            document.processed_chunks = processed_chunks
            db.commit()
            db.refresh(document)
            return DocumentResponse.model_validate(document)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set document {document_id} as processed: {e}")
            raise

    @staticmethod
    async def set_failed(document_id: str, error_message: str, db: Session) -> Optional[DocumentResponse]:
        """
        Set a document as failed.
        """
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return None
            document.status = DocumentStatus.FAILED
            document.error_message = error_message
            db.commit()
            db.refresh(document)
            return DocumentResponse.model_validate(document)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set document {document_id} as failed: {e}")
            raise

    @staticmethod
    async def update(document_id: str, update_data: Dict[str, Any], db: Session) -> Optional[DocumentResponse]:
        """
        Update a document.
        
        Args:
            document_id: Document ID
            update_data: Data to update
            db: Database session
            
        Returns:
            Updated document if found, None otherwise
        """
        try:
            # Get document
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return None
                
            # Update attributes
            for key, value in update_data.items():
                setattr(document, key, value)
                
            db.commit()
            db.refresh(document)
            return DocumentResponse.model_validate(document)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update document {document_id}: {e}")
            raise
    
    @staticmethod
    async def delete(document_id: str, db: Session) -> bool:
        """
        Delete a document.
        
        Args:
            document_id: Document ID
            db: Database session
            
        Returns:
            True if document was deleted, False otherwise
        """
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return False
                
            db.delete(document)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise
    
    @staticmethod
    async def get_by_id(document_id: str, db: Session) -> Optional[DocumentResponse]:
        """
        Class method to get a document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return None
        return DocumentResponse.model_validate(document)