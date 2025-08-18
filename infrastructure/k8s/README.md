# OMTX-Hub Kubernetes Infrastructure

This directory contains the complete Kubernetes infrastructure for deploying OMTX-Hub to Google Kubernetes Engine (GKE).

## 📋 Overview

The infrastructure includes:
- **Production-ready backend deployment** with autoscaling and load balancing
- **Redis cache** for rate limiting and session management
- **Monitoring stack** with Prometheus and alerting
- **Security** with RBAC, network policies, and secrets management
- **High availability** with pod disruption budgets and anti-affinity rules

## 🚀 Quick Deployment

```bash
# 1. Set environment variables
export PROJECT_ID="your-gcp-project-id"
export CLUSTER_NAME="omtx-hub-cluster"
export REGION="us-central1"

# 2. Connect to your GKE cluster
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION --project $PROJECT_ID

# 3. Deploy everything
./deploy.sh -p $PROJECT_ID -c $CLUSTER_NAME -r $REGION -e production
```

## 📁 File Structure

```
k8s/
├── deploy.sh              # Automated deployment script
├── kustomization.yaml     # Kustomize configuration
├── namespace.yaml         # Kubernetes namespaces
├── configmap.yaml         # Application configuration
├── secrets.yaml           # Secret templates (DO NOT commit real secrets)
├── rbac.yaml              # Role-based access control + network policies
├── redis.yaml             # Redis cache deployment
├── backend-deployment.yaml # Main application deployment
├── backend-service.yaml   # Kubernetes services and load balancer
├── ingress.yaml           # Ingress controller and SSL certificates
├── hpa.yaml               # Horizontal Pod Autoscaler + PDB
├── monitoring.yaml        # Prometheus monitoring stack
└── README.md              # This file
```

## 🔧 Manual Deployment Steps

### 1. Prerequisites

```bash
# Install required tools
gcloud components install kubectl
kubectl version --client

# Authenticate with GCP
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Create GKE Cluster (if needed)

```bash
# Create cluster with Terraform (see ../terraform/) or manually:
gcloud container clusters create omtx-hub-cluster \
  --region us-central1 \
  --node-locations us-central1-a,us-central1-b,us-central1-c \
  --num-nodes 3 \
  --machine-type e2-standard-4 \
  --disk-size 100GB \
  --enable-autorepair \
  --enable-autoupgrade \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 20 \
  --enable-network-policy \
  --enable-ip-alias \
  --enable-workload-identity
```

### 3. Set Up Secrets

**⚠️ IMPORTANT: Never commit real secrets to git!**

```bash
# Create GCP service account key
gcloud iam service-accounts create omtx-hub-sa --display-name "OMTX Hub Service Account"
gcloud iam service-accounts keys create sa-key.json --iam-account omtx-hub-sa@PROJECT_ID.iam.gserviceaccount.com

# Grant necessary permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:omtx-hub-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:omtx-hub-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

# Create Kubernetes secrets
kubectl create secret generic omtx-hub-secrets \
  --from-file=gcp-credentials.json=sa-key.json \
  --from-literal=MODAL_TOKEN_ID="your-modal-token-id" \
  --from-literal=MODAL_TOKEN_SECRET="your-modal-token-secret" \
  --from-literal=REDIS_PASSWORD="$(openssl rand -base64 32)" \
  --from-literal=JWT_SECRET_KEY="$(openssl rand -base64 64)" \
  --from-literal=MODAL_WEBHOOK_SECRET="$(openssl rand -base64 32)" \
  --from-literal=DB_ENCRYPTION_KEY="$(openssl rand -base64 32)" \
  --namespace omtx-hub

# Clean up the local key file
rm sa-key.json
```

### 4. Deploy Components

```bash
# 1. Create namespace
kubectl apply -f namespace.yaml

# 2. Deploy configuration and RBAC
kubectl apply -f configmap.yaml
kubectl apply -f rbac.yaml

# 3. Deploy Redis
kubectl apply -f redis.yaml

# 4. Deploy backend application
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml

# 5. Deploy ingress and SSL
kubectl apply -f ingress.yaml

# 6. Deploy autoscaling
kubectl apply -f hpa.yaml

# 7. Deploy monitoring
kubectl apply -f monitoring.yaml
```

## 🔍 Monitoring and Debugging

### Check Deployment Status

```bash
# Check all pods
kubectl get pods -n omtx-hub

# Check services
kubectl get services -n omtx-hub

# Check ingress
kubectl get ingress -n omtx-hub

# Check HPA status
kubectl get hpa -n omtx-hub
```

### View Logs

```bash
# Backend application logs
kubectl logs -f deployment/omtx-hub-backend -n omtx-hub

# Redis logs
kubectl logs -f deployment/redis -n omtx-hub

# Prometheus logs
kubectl logs -f deployment/prometheus -n omtx-hub
```

### Port Forwarding for Local Access

```bash
# Access backend directly
kubectl port-forward service/omtx-hub-backend-service 8000:80 -n omtx-hub

# Access Prometheus
kubectl port-forward service/prometheus-service 9090:9090 -n omtx-hub

