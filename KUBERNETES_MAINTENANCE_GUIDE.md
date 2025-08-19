# **OMTX-Hub Kubernetes Production Maintenance Guide**

## **🏆 PRODUCTION SYSTEM OVERVIEW**

**System Status**: **LIVE IN PRODUCTION** ✅
**Cluster**: `omtx-hub-cluster` in GCP `us-central1-a`
**External Access**: http://34.10.21.160
**Namespace**: `omtx-hub`

---

## **🔧 DAILY SYSTEM HEALTH CHECKS**

### **1. QUICK HEALTH VERIFICATION**
**📁 Files**: `backend/main.py`, `backend/api/health_endpoints.py`
**🎯 Purpose**: Validate core system functionality and API accessibility
```bash
# Primary health check
curl -f http://34.10.21.160/health
# Expected: {"status":"healthy","database":"gcp_firestore","storage":"gcp_cloud_storage"}

# API documentation accessibility
curl -s -o /dev/null -w "%{http_code}" http://34.10.21.160/docs
# Expected: 200

# OpenAPI schema validation
curl -s http://34.10.21.160/openapi.json | jq '.info.title'
# Expected: "OMTX-Hub API"
```

### **2. KUBERNETES CLUSTER HEALTH**
**📁 Files**: `infrastructure/k8s/deployment.yaml`, `infrastructure/terraform/gke.tf`
**🎯 Purpose**: Monitor GKE cluster nodes, status, and auto-scaling configuration
```bash
# Connect to cluster
gcloud container clusters get-credentials omtx-hub-cluster --zone=us-central1-a --project=om-models

# Check cluster nodes
kubectl get nodes
# Expected: 3 nodes in Ready status

# Check cluster status
gcloud container clusters describe omtx-hub-cluster --zone=us-central1-a --project=om-models
# Expected: status: RUNNING

# Verify cluster auto-scaling
kubectl get nodes --show-labels | grep -E "cloud.google.com/gke-nodepool|kubernetes.io/arch"
```

### **3. APPLICATION HEALTH MONITORING**
**📁 Files**: `infrastructure/k8s/service.yaml`, `infrastructure/k8s/hpa.yaml`
**🎯 Purpose**: Check pod status, deployments, services, and load balancer configuration
```bash
# Check all resources in namespace
kubectl get all -n omtx-hub

# Check pod status
kubectl get pods -n omtx-hub
# Expected: 1-3 pods Running (some may be Pending due to resources)

# Check deployment status
kubectl get deployment omtx-hub-backend -n omtx-hub
# Expected: READY 1/3 or better, UP-TO-DATE 3, AVAILABLE >= 1

# Check service and external IP
kubectl get service omtx-hub-backend-service -n omtx-hub
# Expected: TYPE LoadBalancer, EXTERNAL-IP 34.10.21.160
```

### **4. AUTO-SCALER STATUS**
**📁 Files**: `infrastructure/k8s/hpa.yaml`, `infrastructure/k8s/vpa.yaml`
**🎯 Purpose**: Monitor Horizontal Pod Autoscaler performance and resource utilization
```bash
# Check HPA status
kubectl get hpa -n omtx-hub
# Expected: CPU 1%/70%, memory 9%/80%, REPLICAS 3

# Detailed HPA information
kubectl describe hpa omtx-hub-backend-hpa -n omtx-hub
# Check for any scaling events or issues

# Check resource utilization
kubectl top pods -n omtx-hub
kubectl top nodes
```

---

## **📊 PERFORMANCE MONITORING**

### **1. APPLICATION PERFORMANCE METRICS**
**📁 Files**: `backend/monitoring/apm_service.py`, `backend/middleware/rate_limiter.py`
**🎯 Purpose**: Test API response times, load performance, and endpoint availability
```bash
# Response time testing
time curl -s http://34.10.21.160/health > /dev/null
# Expected: < 1 second

# Load test basic endpoints
for i in {1..5}; do
  echo "Request $i:"
  time curl -s http://34.10.21.160/health -w "Status: %{http_code}, Time: %{time_total}s\n" -o /dev/null
done

# Check API endpoint performance
curl -s http://34.10.21.160/openapi.json | wc -c
# Expected: > 10000 characters (complete API schema)
```

