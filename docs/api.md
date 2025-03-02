# DocBrain API Documentation

## Authentication

### Login for Access Token
- **Endpoint**: `POST /auth/token`
- **Description**: OAuth2 compatible token login endpoint
- **Request Body** (form-data):
  ```
  username: string (user's email)
  password: string
  ```
- **Response**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1...",
    "token_type": "bearer"
  }
  ```

## Users

All endpoints require authentication unless specified otherwise.

### Create User
- **Endpoint**: `POST /users`
- **Description**: Create a new user
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "full_name": "John Doe",
    "password": "secretpassword",
    "role": "user"  // Optional, defaults to "user"
  }
  ```
- **Response**: User object

### List Users
- **Endpoint**: `GET /users`
- **Description**: List all users (admin only)
- **Response**: Array of user objects

### Get User
- **Endpoint**: `GET /users/{user_id}`
- **Description**: Get user details
- **Access**: Admin or self only
- **Response**: User object

### Update User
- **Endpoint**: `PUT /users/{user_id}`
- **Description**: Update user details
- **Access**: Admin or self only
- **Request Body**:
  ```json
  {
    "email": "new@example.com",  // Optional
    "full_name": "New Name",     // Optional
    "password": "newpassword",   // Optional
    "role": "admin"              // Optional, admin only
  }
  ```
- **Response**: Updated user object

### Delete User
- **Endpoint**: `DELETE /users/{user_id}`
- **Description**: Delete user
- **Access**: Admin only
- **Response**: Success message

## Knowledge Bases

### Create Knowledge Base
- **Endpoint**: `POST /knowledge-bases`
- **Description**: Creates a new knowledge base
- **Request Body**:
  ```json
  {
    "name": "My Knowledge Base",
    "description": "Description of the knowledge base"
  }
  ```
- **Response**: Knowledge base object

### List Knowledge Bases
- **Endpoint**: `GET /knowledge-bases`
- **Description**: Lists all accessible knowledge bases
- **Response**: Array of knowledge base objects
- **Notes**: 
  - Admins see all knowledge bases
  - Regular users see only owned or shared knowledge bases

### Get Knowledge Base
- **Endpoint**: `GET /knowledge-bases/{kb_id}`
- **Description**: Get knowledge base details
- **Response**: Knowledge base object

### Update Knowledge Base
- **Endpoint**: `PUT /knowledge-bases/{kb_id}`
- **Description**: Update knowledge base details
- **Access**: Owner or admin only
- **Request Body**:
  ```json
  {
    "name": "New Name",           // Optional
    "description": "New Desc"     // Optional
  }
  ```
- **Response**: Updated knowledge base object

### Delete Knowledge Base
- **Endpoint**: `DELETE /knowledge-bases/{kb_id}`
- **Description**: Delete knowledge base and all its documents
- **Access**: Owner or admin only
- **Response**: Success message

### Share Knowledge Base
- **Endpoint**: `POST /knowledge-bases/{kb_id}/share/{user_id}`
- **Description**: Share knowledge base with another user
- **Access**: Owner or admin only
- **Response**: Success message

### Upload Document
- **Endpoint**: `POST /knowledge-bases/{kb_id}/documents`
- **Description**: Upload a new document to a knowledge base
- **Request Body** (multipart/form-data):
  ```
  title: string
  file: binary
  ```
- **Response**: Document object

### List Documents
- **Endpoint**: `GET /knowledge-bases/{kb_id}/documents`
- **Description**: List all documents in a knowledge base
- **Response**: Array of document objects

### Get Document
- **Endpoint**: `GET /knowledge-bases/{kb_id}/documents/{doc_id}`
- **Description**: Get document details
- **Response**: Document object

### Update Document
- **Endpoint**: `PUT /knowledge-bases/{kb_id}/documents/{doc_id}`
- **Description**: Update document details
- **Access**: Knowledge base owner or admin only
- **Request Body**:
  ```json
  {
    "title": "New Title"  // Optional
  }
  ```
- **Response**: Updated document object

### Delete Document
- **Endpoint**: `DELETE /knowledge-bases/{kb_id}/documents/{doc_id}`
- **Description**: Delete a document
- **Access**: Knowledge base owner or admin only
- **Response**: Success message

## Conversations

### Create Conversation
- **Endpoint**: `POST /conversations`
- **Description**: Create a new conversation
- **Request Body**:
  ```json
  {
    "title": "My Conversation",
    "knowledge_base_id": "kb_123"
  }
  ```
- **Response**: Conversation object

