import os
import sys
import logging
import platform
import multiprocessing
from celery import Celery

# Set environment variables for macOS to prevent MPS/GPU issues
# These need to be set before any PyTorch imports
if platform.system() == "Darwin":  # Check if running on macOS
    os.environ["PYTORCH_MPS_ENABLE_WORKSTREAM_WATCHDOG"] = "0"  # Disable MPS watchdog
    os.environ["MPS_VISIBLE_DEVICES"] = ""  # Disable MPS for PyTorch
    os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Disable CUDA if present
    os.environ["OMP_NUM_THREADS"] = "1"  # Limit OpenMP threads
    os.environ["MKL_NUM_THREADS"] = "1"  # Limit MKL threads
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"  # Force PyTorch to use CPU

    # Set multiprocessing start method to 'spawn' on macOS
    # This prevents issues with fork() and MPS
    if multiprocessing.get_start_method(allow_none=True) != 'spawn':
        try:
            multiprocessing.set_start_method('spawn', force=True)
        except RuntimeError:
            # If already set, this will raise a RuntimeError
            pass

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
    
    # Additional configuration for macOS to avoid MPS issues
    if platform.system() == "Darwin":
        app.conf.update(
            worker_prefetch_multiplier=1,  # Reduce prefetch to avoid memory issues
            task_acks_late=True,  # Only acknowledge tasks after they're completed
            worker_max_tasks_per_child=10,  # Restart workers periodically to prevent memory leaks
        )
    
    return app

if __name__ == "__main__":
    logger.info("Starting Celery worker")
    
    # Log platform and multiprocessing information
    logger.info(f"Platform: {platform.system()} {platform.release()}")
    logger.info(f"Multiprocessing start method: {multiprocessing.get_start_method()}")
    
    app = create_celery_app()
    
    # Use --pool=solo on macOS to avoid fork-related issues
    worker_args = ["worker", "--loglevel=info", "-E"]
    if platform.system() == "Darwin":
        worker_args.append("--pool=solo")
        logger.info("Using solo pool for macOS to avoid fork() issues")
    
    app.worker_main(worker_args) 