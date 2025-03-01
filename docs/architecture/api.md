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

### POST /knowledge-bases/{kb_id}/upload

Upload a document to a knowledge base.

**Request:**
Form data with file and metadata.

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size": 1024,
  "status": "PENDING",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### GET /knowledge-bases/{kb_id}/documents

List all documents in a knowledge base.

**Response:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "filename": "document.pdf",
    "content_type": "application/pdf",
    "size": 1024,
    "status": "COMPLETED",
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
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size": 1024,
  "status": "COMPLETED",
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

## Conversations

### POST /conversations

Create a new conversation.

**Request:**
```json
{
  "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "My Conversation"
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "My Conversation",
  "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174000",
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
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
]
```

## Messages

### POST /conversations/{conversation_id}/messages

Send a message in a conversation.

**Request:**
```json
{
  "content": "What is DocBrain?"
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "content": "What is DocBrain?",
  "role": "user",
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2023-01-01T00:00:00Z"
}
```

### GET /conversations/{conversation_id}/messages

List all messages in a conversation.

**Response:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "content": "What is DocBrain?",
    "role": "user",
    "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
    "created_at": "2023-01-01T00:00:00Z"
  },
  {
    "id": "123e4567-e89b-12d3-a456-426614174001",
    "content": "DocBrain is a RAG (Retrieval-Augmented Generation) pipeline backend built with FastAPI, llama-index, and Pinecone.",
    "role": "assistant",
    "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
    "created_at": "2023-01-01T00:00:01Z"
  }
]
```
