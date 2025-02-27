from typing import List, Dict, Any, Optional
import numpy as np
from pinecone import Pinecone
from google import genai
from google.genai.types import ContentEmbedding
from app.core.config import settings
import logging
import random

logger = logging.getLogger(__name__)

class VectorRepository:
    def __init__(self):
        # Initialize Pinecone
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        self.index = self.pc.Index(self.index_name)
        
        # Initialize Gemini for embeddings
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Vector dimension from Gemini text-embedding-004
        self.dimension = 768

    async def add_chunks(self, chunks: List[Dict[str, Any]], knowledge_base_id: str) -> None:
        """Add document chunks to Pinecone
        
        Args:
            chunks: List of dictionaries containing:
                - content: str
                - metadata: Dict containing document_id, chunk_index, metadata, etc.
            knowledge_base_id: ID of the knowledge base
        """
        try:
            logger.info(f"Starting to process {len(chunks)} chunks for knowledge base {knowledge_base_id}")
            
            # Generate embeddings for chunks
            vectors = []
            for i, chunk in enumerate(chunks):
                # Get embedding
                document_id = str(chunk['metadata']['document_id'])
                logger.info(f"Generating embedding for chunk {i+1}/{len(chunks)} (doc_id: {document_id})")
                embedding = await self._get_embedding(chunk['content'])
                
                # Store content and metadata separately for Pinecone
                metadata = {
                    'knowledge_base_id': str(knowledge_base_id),
                    'document_id': document_id,
                    'chunk_index': int(chunk['metadata']['chunk_index']),
                    'chunk_size': str(chunk['metadata']['chunk_size']),
                    'doc_title': str(chunk['metadata']['document_title']),
                    'doc_type': str(chunk['metadata']['document_type']),
                    'section': str(chunk['metadata']['nearest_header']),
                    'path': ','.join(str(x) for x in chunk['metadata']['section_path']),
                    'content': str(chunk['content'])
                }
                
                # Log metadata structure for infoging
                logger.info(f"Input chunk metadata structure: {chunk['metadata']}")
                logger.info(f"Processed metadata for Pinecone: {metadata}")
                
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
                    self.index.upsert(vectors=batch)
                    logger.info(f"Successfully upserted batch {batch_num}")
                except Exception as batch_error:
                    logger.error(f"Failed to upsert batch {batch_num}: {batch_error}")
                    # Log the first vector in the failing batch for infoging
                    if batch:
                        logger.info(f"Sample vector from failing batch: {batch[0]}")
                    raise
                
            logger.info(f"Successfully added {len(chunks)} chunks to Pinecone for knowledge base {knowledge_base_id}")
            
        except Exception as e:
            logger.error(f"Failed to add chunks to Pinecone: {e}", exc_info=True)
            raise

    async def delete_document_chunks(self, document_id: str) -> None:
        """Delete all chunks for a document from Pinecone"""
        try:
            logger.info(f"Attempting to delete chunks for document {document_id}")
            
            # The issue is with the document ID format - MySQL and Pinecone expect different formats
            # First, try to normalize the document ID
            # If it's a timestamp-like ID (from DuckDB), convert it to a string format that Pinecone expects
            try:
                # Check if the ID is a float (timestamp)
                float(document_id)
                # If it is, we need to handle it specially
                logger.info(f"Document ID {document_id} appears to be a timestamp format")
            except ValueError:
                # Not a timestamp, likely a UUID - proceed normally
                logger.info(f"Document ID {document_id} appears to be a UUID format")
            
            # Correct filter structure for Pinecone
            doc_filter = {"document_id": {"$eq": str(document_id)}}
            logger.info(f"Using filter for operations: {doc_filter}")
            
            # First, verify document has vectors in the index
            try:
                # Query to check if vectors exist
                check_results = self.index.query(
                    vector=[0.0] * self.dimension,  # Dummy vector for metadata-only query
                    filter=doc_filter,
                    top_k=1,
                    include_metadata=True
                )
                
                if not check_results.matches:
                    logger.warning(f"No vectors found for document {document_id}")
                    
                    # Try alternative filter formats
                    alternative_filters = [
                        {"document_id": str(document_id)},  # Simple format
                        {"document_id": document_id},  # No string conversion
                    ]
                    
                    for alt_filter in alternative_filters:
                        logger.info(f"Trying alternative filter: {alt_filter}")
                        alt_results = self.index.query(
                            vector=[0.0] * self.dimension,
                            filter=alt_filter,
                            top_k=1,
                            include_metadata=True
                        )
                        
                        if alt_results.matches:
                            logger.info(f"Found vectors using alternative filter: {alt_filter}")
                            doc_filter = alt_filter
                            check_results = alt_results
                            break
                    
                    if not check_results.matches:
                        # Try a prefix search as a last resort
                        logger.info(f"Trying prefix search for document ID: {document_id}")
                        # This is a fallback approach if filtering doesn't work
                        # We'll manually find vectors by querying without a filter and checking metadata
                        all_results = self.index.query(
                            vector=[0.0] * self.dimension,
                            top_k=1000,  # Get a large number of results
                            include_metadata=True
                        )
                        
                        matching_ids = []
                        for match in all_results.matches:
                            meta_doc_id = match.metadata.get('document_id', '')
                            if meta_doc_id == document_id or meta_doc_id.startswith(document_id):
                                matching_ids.append(match.id)
                        
                        if matching_ids:
                            logger.info(f"Found {len(matching_ids)} vectors with document ID prefix: {document_id}")
                            # Delete by IDs
                            self.index.delete(ids=matching_ids)
                            logger.info(f"Deleted {len(matching_ids)} vectors by ID")
                            return
                        else:
                            logger.warning(f"No vectors found with document ID prefix: {document_id}")
                            return
                    
                logger.info(f"Found vectors for document {document_id}, proceeding with deletion")
                logger.info(f"Sample match metadata: {check_results.matches[0].metadata if check_results.matches else 'None'}")
                
            except Exception as check_error:
                logger.error(f"Failed to check for existing vectors: {check_error}")
                logger.error(f"Check query parameters: vector_dim={self.dimension}, filter={doc_filter}")
                raise
            
            # Delete vectors
            try:
                # Get index stats before deletion
                pre_stats = self.index.describe_index_stats()
                logger.info(f"Pre-deletion index stats: {pre_stats}")
                
                # Perform deletion with retries
                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        # Try direct deletion by filter
                        delete_response = self.index.delete(filter=doc_filter)
                        logger.info(f"Successfully initiated deletion for document {document_id}")
                        logger.info(f"Delete response: {delete_response}")
                        break
                    except Exception as retry_error:
                        retry_count += 1
                        logger.warning(f"Deletion attempt {retry_count} failed: {retry_error}")
                        
                        # If filter-based deletion fails, try ID-based deletion
                        if retry_count == max_retries - 1:
                            logger.warning(f"Filter-based deletion failed after {retry_count} attempts, trying ID-based deletion")
                            try:
                                # Query to get all vector IDs for this document
                                id_results = self.index.query(
                                    vector=[0.0] * self.dimension,
                                    filter=doc_filter,
                                    top_k=1000,  # Get up to 1000 matches
                                    include_metadata=False
                                )
                                
                                if id_results.matches:
                                    # Extract IDs
                                    ids_to_delete = [match.id for match in id_results.matches]
                                    logger.info(f"Found {len(ids_to_delete)} vector IDs to delete")
                                    
                                    # Delete by IDs in batches
                                    batch_size = 100
                                    for i in range(0, len(ids_to_delete), batch_size):
                                        batch = ids_to_delete[i:i + batch_size]
                                        self.index.delete(ids=batch)
                                        logger.info(f"Deleted batch of {len(batch)} vectors by ID")
                                    
                                    logger.info(f"Successfully deleted {len(ids_to_delete)} vectors by ID")
                                    break
                                else:
                                    logger.warning(f"No vector IDs found for document {document_id}")
                            except Exception as id_error:
                                logger.error(f"ID-based deletion failed: {id_error}")
                        
                        if retry_count == max_retries:
                            raise retry_error
                        logger.warning(f"Retry {retry_count} failed, retrying deletion...")
                
                # Get index stats after deletion
                post_stats = self.index.describe_index_stats()
                logger.info(f"Post-deletion index stats: {post_stats}")
                
            except Exception as delete_error:
                logger.error(f"Delete operation failed: {delete_error}")
                logger.error(f"Delete parameters: filter={doc_filter}")
                # Log the actual error response if available
                if hasattr(delete_error, 'response'):
                    logger.error(f"Delete error response: {delete_error.response.text if hasattr(delete_error.response, 'text') else delete_error.response}")
                raise
            
            # Verify deletion
            try:
                verify_results = self.index.query(
                    vector=[0.0] * self.dimension,
                    filter=doc_filter,
                    top_k=1,
                    include_metadata=True
                )
                
                if verify_results.matches:
                    logger.warning(f"Some vectors for document {document_id} may remain after deletion")
                    logger.info(f"Remaining vectors: {verify_results.matches}")
                else:
                    logger.info(f"Verified successful deletion of all vectors for document {document_id}")
                    
            except Exception as verify_error:
                logger.error(f"Failed to verify deletion: {verify_error}")
                logger.error(f"Verify query parameters: vector_dim={self.dimension}, filter={doc_filter}")
            
        except Exception as e:
            logger.error(f"Failed to delete document chunks from Pinecone: {e}", exc_info=True)
            raise

    async def search_similar(
        self,
        query: str,
        knowledge_base_id: str,
        limit: int = 5,
        similarity_threshold: float = 0.3,
        metadata_filter: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks in Pinecone"""
        try:
            logger.info("=== Vector Search Details ===")
            logger.info(f"Query: {query}")
            logger.info(f"Knowledge Base: {knowledge_base_id}")
            logger.info(f"Limit: {limit}, Threshold: {similarity_threshold}")
            
            # Get query embedding
            logger.info("Generating query embedding")
            query_vector = await self._get_embedding(query)
            logger.info(f"Generated embedding with dimension {len(query_vector)}")
            
            # Prepare base filter
            base_filter = {'knowledge_base_id': knowledge_base_id}
            logger.info(f"Base filter: {base_filter}")

            # Handle metadata filters
            if metadata_filter:
                logger.info(f"Original metadata filter: {metadata_filter}")
                
                # All metadata fields are already flattened in Pinecone storage
                # Just merge with base filter, ensuring all values are strings
                for key, value in metadata_filter.items():
                    if isinstance(value, (list, tuple)):
                        # Handle list values (like section_path) by joining with commas
                        base_filter[key] = ','.join(str(x) for x in value)
                    else:
                        # Convert all other values to strings
                        base_filter[key] = str(value)
                
                logger.info(f"Final Pinecone filter: {base_filter}")
            
            logger.info(f"Final Pinecone filter: {base_filter}")
            
            # Search in Pinecone with complete filter
            results = self.index.query(
                vector=query_vector,
                filter=base_filter,
                top_k=limit,
                include_metadata=True
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
            final_chunks = chunks[:limit]
            
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
                'knowledge_base_id': knowledge_base_id,
                'limit': limit,
                'threshold': similarity_threshold,
                'filter': metadata_filter
            })
            raise
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using Gemini"""
        try:
            result: ContentEmbedding = self.client.models.embed_content(
                model="text-embedding-004",
                contents=text
            )
            
            # Get embedding values directly from the ContentEmbedding object
            embedding = result.embeddings[0].values
            
            # Verify dimension
            if len(embedding) != self.dimension:
                raise ValueError(f"Expected embedding dimension {self.dimension}, got {len(embedding)}")
            
            logger.info(f"Generated embedding with dimension {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to get embedding from Gemini: {e}", exc_info=True)
            raise

    async def get_random_chunks(self, knowledge_base_id: str, limit: int = 5) -> List[Dict]:
        """
        Get a random sample of chunks from a knowledge base.
        
        Args:
            knowledge_base_id: The ID of the knowledge base to sample from
            limit: Maximum number of chunks to retrieve
            
        Returns:
            List of document chunks with content and metadata
        """
        try:
            # Create a filter to get chunks from the specified knowledge base
            filter = {
                "knowledge_base_id": {"$eq": knowledge_base_id}
            }
            
            # Query Pinecone for random chunks
            # Note: Pinecone doesn't support true random sampling, so we're using a workaround
            # by retrieving a larger set and then sampling from it
            response = self.index.query(
                vector=[0.1] * 1536,  # Dummy vector that will match all documents
                filter=filter,
                top_k=min(100, limit * 5),  # Get more than we need to sample from
                include_metadata=True
            )
            
            if not response.matches:
                logger.warning(f"No chunks found in knowledge base {knowledge_base_id}")
                return []
            
            # Convert to list of dictionaries with content and metadata
            chunks = []
            for match in response.matches:
                if match.metadata:
                    chunk = {
                        "id": match.id,
                        "content": match.metadata.get("content", ""),
                        "metadata": {
                            "doc_title": match.metadata.get("doc_title", ""),
                            "doc_id": match.metadata.get("doc_id", ""),
                            "chunk_id": match.metadata.get("chunk_id", ""),
                            "knowledge_base_id": match.metadata.get("knowledge_base_id", "")
                        }
                    }
                    chunks.append(chunk)
            
            # Randomly sample from the retrieved chunks
            if len(chunks) > limit:
                chunks = random.sample(chunks, limit)
            
            logger.info(f"Retrieved {len(chunks)} random chunks from knowledge base {knowledge_base_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error retrieving random chunks: {e}")
            return []

    async def search_chunks(
        self, 
        query: str, 
        knowledge_base_id: str, 
        top_k: int = 5, 
        metadata_filter: Optional[Dict] = None,
        similarity_threshold: float = 0.3
    ) -> List[Dict]:
        """
        Search for chunks based on a query with metadata filtering.
        
        Args:
            query: The query to process
            knowledge_base_id: The ID of the knowledge base to search
            top_k: The number of chunks to retrieve
            metadata_filter: Optional additional metadata filter to apply
            similarity_threshold: Minimum similarity score for chunks to be included (default: 0.3)
            
        Returns:
            List of chunks with content and metadata
        """
        try:
            # Get embedding for the query
            embedding = await self._get_embedding(query)
            
            # Create base filter for knowledge base
            filter = {
                "knowledge_base_id": {"$eq": knowledge_base_id}
            }
            
            # Add additional metadata filters if provided
            if metadata_filter:
                logger.info(f"Applying metadata filter: {metadata_filter}")
                for key, value in metadata_filter.items():
                    if key == "similarity_threshold":
                        # Skip this key as it's not a metadata filter
                        continue
                    
                    if isinstance(value, dict):
                        # If value is a dict, it's already in Pinecone filter format
                        # Special handling for $in operator with document_id
                        if key == "document_id" and "$in" in value:
                            # Ensure all document IDs are strings
                            value["$in"] = [str(doc_id) for doc_id in value["$in"]]
                            logger.info(f"Formatted document_id $in filter with {len(value['$in'])} IDs")
                        
                        filter[key] = value
                    else:
                        # Otherwise, create an equality filter
                        filter[key] = {"$eq": str(value)}
            
            logger.info(f"Final Pinecone filter: {filter}")
            
            # Query Pinecone
            response = self.index.query(
                vector=embedding,
                filter=filter,
                top_k=top_k * 2,  # Get more results than needed to allow for filtering
                include_metadata=True
            )
            
            if not response.matches:
                logger.info(f"No chunks found for query: '{query}'")
                return []
            
            # Convert to list of dictionaries with content and metadata
            chunks = []
            filtered_out = 0
            for match in response.matches:
                if match.score >= similarity_threshold:
                    if match.metadata:
                        chunk = {
                            "id": match.id,
                            "content": match.metadata.get("content", ""),
                            "document_id": match.metadata.get("document_id", "") or match.metadata.get("doc_id", ""),
                            "metadata": {
                                "doc_title": match.metadata.get("doc_title", ""),
                                "doc_id": match.metadata.get("doc_id", ""),
                                "document_id": match.metadata.get("document_id", "") or match.metadata.get("doc_id", ""),
                                "chunk_id": match.metadata.get("chunk_id", ""),
                                "knowledge_base_id": match.metadata.get("knowledge_base_id", "")
                            },
                            "score": match.score
                        }
                        chunks.append(chunk)
                else:
                    filtered_out += 1
            
            logger.info(f"Found {len(chunks)} chunks above similarity threshold {similarity_threshold} (filtered out {filtered_out})")
            return chunks
            
        except Exception as e:
            logger.error(f"Error searching chunks: {e}", exc_info=True)
            return [] 