### **2. RESOURCE UTILIZATION ANALYSIS**
**📁 Files**: `infrastructure/k8s/deployment.yaml` (resource limits), `infrastructure/terraform/gke.tf`
**🎯 Purpose**: Monitor CPU, memory, and storage usage across pods and nodes
```bash
# Memory and CPU usage by pod
kubectl top pods -n omtx-hub --containers

# Node resource utilization
kubectl describe nodes | grep -A 5 "Allocated resources"

# Storage usage
kubectl get pv
kubectl get pvc -n omtx-hub
```

### **3. CONTAINER METRICS**
**📁 Files**: `Dockerfile`, `infrastructure/k8s/deployment.yaml`
**🎯 Purpose**: Analyze container resource requests, limits, and image information
```bash
# Pod resource requests vs limits
kubectl describe deployment omtx-hub-backend -n omtx-hub | grep -A 10 "Requests\|Limits"

# Container image information
kubectl describe pods -n omtx-hub | grep -E "Image:|Image ID:"
# Expected: gcr.io/om-models/omtx-hub-backend:latest or specific digest
```

---

## **🔍 TROUBLESHOOTING COMMON ISSUES**

### **1. POD ISSUES**

#### **PODS IN PENDING STATE**
**📁 Files**: `infrastructure/k8s/deployment.yaml`, `infrastructure/terraform/gke.tf`
**🎯 Purpose**: Diagnose resource constraints, image pull issues, and scheduling problems
```bash
# Check pod events
kubectl describe pod <pod-name> -n omtx-hub | grep -A 10 Events

# Common causes and solutions:
# - Insufficient CPU/Memory: Scale nodes or adjust resource requests
# - Image pull issues: Check image availability and registry access
# - Node selector issues: Verify node labels and scheduling constraints

# Check node resources
kubectl describe nodes | grep -E "Capacity:|Allocatable:|Allocated resources:" -A 5
```

#### **PODS IN CRASHLOOPBACKOFF**
**📁 Files**: `backend/main.py`, `backend/.env`, `infrastructure/k8s/secrets.yaml`
**🎯 Purpose**: Debug application startup failures, environment variables, and resource limits
```bash
# Check pod logs
kubectl logs <pod-name> -n omtx-hub

# Get previous container logs
kubectl logs <pod-name> -n omtx-hub --previous

# Check pod events
kubectl describe pod <pod-name> -n omtx-hub

# Common fixes:
# - Environment variable issues: Check secrets and configmaps
# - Application startup failures: Review logs for specific errors
# - Resource constraints: Increase memory/CPU limits
```

#### **IMAGE PULL ERRORS**
**📁 Files**: `Dockerfile`, `.github/workflows/deploy.yml`, `infrastructure/k8s/deployment.yaml`
**🎯 Purpose**: Fix container registry access, architecture mismatches, and image availability
```bash
# Check image pull events
kubectl describe pod <pod-name> -n omtx-hub | grep -A 5 "Failed to pull image"

# Verify image exists in registry
gcloud container images list --repository=gcr.io/om-models

# Fix architecture mismatches (ARM vs AMD64)
docker buildx build --platform linux/amd64 -t gcr.io/om-models/omtx-hub-backend:latest backend/ --push

# Update deployment to use specific architecture
kubectl set image deployment/omtx-hub-backend backend=gcr.io/om-models/omtx-hub-backend:latest -n omtx-hub
```

### **2. SERVICE CONNECTIVITY ISSUES**

