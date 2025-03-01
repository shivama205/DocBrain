from typing import List, Dict, Any, Optional
import logging
import random
from pinecone import Pinecone
from google import genai
from google.genai.types import ContentEmbedding
from app.core.config import settings
from app.services.retriever import Retriever

logger = logging.getLogger(__name__)

class PineconeRetriever(Retriever):
    """
    Retriever implementation that uses Pinecone as the vector store.
    Uses the knowledge base ID as the namespace in Pinecone.
    """
    
    def __init__(self, knowledge_base_id: str):
        """
        Initialize the PineconeRetriever with a knowledge base ID.
        
        Args:
            knowledge_base_id: The ID of the knowledge base this retriever will work with
        """
        super().__init__(knowledge_base_id)
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        self.index = self.pc.Index(self.index_name)
        
        # Initialize Gemini for embeddings
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Vector dimension from Gemini text-embedding-004
        self.dimension = 768
    
    async def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Add document chunks to Pinecone.
        
        Args:
            chunks: List of dictionaries containing:
                - content: str
                - metadata: Dict containing document_id, chunk_index, metadata, etc.
        """
        try:
            logger.info(f"Starting to process {len(chunks)} chunks for knowledge base {self.knowledge_base_id}")
            
            # Generate embeddings for chunks
            vectors = []
            for i, chunk in enumerate(chunks):
                # Get embedding
                document_id = str(chunk['metadata']['document_id'])
                logger.info(f"Generating embedding for chunk {i+1}/{len(chunks)} (doc_id: {document_id})")
                embedding = await self._get_embedding(chunk['content'])
                
                # Store content and metadata separately for Pinecone
                metadata = {
                    'document_id': document_id,
                    'chunk_index': int(chunk['metadata']['chunk_index']),
                    'chunk_size': str(chunk['metadata']['chunk_size']),
                    'doc_title': str(chunk['metadata']['document_title']),
                    'doc_type': str(chunk['metadata']['document_type']),
                    'section': str(chunk['metadata']['nearest_header']),
                    'path': ','.join(str(x) for x in chunk['metadata']['section_path']),
                    'content': str(chunk['content'])
                }
                
                # Create vector record with unique ID
                vector_id = f"{document_id}_{metadata['chunk_index']}_{metadata['chunk_size']}"
                vectors.append({
                    'id': vector_id,
                    'values': [float(x) for x in embedding],
                    'metadata': metadata
                })
                logger.info(f"Created vector record for chunk {i+1} with id {vector_id}")
            
            # Upsert vectors in batches of 100
            batch_size = 100
            total_batches = (len(vectors) + batch_size - 1) // batch_size
            
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                logger.info(f"Upserting batch {batch_num}/{total_batches} ({len(batch)} vectors)")
                try:
                    # Use knowledge_base_id as namespace
                    self.index.upsert(vectors=batch, namespace=self.knowledge_base_id)
                    logger.info(f"Successfully upserted batch {batch_num}")
                except Exception as batch_error:
                    logger.error(f"Failed to upsert batch {batch_num}: {batch_error}")
                    # Log the first vector in the failing batch for debugging
                    if batch:
                        logger.info(f"Sample vector from failing batch: {batch[0]}")
                    raise
                
            logger.info(f"Successfully added {len(chunks)} chunks to Pinecone for knowledge base {self.knowledge_base_id}")
            
        except Exception as e:
            logger.error(f"Failed to add chunks to Pinecone: {e}", exc_info=True)
            raise
    
    async def delete_document_chunks(self, document_id: str) -> None:
        """
        Delete all chunks for a document from Pinecone.
        
        Args:
            document_id: ID of the document to delete
        """
        try:
            logger.info(f"Attempting to delete chunks for document {document_id} in knowledge base {self.knowledge_base_id}")
            
            # Use knowledge_base_id as namespace and filter by document_id
            self.index.delete(
                filter={"document_id": {"$eq": str(document_id)}},
                namespace=self.knowledge_base_id
            )
            
            logger.info(f"Successfully deleted chunks for document {document_id} in knowledge base {self.knowledge_base_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete document chunks: {e}", exc_info=True)
            raise
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks in Pinecone.
        
        Args:
            query: The search query
            top_k: Maximum number of results to return
            similarity_threshold: Minimum similarity score for results
            metadata_filter: Optional filter to apply to the search
            
        Returns:
            List of dictionaries containing chunk data
        """
        try:
            logger.info("=== Vector Search Details ===")
            logger.info(f"Query: {query}")
            logger.info(f"Knowledge Base: {self.knowledge_base_id}")
            logger.info(f"Limit: {top_k}, Threshold: {similarity_threshold}")
            
            # Get query embedding
            logger.info("Generating query embedding")
            query_vector = await self._get_embedding(query)
            logger.info(f"Generated embedding with dimension {len(query_vector)}")
            
            # Prepare filter
            filter_dict = {}
            
            # Handle metadata filters
            if metadata_filter:
                logger.info(f"Original metadata filter: {metadata_filter}")
                
                # All metadata fields are already flattened in Pinecone storage
                # Just add to filter, ensuring all values are strings
                for key, value in metadata_filter.items():
                    if isinstance(value, dict) and "$in" in value:
                        # Handle $in operator for multiple values
                        filter_dict[key] = value
                    elif isinstance(value, (list, tuple)):
                        # Handle list values (like section_path) by joining with commas
                        filter_dict[key] = ','.join(str(x) for x in value)
                    else:
                        # Convert all other values to strings
                        filter_dict[key] = str(value)
                
                logger.info(f"Final Pinecone filter: {filter_dict}")
            
            # Search in Pinecone with filter and namespace
            results = self.index.query(
                vector=query_vector,
                filter=filter_dict if filter_dict else None,
                top_k=top_k,
                include_metadata=True,
                namespace=self.knowledge_base_id
            )
            
            logger.info(f"Found {len(results.matches)} initial matches")
            
            # Process matches
            chunks = []
            filtered_out = 0
            for match in results.matches:
                if match.score >= similarity_threshold:
                    try:
                        # Get metadata safely
                        metadata = match.metadata or {}
                        
                        # Build chunk with required fields
                        chunk = {
                            'id': match.id,
                            'score': float(match.score),
                            'document_id': str(metadata.get('document_id', '')),
                            'content': str(metadata.get('content', '')),
                            'chunk_index': int(metadata.get('chunk_index', 0)),
                            'title': str(metadata.get('doc_title', 'Untitled')),
                            'metadata': {
                                'document_id': str(metadata.get('document_id', '')),
                                'chunk_index': int(metadata.get('chunk_index', 0)),
                                'chunk_size': str(metadata.get('chunk_size', '')),
                                'doc_title': str(metadata.get('doc_title', '')),
                                'doc_type': str(metadata.get('doc_type', '')),
                                'section': str(metadata.get('section', '')),
                                'path': metadata.get('path', '').split(',') if metadata.get('path') else []
                            }
                        }
                        
                        # Only skip if absolutely necessary
                        if not chunk['content']:
                            logger.warning(f"Skipping chunk with empty content")
                            continue
                            
                        chunks.append(chunk)
                        logger.info(f"Included chunk with score {match.score:.3f}")
                        
                    except Exception as chunk_error:
                        logger.error(f"Error processing chunk: {chunk_error}")
                        logger.info(f"Problematic metadata: {match.metadata}")
                        continue
                else:
                    filtered_out += 1
                    logger.info(f"Filtered out chunk with score {match.score:.3f} (below threshold)")
            
            # Sort chunks by score
            chunks.sort(key=lambda x: x['score'], reverse=True)
            final_chunks = chunks[:top_k]
            
            logger.info(f"Returning {len(final_chunks)} total chunks")
            if final_chunks:
                logger.info(f"Final score range: {min(c['score'] for c in final_chunks):.3f} - {max(c['score'] for c in final_chunks):.3f}")
                
                # Log sample content from top chunk
                top_chunk = final_chunks[0]
                logger.info("Top chunk preview:")
                logger.info(f"Score: {top_chunk['score']:.3f}")
                logger.info(f"Document ID: {top_chunk['document_id']}")
                logger.info(f"Title: {top_chunk['title']}")
                logger.info(f"Content: {top_chunk['content'][:200]}...")
            
            return final_chunks
            
        except Exception as e:
            logger.error(f"Failed to search in Pinecone: {e}")
            logger.error("Search parameters:", extra={
                'query': query,
                'knowledge_base_id': self.knowledge_base_id,
                'limit': top_k,
                'threshold': similarity_threshold,
                'filter': metadata_filter
            })
            raise
    
    async def get_random_chunks(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get random chunks from Pinecone.
        
        Args:
            limit: Maximum number of chunks to return
            
        Returns:
            List of dictionaries containing chunk data
        """
        try:
            logger.info(f"Fetching random chunks from knowledge base {self.knowledge_base_id}")
            
            # Fetch a larger sample to select random chunks from
            sample_size = min(limit * 5, 100)  # Get more than we need, but not too many
            
            # Create a random vector to fetch diverse results
            random_vector = [random.uniform(-1, 1) for _ in range(self.dimension)]
            
            # Query with the random vector
            results = self.index.query(
                vector=random_vector,
                top_k=sample_size,
                include_metadata=True,
                namespace=self.knowledge_base_id
            )
            
            if not results.matches:
                logger.warning(f"No chunks found in knowledge base {self.knowledge_base_id}")
                return []
            
            # Shuffle the results to randomize further
            matches = list(results.matches)
            random.shuffle(matches)
            
            # Take only the requested number of chunks
            selected_matches = matches[:limit]
            
            # Process the selected matches
            chunks = []
            for match in selected_matches:
                metadata = match.metadata or {}
                
                chunk = {
                    'id': match.id,
                    'document_id': str(metadata.get('document_id', '')),
                    'title': str(metadata.get('doc_title', 'Untitled')),
                    'content': str(metadata.get('content', '')),
                    'chunk_index': int(metadata.get('chunk_index', 0)),
                    'metadata': metadata
                }
                
                chunks.append(chunk)
            
            logger.info(f"Retrieved {len(chunks)} random chunks from knowledge base {self.knowledge_base_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get random chunks: {e}", exc_info=True)
            return []
    
    async def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text using Gemini.
        
        Args:
            text: The text to embed
            
        Returns:
            List of floats representing the embedding
        """
        try:
            result: ContentEmbedding = self.client.models.embed_content(
                model="text-embedding-004",
                contents=text
            )
            
            # Get embedding values directly from the ContentEmbedding object
            embedding = result.embeddings[0].values
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}", exc_info=True)
            raise 