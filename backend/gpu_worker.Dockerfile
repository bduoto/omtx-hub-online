# GPU Worker Service Dockerfile for Cloud Run
# Optimized for L4 GPU with Boltz-2 model execution

FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Set working directory
WORKDIR /app

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-venv \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create Python virtual environment
RUN python3.10 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
COPY requirements.gpu.txt .
RUN pip install --no-cache-dir -r requirements.gpu.txt

# Copy application code
COPY services/gpu_worker_service.py ./services/
COPY models/boltz2_cloud_run.py ./models/
COPY auth/ ./auth/
COPY config/ ./config/
COPY database/ ./database/

# Create necessary directories
RUN mkdir -p /app/logs /app/temp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Run the GPU worker service
CMD ["python", "services/gpu_worker_service.py"]