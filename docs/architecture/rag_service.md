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
│  │               │      │               │      │               │        │
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
│  └───────────────────┘  └───────────────────┘  └───────────────────┘    │
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

## Component Interfaces

- **Ingestor**: `ingest(content, metadata) -> {text, metadata}`
- **Chunker**: `chunk(text, metadata, chunk_size) -> [{content, metadata}]`
- **Retriever**: `add_chunks(chunks)`, `search(query, top_k, similarity_threshold, metadata_filter) -> [chunks]`
- **Reranker**: `rerank(query, chunks, top_k) -> [chunks]`
- **LLM**: `generate_answer(query, context) -> answer`

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