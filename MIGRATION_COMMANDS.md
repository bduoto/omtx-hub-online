# Migration Commands Reference

## Current Setup Status ✅

### 1. Repository Structure
- **Legacy Repo**: `omtx-hub` (current directory)
- **New Repo**: `omtx-hub-online` (https://github.com/bduoto/omtx-hub-online)
- **Remote Added**: `online` remote points to new repo

### 2. Git Commands for Working with Both Repos

```bash
# View all remotes
git remote -v

# Pull latest from NEW repo
git pull online main

# Push to NEW repo
git push online main

# Pull latest from LEGACY repo  
git pull origin main

# Push to LEGACY repo (current)
git push origin main

# Switch default upstream to new repo
git branch --set-upstream-to=online/main

# Fetch updates from both repos
git fetch --all
```

### 3. Working Directory Commands

```bash
# Switch to NEW repo directory
cd /Users/bryanduoto/Desktop/omtx-hub-online

# Switch to LEGACY repo directory  
cd /Users/bryanduoto/Desktop/omtx-hub

# See which repo you're in
pwd
```

### 4. Syncing Changes Between Repos

```bash
# Copy specific file from legacy to new
cp /Users/bryanduoto/Desktop/omtx-hub/path/to/file \
   /Users/bryanduoto/Desktop/omtx-hub-online/path/to/file

# Copy with directory structure preserved
rsync -av --include='*.py' --include='*/' --exclude='*' \
  /Users/bryanduoto/Desktop/omtx-hub/backend/ \
  /Users/bryanduoto/Desktop/omtx-hub-online/backend/
```

### 5. Cherry-picking Commits

```bash
# In new repo, cherry-pick a commit from legacy
cd /Users/bryanduoto/Desktop/omtx-hub-online
git fetch online
git cherry-pick <commit-hash>
```

## Files Successfully Migrated ✅

### Backend
- ✅ `enhanced_job_model.py` - Core data models
- ✅ `task_schemas.py` - Validation schemas  
- ✅ `unified_job_manager.py` - Firestore integration
- ✅ `gcp_storage_service.py` - GCS storage
- ✅ `redis_cache_service.py` - Redis caching
- ✅ `batch_relationship_manager.py` - Batch hierarchy
- ✅ `unified_endpoints.py` - Main API
- ✅ `unified_batch_api.py` - Batch API
- ✅ `task_handlers.py` - Task routing

### Frontend
- ✅ `DynamicTaskForm.tsx` - Form component
- ✅ `taskSchemaService.ts` - Schema service
- ✅ `package.json` - Dependencies
- ✅ `tsconfig.json` - TypeScript config

## Files NOT Migrated (Replaced) ❌

These files use subprocess architecture and are replaced by new implementations:
- ❌ `modal_subprocess_runner.py` → `production_modal_service.py`
- ❌ `modal_monitor.py` → Webhook-based completion
- ❌ `modal_execution_service.py` → `production_modal_service.py`
- ❌ `unified_batch_processor.py` → Will be rewritten for new architecture

## Next Migration Steps

1. **Update imports in migrated files**:
```bash
# In new repo
cd /Users/bryanduoto/Desktop/omtx-hub-online
# Update all imports from modal_subprocess_runner to production_modal_service
grep -r "modal_subprocess_runner" backend/
# Replace with production_modal_service
```

2. **Create new unified batch processor**:
```bash
# This will use production_modal_service instead of subprocess
```

3. **Add webhook endpoints**:
```bash
# Create /api/v3/webhooks/modal endpoint
```

4. **Deploy Modal functions**:
```bash
cd /Users/bryanduoto/Desktop/omtx-hub-online/backend/modal
modal deploy boltz2_persistent.py
```

## Development Workflow

### Working on NEW architecture:
```bash
cd /Users/bryanduoto/Desktop/omtx-hub-online
# Make changes
git add .
git commit -m "feat: description"
git push origin main
```

### Maintaining LEGACY system:
```bash
cd /Users/bryanduoto/Desktop/omtx-hub
# Bug fixes only
git add .
git commit -m "fix: description"
git push origin main
```

### Syncing improvements back to legacy:
```bash
# From new repo
cd /Users/bryanduoto/Desktop/omtx-hub-online
git format-patch -1 HEAD

# In legacy repo
cd /Users/bryanduoto/Desktop/omtx-hub
git am < /Users/bryanduoto/Desktop/omtx-hub-online/0001-*.patch
```