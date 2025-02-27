# DocBrain

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

DocBrain is a RAG (Retrieval-Augmented Generation) pipeline backend built with FastAPI, llama-index, and Pinecone. It allows companies to create knowledge bases, upload documents, and chat with their documents using Gemini LLM.

## Features

- 📚 Create and manage multiple knowledge bases
- 📄 Upload and process various document types
- 🔍 Advanced semantic search with Pinecone vector database 
- 💬 Chat with your documents using Gemini LLM
- 🔒 User authentication and authorization
- 🔄 Background processing with Celery
- 🐳 Docker support for easy deployment

## Prerequisites

- Python 3.9+
- MySQL or another database
- Redis (for Celery)
- Pinecone account (vector database)
- Gemini API key (for LLM)
- SendGrid account (for email notifications)

## Quick Start

1. Clone and setup:
```bash
git clone https://github.com/yourusername/DocBrain.git
cd DocBrain
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
make install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the application:
```bash
# Terminal 1: API Server
make run-dev

# Terminal 2: Celery Worker
make worker
```

## API Endpoints

### Knowledge Bases
- `POST /api/v1/knowledge-bases` - Create knowledge base
- `GET /api/v1/knowledge-bases` - List knowledge bases
- `GET /api/v1/knowledge-bases/{kb_id}` - Get details
- `PUT /api/v1/knowledge-bases/{kb_id}` - Update
- `DELETE /api/v1/knowledge-bases/{kb_id}` - Delete
- `POST /api/v1/knowledge-bases/{kb_id}/share/{user_id}` - Share

### Documents
- `POST /api/v1/knowledge-bases/{kb_id}/upload` - Upload document
- `GET /api/v1/knowledge-bases/{kb_id}/documents` - List documents
- `GET /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}` - Get details
- `DELETE /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}` - Delete

## Environment Variables

Required variables in `.env`:
- `SECRET_KEY`: JWT secret key
- `SENDGRID_API_KEY`: For email verification
- `PINECONE_API_KEY`: Vector store
- `PINECONE_ENVIRONMENT`: Pinecone environment
- `GEMINI_API_KEY`: LLM API key
- `WHITELISTED_EMAILS`: Test emails

See `.env.example` for all configuration options.

## Docker Support

```bash
# Build and start all services
docker-compose up --build

# Run only the worker
docker-compose up celery_worker
```

## Project Structure

```
DocBrain/
├── app/                    # Main application package
│   ├── api/                # API endpoints
│   ├── core/               # Core functionality
│   ├── db/                 # Database models
│   ├── models/             # Pydantic models
│   ├── repositories/       # Data access layer
│   ├── services/           # Business logic
│   └── worker/             # Celery worker tasks
├── scripts/                # Utility scripts
├── tests/                  # Test suite
└── docker/                 # Docker configuration
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code follows the project's style guidelines and includes appropriate tests.

## Security

If you discover any security related issues, please email security@yourdomain.com instead of using the issue tracker.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/)
- [llama-index](https://www.llamaindex.ai/)
- [Pinecone](https://www.pinecone.io/)
- [Gemini API](https://ai.google.dev/) 