#### **EXTERNAL IP NOT ASSIGNED**
**📁 Files**: `infrastructure/k8s/service.yaml`, `infrastructure/terraform/networking.tf`
**🎯 Purpose**: Fix load balancer configuration and GCP networking issues
```bash
# Check service status
kubectl get service omtx-hub-backend-service -n omtx-hub -o yaml

# Check GCP load balancer
gcloud compute forwarding-rules list
gcloud compute target-pools list

# Force service recreation
kubectl delete service omtx-hub-backend-service -n omtx-hub
kubectl apply -f <service-manifest>
```

#### **HEALTH CHECK FAILURES**
**📁 Files**: `backend/api/health_endpoints.py`, `infrastructure/k8s/deployment.yaml`
**🎯 Purpose**: Debug health endpoint issues, service discovery, and port configuration
```bash
# Direct pod health check
kubectl exec -it <pod-name> -n omtx-hub -- curl localhost:8000/health

# Check service endpoints
kubectl get endpoints -n omtx-hub

# Verify port configuration
kubectl describe service omtx-hub-backend-service -n omtx-hub
```

### **3. AUTO-SCALING ISSUES**

#### **HPA NOT SCALING**
**📁 Files**: `infrastructure/k8s/hpa.yaml`, `infrastructure/k8s/metrics-server.yaml`
**🎯 Purpose**: Fix metrics server issues, HPA configuration, and scaling thresholds
```bash
# Check metrics server
kubectl top nodes
kubectl top pods -n omtx-hub

# If metrics not available, install metrics-server:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Check HPA conditions
kubectl describe hpa omtx-hub-backend-hpa -n omtx-hub

# Manual scaling test
kubectl scale deployment omtx-hub-backend --replicas=5 -n omtx-hub
```

---

## **🔄 ROUTINE MAINTENANCE TASKS**

### **1. WEEKLY MAINTENANCE**

#### **CONTAINER IMAGE UPDATES**
**📁 Files**: `.github/workflows/deploy.yml`, `infrastructure/k8s/deployment.yaml`
**🎯 Purpose**: Deploy new application versions, monitor rollouts, and handle rollbacks
```bash
# Check for new image updates
gcloud container images list-tags gcr.io/om-models/omtx-hub-backend --limit=5

# Update to latest image
kubectl set image deployment/omtx-hub-backend backend=gcr.io/om-models/omtx-hub-backend:latest -n omtx-hub

# Monitor rollout
kubectl rollout status deployment/omtx-hub-backend -n omtx-hub

# Rollback if needed
kubectl rollout undo deployment/omtx-hub-backend -n omtx-hub
```

#### **RESOURCE CLEANUP**
**📁 Files**: `scripts/cleanup_resources.sh`, `infrastructure/k8s/`
**🎯 Purpose**: Clean up completed/failed pods and unused container images
```bash
# Clean up completed pods
kubectl delete pods --field-selector=status.phase=Succeeded -n omtx-hub

# Clean up failed pods
kubectl delete pods --field-selector=status.phase=Failed -n omtx-hub

# Clean up unused images on nodes (run on each node)
gcloud compute ssh <node-name> --zone=us-central1-a --command="docker system prune -f"
```

### **2. MONTHLY MAINTENANCE**

#### **CLUSTER NODE UPDATES**
**📁 Files**: `infrastructure/terraform/gke.tf`, `scripts/cluster_upgrade.sh`
**🎯 Purpose**: Update GKE cluster version, node pools, and Kubernetes components
```bash
# Check node version
kubectl get nodes -o wide

# Check available cluster versions
gcloud container get-server-config --zone=us-central1-a

# Update cluster (if needed)
gcloud container clusters upgrade omtx-hub-cluster --zone=us-central1-a --master

# Update node pools
gcloud container clusters upgrade omtx-hub-cluster --zone=us-central1-a --node-pool=default-pool
```

