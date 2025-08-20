#!/bin/bash

# Live Logs Monitoring for CTO Demo - REAL-TIME LOG DASHBOARD
# Distinguished Engineer Implementation - Complete logging visibility

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Configuration
CLUSTER_NAME="omtx-hub-cluster"
ZONE="us-central1-a"
NAMESPACE="default"

echo -e "${CYAN}📊 LIVE BACKEND LOGS MONITORING${NC}"
echo -e "${CYAN}===============================${NC}"
echo ""

print_section() {
    echo -e "${WHITE}$1${NC}"
    echo -e "${BLUE}$(printf '=%.0s' {1..50})${NC}"
}

# Function to show GKE pod logs
show_pod_logs() {
    print_section "🔍 LIVE POD LOGS"
    
    # Get pod names
    pods=$(kubectl get pods -n $NAMESPACE -l app=omtx-hub -o jsonpath='{.items[*].metadata.name}')
    
    if [ -z "$pods" ]; then
        echo -e "${YELLOW}⚠️  No omtx-hub pods found. Showing all pods:${NC}"
        kubectl get pods -n $NAMESPACE
        return
    fi
    
    echo -e "${GREEN}📦 Found pods: $pods${NC}"
    echo ""
    
    # Show logs from first pod
    first_pod=$(echo $pods | cut -d' ' -f1)
    echo -e "${CYAN}Showing logs from: $first_pod${NC}"
    echo ""
    
    # Follow logs with timestamps
    kubectl logs -f $first_pod -n $NAMESPACE --timestamps=true
}

# Function to show Cloud Run logs
show_cloud_run_logs() {
    print_section "☁️  CLOUD RUN LOGS"
    
    echo -e "${CYAN}Fetching Cloud Run service logs...${NC}"
    
    # Get Cloud Run services
    services=$(gcloud run services list --region=us-central1 --format="value(metadata.name)" | grep omtx)
    
    if [ -z "$services" ]; then
        echo -e "${YELLOW}⚠️  No Cloud Run services found${NC}"
        return
    fi
    
    echo -e "${GREEN}📦 Found services: $services${NC}"
    echo ""
    
    # Show recent logs
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name:omtx" \
        --limit=50 \
        --format="table(timestamp,severity,textPayload)" \
        --freshness=1h
}

# Function to show system metrics
show_system_metrics() {
    print_section "📈 SYSTEM METRICS"
    
    echo -e "${CYAN}GKE Cluster Status:${NC}"
    kubectl get nodes -o wide
    echo ""
    
    echo -e "${CYAN}Pod Resource Usage:${NC}"
    kubectl top pods -n $NAMESPACE --sort-by=cpu
    echo ""
    
    echo -e "${CYAN}Service Status:${NC}"
    kubectl get services -n $NAMESPACE
    echo ""
    
    echo -e "${CYAN}Ingress Status:${NC}"
    kubectl get ingress -n $NAMESPACE
}

# Function to show Cloud Run Jobs
show_cloud_run_jobs() {
    print_section "🚀 CLOUD RUN JOBS"
    
    echo -e "${CYAN}Active Cloud Run Jobs:${NC}"
    gcloud run jobs list --region=us-central1
    echo ""
    
    echo -e "${CYAN}Recent Job Executions:${NC}"
    gcloud logging read "resource.type=cloud_run_job" \
        --limit=20 \
        --format="table(timestamp,severity,resource.labels.job_name,textPayload)" \
        --freshness=1h
}

# Function to monitor API health
monitor_api_health() {
    print_section "🏥 API HEALTH MONITORING"
    
    API_URL="http://34.29.29.170"
    
    echo -e "${CYAN}Testing API endpoints...${NC}"
    
    endpoints=("/health" "/ready" "/startup" "/metrics" "/docs")
    
    for endpoint in "${endpoints[@]}"; do
        echo -n "Testing $endpoint: "
        
        response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL$endpoint" --max-time 5)
        
        if [ "$response" = "200" ]; then
            echo -e "${GREEN}✅ OK${NC}"
        elif [ "$response" = "000" ]; then
            echo -e "${RED}❌ TIMEOUT/CONNECTION ERROR${NC}"
        else
            echo -e "${YELLOW}⚠️  HTTP $response${NC}"
        fi
    done
    
    echo ""
    echo -e "${CYAN}API Response Time Test:${NC}"
    curl -w "Response Time: %{time_total}s\nHTTP Code: %{http_code}\n" -s -o /dev/null "$API_URL/health"
}

