# DocBrain API Documentation

This document provides an overview of the DocBrain API endpoints.

## Authentication

### POST /auth/login

Log in with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Knowledge Bases

### POST /knowledge-bases

Create a new knowledge base.

**Request:**
```json
{
  "name": "My Knowledge Base",
  "description": "A collection of documents"
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "My Knowledge Base",
  "description": "A collection of documents",
  "user_id": "user123",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### GET /knowledge-bases

List all knowledge bases.

**Response:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "My Knowledge Base",
    "description": "A collection of documents",
    "user_id": "user123",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
]
```

### GET /knowledge-bases/{kb_id}

Get details of a specific knowledge base.

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "My Knowledge Base",
  "description": "A collection of documents",
  "user_id": "user123",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### PUT /knowledge-bases/{kb_id}

Update a knowledge base.

**Request:**
```json
{
  "name": "Updated Knowledge Base",
  "description": "Updated description"
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Updated Knowledge Base",
  "description": "Updated description",
  "user_id": "user123",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### DELETE /knowledge-bases/{kb_id}

Delete a knowledge base.

**Response:**
```json
{
  "message": "Knowledge base deleted successfully"
}
```

## Documents

### POST /knowledge-bases/{kb_id}/documents

Upload a document to a knowledge base.

**Request:**
Form data with file upload.

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "document.pdf",
  "file_type": "application/pdf",
  "size_bytes": 1024,
  "status": "PENDING",
  "error_message": null,
  "knowledge_base_id": "kb123",
  "user_id": "user123",
  "processed_chunks": null,
  "summary": null,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

**Note:** Document processing is handled asynchronously by Celery workers. The initial status will be "PENDING" and will change to "PROCESSING", "COMPLETED", or "FAILED" as the document is processed.

### GET /knowledge-bases/{kb_id}/documents

List all documents in a knowledge base.

**Response:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "document.pdf",
    "file_type": "application/pdf",
    "size_bytes": 1024,
    "status": "COMPLETED",
    "error_message": null,
    "knowledge_base_id": "kb123",
    "user_id": "user123",
    "processed_chunks": 42,
    "summary": "This is a summary of the document content.",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
]
```

### GET /knowledge-bases/{kb_id}/documents/{doc_id}

Get details of a specific document.

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "document.pdf",
  "file_type": "application/pdf",
  "size_bytes": 1024,
  "status": "COMPLETED",
  "error_message": null,
  "knowledge_base_id": "kb123",
  "user_id": "user123",
  "processed_chunks": 42,
  "summary": "This is a summary of the document content.",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### DELETE /knowledge-bases/{kb_id}/documents/{doc_id}

Delete a document.

**Response:**
```json
{
  "message": "Document deleted successfully"
}
```

**Note:** Document deletion is handled asynchronously by Celery workers. The document's vectors will be removed from the vector store in the background.

## Conversations

### POST /conversations

Create a new conversation.

**Request:**
```json
{
  "title": "My Conversation",
  "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "My Conversation",
  "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user123",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### GET /conversations

List all conversations.

**Response:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "My Conversation",
    "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "user123",
    "is_active": true,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
]
```

### GET /conversations/{conversation_id}

Get details of a specific conversation.

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "My Conversation",
  "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user123",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### PUT /conversations/{conversation_id}

Update a conversation.

**Request:**
```json
{
  "title": "Updated Conversation Title"
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Updated Conversation Title",
  "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user123",
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### DELETE /conversations/{conversation_id}

Delete a conversation.

**Response:**
```json
{
  "message": "Conversation deleted successfully"
}
```

## Messages

### POST /conversations/{conversation_id}/messages

Send a message in a conversation.

**Request:**
```json
{
  "content": "What is DocBrain?",
  "content_type": "TEXT"
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "content": "What is DocBrain?",
  "content_type": "TEXT",
  "kind": "USER",
  "user_id": "user123",
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "knowledge_base_id": "kb123",
  "sources": null,
  "status": "RECEIVED",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

**Note:** When a user sends a message, the system will automatically generate an assistant response. The initial status will be "RECEIVED" and will change to "PROCESSING" and then "PROCESSED" or "FAILED" as the message is processed.

### GET /conversations/{conversation_id}/messages

List all messages in a conversation.

**Response:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "content": "What is DocBrain?",
    "content_type": "TEXT",
    "kind": "USER",
    "user_id": "user123",
    "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
    "knowledge_base_id": "kb123",
    "sources": null,
    "status": "RECEIVED",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  },
  {
    "id": "123e4567-e89b-12d3-a456-426614174001",
    "content": "DocBrain is a RAG (Retrieval-Augmented Generation) pipeline backend built with FastAPI, llama-index, and Pinecone.",
    "content_type": "TEXT",
    "kind": "ASSISTANT",
    "user_id": "system",
    "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
    "knowledge_base_id": "kb123",
    "sources": [
      {
        "score": 0.92,
        "document_id": "doc123",
        "title": "DocBrain Overview",
        "content": "DocBrain is a RAG (Retrieval-Augmented Generation) pipeline backend built with FastAPI, llama-index, and Pinecone.",
        "chunk_index": 3
      }
    ],
    "status": "PROCESSED",
    "created_at": "2023-01-01T00:00:01Z",
    "updated_at": "2023-01-01T00:00:01Z"
  }
]
```

### GET /conversations/{conversation_id}/messages/{message_id}

Get a specific message.

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174001",
  "content": "DocBrain is a RAG (Retrieval-Augmented Generation) pipeline backend built with FastAPI, llama-index, and Pinecone.",
  "content_type": "TEXT",
  "kind": "ASSISTANT",
  "user_id": "system",
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "knowledge_base_id": "kb123",
  "sources": [
    {
      "score": 0.92,
      "document_id": "doc123",
      "title": "DocBrain Overview",
      "content": "DocBrain is a RAG (Retrieval-Augmented Generation) pipeline backend built with FastAPI, llama-index, and Pinecone.",
      "chunk_index": 3
    }
  ],
  "status": "PROCESSED",
  "created_at": "2023-01-01T00:00:01Z",
  "updated_at": "2023-01-01T00:00:01Z"
}
```

## Worker System

DocBrain uses Celery workers for asynchronous tasks such as document ingestion and vector deletion. The worker system is not directly exposed through the API but is an essential part of the backend infrastructure.

### Worker Architecture

- **Celery Workers**: Handle asynchronous tasks triggered by API endpoints
- **Task Queue**: Redis is used as the message broker for task distribution
- **Task Types**:
  - `initiate_document_ingestion`: Processes uploaded documents
  - `initiate_document_vector_deletion`: Removes document vectors from the vector store

### Platform-Specific Considerations

On macOS, there are special considerations for running workers due to issues with Metal Performance Shaders (MPS) and multiprocessing. See the [macOS Troubleshooting Guide](../guides/macos_troubleshooting.md) for details.

## Model Initialization

DocBrain uses a sophisticated model initialization strategy to ensure reliable operation across different environments:

- **Singleton Pattern**: Factory classes use a singleton pattern to ensure models are only initialized once
- **Pre-initialization**: Models are loaded in the main process before any forking occurs
- **CPU-only Mode**: Models are configured to use CPU only on macOS to avoid MPS issues

This approach prevents segmentation faults that can occur when models are initialized after forking, particularly on macOS.
