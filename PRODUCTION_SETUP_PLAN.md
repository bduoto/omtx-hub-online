# 🚀 OMTX-Hub Production Setup Plan
## GKE + Cloud Run Jobs Architecture for Boltz-2 Predictions

### System Overview
```
Frontend → GKE API → Cloud Tasks Queue → Cloud Run Jobs (GPU) → Results
             ↓                                    ↓
         Firestore                          Cloud Storage
        (job records)                      (results & structures)
```

---

## 📋 Phase 1: Infrastructure Setup

### 1.1 Cloud Tasks Queue Configuration
```bash
# Create the job queue
gcloud tasks queues create gpu-job-queue \
    --location=us-central1 \
    --max-dispatches-per-second=10 \
    --max-concurrent-dispatches=100 \
    --max-attempts=3 \
    --min-backoff=10s \
    --max-backoff=300s
```

### 1.2 Firestore Data Structure
```javascript
// Individual Job Document
{
  "job_id": "job_abc123",
  "job_type": "INDIVIDUAL",
  "model": "boltz2",
  "status": "pending|queued|running|completed|failed",
  "user_id": "user_123",
  "created_at": timestamp,
  "updated_at": timestamp,
  "started_at": timestamp,
  "completed_at": timestamp,
  
  // Input data
  "input_data": {
    "protein_sequence": "MKTAYIAK...",
    "ligand_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
    "ligand_name": "Aspirin",
    "parameters": {
      "use_msa": true,
      "num_samples": 5
    }
  },
  
  // Results (after completion)
  "results": {
    "affinity": -8.5,
    "confidence": 0.92,
    "rmsd": 1.2,
    "structure_file": "gs://hub-job-files/jobs/job_abc123/structure.cif"
  },
  
  // Cloud Run Job tracking
  "cloud_run_job": {
    "name": "job-abc123-1234567",
    "execution_id": "exec-xyz",
    "region": "us-central1"
  }
}

// Batch Parent Document
{
  "job_id": "batch_xyz789",
  "job_type": "BATCH_PARENT",
  "batch_name": "Aspirin derivatives screening",
  "status": "pending|running|completed|failed",
  "user_id": "user_123",
  "created_at": timestamp,
  
  // Batch configuration
  "batch_config": {
    "total_ligands": 100,
    "max_concurrent": 10,
    "priority": "normal"
  },
  
  // Progress tracking
  "progress": {
    "total": 100,
    "completed": 45,
    "failed": 2,
    "running": 10,
    "pending": 43
  },
  
  // Child job references
  "child_job_ids": ["job_001", "job_002", ...],
  
  // Aggregated results (after completion)
  "batch_results": {
    "best_affinity": -9.2,
    "best_ligand": "Modified_Aspirin_23",
    "average_affinity": -7.3,
    "results_file": "gs://hub-job-files/batches/batch_xyz789/results.csv"
  }
}

// Batch Child Document
{
  "job_id": "job_001",
  "job_type": "BATCH_CHILD",
  "batch_parent_id": "batch_xyz789",
  "batch_index": 0,
  "model": "boltz2",
  "status": "pending",
  // ... same structure as individual job
}
```

### 1.3 Cloud Storage Bucket Structure
```
gs://hub-job-files/
├── jobs/
│   └── {job_id}/
│       ├── input.json           # Original input data
│       ├── results.json         # Full results
│       ├── structure.cif        # 3D structure file
│       ├── structure.pdb        # Alternative format
│       └── logs.txt            # Execution logs
│
├── batches/
│   └── {batch_id}/
│       ├── batch_config.json    # Batch configuration
│       ├── batch_results.csv    # Aggregated results
│       ├── summary.json         # Statistical summary
│       ├── jobs/
│       │   ├── {job_001}/      # Individual job results
│       │   ├── {job_002}/
│       │   └── ...
│       └── analysis/
│           ├── affinity_distribution.png
│           └── top_10_structures.zip
│
└── models/
    └── boltz2/
        ├── model_weights.pt     # Cached model weights
        └── config.yaml          # Model configuration
```

---

## 📦 Phase 2: Core Services Implementation

