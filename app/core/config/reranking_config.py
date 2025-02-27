from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class RerankingConfig(BaseModel):
    """Configuration for the reranking service."""
    
    # Whether to enable reranking
    enabled: bool = Field(default=True, description="Whether to enable reranking")
    
    # The model to use for reranking
    model_name: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2", 
        description="The cross-encoder model to use for reranking"
    )
    
    # The number of top chunks to consider for reranking
    top_k_to_rerank: int = Field(
        default=20, 
        description="The number of top chunks to consider for reranking"
    )
    
    # The number of chunks to return after reranking
    top_k_after_rerank: int = Field(
        default=5, 
        description="The number of chunks to return after reranking"
    )
    
    # The batch size for reranking
    batch_size: int = Field(
        default=16, 
        description="The batch size for reranking"
    )
    
    # The minimum score for a chunk to be considered relevant
    min_score_threshold: float = Field(
        default=0.1, 
        description="The minimum score for a chunk to be considered relevant"
    )
    
    # Whether to normalize scores
    normalize_scores: bool = Field(
        default=True, 
        description="Whether to normalize scores to [0, 1] range"
    )
    
    # Additional model kwargs
    model_kwargs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional kwargs to pass to the model"
    )
    
    class Config:
        """Pydantic config"""
        extra = "forbid"  # Forbid extra attributes 