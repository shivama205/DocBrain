# DocBrain Document Processing

## Document Upload and Processing Flow

The document upload and processing flow in DocBrain follows these steps:

1. **Document Upload**:
   - User uploads a document through the API
   - Document content is encoded as base64
   - Document entry is created in the database with status `PENDING`
   - Celery task is triggered to process the document

2. **Document Processing**:
   - Celery worker picks up the task
   - Document status is updated to `PROCESSING`
   - Document type is detected based on content type
   - Document is ingested using the appropriate ingestor
   - Document is chunked using the appropriate chunker
   - Chunks are stored in the vector store
   - Document summary is generated
   - Document status is updated to `COMPLETED`

3. **Error Handling**:
   - If any step fails, document status is updated to `FAILED`
   - Error message is stored in the document
   - Celery task is retried up to 3 times with exponential backoff

## Components

### Document Upload API

The document upload API is implemented in `app/api/endpoints/documents.py`. It handles:
- File upload
- Document metadata
- Database entry creation
- Celery task triggering

### Document Processing Task

The document processing task is implemented in `app/worker/tasks.py`. It handles:
- Document retrieval from database
- Document type detection
- Document ingestion
- Document chunking
- Vector store storage
- Summary generation
- Status updates

### RAG Service

The RAG service is implemented in `app/services/rag_service.py`. It provides:
- Document ingestion
- Document chunking
- Vector storage
- Retrieval
- Reranking
- Answer generation

## Testing

### Running the Celery Worker

To run the Celery worker for testing:

```bash
python -m app.worker.run_worker
```

### Testing Document Upload and Processing

To test the document upload and processing flow:

```bash
python -m app.tests.test_document_upload
```

## API Endpoints

### Upload Document

```
POST /api/v1/documents/upload
```

Form data:
- `file`: Document file
- `title`: Document title
- `knowledge_base_id`: Knowledge base ID
- `description`: (Optional) Document description

### Get Document

```
GET /api/v1/documents/{document_id}
```

### List Documents

```
GET /api/v1/documents/
```

Query parameters:
- `knowledge_base_id`: (Optional) Filter by knowledge base
- `skip`: (Optional) Number of records to skip
- `limit`: (Optional) Maximum number of records to return

### Delete Document

```
DELETE /api/v1/documents/{document_id}
``` 