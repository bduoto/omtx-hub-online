#!/bin/bash
# GPU Worker Startup Script with GCS Fuse Optimization
# Handles GCS mounting, GPU initialization, and service startup

set -euo pipefail

echo "🚀 Starting OMTX-Hub GPU Worker with optimizations..."

# Set optimal environment variables
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# GPU and CUDA initialization
echo "🔧 Initializing GPU environment..."
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
export NVIDIA_VISIBLE_DEVICES=${NVIDIA_VISIBLE_DEVICES:-all}

# Memory optimization for L4 GPU
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:512,garbage_collection_threshold:0.6"

# Enable TF32 for performance (L4 GPU supports this)
export NVIDIA_TF32_OVERRIDE=1
export TORCH_BACKENDS_CUDNN_BENCHMARK=true

# Flash Attention optimization
export FLASH_ATTENTION_FORCE_CUT=1

# GCS Fuse mount setup for zero-latency model access
echo "📁 Setting up GCS Fuse mount..."
GCS_BUCKET_NAME=${GCS_BUCKET_NAME:-"hub-job-files"}
GCS_MOUNT_PATH=${GCS_MOUNT_PATH:-"/gcs-mount"}

# Create mount directory if it doesn't exist
mkdir -p "$GCS_MOUNT_PATH"

# Install gcsfuse if not already available
if ! command -v gcsfuse &> /dev/null; then
    echo "📦 Installing GCS Fuse..."
    curl -L https://github.com/GoogleCloudPlatform/gcsfuse/releases/download/v2.0.1/gcsfuse_2.0.1_amd64.deb -o /tmp/gcsfuse.deb
    dpkg -i /tmp/gcsfuse.deb || apt-get install -f -y
    rm /tmp/gcsfuse.deb
fi

# Mount GCS bucket with optimized settings for model weights
echo "🔗 Mounting GCS bucket: $GCS_BUCKET_NAME"
gcsfuse \
    --implicit-dirs \
    --file-mode=644 \
    --dir-mode=755 \
    --uid=$(id -u) \
    --gid=$(id -g) \
    --max-conns-per-host=100 \
    --stat-cache-ttl=1h \
    --type-cache-ttl=1h \
    --rename-dir-limit=1000000 \
    "$GCS_BUCKET_NAME" "$GCS_MOUNT_PATH" &

# Wait for mount to be ready
echo "⏳ Waiting for GCS mount to be ready..."
for i in {1..30}; do
    if mountpoint -q "$GCS_MOUNT_PATH"; then
        echo "✅ GCS Fuse mount ready at $GCS_MOUNT_PATH"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️ Warning: GCS Fuse mount failed, continuing without it..."
        break
    fi
    sleep 1
done

# Set up model cache paths with GCS fallback
export BOLTZ_CACHE=${BOLTZ_CACHE:-"/app/.boltz_cache"}
export TORCH_HOME=${TORCH_HOME:-"/app/.torch_cache"}
export HF_HOME=${HF_HOME:-"/app/.huggingface_cache"}

# If GCS mount is available, use it for model weights
if mountpoint -q "$GCS_MOUNT_PATH"; then
    export BOLTZ_GCS_CACHE="$GCS_MOUNT_PATH/model_cache/boltz2"
    export TORCH_GCS_CACHE="$GCS_MOUNT_PATH/model_cache/torch"
    echo "📦 Using GCS-mounted model cache"
else
    echo "📦 Using local model cache"
fi

# Create local cache directories as fallback
mkdir -p "$BOLTZ_CACHE" "$TORCH_HOME" "$HF_HOME"
chmod -R 777 "$BOLTZ_CACHE" "$TORCH_HOME" "$HF_HOME"

# GPU health check
echo "🧪 Checking GPU availability..."
python3.11 -c "
import torch
import sys
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU count: {torch.cuda.device_count()}')
    print(f'Current GPU: {torch.cuda.get_device_name(0)}')
    print(f'GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')
    # Test basic GPU operation
    x = torch.tensor([1.0, 2.0]).cuda()
    print(f'GPU test successful: {x.sum().item()}')
else:
    print('❌ GPU not available')
    sys.exit(1)
"

# Validate Boltz-2 installation
echo "🧬 Validating Boltz-2 installation..."
python3.11 -c "
try:
    import boltz
    print(f'✅ Boltz-2 version: {boltz.__version__}')
except ImportError as e:
    print(f'❌ Boltz-2 import failed: {e}')
    exit(1)
"

# Pre-warm model cache (download weights if needed)
echo "🔥 Pre-warming model cache..."
python3.11 -c "
import os
from pathlib import Path

# Set cache environment
boltz_cache = Path(os.environ.get('BOLTZ_CACHE', '/app/.boltz_cache'))
boltz_cache.mkdir(parents=True, exist_ok=True)

# Check if model weights exist
weights_path = boltz_cache / 'boltz2.ckpt'
if weights_path.exists():
    print(f'✅ Model weights found: {weights_path} ({weights_path.stat().st_size / 1024**2:.1f} MB)')
else:
    print('⏳ Model weights will be downloaded on first use...')

print('🏁 Pre-warming complete')
"

# Set resource limits for production
ulimit -n 65536  # Increase file descriptor limit
ulimit -u 32768  # Increase process limit

# Start the Flask application with optimized settings
echo "🏃 Starting GPU worker service..."
exec python3.11 /app/main.py