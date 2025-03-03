#!/bin/bash

# =====================================================================
# DocBrain Celery Worker Restart Script
# =====================================================================
# This script is the recommended way to start the Celery worker on macOS
# to avoid issues with Metal Performance Shaders (MPS) and multiprocessing.
#
# The script:
# 1. Stops any running Celery workers
# 2. Sets environment variables to prevent MPS/GPU issues
# 3. Pre-initializes ML models in the main process before forking
# 4. Starts the worker with the correct configuration
#
# Usage: ./restart_worker.sh
# =====================================================================

# Stop any running Celery workers
echo "Stopping any running Celery workers..."
pkill -f "celery worker" || true

# Wait a moment for workers to stop
sleep 2

# Set environment variables to prevent MPS/GPU issues on macOS
export PYTORCH_MPS_ENABLE_WORKSTREAM_WATCHDOG=0
export MPS_VISIBLE_DEVICES=""
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export PYTORCH_ENABLE_MPS_FALLBACK=1

# Start the Celery worker with consolidated configuration
# This will pre-initialize models before forking to prevent segmentation faults
echo "Starting Celery worker with consolidated configuration..."
cd "$(dirname "$0")"
python -m app.worker.celery

echo "Worker started. Check logs for details." 