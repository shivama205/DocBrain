# DocBrain Setup Guide

This guide will help you set up DocBrain for development or production use.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.9+
- MySQL or another database
- Redis (for Celery)
- Pinecone account (vector database)
- Gemini API key (for LLM)
- SendGrid account (for email notifications)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/DocBrain.git
cd DocBrain
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit the `.env` file with your configuration:

```
# Database
DATABASE_URL=postgresql://user:password@localhost/docbrain

# Security
SECRET_KEY=your-secret-key

# Email
SENDGRID_API_KEY=your-sendgrid-api-key
EMAIL_FROM=your-email@example.com

# Vector Database
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
PINECONE_INDEX_NAME=your-pinecone-index-name

# LLM
GEMINI_API_KEY=your-gemini-api-key

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Database Setup

1. Initialize the database:

```bash
alembic upgrade head
```

## Running the Application

1. Start the API server:

```bash
uvicorn app.main:app --reload
```

2. Start the Celery worker:

```bash
celery -A app.worker.celery worker --loglevel=info
```

## Verification

1. Open your browser and navigate to `http://localhost:8000/docs` to access the Swagger UI.

2. Try creating a user and logging in to verify that the API is working correctly.

## Next Steps

- See the [Usage Guide](usage.md) for information on how to use DocBrain.
- See the [Deployment Guide](deployment.md) for information on deploying DocBrain to production.