### 2.1 GKE API Service Updates
**File: `backend/services/job_submission_service.py`**
```python
from google.cloud import tasks_v2, firestore
import json
import uuid

class JobSubmissionService:
    """Handles job submission from API to Cloud Tasks"""
    
    def __init__(self):
        self.tasks_client = tasks_v2.CloudTasksClient()
        self.db = firestore.Client()
        self.queue_path = self.tasks_client.queue_path(
            'om-models', 'us-central1', 'gpu-job-queue'
        )
    
    async def submit_individual_job(self, request: PredictionRequest) -> str:
        """Submit individual Boltz-2 prediction"""
        
        # 1. Create job record in Firestore
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job_data = {
            "job_id": job_id,
            "job_type": "INDIVIDUAL",
            "model": request.model,
            "status": "pending",
            "user_id": request.user_id,
            "created_at": firestore.SERVER_TIMESTAMP,
            "input_data": {
                "protein_sequence": request.protein_sequence,
                "ligand_smiles": request.ligand_smiles,
                "ligand_name": request.ligand_name,
                "parameters": request.parameters
            }
        }
        
        self.db.collection('jobs').document(job_id).set(job_data)
        
        # 2. Queue job for GPU processing
        task = {
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST,
                'url': 'https://gpu-worker-us-central1.run.app/process',
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'job_id': job_id,
                    'job_type': 'INDIVIDUAL'
                }).encode()
            }
        }
        
        self.tasks_client.create_task(
            request={'parent': self.queue_path, 'task': task}
        )
        
        return job_id
    
    async def submit_batch_job(self, request: BatchPredictionRequest) -> str:
        """Submit batch of Boltz-2 predictions"""
        
        # 1. Create batch parent record
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        batch_data = {
            "job_id": batch_id,
            "job_type": "BATCH_PARENT",
            "batch_name": request.batch_name,
            "status": "pending",
            "user_id": request.user_id,
            "created_at": firestore.SERVER_TIMESTAMP,
            "batch_config": {
                "total_ligands": len(request.ligands),
                "max_concurrent": request.max_concurrent,
                "priority": request.priority
            },
            "progress": {
                "total": len(request.ligands),
                "completed": 0,
                "failed": 0,
                "running": 0,
                "pending": len(request.ligands)
            }
        }
        
        # 2. Create child jobs
        child_job_ids = []
        batch_ref = self.db.collection('jobs').document(batch_id)
        batch_ref.set(batch_data)
        
        # Batch write for efficiency
        batch_write = self.db.batch()
        
        for idx, ligand in enumerate(request.ligands):
            child_id = f"job_{batch_id}_{idx:04d}"
            child_data = {
                "job_id": child_id,
                "job_type": "BATCH_CHILD",
                "batch_parent_id": batch_id,
                "batch_index": idx,
                "model": request.model,
                "status": "pending",
                "user_id": request.user_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "input_data": {
                    "protein_sequence": request.protein_sequence,
                    "ligand_smiles": ligand["smiles"],
                    "ligand_name": ligand.get("name", f"Ligand_{idx+1}"),
                    "parameters": request.parameters
                }
            }
            
            batch_write.set(
                self.db.collection('jobs').document(child_id),
                child_data
            )
            child_job_ids.append(child_id)
        
        # Commit all child jobs
        batch_write.commit()
        
        # 3. Update parent with child IDs
        batch_ref.update({"child_job_ids": child_job_ids})
        
        # 4. Queue child jobs with rate limiting
        for i, child_id in enumerate(child_job_ids[:request.max_concurrent]):
            task = {
                'http_request': {
                    'http_method': tasks_v2.HttpMethod.POST,
                    'url': 'https://gpu-worker-us-central1.run.app/process',
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'job_id': child_id,
                        'job_type': 'BATCH_CHILD',
                        'batch_id': batch_id
                    }).encode()
                },
                'schedule_time': Timestamp(seconds=int(time.time()) + i * 2)  # Stagger by 2 seconds
            }
            
            self.tasks_client.create_task(
                request={'parent': self.queue_path, 'task': task}
            )
        
        return batch_id
```

