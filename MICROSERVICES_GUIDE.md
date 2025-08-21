# 🔧 OMTX-Hub Microservices Testing & Maintenance Guide

## 📋 Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Service Components](#service-components)
- [Testing Procedures](#testing-procedures)
- [Maintenance Operations](#maintenance-operations)
- [Troubleshooting](#troubleshooting)
- [Emergency Procedures](#emergency-procedures)

## 🎯 Overview

This guide provides comprehensive testing and maintenance procedures for the OMTX-Hub microservices architecture running on Google Cloud Platform. The system has been migrated from Modal.com to a full GCP stack using Cloud Run, GKE, Firestore, and Cloud Storage.

### Current Production Environment
- **Primary API**: http://34.29.29.170 (Ingress)
- **Backup API**: http://34.10.21.160 (LoadBalancer)
- **GKE Cluster**: omtx-hub-cluster (us-central1-a)
- **GPU Jobs**: Cloud Run Jobs with NVIDIA L4

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Google Cloud Platform                     │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐     ┌──────────────┐    ┌──────────────┐ │
│  │   GKE        │────▶│  Cloud Run   │───▶│  Firestore   │ │
│  │  (Backend)   │     │   (GPU Jobs) │    │  (Database)  │ │
│  └──────────────┘     └──────────────┘    └──────────────┘ │
│         │                     │                    │         │
│         ▼                     ▼                    ▼         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Google Cloud Storage (Results)             │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

## 🔌 Service Components

### 1. Backend API Service (GKE)
- **Purpose**: Main API server handling all client requests
- **Technology**: FastAPI on Kubernetes
- **Endpoints**: `/api/v4/*`
- **Scaling**: 2-10 replicas (auto-scaling)

### 2. Cloud Run Jobs (GPU Processing)
- **Purpose**: Execute ML model predictions
- **Models**: Boltz-2, Chai-1, RFdiffusion
- **GPU**: NVIDIA L4 (24GB VRAM)
- **Concurrency**: 10 parallel tasks max

### 3. Firestore Database
- **Purpose**: Store job metadata and user data
- **Collections**: 
  - `users/{userId}/jobs`
  - `users/{userId}/batches`
  - `system/metrics`

### 4. Cloud Storage
- **Purpose**: Store prediction results and model outputs
- **Structure**: `users/{userId}/batches/{batchId}/results/`
- **Formats**: PDB, CIF, JSON

## 🧪 Testing Procedures

### A. Health Check Testing

```bash
#!/bin/bash
# scripts/test_health_endpoints.sh

echo "🏥 Testing Health Endpoints"
echo "============================"

# Test basic health
curl -f http://34.29.29.170/health || echo "❌ Health check failed"

# Test readiness
curl -f http://34.29.29.170/ready || echo "❌ Readiness check failed"

# Test startup
curl -f http://34.29.29.170/startup || echo "❌ Startup check failed"

# Test metrics
curl -f http://34.29.29.170/metrics || echo "❌ Metrics endpoint failed"
```

### B. Single Prediction Testing

```python
# scripts/test_single_prediction.py
import requests
import json
import time

def test_single_prediction():
    """Test single ligand prediction"""
    
    url = "http://34.29.29.170/api/v4/predict"
    headers = {"X-User-Id": "test-user"}
    
    payload = {
        "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        "ligand_smiles": "CC(C)CC1=CC=C(C=C1)C(C)C",
        "use_msa": False,
        "job_name": "Test Prediction"
    }
    
    # Submit prediction
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    
    job_id = response.json()["job_id"]
    print(f"✅ Prediction submitted: {job_id}")
    
    # Poll for completion
    for i in range(60):  # 5 minutes max
        status_response = requests.get(
            f"http://34.29.29.170/api/v4/jobs/{job_id}/status",
            headers=headers
        )
        
        if status_response.ok:
            status = status_response.json()["status"]
            print(f"  Status: {status}")
            
            if status == "completed":
                print("✅ Prediction completed successfully")
                return True
            elif status == "failed":
                print("❌ Prediction failed")
                return False
        
        time.sleep(5)
    
    print("⏱️ Prediction timed out")
    return False

if __name__ == "__main__":
    test_single_prediction()
```

### C. Batch Processing Testing

```python
# scripts/test_batch_processing.py
import requests
import json

def test_batch_submission():
    """Test batch ligand screening"""
    
    url = "http://34.29.29.170/api/v4/batches/submit"
    headers = {"X-User-Id": "test-user"}
    
    payload = {
        "job_name": "Test Batch Screening",
        "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        "ligands": [
            {"name": "Ligand_1", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C"},
            {"name": "Ligand_2", "smiles": "CC(C)C1=CC=CC=C1"},
            {"name": "Ligand_3", "smiles": "CC1=CC=CC=C1C"},
            {"name": "Ligand_4", "smiles": "C1=CC=CC=C1"},
            {"name": "Ligand_5", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"}
        ],
        "use_msa": False
    }
    
    # Submit batch
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 200, f"Failed: {response.text}"
    
    batch_id = response.json()["batch_id"]
    print(f"✅ Batch submitted: {batch_id}")
    print(f"  Total ligands: {len(payload['ligands'])}")
    
    # Check status
    status_url = f"http://34.29.29.170/api/v4/batches/{batch_id}/status"
    status_response = requests.get(status_url, headers=headers)
    
    if status_response.ok:
        status = status_response.json()
        print(f"  Status: {status['status']}")
        print(f"  Progress: {status.get('progress', {})}")
    
    return batch_id

if __name__ == "__main__":
    test_batch_submission()
```

### D. Storage Testing

```python
# scripts/test_storage_operations.py
from google.cloud import storage
import os

def test_gcs_operations():
    """Test Google Cloud Storage operations"""
    
    bucket_name = "hub-job-files"
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # Test write
    test_blob = bucket.blob("test/storage_test.txt")
    test_blob.upload_from_string("Storage test successful")
    print("✅ Write test passed")
    
    # Test read
    content = test_blob.download_as_text()
    assert content == "Storage test successful"
    print("✅ Read test passed")
    
    # Test list
    blobs = list(bucket.list_blobs(prefix="users/", max_results=5))
    print(f"✅ Found {len(blobs)} user files")
    
    # Cleanup
    test_blob.delete()
    print("✅ Cleanup successful")

if __name__ == "__main__":
    test_gcs_operations()
```

### E. Database Testing

```python
# scripts/test_firestore_operations.py
from google.cloud import firestore
import uuid

def test_firestore_operations():
    """Test Firestore database operations"""
    
    db = firestore.Client()
    test_id = str(uuid.uuid4())
    
    # Test write
    doc_ref = db.collection('test').document(test_id)
    doc_ref.set({
        'test': True,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    print("✅ Write test passed")
    
    # Test read
    doc = doc_ref.get()
    assert doc.exists
    assert doc.to_dict()['test'] == True
    print("✅ Read test passed")
    
    # Test query
    query = db.collection('test').where('test', '==', True).limit(1)
    results = list(query.stream())
    assert len(results) > 0
    print("✅ Query test passed")
    
    # Cleanup
    doc_ref.delete()
    print("✅ Cleanup successful")

if __name__ == "__main__":
    test_firestore_operations()
```

## 🛠️ Maintenance Operations

### 1. Daily Health Checks

```bash
#!/bin/bash
# scripts/daily_health_check.sh

echo "📅 Daily Health Check - $(date)"
echo "================================"

# Check API health
echo -n "API Health: "
curl -s http://34.29.29.170/health | jq -r '.status' || echo "FAILED"

# Check database
echo -n "Firestore: "
gcloud firestore operations list --limit=1 > /dev/null 2>&1 && echo "OK" || echo "FAILED"

# Check storage
echo -n "Cloud Storage: "
gsutil ls gs://hub-job-files > /dev/null 2>&1 && echo "OK" || echo "FAILED"

# Check GPU jobs
echo -n "Cloud Run Jobs: "
gcloud run jobs list --region=us-central1 --format="value(name)" | grep -q "boltz2" && echo "OK" || echo "FAILED"

# Check cluster
echo -n "GKE Cluster: "
kubectl get nodes > /dev/null 2>&1 && echo "OK" || echo "FAILED"

# Check metrics
echo ""
echo "📊 System Metrics:"
kubectl top nodes
kubectl top pods -n default

echo ""
echo "✅ Daily health check complete"
```

### 2. Scaling Operations

```bash
# Scale backend replicas
kubectl scale deployment omtx-hub-backend --replicas=5

# Scale Cloud Run Jobs concurrency
gcloud run jobs update boltz2-batch \
  --parallelism=20 \
  --region=us-central1

# Scale GKE node pool
gcloud container clusters resize omtx-hub-cluster \
  --node-pool=default-pool \
  --num-nodes=5 \
  --zone=us-central1-a
```

### 3. Database Maintenance

```python
# scripts/database_maintenance.py
from google.cloud import firestore
from datetime import datetime, timedelta

def cleanup_old_jobs():
    """Remove jobs older than 30 days"""
    
    db = firestore.Client()
    cutoff = datetime.now() - timedelta(days=30)
    
    # Query old jobs
    old_jobs = db.collection_group('jobs')\
        .where('created_at', '<', cutoff)\
        .limit(100)
    
    count = 0
    for doc in old_jobs.stream():
        doc.reference.delete()
        count += 1
    
    print(f"✅ Deleted {count} old jobs")

def optimize_indexes():
    """Check and optimize Firestore indexes"""
    
    print("📊 Current indexes:")
    os.system("gcloud firestore indexes list")
    
    print("\n💡 Recommended indexes for common queries:")
    print("- Collection: jobs | Fields: user_id, created_at DESC")
    print("- Collection: batches | Fields: user_id, status, created_at DESC")

if __name__ == "__main__":
    cleanup_old_jobs()
    optimize_indexes()
```

### 4. Storage Cleanup

```bash
#!/bin/bash
# scripts/storage_cleanup.sh

echo "🧹 Storage Cleanup"

# Remove files older than 30 days
gsutil -m rm -r "gs://hub-job-files/users/**/results/**" \
  -x ".*\.(pdb|cif)$" \
  -age 30d

# Set lifecycle rule
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://hub-job-files
echo "✅ Lifecycle rules applied"
```

### 5. Log Analysis

```bash
#!/bin/bash
# scripts/analyze_logs.sh

echo "📋 Log Analysis"

# Get error logs
echo "Recent errors:"
gcloud logging read "severity>=ERROR" \
  --limit=10 \
  --format="table(timestamp,jsonPayload.message)"

# Get slow requests
echo ""
echo "Slow requests (>5s):"
gcloud logging read "httpRequest.latency>5s" \
  --limit=10 \
  --format="table(timestamp,httpRequest.requestUrl,httpRequest.latency)"

# Get GPU job failures
echo ""
echo "Failed GPU jobs:"
gcloud logging read "resource.type=cloud_run_job AND severity>=ERROR" \
  --limit=10 \
  --format="table(timestamp,jsonPayload.error)"
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. API Not Responding
```bash
# Check pod status
kubectl get pods -n default

# Check logs
kubectl logs -l app=omtx-hub-backend --tail=50

# Restart pods
kubectl rollout restart deployment omtx-hub-backend
```

#### 2. GPU Jobs Failing
```bash
# Check job status
gcloud run jobs describe boltz2-batch --region=us-central1

# View job logs
gcloud logging read "resource.type=cloud_run_job" --limit=20

# Update GPU quota if needed
gcloud compute project-info describe --project=$PROJECT_ID
```

#### 3. Database Connection Issues
```python
# Test Firestore connection
from google.cloud import firestore

try:
    db = firestore.Client()
    collections = list(db.collections())
    print(f"✅ Connected. {len(collections)} collections found")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

#### 4. Storage Access Issues
```bash
# Check bucket permissions
gsutil iam get gs://hub-job-files

# Test write access
echo "test" | gsutil cp - gs://hub-job-files/test.txt

# Fix permissions
gsutil iam ch allUsers:objectViewer gs://hub-job-files
```

#### 5. High Memory Usage
```bash
# Check memory usage
kubectl top pods

# Increase memory limits
kubectl set resources deployment omtx-hub-backend \
  --limits=memory=8Gi \
  --requests=memory=4Gi
```

## 🆘 Emergency Procedures

### 1. Complete System Failure
```bash
#!/bin/bash
# scripts/emergency_recovery.sh

echo "🚨 EMERGENCY RECOVERY INITIATED"

# 1. Switch to backup URL
echo "Switching to backup LoadBalancer..."
export API_URL="http://34.10.21.160"

# 2. Check critical services
echo "Checking critical services..."
curl -f $API_URL/health || {
    echo "❌ Backup API also down!"
    # Restart all services
    kubectl delete pods --all -n default
    sleep 30
}

# 3. Scale up resources
echo "Scaling up resources..."
kubectl scale deployment omtx-hub-backend --replicas=5
gcloud container clusters resize omtx-hub-cluster --num-nodes=5 --zone=us-central1-a

# 4. Clear any stuck jobs
echo "Clearing stuck jobs..."
gcloud run jobs executions list --region=us-central1 | grep RUNNING | \
  awk '{print $1}' | xargs -I {} gcloud run jobs executions cancel {} --region=us-central1

# 5. Notify team
echo "📧 Sending emergency notifications..."
# Add notification logic here

echo "✅ Emergency recovery complete"
```

### 2. Data Recovery
```python
# scripts/data_recovery.py
from google.cloud import firestore
from google.cloud import storage
import json

def backup_critical_data():
    """Emergency backup of critical data"""
    
    # Backup Firestore
    db = firestore.Client()
    backup_data = {}
    
    for collection in ['users', 'batches', 'jobs']:
        docs = db.collection(collection).limit(1000).stream()
        backup_data[collection] = [doc.to_dict() for doc in docs]
    
    with open('firestore_backup.json', 'w') as f:
        json.dump(backup_data, f)
    
    print("✅ Firestore backed up")
    
    # Backup critical GCS files
    client = storage.Client()
    bucket = client.bucket('hub-job-files')
    
    os.makedirs('gcs_backup', exist_ok=True)
    
    for blob in bucket.list_blobs(prefix='users/', max_results=100):
        if blob.name.endswith(('.pdb', '.cif', '.json')):
            local_path = f"gcs_backup/{blob.name.replace('/', '_')}"
            blob.download_to_filename(local_path)
    
    print("✅ GCS files backed up")

if __name__ == "__main__":
    backup_critical_data()
```

### 3. Cost Control Emergency
```bash
#!/bin/bash
# scripts/emergency_cost_control.sh

echo "💰 EMERGENCY COST CONTROL"

# 1. Stop all GPU jobs immediately
gcloud run jobs executions list --region=us-central1 | grep RUNNING | \
  awk '{print $1}' | xargs -I {} gcloud run jobs executions cancel {} --region=us-central1

# 2. Scale down to minimum
kubectl scale deployment omtx-hub-backend --replicas=1
gcloud container clusters resize omtx-hub-cluster --num-nodes=1 --zone=us-central1-a

# 3. Set strict quotas
gcloud compute project-info add-metadata \
  --metadata google-compute-default-region=us-central1,google-compute-default-zone=us-central1-a

# 4. Disable expensive features
kubectl set env deployment/omtx-hub-backend \
  ENABLE_MSA=false \
  ENABLE_POTENTIALS=false \
  MAX_BATCH_SIZE=10

echo "✅ Cost controls applied"
```

## 📊 Monitoring Dashboard

### Key Metrics to Monitor

1. **API Performance**
   - Response time (target: <2s)
   - Error rate (target: <1%)
   - Requests per second

2. **GPU Utilization**
   - Job completion rate (target: >95%)
   - Average job duration
   - Queue depth

3. **Resource Usage**
   - CPU utilization (warning: >80%)
   - Memory usage (warning: >80%)
   - Storage usage (warning: >80%)

4. **Cost Metrics**
   - Daily spend (alert: >$100)
   - GPU hours used
   - Storage costs

### Monitoring Commands

```bash
# Real-time monitoring
watch -n 5 'kubectl top pods; echo "---"; kubectl get pods'

# Cost monitoring
gcloud billing accounts get-iam-policy $BILLING_ACCOUNT_ID

# Performance monitoring
curl -s http://34.29.29.170/metrics | grep -E "request_duration|request_count"
```

## 📚 Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GKE Best Practices](https://cloud.google.com/kubernetes-engine/docs/best-practices)
- [Firestore Performance Guide](https://firebase.google.com/docs/firestore/best-practices)
- [Cloud Storage Best Practices](https://cloud.google.com/storage/docs/best-practices)

## 📞 Support Contacts

- **On-Call Engineer**: Use PagerDuty
- **GCP Support**: 1-855-817-7333
- **Internal Slack**: #omtx-hub-ops
- **Emergency Escalation**: CTO/VP Engineering

---

**Last Updated**: January 2025
**Version**: 2.0.0 (Post-Modal Migration)
**Maintained By**: OMTX Engineering Team

