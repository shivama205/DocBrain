from typing import List, Dict, Any, Optional
from pinecone import Pinecone
from app.core.config import settings
import logging
import random
from abc import ABC, abstractmethod
import threading
from app.services.llm.factory import LLMFactory

logger = logging.getLogger(__name__)

class VectorStore(ABC):
    """Abstract base class for vector stores"""
    
    @abstractmethod
    async def add_chunks(self, chunks: List[Dict[str, Any]], knowledge_base_id: str) -> None:
        """Add document chunks to the vector store"""
        pass
    
    @abstractmethod
    async def add_texts(self, texts: List[str], metadatas: List[Dict], ids: List[str], collection_name: str) -> None:
        """Add texts with metadata to the vector store"""
        pass
    
    @abstractmethod
    async def delete_document_chunks(self, document_id: str, knowledge_base_id: str) -> None:
        """Delete all chunks for a document from the vector store"""
        pass
    
    @abstractmethod
    async def search_similar(
        self,
        query: str,
        knowledge_base_id: str,
        limit: int = 5,
        similarity_threshold: float = 0.3,
        metadata_filter: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks in the vector store"""
        pass
    
    @abstractmethod
    async def get_random_chunks(self, knowledge_base_id: str, limit: int = 5) -> List[Dict]:
        """Get random chunks from a knowledge base"""
        pass
    
    @abstractmethod
    async def search_chunks(
        self, 
        query: str, 
        knowledge_base_id: str, 
        top_k: int = 5, 
        metadata_filter: Optional[Dict] = None,
        similarity_threshold: float = 0.3
    ) -> List[Dict]:
        """Search for chunks based on a query with metadata filtering"""
        pass


class PineconeVectorStore(VectorStore):
    """Pinecone implementation of the VectorStore interface"""
    
    def __init__(self, index_name: str = "docbrain"):
        """Initialize PineconeVectorStore with specific index name
        
        Args:
            index_name: Name of the Pinecone index to use ('docbrain' or 'summary')
        """
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        
        # Set the index name
        self.index_name = index_name
            
        # Get the index
        try:
            self.index = self.pc.Index(self.index_name)
            logger.info(f"Initialized Pinecone index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index {self.index_name}: {e}")
            raise
        
        # Vector dimension from text-embedding-004
        self.dimension = 768
        
        # Connection status
        self._connected = True

    def cleanup(self):
        """Cleanup resources when this instance is no longer needed"""
        # Pinecone client handles connection pooling, but we could add
        # cleanup logic here if needed in the future
        self._connected = False
        logger.info(f"Cleaned up PineconeVectorStore for index {self.index_name}")
        
    def __del__(self):
        """Destructor to ensure resources are cleaned up"""
        if hasattr(self, '_connected') and self._connected:
            self.cleanup()

    async def add_chunks(self, chunks: List[Dict[str, Any]], knowledge_base_id: str) -> None:
        """Add document chunks to Pinecone
        
        Args:
            chunks: List of dictionaries containing:
                - content: str
                - metadata: Dict containing document_id, chunk_index, metadata, etc.
            knowledge_base_id: ID of the knowledge base (used as namespace)
        """
        try:
            logger.info(f"Starting to process {len(chunks)} chunks for knowledge base {knowledge_base_id} in index {self.index_name}")
            
            # Generate embeddings for chunks
            vectors = []
            for i, chunk in enumerate(chunks):
                # Get embedding
                document_id = str(chunk['metadata']['document_id'])
                logger.info(f"Generating embedding for chunk {i+1}/{len(chunks)} (doc_id: {document_id}) using LLM Factory")
                embedding = await self._get_embedding(chunk['content'])
                logger.info(f"Generated embedding with dimension {len(embedding)}")
                
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
                    # Use knowledge_base_id as namespace
                    self.index.upsert(vectors=batch, namespace=knowledge_base_id)
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

    async def add_texts(self, texts: List[str], metadatas: List[Dict], ids: List[str], collection_name: str) -> None:
        """Add texts with metadata to Pinecone
        
        Args:
            texts: List of text content
            metadatas: List of metadata dictionaries
            ids: List of unique identifiers
            collection_name: Name of collection (used as namespace)
        """
        try:
            logger.info(f"Adding {len(texts)} texts to collection {collection_name}")
            
            # Convert to the format expected by add_chunks
            chunks = []
            for i, (text, metadata, id) in enumerate(zip(texts, metadatas, ids)):
                chunk = {
                    'content': text,
                    'metadata': {
                        'document_id': id,
                        'chunk_index': i,
                        'chunk_size': len(text),
                        'document_title': metadata.get('title', ''),
                        'document_type': metadata.get('type', ''),
                        'nearest_header': metadata.get('section', ''),
                        'section_path': metadata.get('path', '').split(',') if 'path' in metadata else [],
                        **metadata  # Include other metadata fields
                    }
                }
                chunks.append(chunk)
            
            # Use collection_name as knowledge_base_id
            await self.add_chunks(chunks, collection_name)
            
        except Exception as e:
            logger.error(f"Failed to add texts to Pinecone: {e}", exc_info=True)
            raise

    async def delete_document_chunks(self, document_id: str, knowledge_base_id: str) -> None:
        """Delete all chunks for a document from Pinecone
        
        Args:
            document_id: ID of the document to delete
            knowledge_base_id: ID of the knowledge base (used as namespace)
        """
        try:
            logger.info(f"Attempting to delete chunks for document {document_id} in knowledge base {knowledge_base_id} in index {self.index_name}")
            
            # First, fetch all vector IDs for this document by querying with the document_id
            try:
                # Try to use metadata filtering first (works on Standard and Enterprise tiers)
                self.index.delete(
                    filter={"document_id": {"$eq": str(document_id)}},
                    namespace=knowledge_base_id
                )
                logger.info(f"Successfully deleted chunks using metadata filter for document {document_id}")
                return
            except Exception as e:
                # If metadata filtering fails (Serverless and Starter tiers), use vector IDs
                if "Serverless and Starter indexes do not support deleting with metadata filtering" in str(e):
                    logger.info("Pinecone Serverless/Starter tier detected, switching to ID-based deletion")
                    
                    # Query to get all vectors for this document
                    # We need to use a dummy vector for the query
                    dummy_vector = [0.0] * self.dimension
                    
                    # Query with a high top_k to get all vectors for this document
                    results = self.index.query(
                        vector=dummy_vector,
                        top_k=10000,  # Set a high limit to get all vectors
                        include_metadata=True,
                        namespace=knowledge_base_id
                    )
                    
                    # Filter results to only include vectors for this document
                    vector_ids = []
                    for match in results.matches:
                        if match.metadata and match.metadata.get('document_id') == str(document_id):
                            vector_ids.append(match.id)
                    
                    if vector_ids:
                        logger.info(f"Found {len(vector_ids)} vectors to delete for document {document_id}")
                        # Delete vectors by ID
                        self.index.delete(
                            ids=vector_ids,
                            namespace=knowledge_base_id
                        )
                        logger.info(f"Successfully deleted {len(vector_ids)} vectors by ID for document {document_id}")
                    else:
                        logger.info(f"No vectors found for document {document_id} in knowledge base {knowledge_base_id}")
                else:
                    # If it's a different error, re-raise it
                    raise
            
            logger.info(f"Successfully deleted chunks for document {document_id} in knowledge base {knowledge_base_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete document chunks: {e}", exc_info=True)
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
            logger.info(f"Index: {self.index_name}")
            logger.info(f"Limit: {limit}, Threshold: {similarity_threshold}")
            
            # Get query embedding using LLM Factory
            logger.info("Generating query embedding using LLM Factory")
            query_vector = await self._get_embedding(query)
            logger.info(f"Generated embedding with dimension {len(query_vector)}")
            
            # Prepare filter (no need to include knowledge_base_id as it's now a namespace)
            filter_dict = {}
            
            # Handle metadata filters
            if metadata_filter:
                logger.info(f"Original metadata filter: {metadata_filter}")
                
                # All metadata fields are already flattened in Pinecone storage
                # Just add to filter, ensuring all values are strings
                for key, value in metadata_filter.items():
                    if isinstance(value, (list, tuple)):
                        # Handle list values (like section_path) by joining with commas
                        filter_dict[key] = ','.join(str(x) for x in value)
                    else:
                        # Convert all other values to strings
                        filter_dict[key] = str(value)
                
                logger.info(f"Final Pinecone filter: {filter_dict}")
            
            logger.info(f"Final Pinecone filter: {filter_dict}")
            
            # Search in Pinecone with filter and namespace
            results = self.index.query(
                vector=query_vector,
                filter=filter_dict if filter_dict else None,
                top_k=limit,
                include_metadata=True,
                namespace=knowledge_base_id
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
                        
                        # Check if this is a question result (based on metadata fields)
                        is_question = 'question_id' in metadata and 'question' in metadata
                        
                        if is_question:
                            # This is a question result, use question-specific fields
                            chunk = {
                                'score': float(match.score),
                                'content': str(metadata.get('content', '')),
                                'question_id': str(metadata.get('question_id', '')),
                                'question': str(metadata.get('question', '')),
                                'answer': str(metadata.get('answer', '')),
                                'answer_type': str(metadata.get('answer_type', 'DIRECT')),
                                'metadata': {
                                    'question_id': str(metadata.get('question_id', '')),
                                    'knowledge_base_id': str(metadata.get('knowledge_base_id', '')),
                                    'answer': str(metadata.get('answer', '')),
                                    'answer_type': str(metadata.get('answer_type', 'DIRECT')),
                                    'score': float(match.score)
                                }
                            }
                        else:
                            # This is a document chunk, use document-specific fields
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
                
                # Check if this is a question result
                if 'question_id' in top_chunk:
                    # Question result
                    logger.info(f"Question ID: {top_chunk['question_id']}")
                    logger.info(f"Question: {top_chunk['question']}")
                    logger.info(f"Content: {top_chunk['content'][:200]}...")
                else:
                    # Document result
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
        """
        Get embedding for text using the centralized LLM Factory.
        
        Args:
            text: The text to embed
            
        Returns:
            Embedding as a list of floats
        """
        try:
            # Use the LLM Factory for text embeddings (using model from settings)
            embedding = await LLMFactory.embed_text(
                text=text,
                model=settings.EMBEDDING_MODEL  # Use the model from settings
            )
            
            # Verify dimension
            if len(embedding) != self.dimension:
                raise ValueError(f"Expected embedding dimension {self.dimension}, got {len(embedding)}")
            
            logger.info(f"Generated embedding with dimension {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}", exc_info=True)
            raise

    async def get_random_chunks(self, knowledge_base_id: str, limit: int = 5) -> List[Dict]:
        """
        Get random chunks from a knowledge base.
        
        Args:
            knowledge_base_id: The ID of the knowledge base to fetch from (used as namespace)
            limit: The number of chunks to retrieve
            
        Returns:
            List of random chunks with content and metadata
        """
        try:
            logger.info(f"Fetching random chunks from knowledge base {knowledge_base_id} in index {self.index_name}")
            
            # Fetch all document IDs in this knowledge base
            # We need to use a dummy query to get all vectors in the namespace
            dummy_vector = [0.0] * self.dimension
            
            # Query with a high top_k to get a good sample
            response = self.index.query(
                vector=dummy_vector,
                top_k=1000,  # Get a large sample to choose from
                include_metadata=True,
                namespace=knowledge_base_id
            )
            
            if not response.matches:
                logger.info(f"No chunks found in knowledge base {knowledge_base_id}")
                return []
            
            # Get all unique document IDs
            doc_ids = set()
            for match in response.matches:
                if match.metadata and 'document_id' in match.metadata:
                    doc_ids.add(match.metadata['document_id'])
            
            logger.info(f"Found {len(doc_ids)} unique documents in knowledge base {knowledge_base_id}")
            
            if not doc_ids:
                return []
            
            # Select random document IDs (up to 5)
            selected_doc_ids = random.sample(list(doc_ids), min(5, len(doc_ids)))
            logger.info(f"Selected {len(selected_doc_ids)} random documents")
            
            # For each selected document, get a random chunk
            chunks = []
            for doc_id in selected_doc_ids:
                # Get all chunks for this document
                doc_chunks = [
                    match for match in response.matches 
                    if match.metadata and match.metadata.get('document_id') == doc_id
                ]
                
                if doc_chunks:
                    # Select a random chunk
                    random_chunk = random.choice(doc_chunks)
                    
                    # Format the chunk
                    metadata = random_chunk.metadata or {}
                    chunk = {
                        'document_id': str(metadata.get('document_id', '')),
                        'content': str(metadata.get('content', '')),
                        'chunk_index': int(metadata.get('chunk_index', 0)),
                        'title': str(metadata.get('doc_title', 'Untitled')),
                        'metadata': {
                            'document_id': str(metadata.get('document_id', '')),
                            'chunk_index': int(metadata.get('chunk_index', 0)),
                            'doc_title': str(metadata.get('doc_title', '')),
                            'doc_type': str(metadata.get('doc_type', '')),
                            'section': str(metadata.get('section', '')),
                        }
                    }
                    chunks.append(chunk)
            
            # If we don't have enough chunks, get more random ones
            if len(chunks) < limit and response.matches:
                remaining = limit - len(chunks)
                random_matches = random.sample(response.matches, min(remaining, len(response.matches)))
                
                for match in random_matches:
                    # Skip if already included
                    if any(c['document_id'] == match.metadata.get('document_id', '') and 
                           c['chunk_index'] == int(match.metadata.get('chunk_index', 0)) 
                           for c in chunks):
                        continue
                    
                    metadata = match.metadata or {}
                    chunk = {
                        'document_id': str(metadata.get('document_id', '')),
                        'content': str(metadata.get('content', '')),
                        'chunk_index': int(metadata.get('chunk_index', 0)),
                        'title': str(metadata.get('doc_title', 'Untitled')),
                        'metadata': {
                            'document_id': str(metadata.get('document_id', '')),
                            'chunk_index': int(metadata.get('chunk_index', 0)),
                            'doc_title': str(metadata.get('doc_title', '')),
                            'doc_type': str(metadata.get('doc_type', '')),
                            'section': str(metadata.get('section', '')),
                        }
                    }
                    chunks.append(chunk)
                    
                    if len(chunks) >= limit:
                        break
            
            logger.info(f"Returning {len(chunks)} random chunks")
            return chunks[:limit]
            
        except Exception as e:
            logger.error(f"Error getting random chunks: {e}", exc_info=True)
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
            knowledge_base_id: The ID of the knowledge base to search (used as namespace)
            top_k: The number of chunks to retrieve
            metadata_filter: Optional additional metadata filter to apply
            similarity_threshold: Minimum similarity score for chunks to be included (default: 0.3)
            
        Returns:
            List of chunks with content and metadata
        """
        try:
            # Get embedding for the query using LLM Factory
            logger.info(f"Generating embedding for query using LLM Factory: '{query[:50]}...' (truncated)")
            embedding = await self._get_embedding(query)
            logger.info(f"Generated embedding with dimension {len(embedding)}")
            
            # Create filter (no need to include knowledge_base_id as it's now a namespace)
            filter = {}
            
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
            
            # Query Pinecone with namespace
            response = self.index.query(
                vector=embedding,
                filter=filter if filter else None,
                top_k=top_k * 2,  # Get more results than needed to allow for filtering
                include_metadata=True,
                namespace=knowledge_base_id
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

    async def add_questions(self, texts: List[str], metadatas: List[Dict], ids: List[str], collection_name: str) -> None:
        """Add questions with metadata to Pinecone - specialized for question ingestion
        
        Args:
            texts: List of question + answer text content
            metadatas: List of metadata dictionaries with question-specific fields
            ids: List of unique identifiers
            collection_name: Name of collection (used as namespace)
        """
        try:
            logger.info(f"Adding {len(texts)} questions to collection {collection_name}")
            
            # Process each question for storage
            vectors = []
            for i, (text, metadata, id) in enumerate(zip(texts, metadatas, ids)):
                # Get embedding
                logger.info(f"Generating embedding for question {i+1}/{len(texts)} (id: {id})")
                embedding = await self._get_embedding(text)
                logger.info(f"Generated embedding with dimension {len(embedding)}")
                
                # Clean up metadata - only include question-specific fields
                # No document-specific fields like chunk_index, doc_title, etc.
                pinecone_metadata = {
                    'content': text,
                    'question_id': metadata.get('question_id', ''),
                    'knowledge_base_id': metadata.get('knowledge_base_id', ''),
                    'answer_type': metadata.get('answer_type', ''),
                    'question': metadata.get('question', ''),
                    'answer': metadata.get('answer', ''),
                    'user_id': metadata.get('user_id', '')
                }
                
                logger.info(f"Prepared metadata for question: {pinecone_metadata.keys()}")
                
                # Create vector record with unique ID
                vectors.append({
                    'id': id,
                    'values': [float(x) for x in embedding],
                    'metadata': pinecone_metadata
                })
                
            # Upsert vectors in batches of 100
            batch_size = 100
            total_batches = (len(vectors) + batch_size - 1) // batch_size
            
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                logger.info(f"Upserting batch {batch_num}/{total_batches} ({len(batch)} vectors)")
                
                try:
                    # Use collection_name as namespace
                    self.index.upsert(vectors=batch, namespace=collection_name)
                    logger.info(f"Successfully upserted batch {batch_num}")
                except Exception as batch_error:
                    logger.error(f"Failed to upsert batch {batch_num}: {batch_error}")
                    # Log the first vector in the failing batch for debugging
                    if batch:
                        logger.info(f"Sample vector from failing batch: {batch[0]}")
                    raise
                
            logger.info(f"Successfully added {len(texts)} questions to Pinecone for collection {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to add questions to Pinecone: {e}", exc_info=True)
            raise


class VectorStoreFactory:
    """Factory class for creating VectorStore instances"""
    
    # Class-level registry to store instances
    _instances = {}
    # Lock for thread safety
    _lock = threading.RLock()
    
    @classmethod
    def create(cls, store_type: str = "pinecone", index_name: str = "docbrain") -> VectorStore:
        """Create or retrieve a VectorStore instance
        
        Args:
            store_type: Type of vector store to create ('pinecone', 'weaviate', 'chroma', etc.)
            index_name: Name of the Pinecone index to use ('docbrain' or 'summary')
            
        Returns:
            VectorStore: An instance of a VectorStore implementation
        """
        # Create a key for the instance registry
        instance_key = f"{store_type}_{index_name}"
        
        # First check without lock for performance
        if instance_key in cls._instances:
            logger.debug(f"Returning existing {store_type} instance for index {index_name}")
            return cls._instances[instance_key]
        
        # If not found, acquire lock and check again (double-checked locking pattern)
        with cls._lock:
            # Check again with lock held
            if instance_key in cls._instances:
                logger.debug(f"Returning existing {store_type} instance for index {index_name} (after lock)")
                return cls._instances[instance_key]
                
            # Create a new instance
            logger.info(f"Creating new {store_type} instance for index {index_name}")
            if store_type == "pinecone":
                instance = PineconeVectorStore(index_name=index_name)
                # Store in registry
                cls._instances[instance_key] = instance
                return instance
            else:
                # For future implementations like weaviate or chroma
                # We can add them here when needed
                raise ValueError(f"Unsupported vector store type: {store_type}")
            
    @classmethod
    def cleanup(cls, store_type: str = None, index_name: str = None):
        """
        Clean up vector store instances
        
        Args:
            store_type: Optional type to clean up only instances of this type
            index_name: Optional index name to clean up only instances for this index
        """
        with cls._lock:
            if store_type and index_name:
                # Clean up specific instance
                instance_key = f"{store_type}_{index_name}"
                if instance_key in cls._instances:
                    instance = cls._instances[instance_key]
                    if hasattr(instance, 'cleanup'):
                        instance.cleanup()
                    del cls._instances[instance_key]
                    logger.info(f"Cleaned up {store_type} instance for index {index_name}")
            elif store_type:
                # Clean up all instances of this type
                keys_to_remove = []
                for key, instance in cls._instances.items():
                    if key.startswith(f"{store_type}_"):
                        if hasattr(instance, 'cleanup'):
                            instance.cleanup()
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del cls._instances[key]
                
                logger.info(f"Cleaned up all {store_type} instances")
            elif index_name:
                # Clean up all instances with this index name
                keys_to_remove = []
                for key, instance in cls._instances.items():
                    if key.endswith(f"_{index_name}"):
                        if hasattr(instance, 'cleanup'):
                            instance.cleanup()
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del cls._instances[key]
                
                logger.info(f"Cleaned up all instances for index {index_name}")
            else:
                # Clean up all instances
                for instance in cls._instances.values():
                    if hasattr(instance, 'cleanup'):
                        instance.cleanup()
                
                cls._instances.clear()
                logger.info("Cleaned up all vector store instances")


# Helper functions for working with vector stores
def get_vector_store(store_type: str = "pinecone", index_name: str = "docbrain") -> VectorStore:
    """Get a vector store instance - uses singleton pattern
    
    This function returns a singleton instance for each unique combination of
    store_type and index_name. Subsequent calls with the same parameters will
    return the same instance.
    
    Args:
        store_type: Type of vector store ('pinecone', 'weaviate', 'chroma', etc.)
        index_name: Name of the Pinecone index to use ('docbrain' or 'summary')
        
    Returns:
        VectorStore instance (singleton per unique combination of parameters)
    """
    return VectorStoreFactory.create(store_type=store_type, index_name=index_name) 