#### **SECURITY UPDATES**
**📁 Files**: `infrastructure/k8s/network-policy.yaml`, `infrastructure/k8s/secrets.yaml`
**🎯 Purpose**: Apply security patches, rotate secrets, and update network policies
```bash
# Check for security advisories
gcloud container clusters describe omtx-hub-cluster --zone=us-central1-a | grep -A 10 notifications

# Update cluster security
gcloud container clusters update omtx-hub-cluster --zone=us-central1-a --enable-network-policy

# Review and rotate secrets
kubectl get secrets -n omtx-hub
# Recreate secrets as needed with updated credentials
```

---

## **📈 SCALING OPERATIONS**

### **1. MANUAL SCALING**

#### **SCALE APPLICATION REPLICAS**
**📁 Files**: `infrastructure/k8s/deployment.yaml`, `infrastructure/k8s/hpa.yaml`
**🎯 Purpose**: Manually adjust pod replicas for load management and resource optimization
```bash
# Scale up during high load
kubectl scale deployment omtx-hub-backend --replicas=8 -n omtx-hub

# Scale down during low load  
kubectl scale deployment omtx-hub-backend --replicas=2 -n omtx-hub

# Monitor scaling
kubectl get pods -n omtx-hub -w
```

#### **SCALE CLUSTER NODES**
**📁 Files**: `infrastructure/terraform/gke.tf`, `scripts/scale_cluster.sh`
**🎯 Purpose**: Resize GKE cluster nodes and configure cluster autoscaling
```bash
# Scale cluster nodes
gcloud container clusters resize omtx-hub-cluster --num-nodes=5 --zone=us-central1-a

# Enable cluster autoscaling
gcloud container clusters update omtx-hub-cluster --enable-autoscaling --min-nodes=2 --max-nodes=10 --zone=us-central1-a
```

### **2. RESOURCE ADJUSTMENT**

#### **UPDATE RESOURCE LIMITS**
**📁 Files**: `infrastructure/k8s/deployment.yaml`, `infrastructure/k8s/hpa.yaml`
**🎯 Purpose**: Modify CPU/memory limits and HPA thresholds for optimal performance
```bash
# Update CPU limits
kubectl patch deployment omtx-hub-backend -n omtx-hub -p='{"spec":{"template":{"spec":{"containers":[{"name":"backend","resources":{"limits":{"cpu":"2000m"}}}]}}}}'

# Update memory limits  
kubectl patch deployment omtx-hub-backend -n omtx-hub -p='{"spec":{"template":{"spec":{"containers":[{"name":"backend","resources":{"limits":{"memory":"4Gi"}}}]}}}}'

# Update HPA thresholds
kubectl patch hpa omtx-hub-backend-hpa -n omtx-hub -p='{"spec":{"metrics":[{"type":"Resource","resource":{"name":"cpu","target":{"type":"Utilization","averageUtilization":50}}}]}}'
```

---

## **🔐 SECURITY MANAGEMENT**

### **1. SECRETS MANAGEMENT**
**📁 Files**: `infrastructure/k8s/secrets.yaml`, `backend/.env`, `scripts/rotate_secrets.sh`
**🎯 Purpose**: Manage environment variables, rotate secrets, and restart applications
```bash
# List current secrets
kubectl get secrets -n omtx-hub

# Update environment variables
kubectl create secret generic omtx-hub-env --from-env-file=backend/.env --namespace=omtx-hub --dry-run=client -o yaml | kubectl apply -f -

# Rotate secrets (requires app restart)
kubectl rollout restart deployment/omtx-hub-backend -n omtx-hub
```

### **2. NETWORK SECURITY**
**📁 Files**: `infrastructure/k8s/network-policy.yaml`, `infrastructure/k8s/rbac.yaml`
**🎯 Purpose**: Monitor network policies, service accounts, and RBAC configurations
```bash
# Check network policies
kubectl get networkpolicies -n omtx-hub

# View service accounts and RBAC
kubectl get serviceaccounts -n omtx-hub
kubectl get rolebindings -n omtx-hub

# Audit cluster security
gcloud container clusters describe omtx-hub-cluster --zone=us-central1-a | grep -E "masterAuth|networkPolicy|privateCluster"
```

---

