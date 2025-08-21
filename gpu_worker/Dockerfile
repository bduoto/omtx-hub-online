# GPU Worker Dockerfile for Cloud Run Jobs
# Supports NVIDIA L4 GPU for Boltz-2 predictions

FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Note: PyTorch with CUDA will be installed via requirements.txt when needed

# Copy application code
COPY . .

# Create directories for model cache and temporary files
RUN mkdir -p /app/models /app/temp && \
    chmod 755 /app/models /app/temp

# Download and cache common dependencies (optional)
# RUN python -c "import torch; print('PyTorch CUDA available:', torch.cuda.is_available())"

# Create non-root user for security
RUN useradd -m -u 1000 gpu-worker && \
    chown -R gpu-worker:gpu-worker /app
USER gpu-worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE 8080

# Start the application
CMD ["python", "main.py"]