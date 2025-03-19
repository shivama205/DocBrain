import os
import sys
import logging
import platform
import multiprocessing
from celery import Celery

# =====================================================================
# DocBrain Celery Configuration
# =====================================================================
# This file contains the consolidated Celery configuration for DocBrain.
# It handles macOS compatibility issues with MPS and multiprocessing.
# =====================================================================

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
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Set the default Python path
os.environ.setdefault('PYTHONPATH', '.')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import settings after path setup
from app.core.config import settings

# Initialize Celery
celery_app = Celery(
    'docbrain',
    broker=settings.REDIS_URL or settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL or settings.CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=1
)

# Configure Celery for macOS to avoid MPS issues
if platform.system() == "Darwin":
    celery_app.conf.update(
        worker_prefetch_multiplier=1,  # Reduce prefetch to avoid memory issues
        task_acks_late=True,  # Only acknowledge tasks after they're completed
        worker_max_tasks_per_child=10,  # Restart workers periodically to prevent memory leaks
    )

# Pre-initialize models to prevent segmentation faults
def pre_initialize_models():
    """
    Pre-initialize all models before worker starts to prevent segmentation faults.
    This ensures models are loaded in the main process before any forking occurs.
    """
    try:
        logger.info("Pre-initializing models...")
        
        # Import factories
        from app.services.rag.reranker.reranker_factory import RerankerFactory
        from app.services.rag.ingestor.ingestor_factory import IngestorFactory
        
        # Initialize rerankers with default configuration
        RerankerFactory.initialize_models({"type": "flag", "model_name": "BAAI/bge-reranker-v2-m3"})
        
        # Initialize ingestors
        IngestorFactory.initialize_ingestors()
        
        logger.info("Model pre-initialization complete")
    except Exception as e:
        logger.error(f"Failed to pre-initialize models: {e}", exc_info=True)
        logger.warning("Continuing without model pre-initialization")

# Function to run the worker (used by restart_worker.sh)
def run_worker():
    """Run the Celery worker with appropriate configuration"""
    logger.info("Starting Celery worker")
    
    # Log platform and multiprocessing information
    logger.info(f"Platform: {platform.system()} {platform.release()}")
    logger.info(f"Multiprocessing start method: {multiprocessing.get_start_method()}")
    
    # Pre-initialize models to prevent segmentation faults
    # This must be done before worker starts and forks processes
    pre_initialize_models()
    
    # Use --pool=solo on macOS to avoid fork-related issues
    worker_args = ["worker", "--purge", "--loglevel=info", "-E"]
    if platform.system() == "Darwin":
        worker_args.append("--pool=solo")
        logger.info("Using solo pool for macOS to avoid fork() issues")
    
    celery_app.worker_main(worker_args)

# This allows the file to be used both as a module and as a script
if __name__ == '__main__':
    run_worker() 