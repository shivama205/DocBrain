from abc import ABC, abstractmethod
import math
from typing import List, Dict, Any, Optional
import logging
import os
import multiprocessing
import torch
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

# Configure multiprocessing to use 'spawn' instead of 'fork'
# This can help prevent segmentation faults in multiprocessing environments
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    # If already set, this will raise a RuntimeError
    pass

# Disable GPU acceleration to avoid segfaults with MPS on macOS
# This prevents the SIGSEGV (signal 11) crashes that occur when PyTorch tries to use
# the Metal Performance Shaders (MPS) backend on macOS, especially in multiprocessing environments.
os.environ["PYTORCH_MPS_ENABLE_WORKSTREAM_WATCHDOG"] = "0"  # Disable MPS watchdog
os.environ["MPS_VISIBLE_DEVICES"] = ""  # Disable MPS for PyTorch
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Disable CUDA if present

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
            
            # Force CPU usage to avoid segmentation faults
            if torch.cuda.is_available():
                logger.info("CUDA is available but forcing CPU usage to avoid segmentation faults")
            
            # Explicitly set device to CPU
            self.device = "cpu"
            
            # Initialize the model with device="cpu" to force CPU usage
            self.model = CrossEncoder(model_name, device=self.device)
            
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
            
            # Get scores from cross-encoder with explicit batch size to avoid memory issues
            # and show_progress_bar=False to avoid tqdm issues in multiprocessing
            logger.info(f"self.device: {self.device}")
            scores: List[float] = self.model.predict(pairs)

            logger.info(f"type of scores: {type(scores)}")
            logger.info(f"type of scores[0]: {type(scores[0])}")

            # Convert NaN values to 0
            scores = [0 if math.isnan(score) else score for score in scores]

            # Add scores to chunks
            for i, score in enumerate(scores):
                chunks[i]["rerank_score"] = float(score)
                # Keep the original score as similarity_score
                chunks[i]["similarity_score"] = chunks[i].get("score", 0.0)
                # Update the main score to the rerank score
                chunks[i]["score"] = float(score)
                logger.info(f"Chunk {i}: {chunks[i]}")
            
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