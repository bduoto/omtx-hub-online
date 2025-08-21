# 🏗️ OMTX-Hub Architecture Analysis & Improvements

## Current Architecture Status

### ✅ What's Working Well

1. **Hybrid Cloud Approach**
   - GKE for API orchestration (always-on, low latency)
   - Cloud Run Jobs for GPU compute (serverless, cost-effective)
   - 84% cost reduction vs Modal.com

2. **Smart Separation of Concerns**
   ```
   Frontend → GKE API → Queue → Cloud Run Jobs (GPU)
                    ↓           ↓
                Firestore   Cloud Storage
   ```

3. **Cost-Effective GPU Usage**
   - L4 GPUs ($0.65/hour) instead of A100 ($4/hour)
   - Scales to zero when idle
   - Pay only for actual compute time

## 🔧 Recommended Improvements

### 1. **Simplification Opportunity**
Since you're not using Modal anymore, you could simplify to:

**Option A: Full Cloud Run** (Simpler)
```yaml
Cloud Run Service (API) → Cloud Tasks → Cloud Run Jobs (GPU)
         ↓                                    ↓
    Firestore                          Cloud Storage
```

**Option B: Keep Hybrid** (Current - More Control)
```yaml
GKE (API) → Cloud Tasks → Cloud Run Jobs (GPU)
     ↓                            ↓
Firestore                   Cloud Storage
```

### 2. **Missing Components to Add**

```python
# 1. Job Queue Service (currently missing)
from google.cloud import tasks_v2

class JobQueueService:
    """Manages job queuing between API and GPU workers"""
    
    def __init__(self):
        self.client = tasks_v2.CloudTasksClient()
        self.queue_path = f"projects/{PROJECT_ID}/locations/{REGION}/queues/gpu-jobs"
    
    async def enqueue_prediction(self, job_id: str, model: str, priority: int = 0):
        """Queue a job for GPU processing"""
        task = {
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST,
                'url': f'https://gpu-worker-{REGION}.run.app/process',
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'job_id': job_id,
                    'model': model
                }).encode()
            }
        }
        
        if priority > 0:
            task['dispatch_deadline'] = duration_pb2.Duration(seconds=300)
        
        response = self.client.create_task(
            request={'parent': self.queue_path, 'task': task}
        )
        return response.name
```

### 3. **GPU Worker Service** (Cloud Run Jobs)

```python
# gpu_worker.py - Runs on Cloud Run Jobs with GPU
import os
from google.cloud import firestore, storage

class GPUWorker:
    """Processes ML predictions on GPU"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.storage = storage.Client()
        
    def process_job(self, job_id: str, model: str):
        """Main processing function for GPU jobs"""
        
        # 1. Get job data from Firestore
        job = self.db.collection('jobs').document(job_id).get()
        
        # 2. Load model (cached in container)
        if model == "boltz2":
            predictor = self.load_boltz2()
        elif model == "rfantibody":
            predictor = self.load_rfantibody()
        
        # 3. Run prediction
        result = predictor.predict(job.get('input_data'))
        
        # 4. Save results
        self.save_results(job_id, result)
        
        # 5. Update job status
        self.db.collection('jobs').document(job_id).update({
            'status': 'completed',
            'completed_at': firestore.SERVER_TIMESTAMP
        })
```

### 4. **Monitoring & Observability**

```yaml
# monitoring.yaml - Deploy monitoring stack
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
      - job_name: 'omtx-api'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: omtx-hub-backend
      
      - job_name: 'cloud-run-jobs'
        static_configs:
          - targets: ['monitoring.googleapis.com']
        metrics_path: '/v1/projects/om-models/timeSeries'
```

## 🎯 Architecture Decision Matrix

| Consideration | Pure Cloud Run | GKE + Cloud Run (Current) | Recommendation |
|---------------|---------------|--------------------------|----------------|
| **Complexity** | Low ✅ | Medium ⚠️ | Start simple, add GKE if needed |
| **Cost (API)** | $0 when idle ✅ | ~$100/month minimum | Cloud Run better for MVP |
| **Cost (GPU)** | Same | Same | Both use Cloud Run Jobs |
| **Latency** | 100-500ms cold start | <50ms always warm ✅ | GKE better for production |
| **Scale** | Auto ✅ | Manual config | Cloud Run easier |
| **Control** | Limited | Full ✅ | GKE for complex needs |

## 📊 Cost Breakdown

### Current Architecture Costs
```
GKE Cluster (3 nodes):     $150/month
Cloud Run Jobs (100 hrs):   $65/month  
Firestore:                  $20/month
Cloud Storage:              $10/month
Total:                     $245/month
```

### Optimized Cloud Run Only
```
Cloud Run Service:          $10/month (with free tier)
Cloud Run Jobs (100 hrs):   $65/month
Firestore:                  $20/month
Cloud Storage:              $10/month
Total:                     $105/month (57% savings)
```

## 🚀 Recommended Migration Path

### Phase 1: Current State ✅
- GKE API + Cloud Run Jobs working
- Basic job submission working

### Phase 2: Add Missing Components
1. Implement Cloud Tasks for job queuing
2. Create dedicated GPU worker service
3. Add monitoring and logging

### Phase 3: Optimize
1. Consider migrating GKE → Cloud Run Service (save $140/month)
2. Implement caching layer (Redis/Memorystore)
3. Add batch optimization for GPU utilization

### Phase 4: Scale
1. Multi-region deployment
2. Advanced queue prioritization  
3. Cost optimization with preemptible GPUs

## 💡 Key Insights

1. **Your architecture is solid** - The hybrid approach makes sense for production
2. **Main gap**: Job queuing between API and GPU workers
3. **Cost opportunity**: Could save 57% by going full Cloud Run
4. **Performance tradeoff**: GKE gives better latency but costs more

## 🎯 Immediate Next Steps

1. **Keep current setup** if latency is critical
2. **Add Cloud Tasks** for proper job queuing
3. **Implement monitoring** to track GPU utilization
4. **Consider full Cloud Run** if you can accept 100-500ms cold starts

The architecture is well-thought-out for replacing Modal! The main improvement would be adding proper job queuing and considering if the GKE overhead is worth the latency benefits for your use case.