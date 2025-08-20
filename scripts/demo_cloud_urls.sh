#!/bin/bash

# Demo Cloud Console URLs - BOOKMARK THESE FOR CTO DEMO
# Distinguished Engineer Implementation - Quick access to all monitoring dashboards

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

PROJECT_ID=${GCP_PROJECT_ID:-"om-models"}

echo -e "${CYAN}🔗 GOOGLE CLOUD MONITORING URLS FOR DEMO${NC}"
echo -e "${CYAN}=======================================${NC}"
echo ""

echo -e "${WHITE}🏗️  INFRASTRUCTURE MONITORING${NC}"
echo -e "${BLUE}GKE Cluster Dashboard:${NC}"
echo "https://console.cloud.google.com/kubernetes/clusters/details/us-central1-a/omtx-hub-cluster?project=$PROJECT_ID"
echo ""

echo -e "${BLUE}GKE Workloads:${NC}"
echo "https://console.cloud.google.com/kubernetes/workload?project=$PROJECT_ID"
echo ""

echo -e "${BLUE}GKE Services & Ingress:${NC}"
echo "https://console.cloud.google.com/kubernetes/discovery?project=$PROJECT_ID"
echo ""

echo -e "${WHITE}☁️  CLOUD RUN SERVICES${NC}"
echo -e "${BLUE}Cloud Run Services:${NC}"
echo "https://console.cloud.google.com/run?project=$PROJECT_ID"
echo ""

echo -e "${BLUE}Cloud Run Jobs:${NC}"
echo "https://console.cloud.google.com/run/jobs?project=$PROJECT_ID"
echo ""

echo -e "${WHITE}🗄️  STORAGE & DATABASES${NC}"
echo -e "${BLUE}Cloud Storage Buckets:${NC}"
echo "https://console.cloud.google.com/storage/browser?project=$PROJECT_ID"
echo ""

echo -e "${BLUE}Firestore Database:${NC}"
echo "https://console.cloud.google.com/firestore/databases?project=$PROJECT_ID"
echo ""

echo -e "${WHITE}📊 MONITORING & LOGGING${NC}"
echo -e "${BLUE}Cloud Monitoring:${NC}"
echo "https://console.cloud.google.com/monitoring?project=$PROJECT_ID"
echo ""

echo -e "${BLUE}Cloud Logging:${NC}"
echo "https://console.cloud.google.com/logs/query?project=$PROJECT_ID"
echo ""

echo -e "${BLUE}Error Reporting:${NC}"
echo "https://console.cloud.google.com/errors?project=$PROJECT_ID"
echo ""

echo -e "${WHITE}💰 COST MONITORING${NC}"
echo -e "${BLUE}Billing Dashboard:${NC}"
echo "https://console.cloud.google.com/billing?project=$PROJECT_ID"
echo ""

echo -e "${BLUE}Cost Breakdown:${NC}"
echo "https://console.cloud.google.com/billing/reports?project=$PROJECT_ID"
echo ""

echo -e "${WHITE}🔐 SECURITY & IAM${NC}"
echo -e "${BLUE}IAM & Admin:${NC}"
echo "https://console.cloud.google.com/iam-admin/iam?project=$PROJECT_ID"
echo ""

echo -e "${BLUE}Service Accounts:${NC}"
echo "https://console.cloud.google.com/iam-admin/serviceaccounts?project=$PROJECT_ID"
echo ""

echo -e "${WHITE}🎯 DEMO-SPECIFIC DASHBOARDS${NC}"
echo -e "${BLUE}Custom Monitoring Dashboard:${NC}"
echo "https://console.cloud.google.com/monitoring/dashboards/custom?project=$PROJECT_ID"
echo ""

echo -e "${BLUE}API Gateway (if configured):${NC}"
echo "https://console.cloud.google.com/api-gateway?project=$PROJECT_ID"
echo ""

echo -e "${WHITE}📱 MOBILE-FRIENDLY URLS${NC}"
echo -e "${BLUE}Cloud Console Mobile:${NC}"
echo "https://console.cloud.google.com/?project=$PROJECT_ID"
echo ""

# Function to open all URLs
open_all_urls() {
    echo -e "${YELLOW}🌐 Opening all monitoring URLs...${NC}"
    
    urls=(
        "https://console.cloud.google.com/kubernetes/clusters/details/us-central1-a/omtx-hub-cluster?project=$PROJECT_ID"
        "https://console.cloud.google.com/run?project=$PROJECT_ID"
        "https://console.cloud.google.com/monitoring?project=$PROJECT_ID"
        "https://console.cloud.google.com/logs/query?project=$PROJECT_ID"
        "https://console.cloud.google.com/billing/reports?project=$PROJECT_ID"
    )
    
    for url in "${urls[@]}"; do
        if command -v open &> /dev/null; then
            open "$url"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$url"
        else
            echo "Please open manually: $url"
        fi
        sleep 1  # Prevent browser overload
    done
}

# Function to create monitoring dashboard
create_monitoring_dashboard() {
    echo -e "${CYAN}📊 Creating custom monitoring dashboard...${NC}"
    
    cat > monitoring_dashboard.json << EOF
{
  "displayName": "OMTX-Hub Production Dashboard",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "GKE Pod CPU Usage",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"k8s_container\" AND resource.labels.cluster_name=\"omtx-hub-cluster\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_MEAN"
                    }
                  }
                }
              }
            ]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "xPos": 6,
        "widget": {
          "title": "API Request Rate",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"omtx-hub-backend\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE"
                    }
                  }
                }
              }
            ]
          }
        }
      }
    ]
  }
}
EOF
    
    echo -e "${GREEN}✅ Dashboard configuration created: monitoring_dashboard.json${NC}"
    echo -e "${CYAN}Upload this to Cloud Monitoring for custom dashboard${NC}"
}

# Check if we should open URLs
if [ "$1" = "open" ]; then
    open_all_urls
elif [ "$1" = "dashboard" ]; then
    create_monitoring_dashboard
else
    echo -e "${WHITE}💡 USAGE:${NC}"
    echo "  $0 open      - Open all monitoring URLs in browser"
    echo "  $0 dashboard - Create custom monitoring dashboard"
    echo ""
    echo -e "${CYAN}📋 Copy these URLs to your browser bookmarks for quick demo access!${NC}"
fi
