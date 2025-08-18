# OMTX-Hub Online - Production GKE + Modal Architecture

## Overview
Enterprise-grade protein-ligand prediction platform leveraging GKE for orchestration and Modal for serverless GPU compute.

## Architecture
- **GKE Backend**: API, orchestration, monitoring, storage
- **Modal Functions**: Serverless GPU layer for Boltz-2 predictions
- **Two-Lane QoS**: Interactive (p95 < 90s) and Bulk processing
- **Webhook-First**: Real-time completion notifications
- **Production Storage**: GCS with atomic writes and indexing

## Key Improvements Over Legacy System
- ✅ No subprocess overhead - Native Modal function handles
- ✅ Persistent GPU containers with warm pools
- ✅ Shared volumes for weights and MSA cache
- ✅ Idempotency and deduplication
- ✅ Per-user quotas and rate limiting
- ✅ HMAC-secured webhooks
- ✅ Intelligent sharding and coalescing
- ✅ Real-time progress via WebSockets

## Project Structure
```
omtx-hub-online/
├── backend/
│   ├── api/           # FastAPI endpoints
│   ├── services/      # Core services
│   ├── modal/         # Modal GPU functions
│   ├── models/        # Data models
│   └── k8s/           # Kubernetes manifests
├── frontend/
│   ├── src/
│   └── public/
├── infrastructure/
│   ├── terraform/     # GKE infrastructure
│   └── monitoring/    # Grafana, Prometheus
└── tests/
    ├── load/          # Load testing
    └── integration/   # E2E tests
```

## Quick Start
```bash
# Deploy to GKE
kubectl apply -f k8s/

# Deploy Modal functions
modal deploy modal/

# Run locally
docker-compose up
```

## Performance Targets
- **Interactive Lane**: p95 TTFB < 90s
- **Bulk Lane**: 1000 ligands < 30 min
- **Throughput**: >100 RPS
- **GPU Utilization**: >80%
- **Cache Hit Rate**: >90%

## Technology Stack
- **Backend**: FastAPI, Pydantic, Redis
- **GPU Compute**: Modal (A100-40GB)
- **Storage**: GCS, Firestore
- **Orchestration**: GKE, Kubernetes
- **Monitoring**: Prometheus, Grafana, OpenTelemetry
- **Frontend**: React, TypeScript, WebSockets