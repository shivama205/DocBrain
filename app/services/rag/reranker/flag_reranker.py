from typing import Any, Dict, List
from FlagEmbedding import FlagReranker
from app.services.rag.reranker.reranker import Reranker
import logging

logger = logging.getLogger(__name__)

class FlagEmbeddingReranker(Reranker):
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-gemma"):
        # Force CPU usage for the model to avoid MPS issues
        self.reranker = FlagReranker(model_name, use_fp16=False)
        logger.info(f"Initialized FlagEmbeddingReranker with model: {model_name} (using CPU only)")

    async def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Reranking {len(chunks)} chunks with query: {query}")
            pairs = [(query, chunk["content"]) for chunk in chunks]
            scores = self.reranker.compute_score(pairs)
            logger.info(f"Scores: {scores}")

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
            # Return the original chunks sorted by their original scores as fallback
            sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
            return sorted_chunks[:top_k]