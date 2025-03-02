from typing import Any, Dict, List, Optional
from app.services.rag.reranker.reranker import Reranker
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Try importing pinecone for the PineconeReranker
try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("Pinecone not installed. PineconeReranker will not be available.")


class PineconeReranker(Reranker):
    """
    Reranker implementation that uses Pinecone's Cohere rerank-3.5 model.
    
    This reranker offers:
    - Improved performance for complex queries with constraints
    - Multilingual support for over 100+ languages
    - SOTA performance in domains like finance, hospitality, and more
    - Context length of 4096 tokens
    """
    
    def __init__(self, model_name: str = "cohere-rerank-3.5"):
        """
        Initialize the PineconeReranker with an API key.
        
        Args:
            api_key: Pinecone API key
            model_name: Name of the reranking model to use (default: "cohere-rerank-3.5")
        """
        if not PINECONE_AVAILABLE:
            raise ImportError(
                "Pinecone package is not installed. "
                "Please install it with 'pip install -U pinecone'"
            )
        
        try:
            logger.info(f"Initializing PineconeReranker with model {model_name}")
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.model_name = model_name
            logger.info(f"PineconeReranker initialized with model {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize PineconeReranker: {e}", exc_info=True)
            raise
    
    async def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks using Pinecone's Cohere rerank model.
        
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
            
            logger.info(f"Reranking {len(chunks)} chunks with Pinecone using query: {query}")
            
            # Extract content from chunks
            documents = [chunk["content"] for chunk in chunks]
            
            # Call Pinecone's rerank API
            results = self.pc.inference.rerank(
                model=self.model_name,
                query=query,
                documents=documents,
                top_n=top_k,
                return_documents=True
            )
            
            # Map the reranked results back to the original chunks
            reranked_chunks = []
            for result in results.data:
                # Find the original chunk that corresponds to this result
                original_idx = documents.index(result.document.text)
                original_chunk = chunks[original_idx]
                
                # Update the scores
                original_chunk["rerank_score"] = float(result.score)
                original_chunk["similarity_score"] = original_chunk.get("score", 0.0)
                original_chunk["score"] = float(result.score)
                
                reranked_chunks.append(original_chunk)
            
            logger.info(f"Reranking complete. Top score: {reranked_chunks[0]['rerank_score'] if reranked_chunks else 0}")
            
            return reranked_chunks
            
        except Exception as e:
            logger.error(f"Failed to rerank chunks with Pinecone: {e}", exc_info=True)
            # Return the original chunks if reranking fails
            logger.warning("Returning original chunks due to reranking failure")
            return chunks[:top_k] if top_k is not None else chunks