## **💾 BACKUP AND RECOVERY**

### **1. CONFIGURATION BACKUP**
**📁 Files**: `scripts/backup_cluster.sh`, `infrastructure/k8s/`, `backend/.env`
**🎯 Purpose**: Export Kubernetes manifests, secrets, and cluster configuration
```bash
# Export all Kubernetes manifests
kubectl get all -n omtx-hub -o yaml > omtx-hub-backup-$(date +%Y%m%d).yaml

# Backup secrets (be careful with sensitive data)
kubectl get secrets -n omtx-hub -o yaml > omtx-hub-secrets-backup-$(date +%Y%m%d).yaml

# Export cluster configuration
gcloud container clusters describe omtx-hub-cluster --zone=us-central1-a > cluster-config-$(date +%Y%m%d).yaml
```

### **2. DISASTER RECOVERY**
**📁 Files**: `scripts/restore_cluster.sh`, `infrastructure/k8s/`, backup files
**🎯 Purpose**: Restore from backups and verify system functionality
```bash
# Restore from backup
kubectl apply -f omtx-hub-backup-<date>.yaml

# Restore specific resources
kubectl apply -f - <<EOF
<paste-backup-yaml-here>
EOF

# Verify restoration
kubectl get all -n omtx-hub
curl -f http://34.10.21.160/health
```

---

## **🚨 EMERGENCY PROCEDURES**

### **1. APPLICATION DOWN**
**📁 Files**: `infrastructure/k8s/deployment.yaml`, `scripts/emergency_restart.sh`
**🎯 Purpose**: Quick diagnosis, emergency restart, and force pod deletion
```bash
# Quick diagnosis
kubectl get pods -n omtx-hub
kubectl logs -l app=omtx-hub-backend -n omtx-hub --tail=50

# Emergency restart
kubectl rollout restart deployment/omtx-hub-backend -n omtx-hub

# Scale up immediately
kubectl scale deployment omtx-hub-backend --replicas=5 -n omtx-hub

# Force pod deletion if stuck
kubectl delete pods -l app=omtx-hub-backend -n omtx-hub --force --grace-period=0
```

### **2. CLUSTER ISSUES**
**📁 Files**: `infrastructure/terraform/gke.tf`, `scripts/emergency_scale.sh`
**🎯 Purpose**: Diagnose cluster problems, emergency node scaling, and troubleshooting
```bash
# Check cluster status
gcloud container clusters describe omtx-hub-cluster --zone=us-central1-a

# Emergency node creation
gcloud container clusters resize omtx-hub-cluster --num-nodes=5 --zone=us-central1-a

# Node troubleshooting
kubectl describe node <node-name>
kubectl get events --sort-by=.metadata.creationTimestamp
```

### **3. COMPLETE SYSTEM RECOVERY**
**📁 Files**: `infrastructure/terraform/`, `infrastructure/k8s/`, `backend/.env`
**🎯 Purpose**: Recreate cluster from scratch and redeploy entire application
```bash
# Recreate cluster if needed
gcloud container clusters delete omtx-hub-cluster --zone=us-central1-a
gcloud container clusters create omtx-hub-cluster --zone=us-central1-a --num-nodes=3

# Redeploy application
kubectl create namespace omtx-hub
kubectl create secret generic omtx-hub-env --from-env-file=backend/.env --namespace=omtx-hub
kubectl apply -f <deployment-manifests>

# Verify recovery
curl -f http://<new-external-ip>/health
```

---

## **📱 MONITORING AND ALERTING SETUP**

### **1. BASIC MONITORING**
**📁 Files**: `infrastructure/k8s/monitoring/`, `scripts/setup_monitoring.sh`
**🎯 Purpose**: Set up Kubernetes dashboard and monitoring service accounts
```bash
# Set up basic monitoring dashboard
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

# Create monitoring service account
kubectl create serviceaccount dashboard-admin-sa -n kube-system
kubectl create clusterrolebinding dashboard-admin-sa --clusterrole=cluster-admin --serviceaccount=kube-system:dashboard-admin-sa
```