# Function to show comprehensive dashboard
show_dashboard() {
    while true; do
        clear
        
        echo -e "${CYAN}🎯 OMTX-HUB LIVE MONITORING DASHBOARD${NC}"
        echo -e "${CYAN}Time: $(date)${NC}"
        echo -e "${CYAN}============================================${NC}"
        echo ""
        
        # Quick system status
        echo -e "${WHITE}📊 QUICK STATUS${NC}"
        
        # Node status
        ready_nodes=$(kubectl get nodes --no-headers | grep -c "Ready")
        total_nodes=$(kubectl get nodes --no-headers | wc -l)
        echo -e "GKE Nodes: ${GREEN}$ready_nodes/$total_nodes Ready${NC}"
        
        # Pod status
        running_pods=$(kubectl get pods -n $NAMESPACE --no-headers | grep -c "Running")
        total_pods=$(kubectl get pods -n $NAMESPACE --no-headers | wc -l)
        echo -e "Pods: ${GREEN}$running_pods/$total_pods Running${NC}"
        
        # API health
        api_status=$(curl -s -o /dev/null -w "%{http_code}" "http://34.29.29.170/health" --max-time 3)
        if [ "$api_status" = "200" ]; then
            echo -e "API Health: ${GREEN}✅ Healthy${NC}"
        else
            echo -e "API Health: ${RED}❌ Unhealthy (HTTP $api_status)${NC}"
        fi
        
        echo ""
        echo -e "${WHITE}📋 RECENT LOGS (Last 10 entries)${NC}"
        echo -e "${BLUE}$(printf '=%.0s' {1..50})${NC}"
        
        # Show recent pod logs
        pods=$(kubectl get pods -n $NAMESPACE -l app=omtx-hub -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [ ! -z "$pods" ]; then
            kubectl logs $pods -n $NAMESPACE --tail=10 --timestamps=true 2>/dev/null | head -10
        else
            echo -e "${YELLOW}No application pods found${NC}"
        fi
        
        echo ""
        echo -e "${CYAN}Press Ctrl+C to exit, or wait 10s for refresh...${NC}"
        
        sleep 10
    done
}

# Main menu
show_menu() {
    echo -e "${WHITE}🎯 DEMO MONITORING OPTIONS${NC}"
    echo "1. Live Pod Logs (Follow)"
    echo "2. Cloud Run Logs"
    echo "3. System Metrics"
    echo "4. Cloud Run Jobs"
    echo "5. API Health Check"
    echo "6. Live Dashboard"
    echo "7. All Logs (Combined)"
    echo ""
    echo -n "Choose option (1-7): "
}

# Combined logs function
show_all_logs() {
    print_section "📊 COMBINED LOGS VIEW"
    
    echo -e "${CYAN}Showing combined logs from all sources...${NC}"
    echo ""
    
    # GKE logs
    echo -e "${WHITE}🔍 GKE Pod Logs:${NC}"
    pods=$(kubectl get pods -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}')
    for pod in $pods; do
        echo -e "${BLUE}--- Logs from $pod ---${NC}"
        kubectl logs $pod -n $NAMESPACE --tail=5 --timestamps=true 2>/dev/null || echo "No logs available"
        echo ""
    done
    
    # Cloud Run logs
    echo -e "${WHITE}☁️  Cloud Run Logs:${NC}"
    gcloud logging read "resource.type=cloud_run_revision" \
        --limit=10 \
        --format="table(timestamp,severity,textPayload)" \
        --freshness=30m
}

# Main execution
case "${1:-menu}" in
    "pods")
        show_pod_logs
        ;;
    "cloudrun")
        show_cloud_run_logs
        ;;
    "metrics")
        show_system_metrics
        ;;
    "jobs")
        show_cloud_run_jobs
        ;;
    "health")
        monitor_api_health
        ;;
    "dashboard")
        show_dashboard
        ;;
    "all")
        show_all_logs
        ;;
    "menu"|*)
        show_menu
        read -r choice
        case $choice in
            1) show_pod_logs ;;
            2) show_cloud_run_logs ;;
            3) show_system_metrics ;;
            4) show_cloud_run_jobs ;;
            5) monitor_api_health ;;
            6) show_dashboard ;;
            7) show_all_logs ;;
            *) echo -e "${RED}Invalid option${NC}" ;;
        esac
        ;;
esac
