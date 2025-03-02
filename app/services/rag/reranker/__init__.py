"""
Reranker module for RAG (Retrieval-Augmented Generation) systems.

This module provides reranking capabilities to improve the relevance of retrieved chunks
by reordering them based on their relevance to the query.
"""

from app.services.rag.reranker.reranker import (
    Reranker,
    CrossEncoderReranker,
)
from app.services.rag.reranker.reranker_factory import (
    RerankerFactory,
    create_reranker
)
from app.services.rag.reranker.pinecone_reranker import (
    PineconeReranker,
    PINECONE_AVAILABLE
)
from app.services.rag.reranker.flag_reranker import (
    FlagEmbeddingReranker,
)

__all__ = [
    'Reranker',
    'CrossEncoderReranker',
    'PineconeReranker',
    'RerankerFactory',
    'create_reranker',
    'PINECONE_AVAILABLE',
    'FlagEmbeddingReranker'
] 