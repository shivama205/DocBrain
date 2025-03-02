from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import torch
from sentence_transformers import CrossEncoder
from app.core.config import settings

logger = logging.getLogger(__name__)

class Reranker(ABC):
    """
    Abstract base class for rerankers that reorder retrieved chunks
    based on their relevance to the query.
    """
    
    @abstractmethod
    async def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks based on their relevance to the query.
        
        Args:
            query: The search query
            chunks: List of chunks to rerank
            top_k: Maximum number of chunks to return after reranking
            
        Returns:
            Reranked list of chunks
        """
        pass

class CrossEncoderReranker(Reranker):
    """
    Reranker implementation that uses a cross-encoder model to rerank chunks.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize the CrossEncoderReranker with a model.
        
        Args:
            model_name: Name of the cross-encoder model to use
        """
        try:
            logger.info(f"Initializing CrossEncoderReranker with model {model_name}")
            self.model = CrossEncoder(model_name)
            self.device = "cpu" 
            logger.info(f"CrossEncoderReranker initialized on device: {self.device}")
        except Exception as e:
            logger.error(f"Failed to initialize CrossEncoderReranker: {e}", exc_info=True)
            raise
    
    async def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks using the cross-encoder model.
        
        Args:
            query: The search query
            chunks: List of chunks to rerank
            top_k: Maximum number of chunks to return after reranking
            
        Returns:
            Reranked list of chunks
        """
        try:
            if not chunks:
                logger.warning("No chunks provided for reranking")
                return []
            
            # If top_k is not specified, use the number of chunks
            if top_k is None:
                top_k = len(chunks)
            
            logger.info(f"Reranking {len(chunks)} chunks with query: {query}")
            
            # Prepare pairs for cross-encoder
            pairs = [(query, chunk["content"]) for chunk in chunks]
            
            # Get scores from cross-encoder
            scores = self.model.predict(pairs)
            
            # Add scores to chunks
            for i, score in enumerate(scores):
                chunks[i]["rerank_score"] = float(score)
                # Keep the original score as similarity_score
                chunks[i]["similarity_score"] = chunks[i].get("score", 0.0)
                # Update the main score to the rerank score
                chunks[i]["score"] = float(score)
            
            # Sort by rerank score
            reranked_chunks = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
            
            # Limit to top_k
            result = reranked_chunks[:top_k]
            
            logger.info(f"Reranking complete. Top score: {result[0]['rerank_score'] if result else 0}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to rerank chunks: {e}", exc_info=True)
            # Return the original chunks if reranking fails
            logger.warning("Returning original chunks due to reranking failure")
            return chunks[:top_k] if top_k is not None else chunks 