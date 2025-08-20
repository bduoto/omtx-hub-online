# OMTX-Hub Consolidated API Production Dockerfile
# Supports Boltz-2, RFAntibody, and Chai-1 predictions

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.prod.txt ./
RUN pip install --no-cache-dir -r requirements.prod.txt

# Copy backend application
COPY backend/ ./

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the consolidated API
CMD ["python", "main.py"]