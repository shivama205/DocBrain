# RAG Service Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                             RAG Service                                  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Document Processing                             │
│                                                                         │
│  ┌───────────────┐      ┌───────────────┐      ┌───────────────┐        │
│  │   Ingestor    │──────▶    Chunker    │──────▶   Retriever   │        │
│  │               │      │               │      │               │        │
│  │ - PDFIngestor │      │ - SingleChunker│      │ - PineconeRetriever │ │
│  │   (docling)   │      │ - MultiLevelChunker│  │               │      │
│  │ - CSVIngestor │      │               │      │               │        │
│  │ - MarkdownIngestor│  │               │      │               │        │
│  │ - ImageIngestor │   │               │      │               │        │
│  │   (docling OCR) │   │               │      │               │        │
│  │ - TextIngestor  │   │               │      │               │        │
│  └───────────────┘      └───────────────┘      └───────────────┘        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Query Processing                               │
│                                                                         │
│  ┌───────────────┐      ┌───────────────┐      ┌───────────────┐        │
│  │   Retriever   │──────▶    Reranker   │──────▶      LLM      │        │
│  │               │      │               │      │               │        │
│  │ - PineconeRetriever │ │ - CrossEncoderReranker │ │ - GeminiLLM │    │
│  │               │      │ - FlagEmbeddingReranker │ │               │   │
│  └───────────────┘      └───────────────┘      └───────────────┘        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                               Result                                     │
│                                                                         │
│                        ┌───────────────────┐                            │
│                        │     Answer +      │                            │
│                        │     Sources       │                            │
│                        └───────────────────┘                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                             Factories                                    │
│                                                                         │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐    │
│  │  IngestorFactory  │  │  ChunkerFactory   │  │  RetrieverFactory │    │
│  │  (Singleton)      │  │                   │  │  (Singleton)      │    │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘    │
│                                                                         │
│  ┌───────────────────┐                                                  │
│  │  RerankerFactory  │                                                  │
│  │  (Singleton)      │                                                  │
│  └───────────────────┘                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Document Processing**:
   - Document content is passed to an appropriate `Ingestor` based on content type
   - Ingestor extracts text and metadata from the document (using docling for PDFs and images)
   - Text and metadata are passed to a `Chunker` based on document type
   - Chunker splits the text into chunks with enhanced metadata
   - Chunks are stored in a vector store using a `Retriever`

2. **Query Processing**:
   - Query is passed to the `Retriever` to find relevant chunks
   - Retrieved chunks are passed to the `Reranker` to improve relevance
   - Reranked chunks are passed to the `LLM` to generate an answer
   - Answer and source chunks are returned as the result

3. **Factories**:
   - `IngestorFactory` creates the appropriate ingestor based on content type
   - `ChunkerFactory` creates the appropriate chunker based on document type
   - `RetrieverFactory` creates the appropriate retriever based on configuration
   - `RerankerFactory` creates the appropriate reranker based on configuration

## Component Interfaces

- **Ingestor**: `ingest(content, metadata) -> {text, metadata}`
- **Chunker**: `chunk(text, metadata, chunk_size) -> [{content, metadata}]`
- **Retriever**: `add_chunks(chunks)`, `search(query, top_k, similarity_threshold, metadata_filter) -> [chunks]`
- **Reranker**: `rerank(query, chunks, top_k) -> [chunks]`
- **LLM**: `generate_answer(query, context) -> answer`

## Factory Pattern Implementation

The factory pattern is used to create instances of various components in the RAG pipeline. Key improvements include:

1. **Singleton Pattern**:
   - Factory classes (`IngestorFactory`, `RerankerFactory`) use a singleton pattern
   - Models are only initialized once and reused, preventing redundant initialization
   - This is particularly important for ML models that are expensive to load

2. **Pre-initialization**:
   - Models can be pre-initialized at application or worker startup
   - This ensures models are loaded in the main process before any forking occurs
   - Prevents segmentation faults in multiprocessing environments

3. **Platform-Specific Handling**:
   - Special handling for macOS to avoid issues with Metal Performance Shaders (MPS)
   - Models are configured to use CPU only on macOS
   - Environment variables are set to disable GPU acceleration

Example of singleton factory implementation:
```python
class RerankerFactory:
    # Singleton instances
    _flag_embedding_instance: Optional[Reranker] = None
    
    @staticmethod
    def _create_flag_embedding_reranker(config: Dict[str, Any]) -> Reranker:
        # Return existing instance if available
        if RerankerFactory._flag_embedding_instance is not None:
            return RerankerFactory._flag_embedding_instance
            
        # Create and store the instance
        RerankerFactory._flag_embedding_instance = FlagEmbeddingReranker(
            model_name=config.get("model_name", "BAAI/bge-reranker-v2-m3")
        )
        return RerankerFactory._flag_embedding_instance
        
    @staticmethod
    def initialize_models(config: Dict[str, Any] = None) -> None:
        # Pre-initialize models at startup
        RerankerFactory._create_flag_embedding_reranker(config or {})
```

## Docling Integration

The docling library is integrated into the document processing pipeline to provide:

1. **Enhanced PDF Processing**:
   - Better structure preservation
   - Table extraction
   - Markdown conversion
   - Metadata extraction

2. **Improved OCR**:
   - More accurate text extraction from images
   - Better handling of complex layouts

3. **Fallback Mechanisms**:
   - If docling processing fails, the system falls back to traditional methods
   - PyPDF2 for PDF processing
   - pytesseract for OCR 