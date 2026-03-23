from typing import List, Dict, Any, Optional
import logging
import random
from app.services.rag.vector_store import VectorStore
from app.services.llm.factory import LLMFactory
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChromaVectorStore(VectorStore):
    """ChromaDB implementation of the VectorStore interface.

    Uses ChromaDB as a local vector store — no external API keys required.
    Each (index_name, knowledge_base_id) pair maps to a ChromaDB collection.
    """

    def __init__(self, index_name: str = "docbrain"):
        import chromadb

        self.index_name = index_name
        self.dimension = 3072  # gemini-embedding-001

        persist_dir = getattr(settings, "CHROMA_PERSIST_DIR", "./chroma_data")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self._connected = True
        logger.info(f"Initialized ChromaDB vector store (index={index_name}, persist_dir={persist_dir})")

    def _collection_name(self, knowledge_base_id: str) -> str:
        """Build a collection name from index + namespace.
        ChromaDB collection names must be 3-63 chars, start/end with alphanumeric."""
        raw = f"{self.index_name}_{knowledge_base_id}"
        # Sanitize: replace non-alphanumeric (except underscore/hyphen) with underscore
        sanitized = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in raw)
        # Ensure length constraints
        if len(sanitized) < 3:
            sanitized = sanitized + "_col"
        if len(sanitized) > 63:
            sanitized = sanitized[:63]
        # Ensure starts and ends with alphanumeric
        if not sanitized[0].isalnum():
            sanitized = "c" + sanitized[1:]
        if not sanitized[-1].isalnum():
            sanitized = sanitized[:-1] + "0"
        return sanitized

    def _get_collection(self, knowledge_base_id: str):
        name = self._collection_name(knowledge_base_id)
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )

    def cleanup(self):
        self._connected = False
        logger.info(f"Cleaned up ChromaVectorStore for index {self.index_name}")

    def __del__(self):
        if hasattr(self, '_connected') and self._connected:
            self.cleanup()

    async def add_chunks(self, chunks: List[Dict[str, Any]], knowledge_base_id: str) -> None:
        try:
            logger.info(f"Adding {len(chunks)} chunks to ChromaDB for kb {knowledge_base_id}")
            collection = self._get_collection(knowledge_base_id)

            ids = []
            embeddings = []
            documents = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                document_id = str(chunk['metadata']['document_id'])
                embedding = await self._get_embedding(chunk['content'])

                metadata = {
                    'document_id': document_id,
                    'chunk_index': int(chunk['metadata']['chunk_index']),
                    'chunk_size': str(chunk['metadata']['chunk_size']),
                    'doc_title': str(chunk['metadata']['document_title']),
                    'doc_type': str(chunk['metadata']['document_type']),
                    'section': str(chunk['metadata']['nearest_header']),
                    'path': ','.join(str(x) for x in chunk['metadata']['section_path']),
                }

                vector_id = f"{document_id}_chunk_{i}"
                ids.append(vector_id)
                embeddings.append([float(x) for x in embedding])
                documents.append(str(chunk['content']))
                metadatas.append(metadata)

            # Upsert in batches
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                end = min(i + batch_size, len(ids))
                collection.upsert(
                    ids=ids[i:end],
                    embeddings=embeddings[i:end],
                    documents=documents[i:end],
                    metadatas=metadatas[i:end],
                )

            logger.info(f"Successfully added {len(chunks)} chunks to ChromaDB")

        except Exception as e:
            logger.error(f"Failed to add chunks to ChromaDB: {e}", exc_info=True)
            raise

    async def add_texts(self, texts: List[str], metadatas: List[Dict], ids: List[str], collection_name: str) -> None:
        try:
            chunks = []
            for text, metadata, id_ in zip(texts, metadatas, ids):
                chunk = {
                    'content': text,
                    'metadata': {
                        'document_id': id_,
                        'chunk_index': 0,
                        'chunk_size': len(text),
                        'document_title': metadata.get('title', ''),
                        'document_type': metadata.get('type', ''),
                        'nearest_header': metadata.get('section', ''),
                        'section_path': metadata.get('path', '').split(',') if 'path' in metadata else [],
                        **metadata,
                    }
                }
                chunks.append(chunk)
            await self.add_chunks(chunks, collection_name)
        except Exception as e:
            logger.error(f"Failed to add texts to ChromaDB: {e}", exc_info=True)
            raise

    async def delete_document_chunks(self, document_id: str, knowledge_base_id: str) -> None:
        try:
            logger.info(f"Deleting chunks for document {document_id} from ChromaDB")
            collection = self._get_collection(knowledge_base_id)

            # ChromaDB supports filtering on metadata
            collection.delete(
                where={"document_id": {"$eq": str(document_id)}}
            )
            logger.info(f"Successfully deleted chunks for document {document_id}")

        except Exception as e:
            logger.error(f"Failed to delete document chunks from ChromaDB: {e}", exc_info=True)
            raise

    async def search_similar(
        self,
        query: str,
        knowledge_base_id: str,
        limit: int = 5,
        similarity_threshold: float = 0.3,
        metadata_filter: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        try:
            query_vector = await self._get_embedding(query)
            collection = self._get_collection(knowledge_base_id)

            where_filter = None
            if metadata_filter:
                where_filter = {}
                for key, value in metadata_filter.items():
                    if key == "knowledge_base_id":
                        continue
                    if isinstance(value, (list, tuple)):
                        where_filter[key] = ','.join(str(x) for x in value)
                    else:
                        where_filter[key] = str(value)
                if not where_filter:
                    where_filter = None

            results = collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                where=where_filter if where_filter else None,
                include=["embeddings", "documents", "metadatas", "distances"],
            )

            chunks = []
            if results and results['ids'] and results['ids'][0]:
                for i, id_ in enumerate(results['ids'][0]):
                    # ChromaDB returns distances (lower is better for cosine).
                    # cosine distance = 1 - cosine_similarity
                    distance = results['distances'][0][i] if results['distances'] else 0
                    score = 1.0 - distance

                    if score < similarity_threshold:
                        continue

                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    content = results['documents'][0][i] if results['documents'] else ''

                    is_question = 'question_id' in metadata and 'question' in metadata

                    if is_question:
                        chunk = {
                            'score': float(score),
                            'content': content,
                            'question_id': str(metadata.get('question_id', '')),
                            'question': str(metadata.get('question', '')),
                            'answer': str(metadata.get('answer', '')),
                            'answer_type': str(metadata.get('answer_type', 'DIRECT')),
                            'metadata': {
                                'question_id': str(metadata.get('question_id', '')),
                                'knowledge_base_id': str(metadata.get('knowledge_base_id', '')),
                                'answer': str(metadata.get('answer', '')),
                                'answer_type': str(metadata.get('answer_type', 'DIRECT')),
                                'score': float(score),
                            }
                        }
                    else:
                        chunk = {
                            'score': float(score),
                            'document_id': str(metadata.get('document_id', '')),
                            'content': content,
                            'chunk_index': int(metadata.get('chunk_index', 0)),
                            'title': str(metadata.get('doc_title', 'Untitled')),
                            'metadata': {
                                'document_id': str(metadata.get('document_id', '')),
                                'chunk_index': int(metadata.get('chunk_index', 0)),
                                'chunk_size': str(metadata.get('chunk_size', '')),
                                'doc_title': str(metadata.get('doc_title', '')),
                                'doc_type': str(metadata.get('doc_type', '')),
                                'section': str(metadata.get('section', '')),
                                'path': metadata.get('path', '').split(',') if metadata.get('path') else [],
                            }
                        }

                    if not chunk['content']:
                        continue
                    chunks.append(chunk)

            chunks.sort(key=lambda x: x['score'], reverse=True)
            return chunks[:limit]

        except Exception as e:
            logger.error(f"Failed to search in ChromaDB: {e}", exc_info=True)
            raise

    async def get_random_chunks(self, knowledge_base_id: str, limit: int = 5) -> List[Dict]:
        try:
            collection = self._get_collection(knowledge_base_id)
            count = collection.count()
            if count == 0:
                return []

            # Get all items (up to a reasonable limit) and sample randomly
            sample_size = min(count, 1000)
            results = collection.get(
                limit=sample_size,
                include=["documents", "metadatas"],
            )

            if not results['ids']:
                return []

            indices = list(range(len(results['ids'])))
            random.shuffle(indices)
            selected = indices[:limit]

            chunks = []
            for idx in selected:
                metadata = results['metadatas'][idx] if results['metadatas'] else {}
                content = results['documents'][idx] if results['documents'] else ''
                chunk = {
                    'document_id': str(metadata.get('document_id', '')),
                    'content': content,
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

            return chunks

        except Exception as e:
            logger.error(f"Error getting random chunks from ChromaDB: {e}", exc_info=True)
            return []

    async def search_chunks(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict] = None,
        similarity_threshold: float = 0.3
    ) -> List[Dict]:
        try:
            embedding = await self._get_embedding(query)
            collection = self._get_collection(knowledge_base_id)

            where_filter = None
            if metadata_filter:
                where_filter = {}
                for key, value in metadata_filter.items():
                    if key in ("similarity_threshold", "knowledge_base_id"):
                        continue
                    if isinstance(value, dict):
                        if "$in" in value:
                            where_filter[key] = {"$in": [str(v) for v in value["$in"]]}
                        else:
                            where_filter[key] = value
                    else:
                        where_filter[key] = {"$eq": str(value)}
                if not where_filter:
                    where_filter = None

            results = collection.query(
                query_embeddings=[embedding],
                n_results=top_k * 2,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"],
            )

            chunks = []
            if results and results['ids'] and results['ids'][0]:
                for i, id_ in enumerate(results['ids'][0]):
                    distance = results['distances'][0][i] if results['distances'] else 0
                    score = 1.0 - distance

                    if score < similarity_threshold:
                        continue

                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    content = results['documents'][0][i] if results['documents'] else ''

                    chunk = {
                        "id": id_,
                        "content": content,
                        "document_id": metadata.get("document_id", "") or metadata.get("doc_id", ""),
                        "metadata": {
                            "doc_title": metadata.get("doc_title", ""),
                            "doc_id": metadata.get("doc_id", ""),
                            "document_id": metadata.get("document_id", "") or metadata.get("doc_id", ""),
                            "chunk_id": metadata.get("chunk_id", ""),
                            "knowledge_base_id": metadata.get("knowledge_base_id", ""),
                        },
                        "score": score,
                    }
                    chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"Error searching chunks in ChromaDB: {e}", exc_info=True)
            return []

    async def add_questions(self, texts: List[str], metadatas: List[Dict], ids: List[str], collection_name: str) -> None:
        try:
            logger.info(f"Adding {len(texts)} questions to ChromaDB collection {collection_name}")
            collection = self._get_collection(collection_name)

            all_ids = []
            all_embeddings = []
            all_documents = []
            all_metadatas = []

            for i, (text, metadata, id_) in enumerate(zip(texts, metadatas, ids)):
                embedding = await self._get_embedding(text)

                chroma_metadata = {
                    'question_id': metadata.get('question_id', ''),
                    'knowledge_base_id': metadata.get('knowledge_base_id', ''),
                    'answer_type': metadata.get('answer_type', ''),
                    'question': metadata.get('question', ''),
                    'answer': metadata.get('answer', ''),
                    'user_id': metadata.get('user_id', ''),
                }

                all_ids.append(id_)
                all_embeddings.append([float(x) for x in embedding])
                all_documents.append(text)
                all_metadatas.append(chroma_metadata)

            batch_size = 100
            for i in range(0, len(all_ids), batch_size):
                end = min(i + batch_size, len(all_ids))
                collection.upsert(
                    ids=all_ids[i:end],
                    embeddings=all_embeddings[i:end],
                    documents=all_documents[i:end],
                    metadatas=all_metadatas[i:end],
                )

            logger.info(f"Successfully added {len(texts)} questions to ChromaDB")

        except Exception as e:
            logger.error(f"Failed to add questions to ChromaDB: {e}", exc_info=True)
            raise

    async def _get_embedding(self, text: str) -> List[float]:
        try:
            embedding = await LLMFactory.embed_text(
                text=text,
                model=settings.EMBEDDING_MODEL,
            )
            if len(embedding) != self.dimension:
                raise ValueError(f"Expected embedding dimension {self.dimension}, got {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}", exc_info=True)
            raise
