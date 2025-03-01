import os
import sys
import logging
from celery import Celery

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_celery_app():
    """Create Celery app"""
    app = Celery(
        "docbrain",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["app.worker.tasks"]
    )
    
    # Configure Celery
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour
        worker_max_tasks_per_child=100,
        worker_prefetch_multiplier=1
    )
    
    return app

if __name__ == "__main__":
    logger.info("Starting Celery worker")
    app = create_celery_app()
    app.worker_main(["worker", "--loglevel=info", "-E"]) 