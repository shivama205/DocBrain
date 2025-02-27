from celery import Celery
import os
from app.core.config import settings

# Set the default Django settings module
os.environ.setdefault('PYTHONPATH', '.')

# Initialize Celery
celery_app = Celery(
    'docbrain',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Load tasks from worker module
celery_app.autodiscover_tasks(['app.worker'])

if __name__ == '__main__':
    celery_app.start() 