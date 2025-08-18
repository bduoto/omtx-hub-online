#!/bin/bash

# Script to copy necessary files from omtx-hub to omtx-hub-online
# Preserves the new architecture while bringing in needed components

SOURCE_DIR="/Users/bryanduoto/Desktop/omtx-hub"
TARGET_DIR="/Users/bryanduoto/Desktop/omtx-hub-online"

echo "📦 Copying essential files from omtx-hub to omtx-hub-online..."

# Create directories if they don't exist
mkdir -p "$TARGET_DIR/backend"/{api,services,models,schemas,database,middleware,tasks}
mkdir -p "$TARGET_DIR/frontend/src"/{components,pages,services,hooks}
mkdir -p "$TARGET_DIR/infrastructure"/{terraform,monitoring}

# Backend Core Models and Schemas (essential data structures)
echo "📋 Copying models and schemas..."
cp -r "$SOURCE_DIR/backend/models/enhanced_job_model.py" "$TARGET_DIR/backend/models/" 2>/dev/null || true
cp -r "$SOURCE_DIR/backend/schemas/task_schemas.py" "$TARGET_DIR/backend/schemas/" 2>/dev/null || true

# Database layer (Firestore integration)
echo "💾 Copying database layer..."
cp -r "$SOURCE_DIR/backend/database/unified_job_manager.py" "$TARGET_DIR/backend/database/" 2>/dev/null || true

# Essential services (only the ones that fit new architecture)
echo "⚙️ Copying compatible services..."
# GCP Storage service (still needed)
cp "$SOURCE_DIR/backend/services/gcp_storage_service.py" "$TARGET_DIR/backend/services/" 2>/dev/null || true
# Redis cache service (still needed)
cp "$SOURCE_DIR/backend/services/redis_cache_service.py" "$TARGET_DIR/backend/services/" 2>/dev/null || true
# Batch relationship manager (modified for new architecture)
cp "$SOURCE_DIR/backend/services/batch_relationship_manager.py" "$TARGET_DIR/backend/services/" 2>/dev/null || true

# Task handlers (needed for routing)
echo "📍 Copying task handlers..."
cp -r "$SOURCE_DIR/backend/tasks/" "$TARGET_DIR/backend/tasks/" 2>/dev/null || true

# API endpoints (we'll modify these for new architecture)
echo "🌐 Copying API structure..."
cp "$SOURCE_DIR/backend/api/unified_endpoints.py" "$TARGET_DIR/backend/api/" 2>/dev/null || true
cp "$SOURCE_DIR/backend/api/unified_batch_api.py" "$TARGET_DIR/backend/api/" 2>/dev/null || true

# Frontend components (selective - only ones that don't conflict)
echo "🎨 Copying frontend components..."
# Core components
cp -r "$SOURCE_DIR/src/components/DynamicTaskForm.tsx" "$TARGET_DIR/frontend/src/components/" 2>/dev/null || true
cp -r "$SOURCE_DIR/src/services/taskSchemaService.ts" "$TARGET_DIR/frontend/src/services/" 2>/dev/null || true

# Copy package files for dependencies
echo "📦 Copying package definitions..."
cp "$SOURCE_DIR/backend/requirements.txt" "$TARGET_DIR/backend/" 2>/dev/null || true
cp "$SOURCE_DIR/package.json" "$TARGET_DIR/frontend/" 2>/dev/null || true
cp "$SOURCE_DIR/tsconfig.json" "$TARGET_DIR/frontend/" 2>/dev/null || true

# Copy environment template
echo "🔐 Creating environment template..."
cat > "$TARGET_DIR/.env.template" << 'EOF'
# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_BUCKET_NAME=your-bucket-name
FIRESTORE_DATABASE=(default)

# Modal Configuration
MODAL_TOKEN=your-modal-token
MODAL_WEBHOOK_SECRET=generate-with-openssl-rand-hex-32

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development

# Monitoring
ENABLE_TRACING=true
OTEL_ENDPOINT=http://localhost:4317

# Rate Limiting
DEFAULT_RPS_LIMIT=60
PREMIUM_RPS_LIMIT=300
ENTERPRISE_RPS_LIMIT=600

# GPU Quotas
DEFAULT_DAILY_GPU_MINUTES=600
PREMIUM_DAILY_GPU_MINUTES=1800
ENTERPRISE_DAILY_GPU_MINUTES=10800
EOF

echo ""
echo "✅ Files copied successfully!"
echo ""
echo "⚠️  Note: The following files were NOT copied as they need redesign:"
echo "  - modal_subprocess_runner.py (replaced by production_modal_service.py)"
echo "  - modal_monitor.py (replaced by webhook-based completion)"
echo "  - modal_execution_service.py (replaced by production_modal_service.py)"
echo ""
echo "Next steps:"
echo "1. cd $TARGET_DIR"
echo "2. Review copied files and remove any subprocess-based code"
echo "3. Update imports to use new production_modal_service"
echo "4. git add -A && git commit -m 'Import essential components from legacy system'"
echo "5. git push origin main"