# Enhanced Results Endpoints Integration Guide

## Overview
The Enhanced Results Endpoints provide a unified API for both individual and batch job management, designed to replace fragmented endpoints and provide consistent responses for the frontend.

## Key Features

### 🎯 Unified Job Management
- **Single API**: All job types (individual, batch_parent, batch_child) through one interface
- **Smart Filtering**: Filter by job type, status, task type with consistent parameters
- **Enhanced Search**: Full-text search across job names, task types, and input data
- **Pagination**: Consistent pagination across all endpoints

### 🔄 Backward Compatibility
- **Legacy Endpoints**: Maintains compatibility with existing BatchResults.tsx
- **Consistent Response Format**: Same field names and structures as existing API
- **Gradual Migration**: Can be adopted incrementally without breaking changes

## API Endpoints

### Core Endpoints

#### `GET /api/v2/results/my-jobs`
**Purpose**: Main job listing with advanced filtering
**Frontend**: MyResults.tsx, job dashboards
**Parameters**: 
- `page`, `per_page`: Pagination
- `job_type`: Filter by individual/batch_parent/batch_child  
- `status`: Filter by pending/running/completed/failed
- `task_type`: Filter by specific task types
- `search`: Full-text search query

**Response Format**:
```json
{
  "jobs": [
    {
      "id": "job-123",
      "name": "Job Name", 
      "job_type": "individual",
      "status": "completed",
      "created_at": 1691234567.0,
      "can_view": true,
      "has_results": true,
      "batch_info": null
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "has_more": true
  },
  "statistics": {
    "total_jobs": 100,
    "success_rate": 85.0
  }
}
```

#### `GET /api/v2/results/job/{job_id}`
**Purpose**: Detailed job information with results
**Frontend**: Job detail modals, individual job pages
**Parameters**:
- `include_results`: Include job output data
- `include_children`: Include batch children if applicable

**Response Format**:
```json
{
  "job": {
    "id": "job-123",
    "name": "Job Name",
    "status": "completed",
    "input_data": {...},
    "output_data": {...}
  },
  "results": {...},
  "batch_children": [...],  // If batch parent
  "batch_statistics": {...} // If batch parent
}
```

#### `GET /api/v2/results/batch/{batch_id}/results`  
**Purpose**: Comprehensive batch results - **Direct replacement for BatchResults.tsx**
**Frontend**: BatchResults.tsx component
**Parameters**:
- `status_filter`: Filter children by status
- `include_results`: Include individual child results

**Response Format**:
```json
{
  "parent": {
    "id": "batch-123",
    "name": "Batch Job",
    "job_type": "batch_parent",
    "status": "completed"
  },
  "children": [
    {
      "id": "batch-123-0001",
      "name": "Child Job 1", 
      "job_type": "batch_child",
      "status": "completed",
      "batch_index": 0,
      "batch_parent_id": "batch-123"
    }
  ],
  "statistics": {
    "completed": 8,
    "failed": 1,
    "running": 1,
    "progress": 90.0
  },
  "summary": {
    "total_jobs": 10,
    "success_rate": 80.0,
    "batch_complete": false
  }
}
```

### Search and Analytics

#### `GET /api/v2/results/search`
**Purpose**: Full-text job search
**Parameters**: `q` (query), `job_type`, `limit`

#### `GET /api/v2/results/statistics`  
**Purpose**: User analytics and statistics

#### `GET /api/v2/results/status/{status}`
**Purpose**: Get all jobs with specific status

### Legacy Compatibility

#### `GET /api/v2/results/legacy/batch/{batch_id}/results`
**Purpose**: **Direct drop-in replacement for existing BatchResults.tsx**
- Same response format as new batch endpoint
- Zero code changes required in frontend
- Maintains exact compatibility

#### `GET /api/v2/results/legacy/my-results`
**Purpose**: Individual jobs only (legacy MyResults.tsx compatibility)

## Frontend Integration

### BatchResults.tsx Integration
**Zero Changes Required** - Use legacy endpoint initially:
```typescript
// Current code works unchanged
const response = await fetch(`/api/v2/results/legacy/batch/${batchId}/results`);
```

**Enhanced Integration** - Migrate to new endpoint for additional features:
```typescript
// Enhanced version with status filtering
const response = await fetch(`/api/v2/results/batch/${batchId}/results?status_filter=completed`);
```

### MyResults.tsx Integration
**Current Compatibility**:
```typescript
// Works with existing pagination
const response = await fetch(`/api/v2/results/legacy/my-results?page=1&limit=20`);
```

**Enhanced Version**:
```typescript
// Advanced filtering and search
const response = await fetch(`/api/v2/results/my-jobs?job_type=individual&status=completed&search=protein`);
```

## Migration Strategy

### Phase 1: Drop-in Replacement ✅
- Use `/legacy/` endpoints with existing frontend code
- Zero changes required
- Immediate benefit from unified backend

### Phase 2: Enhanced Features
- Update frontend to use main endpoints
- Add advanced filtering and search
- Implement real-time statistics

### Phase 3: Full Unification
- Remove legacy endpoints
- Single codebase for all job types
- Complete architectural unification

## Response Model Guarantees

### Consistent Fields Across All Jobs
- `id`: Unique job identifier
- `name`: Human-readable job name  
- `job_type`: "individual" | "batch_parent" | "batch_child"
- `task_type`: Specific task type string
- `status`: "pending" | "running" | "completed" | "failed"
- `created_at`: Unix timestamp
- `updated_at`: Unix timestamp (optional)
- `can_view`: Boolean - whether job can be viewed
- `has_results`: Boolean - whether results are available

### Batch-Specific Fields
- `batch_parent_id`: ID of parent job (batch children only)
- `batch_child_ids`: Array of child IDs (batch parents only)
- `batch_index`: Index within batch (batch children only)
- `batch_info`: Progress and statistics (batch parents only)

### Result Enrichment
- Automatic result loading for completed jobs
- GCP storage integration
- Caching for performance
- Lazy loading support

## Technical Architecture

### Built on Unified Components
- **Enhanced Job Model**: Type-safe job representations
- **Unified Job Storage**: Consistent database interface with caching  
- **Smart Job Router**: Intelligent request routing
- **Modal Integration**: Seamless GPU prediction execution

### Performance Features
- **5-minute TTL Cache**: Reduced database load
- **Smart Invalidation**: Cache updates on job changes
- **Pagination**: Efficient large dataset handling
- **Background Monitoring**: Automatic stuck job detection

### Error Handling
- **Comprehensive Logging**: Full request/response logging
- **Graceful Degradation**: Fallback for missing dependencies
- **User-Friendly Errors**: Clear error messages for frontend
- **Monitoring Integration**: Automatic job monitoring triggers

## Production Ready Features
- ✅ **Type Safety**: Pydantic models for all responses
- ✅ **Caching**: 5-minute TTL with smart invalidation  
- ✅ **Monitoring**: Background job monitoring integration
- ✅ **Pagination**: Efficient large dataset handling
- ✅ **Search**: Full-text search with relevance
- ✅ **Analytics**: Comprehensive user statistics
- ✅ **Legacy Support**: Zero-disruption migration path
- ✅ **Error Recovery**: Graceful error handling and logging

---

**Status**: READY FOR INTEGRATION ✅  
**Compatibility**: 100% backward compatible  
**Performance**: Optimized with caching and pagination  
**Frontend Impact**: Zero changes required for initial adoption