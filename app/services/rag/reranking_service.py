from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from app.core.config.reranking_config import RerankingConfig

logger = logging.getLogger(__name__)

class RerankingService(ABC):
    """Interface for reranking services."""
    
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
            query: The user query
            chunks: List of chunks to rerank, each with at least 'content' and 'score' fields
            top_k: Number of top chunks to return after reranking
            
        Returns:
            List of reranked chunks with updated scores
        """
        pass


class CrossEncoderRerankingService(RerankingService):
    """Reranking service using a cross-encoder model."""
    
    def __init__(self, config: Optional[RerankingConfig] = None):
        """
        Initialize the cross-encoder reranking service.
        
        Args:
            config: Configuration for the reranking service
        """
        self.config = config or RerankingConfig()
        logger.info(f"Initializing CrossEncoderRerankingService with config: {self.config}")
        
        try:
            # Import here to avoid dependency issues if the package is not installed
            from sentence_transformers import CrossEncoder
            
            logger.info(f"Loading cross-encoder model: {self.config.model_name}")
            self.model = CrossEncoder(
                self.config.model_name,
                max_length=512,
                **self.config.model_kwargs
            )
            logger.info(f"Successfully loaded cross-encoder model: {self.config.model_name}")
        except ImportError as e:
            logger.error(f"Failed to import sentence_transformers: {e}")
            logger.error("Please install the package with: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize cross-encoder model: {e}")
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
            query: The user query
            chunks: List of chunks to rerank
            top_k: Number of top chunks to return (overrides config if provided)
            
        Returns:
            List of reranked chunks with updated scores
        """
        if not self.config.enabled:
            logger.info("Reranking is disabled, returning original chunks")
            return chunks
        
        if not chunks:
            logger.warning("No chunks provided for reranking")
            return []
        
        try:
            # Determine how many chunks to return
            top_k_final = top_k or self.config.top_k_after_rerank
            
            # Limit chunks to rerank if there are too many
            chunks_to_rerank = chunks
            if len(chunks) > self.config.top_k_to_rerank:
                logger.info(f"Limiting reranking to top {self.config.top_k_to_rerank} chunks")
                # Sort by initial score and take top_k_to_rerank
                chunks_to_rerank = sorted(
                    chunks, 
                    key=lambda x: x.get('score', 0.0), 
                    reverse=True
                )[:self.config.top_k_to_rerank]
            
            # Prepare sentence pairs for the cross-encoder
            sentence_pairs = [(query, chunk['content']) for chunk in chunks_to_rerank]
            
            logger.info(f"Reranking {len(sentence_pairs)} chunks with cross-encoder")
            
            # Get cross-encoder scores
            cross_scores = self.model.predict(
                sentence_pairs,
                batch_size=self.config.batch_size,
                show_progress_bar=False
            )
            
            # Update chunks with new scores
            for i, chunk in enumerate(chunks_to_rerank):
                chunk['original_score'] = chunk.get('score', 0.0)
                chunk['score'] = float(cross_scores[i])
            
            # Filter by minimum score if needed
            if self.config.min_score_threshold > 0:
                chunks_to_rerank = [
                    chunk for chunk in chunks_to_rerank 
                    if chunk['score'] >= self.config.min_score_threshold
                ]
                logger.info(f"Filtered to {len(chunks_to_rerank)} chunks above score threshold {self.config.min_score_threshold}")
            
            # Normalize scores if enabled
            if self.config.normalize_scores and chunks_to_rerank:
                max_score = max(chunk['score'] for chunk in chunks_to_rerank)
                min_score = min(chunk['score'] for chunk in chunks_to_rerank)
                score_range = max_score - min_score
                
                if score_range > 0:
                    for chunk in chunks_to_rerank:
                        chunk['score'] = (chunk['score'] - min_score) / score_range
                    logger.info(f"Normalized scores to range [0, 1]")
            
            # Sort by new score and take top_k
            reranked_chunks = sorted(
                chunks_to_rerank, 
                key=lambda x: x['score'], 
                reverse=True
            )[:top_k_final]
            
            logger.info(f"Returning top {len(reranked_chunks)} chunks after reranking")
            
            # Log score improvements
            if reranked_chunks:
                logger.info(f"Reranking score range: {min(c['score'] for c in reranked_chunks):.3f} - {max(c['score'] for c in reranked_chunks):.3f}")
                
                # Log top chunk details
                top_chunk = reranked_chunks[0]
                logger.info(f"Top chunk after reranking: score={top_chunk['score']:.3f}, original_score={top_chunk.get('original_score', 0.0):.3f}")
            
            return reranked_chunks
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}", exc_info=True)
            logger.warning("Falling back to original chunks due to reranking error")
            return chunks 