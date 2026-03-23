from typing import List, Dict, Any, Optional
import logging
import random
from app.core.config import settings
from app.services.rag.retriever.retriever import Retriever
from app.services.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


class ChromaRetriever(Retriever):
    """Retriever implementation using ChromaDB as the vector store."""

    def __init__(self, knowledge_base_id: str):
        super().__init__(knowledge_base_id)
        import chromadb

        persist_dir = getattr(settings, "CHROMA_PERSIST_DIR", "./chroma_data")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.index_name = getattr(settings, "CHROMA_COLLECTION_NAME", "docbrain")
        self.dimension = 3072

    def _collection_name(self) -> str:
        raw = f"{self.index_name}_{self.knowledge_base_id}"
        sanitized = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in raw)
        if len(sanitized) < 3:
            sanitized = sanitized + "_col"
        if len(sanitized) > 63:
            sanitized = sanitized[:63]
        if not sanitized[0].isalnum():
            sanitized = "c" + sanitized[1:]
        if not sanitized[-1].isalnum():
            sanitized = sanitized[:-1] + "0"
        return sanitized

    def _get_collection(self):
        return self.client.get_or_create_collection(
            name=self._collection_name(),
            metadata={"hnsw:space": "cosine"},
        )

    async def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        try:
            logger.info(f"Adding {len(chunks)} chunks to ChromaDB for kb {self.knowledge_base_id}")
            collection = self._get_collection()

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

    async def delete_document_chunks(self, document_id: str) -> None:
        try:
            logger.info(f"Deleting chunks for document {document_id} from ChromaDB")
            collection = self._get_collection()
            collection.delete(where={"document_id": {"$eq": str(document_id)}})
            logger.info(f"Successfully deleted chunks for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to delete document chunks from ChromaDB: {e}", exc_info=True)
            raise

    async def search(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            query_vector = await self._get_embedding(query)
            collection = self._get_collection()

            where_filter = None
            if metadata_filter:
                where_filter = {}
                for key, value in metadata_filter.items():
                    # Skip knowledge_base_id — ChromaDB uses separate collections per KB
                    if key == "knowledge_base_id":
                        continue
                    if isinstance(value, dict) and "$in" in value:
                        where_filter[key] = value
                    elif isinstance(value, (list, tuple)):
                        where_filter[key] = ','.join(str(x) for x in value)
                    else:
                        where_filter[key] = str(value)
                if not where_filter:
                    where_filter = None

            results = collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
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
                        'id': id_,
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
            return chunks[:top_k]

        except Exception as e:
            logger.error(f"Failed to search in ChromaDB: {e}", exc_info=True)
            raise

    async def get_random_chunks(self, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            collection = self._get_collection()
            count = collection.count()
            if count == 0:
                return []

            sample_size = min(count, 100)
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
                    'id': results['ids'][idx],
                    'document_id': str(metadata.get('document_id', '')),
                    'title': str(metadata.get('doc_title', 'Untitled')),
                    'content': content,
                    'chunk_index': int(metadata.get('chunk_index', 0)),
                    'metadata': metadata,
                }
                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"Failed to get random chunks from ChromaDB: {e}", exc_info=True)
            return []

    async def _get_embedding(self, text: str) -> List[float]:
        try:
            embedding = await LLMFactory.embed_text(
                text=text,
                model=settings.EMBEDDING_MODEL,
            )
            return embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}", exc_info=True)
            raise
