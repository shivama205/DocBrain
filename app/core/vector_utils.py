from typing import List, Dict, Any
import logging
from app.core.config import settings
from llama_index.embeddings.gemini import GeminiEmbedding
from pinecone import Pinecone

logger = logging.getLogger(__name__)

# Initialize Gemini embedding model
try:
    embed_model = GeminiEmbedding(
        model_name="models/embedding-001",
        api_key=settings.GEMINI_API_KEY,
        timeout=60
    )
except Exception as e:
    logger.error(f"Failed to initialize Gemini embedding model: {e}")
    raise

# Initialize Pinecone
try:
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX_NAME)
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {e}")
    raise

class VectorUtils:
    """Utility class for vector operations"""

    @staticmethod
    async def get_embedding(text: str) -> List[float]:
        """
        Get embedding for text using Gemini embedding model
        
        Args:
            text: The text to generate embedding for
            
        Returns:
            List[float]: The embedding vector
            
        Raises:
            Exception: If embedding generation fails
        """
        try:
            # Preprocess text - remove extra whitespace and normalize
            text = " ".join(text.split())
            
            # Generate embedding using Gemini
            embedding = embed_model.get_text_embedding(text)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    @staticmethod
    async def search_vectors(
        query_embedding: List[float],
        knowledge_base_id: str,
        top_k: int = 5,
        similarity_cutoff: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Search vector store for similar vectors
        
        Args:
            query_embedding: The query vector to search with
            knowledge_base_id: ID of knowledge base to search in
            top_k: Number of results to return
            similarity_cutoff: Minimum similarity score threshold
            
        Returns:
            List[Dict[str, Any]]: List of matches with metadata
        """
        try:
            # Query Pinecone with metadata filter for knowledge base
            query_response = index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter={
                    "knowledge_base_id": {"$eq": knowledge_base_id}
                }
            )
            
            # Format results and filter by similarity cutoff
            results = []
            for match in query_response.matches:
                if match.score >= similarity_cutoff:
                    results.append({
                        'score': match.score,
                        'document_id': match.metadata['document_id'],
                        'title': match.metadata['title'],
                        'content': match.metadata['text'],
                        'chunk_index': match.metadata['chunk_index']
                    })
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            raise

    @staticmethod
    async def store_vectors(
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]],
        knowledge_base_id: str
    ) -> List[str]:
        """
        Store vectors in Pinecone vector store
        
        Args:
            vectors: List of vectors to store
            metadata: List of metadata dicts for each vector
            knowledge_base_id: ID of knowledge base the vectors belong to
            
        Returns:
            List[str]: List of vector IDs
            
        Raises:
            Exception: If vector storage fails
        """
        try:
            if len(vectors) != len(metadata):
                raise ValueError("Number of vectors must match number of metadata entries")
                
            # Generate vector IDs
            vector_ids = [f"{knowledge_base_id}_{i}" for i in range(len(vectors))]
            
            # Add knowledge base ID to metadata
            for meta in metadata:
                meta['knowledge_base_id'] = knowledge_base_id
            
            # Format vectors for Pinecone
            pinecone_vectors = [
                (vector_id, vector, meta)
                for vector_id, vector, meta 
                in zip(vector_ids, vectors, metadata)
            ]
            
            # Upsert vectors in batches of 100
            batch_size = 100
            for i in range(0, len(pinecone_vectors), batch_size):
                batch = pinecone_vectors[i:i + batch_size]
                index.upsert(vectors=batch)
                
            return vector_ids
            
        except Exception as e:
            logger.error(f"Failed to store vectors: {e}")
            raise

    @staticmethod
    async def delete_vectors(vector_ids: List[str]) -> None:
        """
        Delete vectors from Pinecone vector store
        
        Args:
            vector_ids: List of vector IDs to delete
            
        Raises:
            Exception: If vector deletion fails
        """
        try:
            # Delete vectors in batches of 100
            batch_size = 100
            for i in range(0, len(vector_ids), batch_size):
                batch = vector_ids[i:i + batch_size]
                index.delete(ids=batch)
                
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            raise 