# Access Redis
kubectl port-forward service/redis-service 6379:6379 -n omtx-hub
```

### Health Checks

```bash
# Get load balancer IP
LB_IP=$(kubectl get service omtx-hub-backend-lb -n omtx-hub -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test health endpoint
curl "http://$LB_IP/health"

# Test API endpoint
curl "http://$LB_IP/api/v3/health/status"
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `configmap.yaml`:

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | your-project-id |
| `ENVIRONMENT` | Deployment environment | production |
| `LOG_LEVEL` | Logging level | INFO |
| `WORKERS` | Number of worker processes | 4 |
| `MAX_CONCURRENT_JOBS` | Max concurrent jobs | 100 |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | true |
| `DEFAULT_RATE_LIMIT` | Default rate limit (req/min) | 60 |

### Secrets

Required secrets in `omtx-hub-secrets`:

| Secret | Description |
|--------|-------------|
| `GCP_CREDENTIALS_JSON` | Service account key (base64) |
| `MODAL_TOKEN_ID` | Modal authentication token ID |
| `MODAL_TOKEN_SECRET` | Modal authentication token secret |
| `REDIS_PASSWORD` | Redis authentication password |
| `JWT_SECRET_KEY` | JWT signing key |
| `MODAL_WEBHOOK_SECRET` | Modal webhook HMAC secret |

## 🚀 Scaling and Performance

### Horizontal Pod Autoscaler

The HPA automatically scales based on:
- **CPU utilization** (target: 70%)
- **Memory utilization** (target: 80%)
- **Requests per second** (target: 50 RPS per pod)

```bash
# Check HPA status
kubectl get hpa omtx-hub-backend-hpa -n omtx-hub

# View HPA events
kubectl describe hpa omtx-hub-backend-hpa -n omtx-hub
```

### Manual Scaling

```bash
# Scale to specific number of replicas
kubectl scale deployment omtx-hub-backend --replicas=10 -n omtx-hub

# Check scaling status
kubectl get deployment omtx-hub-backend -n omtx-hub
```

### Resource Limits

Current resource configuration:
- **Requests**: 2Gi memory, 1000m CPU
- **Limits**: 4Gi memory, 2000m CPU
- **Min replicas**: 3
- **Max replicas**: 20

## 🔐 Security

### RBAC

The deployment includes:
- **Service account** for pod identity
- **Role** with minimal required permissions
- **Network policies** to restrict traffic

### Network Security

- Pods can only communicate with authorized services
- Ingress restricted to load balancer
- Egress allowed to GCP services and Modal

### Secrets Management

- All sensitive data stored in Kubernetes secrets
- Service account key for GCP authentication
- Encrypted at rest in etcd

## 🚨 Troubleshooting

### Common Issues

1. **Pod CrashLoopBackOff**
   ```bash
   kubectl describe pod <pod-name> -n omtx-hub
   kubectl logs <pod-name> -n omtx-hub
   ```

2. **Service Unavailable**
   ```bash
   kubectl get endpoints -n omtx-hub
   kubectl describe service omtx-hub-backend-service -n omtx-hub
   ```

3. **Ingress Issues**
   ```bash
   kubectl describe ingress omtx-hub-ingress -n omtx-hub
   kubectl get events -n omtx-hub
   ```

4. **Authentication Errors**
   ```bash
   kubectl get secret omtx-hub-secrets -n omtx-hub -o yaml
   kubectl exec -it <pod-name> -n omtx-hub -- env | grep -E "(GCP|MODAL)"
   ```

### Performance Issues

1. **High Memory Usage**
   ```bash
   kubectl top pods -n omtx-hub
   kubectl describe pod <pod-name> -n omtx-hub
   ```

2. **Slow Response Times**
   ```bash
   # Check Prometheus metrics
   kubectl port-forward service/prometheus-service 9090:9090 -n omtx-hub
   # Access http://localhost:9090
   ```

### Recovery Procedures

1. **Rolling Restart**
   ```bash
   kubectl rollout restart deployment/omtx-hub-backend -n omtx-hub
   ```

2. **Rollback Deployment**
   ```bash
   kubectl rollout undo deployment/omtx-hub-backend -n omtx-hub
   ```

3. **Emergency Scale Down**
   ```bash
   kubectl scale deployment omtx-hub-backend --replicas=1 -n omtx-hub
   ```

## 📊 Monitoring

### Prometheus Metrics

Available at: `http://<prometheus-ip>:9090`

Key metrics:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request duration
- `container_memory_usage_bytes` - Memory usage
- `container_cpu_usage_seconds_total` - CPU usage

### Alerts

Configured alerts:
- High error rate (>10% for 5 minutes)
- High response time (>1s P95 for 5 minutes)
- Pod crash looping
- High memory usage (>90% for 10 minutes)

## 🔄 Updates and Maintenance

### Update Application

```bash
# Build and push new image
docker build -t gcr.io/$PROJECT_ID/omtx-hub-backend:v1.1.0 .
docker push gcr.io/$PROJECT_ID/omtx-hub-backend:v1.1.0

# Update deployment
kubectl set image deployment/omtx-hub-backend backend=gcr.io/$PROJECT_ID/omtx-hub-backend:v1.1.0 -n omtx-hub

# Check rollout status
kubectl rollout status deployment/omtx-hub-backend -n omtx-hub
```

### Update Configuration

```bash
# Edit ConfigMap
kubectl edit configmap omtx-hub-config -n omtx-hub

# Restart deployment to pick up changes
kubectl rollout restart deployment/omtx-hub-backend -n omtx-hub
```

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review pod logs and events
3. Check Prometheus metrics and alerts
4. Refer to the main project documentation