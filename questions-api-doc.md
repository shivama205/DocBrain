# Questions API Documentation

## 1. List Questions

Retrieves all questions for a specific knowledge base.

- **URL**: `/api/knowledge-bases/{kb_id}/questions`
- **Method**: `GET`
- **Authentication**: Required

### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| kb_id     | string | Knowledge base ID |

### Query Parameters
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| skip      | integer | Number of records to skip | 0 |
| limit     | integer | Maximum number of records to return | 100 |

### Success Response
- **Code**: 200 OK
- **Content**:
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "question": "What is DocBrain?",
    "answer": "DocBrain is a knowledge management system.",
    "answer_type": "DIRECT",
    "status": "COMPLETED",
    "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174001",
    "user_id": "123e4567-e89b-12d3-a456-426614174002",
    "created_at": "2023-01-01T00:00:00",
    "updated_at": "2023-01-01T01:00:00"
  }
]
```

## 2. Get Question

Retrieves a specific question by ID.

- **URL**: `/api/knowledge-bases/{kb_id}/questions/{question_id}`
- **Method**: `GET`
- **Authentication**: Required

### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| kb_id     | string | Knowledge base ID |
| question_id | string | Question ID |

### Success Response
- **Code**: 200 OK
- **Content**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "question": "What is DocBrain?",
  "answer": "DocBrain is a knowledge management system.",
  "answer_type": "DIRECT",
  "status": "COMPLETED",
  "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174001",
  "user_id": "123e4567-e89b-12d3-a456-426614174002",
  "created_at": "2023-01-01T00:00:00",
  "updated_at": "2023-01-01T01:00:00"
}
```

### Error Responses
- **Code**: 404 Not Found
- **Content**: `{"detail": "Question not found"}`

## 3. Create Question

Creates a new question in a knowledge base.

- **URL**: `/api/knowledge-bases/{kb_id}/questions`
- **Method**: `POST`
- **Authentication**: Required

### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| kb_id     | string | Knowledge base ID |

### Request Body
```json
{
  "question": "What is DocBrain?",
  "answer": "DocBrain is a knowledge management system.",
  "answer_type": "DIRECT"
}
```

### Success Response
- **Code**: 200 OK
- **Content**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "question": "What is DocBrain?",
  "answer": "DocBrain is a knowledge management system.",
  "answer_type": "DIRECT",
  "status": "PENDING",
  "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174001",
  "user_id": "123e4567-e89b-12d3-a456-426614174002",
  "created_at": "2023-01-01T00:00:00",
  "updated_at": null
}
```

## 4. Update Question

Updates an existing question.

- **URL**: `/api/knowledge-bases/{kb_id}/questions/{question_id}`
- **Method**: `PUT`
- **Authentication**: Required

### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| kb_id     | string | Knowledge base ID |
| question_id | string | Question ID |

### Request Body
```json
{
  "question": "What is DocBrain used for?",
  "answer": "DocBrain is used for knowledge management and document retrieval.",
  "answer_type": "DIRECT"
}
```

### Success Response
- **Code**: 200 OK
- **Content**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "question": "What is DocBrain used for?",
  "answer": "DocBrain is used for knowledge management and document retrieval.",
  "answer_type": "DIRECT",
  "status": "PENDING",
  "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174001",
  "user_id": "123e4567-e89b-12d3-a456-426614174002",
  "created_at": "2023-01-01T00:00:00",
  "updated_at": "2023-01-01T02:00:00"
}
```

### Error Responses
- **Code**: 404 Not Found
- **Content**: `{"detail": "Question not found"}`

## 5. Delete Question

Deletes a question.

- **URL**: `/api/knowledge-bases/{kb_id}/questions/{question_id}`
- **Method**: `DELETE`
- **Authentication**: Required

### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| kb_id     | string | Knowledge base ID |
| question_id | string | Question ID |

### Success Response
- **Code**: 200 OK
- **Content**: `{"message": "Question deleted successfully"}`

### Error Responses
- **Code**: 404 Not Found
- **Content**: `{"detail": "Question not found"}`

## 6. Get Question Status

Retrieves the status of a specific question.

- **URL**: `/api/knowledge-bases/{kb_id}/questions/{question_id}/status`
- **Method**: `GET`
- **Authentication**: Required

### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| kb_id     | string | Knowledge base ID |
| question_id | string | Question ID |

### Success Response
- **Code**: 200 OK
- **Content**: `"COMPLETED"` (or "PENDING", "INGESTING", "FAILED")

### Error Responses
- **Code**: 404 Not Found
- **Content**: `{"detail": "Question not found"}`

## 7. Bulk Upload Questions

Uploads multiple questions to a knowledge base from a CSV file.

- **URL**: `/api/knowledge-bases/{kb_id}/questions/bulk-upload`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Authentication**: Required

### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| kb_id     | string | Knowledge base ID |

### Form Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| file | file | CSV file containing questions (must end with .csv extension) |

### CSV File Format
The CSV file must include the following columns:
- `question`: The question text
- `answer`: The answer text
- `answer_type`: Must be either "DIRECT" or "SQL_QUERY"

Example CSV:
```
question,answer,answer_type
What is DocBrain?,DocBrain is a knowledge management system.,DIRECT
How to use DocBrain?,DocBrain can be used through its web interface.,DIRECT
```

### Success Response
- **Code**: 200 OK
- **Content**:
```json
{
  "success": 2,
  "failed": 0,
  "errors": []
}
```

### Error Responses
- **Code**: 400 Bad Request
- **Content**: `{"detail": "Only CSV files are allowed"}`

OR

- **Code**: 400 Bad Request
- **Content**: `{"detail": "CSV must contain the following columns: question, answer, answer_type"}`

OR

- **Code**: 200 OK (with partial success)
- **Content**:
```json
{
  "success": 1,
  "failed": 1,
  "errors": ["Row 3: Value error, answer_type must be one of: DIRECT, SQL_QUERY"]
}
``` 