# DocBrain Worker

This directory contains the Celery worker configuration and tasks for DocBrain.

## Celery Configuration

The Celery configuration is consolidated in a single file:
- `celery.py`: Contains all Celery configuration and worker startup logic

## Model Initialization

One of the key improvements in this codebase is the pre-initialization of ML models:

1. **Pre-initialization**: Models are loaded in the main process before any forking occurs
2. **Singleton Pattern**: Factory classes use a singleton pattern to ensure models are only initialized once
3. **CPU-only Mode**: Models are configured to use CPU only on macOS to avoid MPS issues

This approach prevents segmentation faults that can occur when models are initialized after forking.

## macOS Compatibility

When running on macOS, there are known issues with PyTorch, Metal Performance Shaders (MPS), and Python's multiprocessing that can cause crashes with error messages like:

```
objc[xxxxx]: +[MPSGraphObject initialize] may have been in progress in another thread when fork() was called.
objc[xxxxx]: +[MPSGraphObject initialize] may have been in progress in another thread when fork() was called. We cannot safely call it or ignore it in the fork() child process. Crashing instead.
```

### Solution

To avoid these issues, we've implemented several safeguards:

1. Environment variables to disable MPS/GPU acceleration
2. Using 'spawn' instead of 'fork' for multiprocessing
3. Using the 'solo' pool for Celery workers
4. Configuring worker settings to minimize memory issues
5. Pre-initializing models before any forking occurs
6. Using singleton patterns for model instances

### Running the Worker

The recommended way to start the worker on macOS is to use the `restart_worker.sh` script in the project root:

```bash
./restart_worker.sh
```

This script:
- Stops any running workers
- Sets the necessary environment variables
- Pre-initializes ML models in the main process
- Starts the worker with the correct configuration

### Manual Configuration

If you need to start the worker manually, make sure to:

1. Set these environment variables:
   ```bash
   export PYTORCH_MPS_ENABLE_WORKSTREAM_WATCHDOG=0
   export MPS_VISIBLE_DEVICES=""
   export CUDA_VISIBLE_DEVICES=""
   export OMP_NUM_THREADS=1
   export MKL_NUM_THREADS=1
   export PYTORCH_ENABLE_MPS_FALLBACK=1
   ```

2. Start the worker with the solo pool:
   ```bash
   python -m app.worker.celery
   ```

## Troubleshooting

If you still encounter crashes:

1. Make sure you're using the `restart_worker.sh` script
2. Check that no other Celery workers are running in the background
3. Verify that the environment variables are set correctly
4. Consider restarting your computer to clear any lingering processes 