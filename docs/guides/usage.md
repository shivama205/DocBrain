# DocBrain Usage Guide

This guide will help you use DocBrain effectively to manage your knowledge bases and chat with your documents.

## Getting Started

After setting up DocBrain, you can access it through the API or a client application.

## Creating a Knowledge Base

A knowledge base is a collection of documents that you can query. To create a knowledge base:

1. Send a POST request to `/knowledge-bases` with a name and description:

```json
{
  "name": "My Knowledge Base",
  "description": "A collection of documents about a specific topic"
}
```

2. Note the `id` in the response, which you'll use to reference this knowledge base.

## Uploading Documents

To upload documents to a knowledge base:

1. Send a POST request to `/knowledge-bases/{kb_id}/upload` with the document file and metadata.

2. The document will be processed in the background. You can check its status by sending a GET request to `/knowledge-bases/{kb_id}/documents/{doc_id}`.

3. Once the document status is `COMPLETED`, it's ready to be queried.

## Supported Document Types

DocBrain supports the following document types:

- PDF (`.pdf`)
- Word (`.docx`, `.doc`)
- Excel (`.xlsx`, `.xls`)
- PowerPoint (`.pptx`, `.ppt`)
- Text (`.txt`)
- Markdown (`.md`)
- CSV (`.csv`)
- Images with text (`.jpg`, `.png`) via OCR

## Creating a Conversation

To chat with your documents, you need to create a conversation:

1. Send a POST request to `/conversations` with the knowledge base ID:

```json
{
  "knowledge_base_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "My Conversation"
}
```

2. Note the `id` in the response, which you'll use to reference this conversation.

## Sending Messages

To send a message in a conversation:

1. Send a POST request to `/conversations/{conversation_id}/messages` with your question:

```json
{
  "content": "What is the main topic of the document?"
}
```

2. The response will include your message. The assistant's response will be generated asynchronously.

3. To get the assistant's response, send a GET request to `/conversations/{conversation_id}/messages`.

## Effective Querying

To get the best results from DocBrain, follow these tips:

1. **Be specific**: Ask clear, specific questions rather than vague ones.

2. **Provide context**: If your question refers to something specific, include that context.

3. **One question at a time**: Ask one question per message for the best results.

4. **Follow up**: If the answer is incomplete, ask follow-up questions to get more details.

## Managing Knowledge Bases

You can manage your knowledge bases through the following endpoints:

- GET `/knowledge-bases`: List all knowledge bases
- GET `/knowledge-bases/{kb_id}`: Get details of a specific knowledge base
- PUT `/knowledge-bases/{kb_id}`: Update a knowledge base
- DELETE `/knowledge-bases/{kb_id}`: Delete a knowledge base

## Managing Documents

You can manage your documents through the following endpoints:

- GET `/knowledge-bases/{kb_id}/documents`: List all documents in a knowledge base
- GET `/knowledge-bases/{kb_id}/documents/{doc_id}`: Get details of a specific document
- DELETE `/knowledge-bases/{kb_id}/documents/{doc_id}`: Delete a document

## Managing Conversations

You can manage your conversations through the following endpoints:

- GET `/conversations`: List all conversations
- GET `/conversations/{conversation_id}`: Get details of a specific conversation
- PUT `/conversations/{conversation_id}`: Update a conversation
- DELETE `/conversations/{conversation_id}`: Delete a conversation

## Managing Messages

You can manage your messages through the following endpoints:

- GET `/conversations/{conversation_id}/messages`: List all messages in a conversation
- GET `/conversations/{conversation_id}/messages/{message_id}`: Get details of a specific message

## Troubleshooting

If you encounter issues with DocBrain, check the following:

1. **Document processing fails**: Ensure the document is in a supported format and not corrupted.

2. **No results from queries**: Check that the document was processed successfully and that your query is relevant to the document content.

3. **Poor quality answers**: Try rephrasing your question to be more specific and clear.

For more detailed troubleshooting, refer to the [Troubleshooting Guide](troubleshooting.md).
