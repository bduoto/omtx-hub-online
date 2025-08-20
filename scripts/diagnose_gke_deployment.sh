#!/bin/bash

# Diagnose GKE Deployment - FIND THE ACTUAL DEPLOYMENT
# Distinguished Engineer Implementation - Complete GKE diagnosis

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

echo -e "${CYAN}🔍 GKE DEPLOYMENT DIAGNOSIS${NC}"
echo -e "${CYAN}==========================${NC}"
echo ""

print_section() {
    echo -e "${WHITE}$1${NC}"
    echo -e "${BLUE}$(printf '=%.0s' {1..50})${NC}"
}

# Check cluster connection
print_section "📡 CLUSTER CONNECTION"
echo "Current context:"
kubectl config current-context
echo ""

echo "Cluster info:"
kubectl cluster-info
echo ""

# Check namespaces
print_section "📁 NAMESPACES"
echo "Available namespaces:"
kubectl get namespaces
echo ""

# Check all deployments across namespaces
print_section "🚀 ALL DEPLOYMENTS"
echo "Deployments in default namespace:"
kubectl get deployments
echo ""

echo "Deployments in all namespaces:"
kubectl get deployments --all-namespaces
echo ""

# Check all pods
print_section "📦 ALL PODS"
echo "Pods in default namespace:"
kubectl get pods
echo ""

echo "Pods in all namespaces:"
kubectl get pods --all-namespaces | grep -E "(omtx|hub|backend)"
echo ""

# Check all services
print_section "🌐 ALL SERVICES"
echo "Services in default namespace:"
kubectl get services
echo ""

echo "Services in all namespaces:"
kubectl get services --all-namespaces | grep -E "(omtx|hub|backend)"
echo ""

# Check for ingress
print_section "🔗 INGRESS"
echo "Ingress in default namespace:"
kubectl get ingress
echo ""

echo "Ingress in all namespaces:"
kubectl get ingress --all-namespaces
echo ""

# Check for any resources with omtx/hub/backend in name
print_section "🔍 SEARCH FOR OMTX/HUB/BACKEND RESOURCES"
echo "Searching for resources containing 'omtx', 'hub', or 'backend'..."
echo ""

echo "Deployments:"
kubectl get deployments --all-namespaces | grep -E "(omtx|hub|backend)" || echo "No matching deployments found"
echo ""

echo "Pods:"
kubectl get pods --all-namespaces | grep -E "(omtx|hub|backend)" || echo "No matching pods found"
echo ""

echo "Services:"
kubectl get services --all-namespaces | grep -E "(omtx|hub|backend)" || echo "No matching services found"
echo ""

# Check for LoadBalancer services (might be how the API is exposed)
print_section "⚖️ LOAD BALANCER SERVICES"
echo "LoadBalancer services:"
kubectl get services --all-namespaces --field-selector spec.type=LoadBalancer
echo ""

# Check for any service with external IP 34.29.29.170
print_section "🎯 SERVICES WITH EXTERNAL IP 34.29.29.170"
echo "Looking for services with external IP 34.29.29.170..."
kubectl get services --all-namespaces -o wide | grep "34.29.29.170" || echo "No services found with that IP"
echo ""

# Check for any ingress with that IP
echo "Looking for ingress with IP 34.29.29.170..."
kubectl get ingress --all-namespaces -o wide | grep "34.29.29.170" || echo "No ingress found with that IP"
echo ""

# Summary and recommendations
print_section "📋 SUMMARY & RECOMMENDATIONS"

echo -e "${YELLOW}Based on the diagnosis above:${NC}"
echo ""

echo "1. If you see a deployment with a different name, use that name instead"
echo "2. If the deployment is in a different namespace, add -n <namespace>"
echo "3. If no deployment exists, we need to create one"
echo "4. The service exposing 34.29.29.170 should give us clues"
echo ""

echo -e "${CYAN}🔧 NEXT STEPS:${NC}"
echo ""
echo "If you found a deployment with a different name:"
echo "  kubectl set image deployment/<ACTUAL_NAME> <CONTAINER_NAME>=gcr.io/om-models/omtx-hub-backend:missing-endpoints"
echo ""
echo "If the deployment is in a different namespace:"
echo "  kubectl set image deployment/omtx-hub-backend <CONTAINER_NAME>=gcr.io/om-models/omtx-hub-backend:missing-endpoints -n <NAMESPACE>"
echo ""
echo "If no deployment exists, we need to create one:"
echo "  kubectl create deployment omtx-hub-backend --image=gcr.io/om-models/omtx-hub-backend:missing-endpoints"
echo ""

echo -e "${GREEN}✅ Diagnosis complete!${NC}"
