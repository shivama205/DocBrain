# RAG Service Changes

## Overview

We've completely redesigned the RAG (Retrieval-Augmented Generation) service to be more modular, extensible, and maintainable. The new architecture follows a component-based design with clear interfaces and factory patterns.

## Key Changes

1. **Modular Architecture**:
   - Created abstract base classes for each component
   - Implemented concrete classes for each component
   - Used factory patterns to create components based on configuration

2. **Enhanced Document Processing**:
   - Integrated docling for better PDF processing and OCR
   - Improved structure preservation in document extraction
   - Added fallback mechanisms for robustness

3. **Improved Retrieval**:
   - Implemented a dedicated Retriever interface
   - Created a PineconeRetriever implementation
   - Added namespace support for better organization

4. **Neural Reranking**:
   - Added cross-encoder reranking for better relevance
   - Made reranking optional and configurable

5. **Simplified API**:
   - Consolidated the RAG pipeline into a single service
   - Reduced the number of parameters needed for common operations
   - Improved error handling and logging

## Component Changes

### Ingestors

- Created a base `Ingestor` interface
- Implemented specialized ingestors for different document types
- Added docling integration for PDF and image processing
- Improved metadata extraction

### Chunkers

- Created a base `Chunker` interface
- Implemented `SingleChunker` and `MultiLevelChunker`
- Enhanced metadata preservation during chunking
- Added structure-aware chunking

### Retrievers

- Created a base `Retriever` interface
- Implemented `PineconeRetriever`
- Added namespace support for better organization
- Improved error handling and logging

### Rerankers

- Created a base `Reranker` interface
- Implemented `CrossEncoderReranker`
- Added fallback to original scores if reranking fails

### LLMs

- Created a base `LLM` interface
- Implemented `GeminiLLM`
- Improved prompt construction
- Enhanced error handling

### Factories

- Created factories for each component type
- Simplified component creation
- Made it easy to add new implementations

## Migration Guide

To migrate from the old RAG service to the new one:

1. Replace imports:
   ```python
   # Old
   from app.repositories.vector_repository import VectorRepository
   from app.services.rag_service import RAGService
   
   # New
   from app.services.rag_service import RAGService
   ```

2. Update initialization:
   ```python
   # Old
   vector_repo = VectorRepository()
   rag_service = RAGService(vector_repo)
   
   # New
   rag_service = RAGService(knowledge_base_id="your-kb-id")
   ```

3. Update method calls:
   ```python
   # Old
   response = await rag_service.process_query(
       query=query,
       top_k=5,
       metadata_filter=None,
       similarity_threshold=0.3
   )
   
   # New
   response = await rag_service.retrieve(
       query=query,
       top_k=5,
       similarity_threshold=0.3,
       rerank=True
   )
   ```

## Examples

See the following examples for how to use the new RAG service:

- `app/examples/rag_example.py`: Basic usage example
- `app/examples/docling_test.py`: Example with docling integration

## Setup

Run the setup script to install the necessary dependencies:

```bash
./app/examples/setup_rag.sh
``` 