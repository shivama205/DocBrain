from celery import Celery
import os
import platform
import multiprocessing
from app.core.config import settings

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

# Configure Celery for macOS to avoid MPS issues
if platform.system() == "Darwin":
    celery_app.conf.update(
        worker_prefetch_multiplier=1,  # Reduce prefetch to avoid memory issues
        task_acks_late=True,  # Only acknowledge tasks after they're completed
        worker_max_tasks_per_child=10,  # Restart workers periodically to prevent memory leaks
    )

# Load tasks from worker module
celery_app.autodiscover_tasks(['app.worker'])

if __name__ == '__main__':
    celery_app.start() 