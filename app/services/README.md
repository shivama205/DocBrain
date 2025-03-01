# RAG Service Architecture

This directory contains the implementation of a modular Retrieval-Augmented Generation (RAG) service for the DocBrain application. The architecture is designed to be flexible, extensible, and maintainable.

## Components

### 1. Ingestors

Ingestors extract text and metadata from different document types:

- `PDFIngestor`: Extracts text and metadata from PDF documents using docling for better structure preservation
- `CSVIngestor`: Extracts text and metadata from CSV documents
- `MarkdownIngestor`: Extracts text and metadata from Markdown documents
- `ImageIngestor`: Extracts text from images using docling OCR with pytesseract fallback
- `TextIngestor`: Extracts text from plain text documents

### 2. Chunkers

Chunkers split documents into smaller chunks for efficient retrieval:

- `SingleChunker`: Simple chunker that splits text into chunks of roughly equal size
- `MultiLevelChunker`: Advanced chunker that preserves document structure and hierarchy

### 3. Retrievers

Retrievers handle vector storage and retrieval:

- `PineconeRetriever`: Uses Pinecone as the vector store

### 4. Rerankers

Rerankers improve retrieval quality by reordering chunks based on relevance:

- `CrossEncoderReranker`: Uses a cross-encoder model to rerank chunks

### 5. LLMs

Language models generate answers based on retrieved chunks:

- `GeminiLLM`: Uses Google's Gemini API for answer generation

### 6. Factories

Factories create instances of the above components based on configuration:

- `IngestorFactory`: Creates ingestors based on document type
- `ChunkerFactory`: Creates chunkers based on document type
- `RetrieverFactory`: Creates retrievers based on configuration

## Main Service

The `RAGService` class combines all of these components to provide a complete RAG pipeline:

1. Document ingestion: Extract text and metadata from documents using docling for better quality
2. Chunking: Split documents into chunks with structure-aware chunking
3. Vector storage: Store chunks in a vector store
4. Retrieval: Find relevant chunks for a query
5. Reranking: Improve retrieval quality with cross-encoder reranking
6. Answer generation: Generate an answer based on retrieved chunks

## Usage

```python
from app.services.rag_service import RAGService
from app.services.chunker import ChunkSize

# Initialize RAG service
rag_service = RAGService(
    knowledge_base_id="your-kb-id",
    use_reranker=True
)

# Ingest a document
result = await rag_service.ingest_document(
    content=document_content,
    metadata=document_metadata,
    content_type="application/pdf",
    chunk_size=ChunkSize.MEDIUM
)

# Query the RAG service
result = await rag_service.retrieve(
    query="What is the main topic of the document?",
    top_k=5,
    similarity_threshold=0.3,
    rerank=True
)

# Access the answer and sources
answer = result["answer"]
sources = result["sources"]
```

## Docling Integration

The RAG service now uses [docling](https://github.com/docling/docling) for enhanced document processing:

- **PDF Processing**: Docling preserves document structure, extracts tables, and converts PDFs to markdown format
- **OCR Capabilities**: Improved text extraction from images with better accuracy
- **Fallback Mechanisms**: If docling processing fails, the system falls back to traditional methods (PyPDF2, pytesseract)

## Extending the Architecture

To add support for new components:

1. Create a new class that inherits from the appropriate base class
2. Implement the required methods
3. Update the corresponding factory to create instances of your new class

For example, to add a new retriever:

1. Create a new class that inherits from `Retriever`
2. Implement the required methods
3. Update `RetrieverFactory` to create instances of your new retriever