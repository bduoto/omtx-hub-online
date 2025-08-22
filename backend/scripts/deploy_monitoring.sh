#!/bin/bash

# Deploy Monitoring Stack to GKE
# This script deploys Prometheus, Grafana, and related monitoring components

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"om-models"}
CLUSTER_NAME=${GKE_CLUSTER_NAME:-"omtx-hub-cluster"}
ZONE=${GKE_ZONE:-"us-central1-a"}
NAMESPACE="monitoring"

echo "🚀 Deploying OMTX-Hub Monitoring Stack"
echo "   Project: ${PROJECT_ID}"
echo "   Cluster: ${CLUSTER_NAME}"
echo "   Zone: ${ZONE}"
echo "   Namespace: ${NAMESPACE}"

# Step 1: Set up kubectl context
echo ""
echo "🔧 Setting up kubectl context..."
gcloud container clusters get-credentials ${CLUSTER_NAME} \
  --zone ${ZONE} \
  --project ${PROJECT_ID}

# Step 2: Create monitoring namespace
echo ""
echo "📦 Creating monitoring namespace..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Step 3: Deploy Prometheus
echo ""
echo "📊 Deploying Prometheus..."
kubectl apply -f k8s/monitoring/prometheus-config.yaml -n ${NAMESPACE}
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml -n ${NAMESPACE}

# Step 4: Deploy Grafana
echo ""
echo "📈 Deploying Grafana..."

# Create Grafana dashboards ConfigMap
kubectl create configmap grafana-dashboards \
  --from-file=k8s/monitoring/dashboards/ \
  --namespace=${NAMESPACE} \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f k8s/monitoring/grafana-deployment.yaml -n ${NAMESPACE}

# Step 5: Deploy Node Exporter (for detailed node metrics)
echo ""
echo "🖥️ Deploying Node Exporter..."
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: ${NAMESPACE}
  labels:
    app.kubernetes.io/name: node-exporter
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: node-exporter
  template:
    metadata:
      labels:
        app.kubernetes.io/name: node-exporter
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9100"
    spec:
      hostPID: true
      hostIPC: true
      hostNetwork: true
      containers:
        - name: node-exporter
          image: prom/node-exporter:v1.6.1
          ports:
            - containerPort: 9100
              name: metrics
          resources:
            requests:
              memory: "50Mi"
              cpu: "50m"
            limits:
              memory: "100Mi"
              cpu: "100m"
          securityContext:
            privileged: true
          volumeMounts:
            - name: proc
              mountPath: /host/proc
              readOnly: true
            - name: sys
              mountPath: /host/sys
              readOnly: true
            - name: root
              mountPath: /rootfs
              readOnly: true
          args:
            - '--path.procfs=/host/proc'
            - '--path.sysfs=/host/sys'
            - '--collector.filesystem.ignored-mount-points=^/(dev|proc|sys|var/lib/docker/.+)($|/)'
      volumes:
        - name: proc
          hostPath:
            path: /proc
        - name: sys
          hostPath:
            path: /sys
        - name: root
          hostPath:
            path: /
      tolerations:
        - operator: Exists
---
apiVersion: v1
kind: Service
metadata:
  name: node-exporter
  namespace: ${NAMESPACE}
  labels:
    app.kubernetes.io/name: node-exporter
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9100"
spec:
  type: ClusterIP
  ports:
    - port: 9100
      targetPort: 9100
      name: metrics
  selector:
    app.kubernetes.io/name: node-exporter
EOF

# Step 6: Wait for deployments to be ready
echo ""
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n ${NAMESPACE}
kubectl wait --for=condition=available --timeout=300s deployment/grafana -n ${NAMESPACE}

# Step 7: Get access information
echo ""
echo "🔍 Getting service endpoints..."
PROMETHEUS_IP=$(kubectl get service prometheus -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
GRAFANA_IP=$(kubectl get service grafana -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")

echo ""
echo "✅ Monitoring stack deployed successfully!"
echo ""
echo "📊 Prometheus:"
echo "   External IP: ${PROMETHEUS_IP}"
echo "   URL: http://${PROMETHEUS_IP}:9090 (when available)"
echo "   Port Forward: kubectl port-forward -n ${NAMESPACE} svc/prometheus 9090:9090"
echo ""
echo "📈 Grafana:"
echo "   External IP: ${GRAFANA_IP}"
echo "   URL: http://${GRAFANA_IP}:3000 (when available)"
echo "   Port Forward: kubectl port-forward -n ${NAMESPACE} svc/grafana 3000:3000"
echo "   Username: admin"
echo "   Password: omtx-hub-grafana-admin"
echo ""
echo "📝 Useful commands:"
echo "   kubectl get pods -n ${NAMESPACE}"
echo "   kubectl logs -f deployment/prometheus -n ${NAMESPACE}"
echo "   kubectl logs -f deployment/grafana -n ${NAMESPACE}"
echo ""
echo "🎯 Next steps:"
echo "   1. Wait for LoadBalancer IPs to be assigned"
echo "   2. Access Grafana and import dashboards"
echo "   3. Configure alerting channels in Grafana"
echo "   4. Set up external alerting (PagerDuty, Slack, etc.)"