### 2.2 GPU Worker Service (Cloud Run Jobs)
**File: `gpu_worker/main.py`**
```python
import os
import json
from flask import Flask, request, jsonify
from google.cloud import firestore, storage
import torch
from boltz2_model import Boltz2Predictor  # Your model code

app = Flask(__name__)
db = firestore.Client()
storage_client = storage.Client()
bucket = storage_client.bucket('hub-job-files')

# Initialize model (cached between requests)
model = Boltz2Predictor()

@app.route('/process', methods=['POST'])
def process_job():
    """Process a single GPU job"""
    
    data = request.get_json()
    job_id = data['job_id']
    job_type = data.get('job_type', 'INDIVIDUAL')
    batch_id = data.get('batch_id')
    
    try:
        # 1. Update job status to running
        job_ref = db.collection('jobs').document(job_id)
        job_ref.update({
            'status': 'running',
            'started_at': firestore.SERVER_TIMESTAMP,
            'cloud_run_job': {
                'execution_id': os.environ.get('CLOUD_RUN_EXECUTION', 'unknown'),
                'region': 'us-central1'
            }
        })
        
        # 2. Get job data
        job_doc = job_ref.get()
        job_data = job_doc.to_dict()
        input_data = job_data['input_data']
        
        # 3. Run prediction
        result = model.predict(
            protein_sequence=input_data['protein_sequence'],
            ligand_smiles=input_data['ligand_smiles'],
            **input_data.get('parameters', {})
        )
        
        # 4. Save results to Cloud Storage
        job_folder = f"jobs/{job_id}"
        if job_type == 'BATCH_CHILD':
            job_folder = f"batches/{batch_id}/jobs/{job_id}"
        
        # Save structure file
        structure_path = f"{job_folder}/structure.cif"
        blob = bucket.blob(structure_path)
        blob.upload_from_string(result['structure_cif'])
        
        # Save full results
        results_path = f"{job_folder}/results.json"
        blob = bucket.blob(results_path)
        blob.upload_from_string(json.dumps(result))
        
        # 5. Update job with results
        job_ref.update({
            'status': 'completed',
            'completed_at': firestore.SERVER_TIMESTAMP,
            'results': {
                'affinity': result['affinity'],
                'confidence': result['confidence'],
                'rmsd': result.get('rmsd', 0),
                'structure_file': f"gs://hub-job-files/{structure_path}",
                'results_file': f"gs://hub-job-files/{results_path}"
            }
        })
        
        # 6. Update batch progress if child job
        if job_type == 'BATCH_CHILD' and batch_id:
            update_batch_progress(batch_id)
        
        return jsonify({'status': 'success', 'job_id': job_id}), 200
        
    except Exception as e:
        # Update job as failed
        job_ref.update({
            'status': 'failed',
            'error': str(e),
            'completed_at': firestore.SERVER_TIMESTAMP
        })
        
        if job_type == 'BATCH_CHILD' and batch_id:
            update_batch_progress(batch_id)
        
        return jsonify({'status': 'error', 'error': str(e)}), 500

def update_batch_progress(batch_id: str):
    """Update batch parent progress based on child statuses"""
    
    # Get all child jobs
    children = db.collection('jobs').where(
        'batch_parent_id', '==', batch_id
    ).stream()
    
    status_counts = {
        'completed': 0,
        'failed': 0,
        'running': 0,
        'pending': 0
    }
    
    results = []
    for child in children:
        child_data = child.to_dict()
        status = child_data['status']
        status_counts[status] = status_counts.get(status, 0) + 1
        
        if status == 'completed' and 'results' in child_data:
            results.append({
                'ligand_name': child_data['input_data']['ligand_name'],
                'affinity': child_data['results']['affinity']
            })
    
    # Update batch parent
    batch_ref = db.collection('jobs').document(batch_id)
    update_data = {
        'progress': status_counts,
        'updated_at': firestore.SERVER_TIMESTAMP
    }
    
    # If all jobs complete, generate batch results
    total = sum(status_counts.values())
    if status_counts['completed'] + status_counts['failed'] == total:
        update_data['status'] = 'completed'
        
        if results:
            # Sort by affinity
            results.sort(key=lambda x: x['affinity'])
            
            # Save batch results to GCS
            batch_results = {
                'best_ligand': results[0]['ligand_name'],
                'best_affinity': results[0]['affinity'],
                'top_10': results[:10],
                'average_affinity': sum(r['affinity'] for r in results) / len(results)
            }
            
            # Save to Cloud Storage
            results_path = f"batches/{batch_id}/batch_results.json"
            blob = bucket.blob(results_path)
            blob.upload_from_string(json.dumps(batch_results))
            
            update_data['batch_results'] = batch_results
            update_data['batch_results']['results_file'] = f"gs://hub-job-files/{results_path}"
    
    batch_ref.update(update_data)
    
    # Queue next jobs if needed
    if status_counts['pending'] > 0 and status_counts['running'] < 10:
        queue_next_batch_jobs(batch_id, 10 - status_counts['running'])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
```

### 2.3 Deployment Configuration
**File: `gpu_worker/Dockerfile`**
```dockerfile
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Download and cache model weights
RUN python3 -c "from boltz2_model import download_weights; download_weights()"

ENV PORT=8080
EXPOSE 8080

CMD ["python3", "main.py"]
```

---

## 🧪 Phase 3: Testing Plan

### 3.1 Individual Job Test
```python
# Test individual prediction
curl -X POST https://your-gke-api.com/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model": "boltz2",
    "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEK",
    "ligand_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
    "ligand_name": "Aspirin",
    "user_id": "test_user_001"
  }'

# Expected flow:
# 1. API creates job in Firestore
# 2. Job queued in Cloud Tasks
# 3. Cloud Run Job picks up task
# 4. GPU processes prediction
# 5. Results saved to GCS
# 6. Firestore updated with results
```

### 3.2 Batch Job Test
```python
# Test batch prediction with 10 ligands
curl -X POST https://your-gke-api.com/api/v1/predict/batch \
  -H "Content-Type: application/json" \
  -d '{
    "model": "boltz2",
    "batch_name": "Aspirin derivatives screening",
    "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEK",
    "ligands": [
      {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
      {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"},
      // ... 8 more ligands
    ],
    "max_concurrent": 5,
    "user_id": "test_user_001"
  }'
```