### List Conversations
- **Endpoint**: `GET /conversations`
- **Description**: List all conversations for the current user
- **Response**: Array of conversation objects

### Get Conversation
- **Endpoint**: `GET /conversations/{conversation_id}`
- **Description**: Get conversation details including messages
- **Response**: Conversation object with messages

### Update Conversation
- **Endpoint**: `PUT /conversations/{conversation_id}`
- **Description**: Update conversation details
- **Request Body**:
  ```json
  {
    "title": "New Title"  // Optional
  }
  ```
- **Response**: Updated conversation object

### Delete Conversation
- **Endpoint**: `DELETE /conversations/{conversation_id}`
- **Description**: Delete a conversation and all its messages
- **Response**: Success message

## Messages

### Create Message
- **Endpoint**: `POST /conversations/{conversation_id}/messages`
- **Description**: Create a new message in a conversation
- **Request Body**:
  ```json
  {
    "content": "What is this document about?",
    "type": "user",
    "top_k": 5,              // Optional, default: 5
    "similarity_cutoff": 0.3  // Optional, default: 0.3
  }
  ```
- **Response**: Message object
- **Notes**:
  - Creates both user message and assistant response
  - Assistant response is processed asynchronously
  - Response includes only the user message, assistant message can be retrieved later

### List Messages
- **Endpoint**: `GET /conversations/{conversation_id}/messages`
- **Description**: List all messages in a conversation
- **Response**: Array of message objects

### Get Message
- **Endpoint**: `GET /conversations/{conversation_id}/messages/{message_id}`
- **Description**: Get message details
- **Response**: Message object

## Response Objects

### User Object
```json
{
  "id": "user_id",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "user",
  "is_active": true
}
```

### Knowledge Base Object
```json
{
  "id": "kb_id",
  "name": "My Knowledge Base",
  "description": "Description",
  "user_id": "user_id",
  "shared_with": ["user_id1", "user_id2"],
  "created_at": "2024-02-24T12:00:00Z",
  "updated_at": "2024-02-24T12:00:00Z"
}
```

### Document Object
```json
{
  "id": "doc_id",
  "title": "Document Title",
  "knowledge_base_id": "kb_id",
  "file_name": "document.pdf",
  "content_type": "application/pdf",
  "vector_ids": ["vector1", "vector2"],
  "status": "completed",
  "created_at": "2024-02-24T12:00:00Z",
  "updated_at": "2024-02-24T12:00:00Z"
}
```

### Conversation Object
```json
{
  "id": "conversation_id",
  "title": "My Conversation",
  "knowledge_base_id": "kb_id",
  "user_id": "user_id",
  "messages": [
    {
      "id": "message_id",
      "conversation_id": "conversation_id",
      "content": "What is this document about?",
      "type": "user",
      "sources": null,
      "created_at": "2024-02-24T12:00:00Z",
      "status": "completed"
    },
    {
      "id": "message_id2",
      "conversation_id": "conversation_id",
      "content": "This document discusses...",
      "type": "assistant",
      "sources": [
        {
          "score": 0.95,
          "document_id": "doc_123",
          "title": "Example Document",
          "content": "Relevant content...",
          "chunk_index": 0
        }
      ],
      "created_at": "2024-02-24T12:00:01Z",
      "status": "completed"
    }
  ],
  "created_at": "2024-02-24T12:00:00Z",
  "updated_at": "2024-02-24T12:00:00Z"
}
```

### Message Object
```json
{
  "id": "message_id",
  "conversation_id": "conversation_id",
  "content": "What is this document about?",
  "type": "user",
  "sources": null,
  "created_at": "2024-02-24T12:00:00Z",
  "status": "completed"
}
```

## Error Responses

All endpoints may return these error responses:

### Authentication Errors
- **401 Unauthorized**
  ```json
  {
    "detail": "Could not validate credentials"
  }
  ```
  
- **403 Forbidden**
  ```json
  {
    "detail": "Not enough privileges"
  }
  ```

### Resource Errors
- **404 Not Found**
  ```json
  {
    "detail": "Resource not found"
  }
  ```

- **400 Bad Request**
  ```json
  {
    "detail": "Invalid input"
  }
  ```

## Authentication Flow

1. **Get Access Token**:
   ```bash
   curl -X POST "http://localhost:8000/auth/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=user@example.com&password=userpassword"
   ```

2. **Use Token in Requests**:
   ```bash
   curl -X GET "http://localhost:8000/api/conversations" \
        -H "Authorization: Bearer eyJhbGciOiJIUzI1..."
   ``` 