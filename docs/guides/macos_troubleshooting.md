# macOS Troubleshooting Guide

This guide addresses common issues when running DocBrain on macOS, particularly related to Celery workers and ML model initialization.

## Common Issues

### Segmentation Faults with Metal Performance Shaders (MPS)

**Symptoms:**
- Worker processes crash with error messages like:
  ```
  objc[xxxxx]: +[MPSGraphObject initialize] may have been in progress in another thread when fork() was called.
  objc[xxxxx]: +[MPSGraphObject initialize] may have been in progress in another thread when fork() was called. We cannot safely call it or ignore it in the fork() child process. Crashing instead.
  ```
- SIGABRT (signal 6) or SIGSEGV (signal 11) errors
- Crashes when initializing ML models like FlagEmbeddingReranker

**Cause:**
This issue occurs due to conflicts between Apple's Metal Performance Shaders (MPS) framework and Python's fork() system call in multiprocessing environments. When Celery workers are forked, they inherit the memory space of the parent process, including any initialized GPU/MPS resources, which can cause conflicts.

**Solution:**
1. Use the provided `restart_worker.sh` script to start workers:
   ```bash
   ./restart_worker.sh
   ```

2. If you need to start workers manually, set these environment variables:
   ```bash
   export PYTORCH_MPS_ENABLE_WORKSTREAM_WATCHDOG=0
   export MPS_VISIBLE_DEVICES=""
   export CUDA_VISIBLE_DEVICES=""
   export OMP_NUM_THREADS=1
   export MKL_NUM_THREADS=1
   export PYTORCH_ENABLE_MPS_FALLBACK=1
   ```

3. Start the worker with the solo pool:
   ```bash
   python -m app.worker.celery
   ```

### Understanding the Fix

Our solution implements several safeguards:

1. **Environment Variables**: Disable MPS/GPU acceleration to avoid conflicts with Apple's Metal framework.

2. **Multiprocessing Method**: Use 'spawn' instead of 'fork' for multiprocessing. While Celery doesn't natively use 'spawn', we force it to use the 'solo' pool, which avoids the problematic forking behavior.

3. **Model Initialization Strategy**:
   - **Pre-initialization**: Models are loaded in the main process before any forking occurs
   - **Singleton Pattern**: Factory classes use a singleton pattern to ensure models are only initialized once
   - **CPU-only Mode**: Models are configured to use CPU only on macOS

## Advanced Troubleshooting

If you're still experiencing issues:

### Check Running Workers

Make sure no other Celery workers are running in the background:

```bash
ps aux | grep celery
```

Kill any existing workers:

```bash
pkill -f "celery worker"
```

### Verify Environment Variables

Check that environment variables are set correctly:

```bash
env | grep MPS
env | grep CUDA
env | grep OMP
env | grep MKL
env | grep PYTORCH
```

### Check Multiprocessing Method

Verify the multiprocessing start method:

```python
import multiprocessing
print(multiprocessing.get_start_method())
```

It should return 'spawn' on macOS.

### Debug Model Initialization

If you suspect issues with model initialization, you can add debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Last Resort: Restart Your Computer

In some cases, restarting your computer can clear any lingering processes or GPU/MPS resources that might be causing conflicts.

## Performance Considerations

Using CPU-only mode on macOS will be slower than GPU acceleration. If you need better performance:

1. Consider running workers on a Linux machine where these issues don't occur
2. Use Docker to isolate the worker processes
3. Explore alternative worker pools like 'threads' or 'gevent' instead of 'solo'

## Further Reading

- [PyTorch macOS Documentation](https://pytorch.org/docs/stable/notes/mps.html)
- [Python Multiprocessing Documentation](https://docs.python.org/3/library/multiprocessing.html)
- [Celery Worker Documentation](https://docs.celeryq.dev/en/stable/userguide/workers.html) 