### 3.3 Data Validation Tests
```python
# Verify Firestore hierarchy
def test_firestore_hierarchy():
    # Check parent-child relationships
    batch = db.collection('jobs').document('batch_xyz789').get()
    assert batch.to_dict()['job_type'] == 'BATCH_PARENT'
    
    # Check children reference parent
    children = db.collection('jobs').where(
        'batch_parent_id', '==', 'batch_xyz789'
    ).stream()
    
    for child in children:
        assert child.to_dict()['job_type'] == 'BATCH_CHILD'
        assert child.to_dict()['batch_parent_id'] == 'batch_xyz789'

# Verify GCS structure
def test_gcs_structure():
    # Check individual job files
    blobs = bucket.list_blobs(prefix='jobs/job_abc123/')
    expected_files = ['input.json', 'results.json', 'structure.cif']
    
    # Check batch structure
    batch_blobs = bucket.list_blobs(prefix='batches/batch_xyz789/')
    assert 'batch_results.csv' in [b.name for b in batch_blobs]
```

---

## 📊 Phase 4: Monitoring & Operations

### 4.1 Monitoring Setup
```yaml
# monitoring-config.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: omtx-hub-monitoring
spec:
  selector:
    matchLabels:
      app: omtx-hub
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

### 4.2 Key Metrics to Track
- **API Metrics** (GKE)
  - Requests per second
  - Response time (P50, P95, P99)
  - Error rate
  - Queue depth

- **GPU Metrics** (Cloud Run Jobs)
  - Job completion time
  - GPU utilization
  - Success/failure rate
  - Cost per prediction

- **Storage Metrics**
  - Firestore read/write operations
  - GCS bandwidth usage
  - Storage costs

### 4.3 Alerting Rules
```yaml
alerts:
  - name: HighJobFailureRate
    expr: rate(job_failures[5m]) > 0.1
    for: 10m
    annotations:
      summary: "High job failure rate detected"
      
  - name: QueueBacklog
    expr: cloud_tasks_queue_depth > 1000
    for: 5m
    annotations:
      summary: "Large queue backlog detected"
      
  - name: GPUUtilizationLow
    expr: gpu_utilization < 0.5
    for: 30m
    annotations:
      summary: "GPU underutilized"
```

---

## 🚀 Phase 5: Production Deployment

### 5.1 Deployment Commands
```bash
# 1. Deploy GKE API updates
kubectl apply -f k8s/api-deployment.yaml

# 2. Create Cloud Run Job
gcloud run jobs create gpu-worker \
    --image gcr.io/om-models/gpu-worker:latest \
    --region us-central1 \
    --memory 32Gi \
    --cpu 8 \
    --task-timeout 30m \
    --parallelism 10 \
    --max-retries 2 \
    --service-account gpu-worker@om-models.iam.gserviceaccount.com \
    --set-env-vars GPU_TYPE=L4 \
    --execution-environment gen2

# 3. Configure Cloud Tasks
gcloud tasks queues create gpu-job-queue \
    --location us-central1

# 4. Set up Firestore indexes
gcloud firestore indexes create --collection-group=jobs \
    --field-config field-path=batch_parent_id,order=ascending \
    --field-config field-path=created_at,order=descending
```

### 5.2 Cost Optimization
- **Use L4 GPUs**: $0.65/hour vs A100 at $4/hour
- **Batch processing**: Group jobs to maximize GPU utilization
- **Spot instances**: Use preemptible GPUs for 60-91% discount
- **Auto-scaling**: Scale to zero when idle

---

## ✅ Success Criteria

1. **Individual Jobs**
   - Submit → Complete in <5 minutes
   - Results stored in GCS
   - Status tracked in Firestore

2. **Batch Jobs**
   - Process 100 ligands in <30 minutes
   - Parent-child relationships preserved
   - Aggregated results generated

3. **Reliability**
   - 99.9% success rate
   - Automatic retries on failure
   - No data loss

4. **Performance**
   - API response <100ms
   - GPU utilization >70%
   - Queue processing <10s delay

5. **Cost**
   - <$0.10 per individual prediction
   - <$0.05 per batch prediction (amortized)
   - Total monthly cost <$500 for 10,000 predictions

---

## 🎯 Next Steps

1. Start with Phase 1 (Infrastructure)
2. Implement Phase 2 (Core Services)
3. Run Phase 3 (Testing)
4. Deploy Phase 4 (Monitoring)
5. Go live with Phase 5 (Production)

This plan provides a complete, production-ready system for Boltz-2 predictions using GKE + Cloud Run Jobs!