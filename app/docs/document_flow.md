# Document Upload and Processing Flow

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│  Client/User    │──────▶  API Endpoint   │──────▶  Database       │
│                 │      │                 │      │                 │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         │                        │                        │
         │                        ▼                        │
         │               ┌─────────────────┐               │
         │               │                 │               │
         └──────────────▶│  Celery Task    │◀──────────────┘
                         │                 │
                         └────────┬────────┘
                                  │
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                         Document Processing                         │
│                                                                     │
│  ┌───────────────┐      ┌───────────────┐      ┌───────────────┐    │
│  │               │      │               │      │               │    │
│  │   Ingestor    │──────▶    Chunker    │──────▶   Retriever   │    │
│  │               │      │               │      │               │    │
│  └───────────────┘      └───────────────┘      └───────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │
                                  ▼
                         ┌─────────────────┐
                         │                 │
                         │  Update Status  │
                         │                 │
                         └─────────────────┘
```

## Flow Description

1. **Client/User**:
   - User uploads a document through the client application
   - Document is sent to the API endpoint

2. **API Endpoint**:
   - Receives the document
   - Validates the document
   - Creates a document entry in the database with status `PENDING`
   - Triggers a Celery task to process the document

3. **Database**:
   - Stores the document metadata
   - Stores the document content (base64 encoded)
   - Stores the document status

4. **Celery Task**:
   - Retrieves the document from the database
   - Updates document status to `PROCESSING`
   - Processes the document

5. **Document Processing**:
   - **Ingestor**: Extracts text and metadata from the document
   - **Chunker**: Splits the document into chunks
   - **Retriever**: Stores chunks in the vector store

6. **Update Status**:
   - Updates document status to `COMPLETED` if successful
   - Updates document status to `FAILED` if an error occurs
   - Stores error message if applicable
   - Stores processed chunks count
   - Stores document summary

## Sequence Diagram

```
┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐
│ Client  │          │   API   │          │ Database│          │ Celery  │
└────┬────┘          └────┬────┘          └────┬────┘          └────┬────┘
     │                    │                    │                    │
     │ Upload Document    │                    │                    │
     │ ─────────────────> │                    │                    │
     │                    │                    │                    │
     │                    │ Create Document    │                    │
     │                    │ ─────────────────> │                    │
     │                    │                    │                    │
     │                    │ Trigger Task       │                    │
     │                    │ ───────────────────────────────────────>│
     │                    │                    │                    │
     │ Return Document ID │                    │                    │
     │ <───────────────── │                    │                    │
     │                    │                    │                    │
     │                    │                    │ Get Document       │
     │                    │                    │ <─────────────────┐│
     │                    │                    │                    │
     │                    │                    │ Return Document    │
     │                    │                    │ ─────────────────>│
     │                    │                    │                    │
     │                    │                    │                    │ Process
     │                    │                    │                    │ Document
     │                    │                    │                    │
     │                    │                    │ Update Status      │
     │                    │                    │ <─────────────────┐│
     │                    │                    │                    │
     │ Get Document Status│                    │                    │
     │ ─────────────────> │                    │                    │
     │                    │                    │                    │
     │                    │ Get Document       │                    │
     │                    │ ─────────────────> │                    │
     │                    │                    │                    │
     │                    │ Return Document    │                    │
     │                    │ <───────────────── │                    │
     │                    │                    │                    │
     │ Return Status      │                    │                    │
     │ <───────────────── │                    │                    │
     │                    │                    │                    │
┌────┴────┐          ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
│ Client  │          │   API   │          │ Database│          │ Celery  │
└─────────┘          └─────────┘          └─────────┘          └─────────┘
``` 