### **2. LOG AGGREGATION**
**📁 Files**: `scripts/collect_logs.sh`, `infrastructure/k8s/logging/`
**🎯 Purpose**: Aggregate application logs and set up log rotation
```bash
# View aggregated logs
kubectl logs -l app=omtx-hub-backend -n omtx-hub --tail=100 -f

# Set up log rotation
kubectl logs --previous -l app=omtx-hub-backend -n omtx-hub > logs-$(date +%Y%m%d-%H%M).log
```

### **3. PERFORMANCE MONITORING**
**📁 Files**: `scripts/monitor_performance.sh`, `backend/monitoring/apm_service.py`
**🎯 Purpose**: Monitor resource usage and response times over time
```bash
# Monitor resource usage over time
while true; do
  echo "$(date): $(kubectl top pods -n omtx-hub --no-headers)"
  sleep 60
done > resource-usage-$(date +%Y%m%d).log

# Monitor response times
while true; do
  echo "$(date): $(curl -s -w '%{time_total}' -o /dev/null http://34.10.21.160/health)"
  sleep 30
done > response-times-$(date +%Y%m%d).log
```

---

## **🔧 ADVANCED CONFIGURATION**

### **1. ENVIRONMENT VARIABLE UPDATES**
**📁 Files**: `infrastructure/k8s/deployment.yaml`, `backend/.env`, `infrastructure/k8s/secrets.yaml`
**🎯 Purpose**: Update application configuration, add/remove environment variables
```bash
# Update specific environment variables
kubectl patch deployment omtx-hub-backend -n omtx-hub -p='{"spec":{"template":{"spec":{"containers":[{"name":"backend","env":[{"name":"LOG_LEVEL","value":"DEBUG"}]}]}}}}'

# Add new environment variables
kubectl set env deployment/omtx-hub-backend -n omtx-hub NEW_VAR=value

# Remove environment variables
kubectl set env deployment/omtx-hub-backend -n omtx-hub NEW_VAR-
```

### **2. STORAGE CONFIGURATION**
**📁 Files**: `infrastructure/k8s/pvc.yaml`, `infrastructure/terraform/storage.tf`
**🎯 Purpose**: Configure persistent volumes and storage classes
```bash
# Check storage classes
kubectl get storageclass

# Create persistent volume if needed
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: omtx-hub-storage
  namespace: omtx-hub
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
EOF
```

### **3. INGRESS CONFIGURATION (FOR SSL SETUP)**
**📁 Files**: `infrastructure/k8s/ingress.yaml`, `infrastructure/k8s/ssl-cert.yaml`
**🎯 Purpose**: Set up ingress controller and SSL certificates for HTTPS
```bash
# Install ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# Create ingress resource (prepare for SSL)
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: omtx-hub-ingress
  namespace: omtx-hub
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
  - host: api.omtx-hub.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: omtx-hub-backend-service
            port:
              number: 80
EOF
```

---

## **📞 Support and Escalation**

### **Contact Information**
- **System Administrator**: [Your contact info]
- **Development Team**: [Team contact info]
- **GCP Support**: [GCP support details]

### **Escalation Matrix**
1. **Level 1**: Basic health checks and restart procedures
2. **Level 2**: Resource scaling and configuration changes  
3. **Level 3**: Cluster-level issues and infrastructure changes
4. **Level 4**: Complete system reconstruction and vendor support

### **Documentation References**
- **Kubernetes Documentation**: https://kubernetes.io/docs/
- **GKE Documentation**: https://cloud.google.com/kubernetes-engine/docs
- **OMTX-Hub README**: README.md in project root
- **Architecture Documentation**: CLAUDE.md in project root

---

**Last Updated**: August 18, 2025  
**System Version**: Production v1.0  
**Cluster**: omtx-hub-cluster (GKE us-central1-a)  
**External Access**: http://34.10.21.160