FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    google-cloud-firestore==2.11.0 \
    google-cloud-storage==2.10.0

# Copy job script
COPY boltz2_job.py .

# Run the job
ENTRYPOINT ["python", "boltz2_job.py"]