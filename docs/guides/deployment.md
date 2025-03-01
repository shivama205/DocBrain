# DocBrain Deployment Guide

This guide will help you deploy DocBrain to a production environment.

## Prerequisites

Before deploying DocBrain, ensure you have the following:

- A server with Docker and Docker Compose installed
- A domain name pointing to your server
- SSL certificates for your domain
- Pinecone account with an index created
- Gemini API key
- SendGrid account for email notifications

## Deployment Options

DocBrain can be deployed in several ways:

1. Docker Compose (recommended for most users)
2. Kubernetes (for large-scale deployments)
3. Manual deployment (for custom setups)

This guide focuses on the Docker Compose deployment method.

## Docker Compose Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/DocBrain.git
cd DocBrain
```

### 2. Configure Environment Variables

Create a `.env` file based on the `.env.example` file:

```bash
cp .env.example .env
```

Edit the `.env` file with your production settings:

```
# Database
DATABASE_URL=postgresql://user:password@db/docbrain

# Security
SECRET_KEY=your-secure-secret-key

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
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Server
DOMAIN=yourdomain.com
```

### 3. Configure Nginx

Create an `nginx.conf` file in the `docker/nginx` directory:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Start the Services

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 5. Initialize the Database

```bash
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### 6. Create an Admin User

```bash
docker-compose -f docker-compose.prod.yml exec app python -m scripts.create_admin
```

## Kubernetes Deployment

For Kubernetes deployment, refer to the Kubernetes manifests in the `kubernetes` directory.

## Scaling

DocBrain can be scaled horizontally by adding more instances of the API and worker services.

### Scaling with Docker Compose

```bash
docker-compose -f docker-compose.prod.yml up -d --scale app=3 --scale worker=5
```

### Scaling with Kubernetes

```bash
kubectl scale deployment docbrain-app --replicas=3
kubectl scale deployment docbrain-worker --replicas=5
```

## Monitoring

It's recommended to set up monitoring for your DocBrain deployment using tools like Prometheus and Grafana.

## Backup and Recovery

Regularly back up your database and document storage to prevent data loss.

### Database Backup

```bash
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres docbrain > backup.sql
```

### Database Restore

```bash
cat backup.sql | docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres docbrain
```

## Troubleshooting

If you encounter issues with your deployment, check the logs:

```bash
docker-compose -f docker-compose.prod.yml logs -f app
docker-compose -f docker-compose.prod.yml logs -f worker
```

For more detailed troubleshooting, refer to the [Troubleshooting Guide](troubleshooting.md).
