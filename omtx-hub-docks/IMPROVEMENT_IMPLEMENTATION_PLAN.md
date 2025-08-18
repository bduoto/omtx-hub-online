# OMTX-Hub Improvement Implementation Plan
*Based on comprehensive codebase analysis and optimization priorities*

## Executive Summary

This document outlines the systematic implementation plan for optimizing OMTX-Hub's architecture and functionality. The plan addresses critical architectural inconsistencies, completes missing features, and establishes a production-ready foundation before expanding to additional models.

## Current System State Analysis

### ✅ **PRODUCTION-READY STRENGTHS**
- **Sophisticated Model Registry**: 80+ model support with task workflows
- **Advanced Modal Integration**: Professional log management with error analysis
- **Well-designed Database Schema**: PostgreSQL with proper indexing and RLS policies
- **Comprehensive Frontend**: Professional UI with 6 task types
- **Cloud Infrastructure**: Supabase integration with three-bucket architecture
- **Stable 3D Visualization**: Production-ready MolstarViewer with resolved DOM conflicts and WebGL management

### ⚠️ **CRITICAL ISSUES IDENTIFIED**

#### 1. **Architectural Inconsistencies**
- **Three Job Management Systems**: File-based, Supabase-focused, and API hybrid
- **Frontend-Backend Mismatch**: UI supports 6 tasks, backend implements 1
- **Underutilized Components**: Sophisticated features not fully integrated

#### 2. **Incomplete Integration**
- **Modal Prediction Results**: Not properly routed to UI components
- **File Downloads**: .cif download button not working
- **UI Components**: Logs not displayed, overview/affinity sections incomplete

#### 3. **Production Readiness Gaps**
- **Environment Configuration**: Missing monitoring, secrets management, deployment configs
- **Error Handling**: Basic error handling without centralized monitoring
- **Performance**: No caching, limited optimization

## Implementation Priorities

### **Phase 1: Core Architecture Unification (Weeks 1-2)**
*Focus: Unify job management and fix frontend-backend mismatch*

#### **Priority 1: Unify Job Management Systems**
**Objective**: Move to Supabase-only job management with FastAPI endpoints

**Current State**:
```python
# Three different systems:
# 1. backend/database/job_manager.py - File-based (JSON)
# 2. backend/database/supabase_models.py - Supabase MyResults/Gallery
# 3. backend/main.py - Hybrid approach
```

**Target State**:
```python
# Single unified system:
# backend/database/unified_job_manager.py - Supabase-primary with fallback
# All endpoints use same job management interface
```

**Implementation Tasks**:
- [ ] Create `UnifiedJobManager` class with Supabase primary
- [ ] Implement fallback to SQLite for development/offline mode
- [ ] Update all API endpoints to use unified manager
- [ ] Remove redundant job management code
- [ ] Add comprehensive error handling and logging

#### **Priority 2: Complete Task Implementation for Boltz-2**
**Objective**: All 6 task types work properly with correct UI routing

**Current Frontend Tasks** (in `src/components/Boltz2/InputSection.tsx`):
1. `protein_ligand_binding` ✅ (Working)
2. `protein_structure` ❌ (UI only)
3. `protein_complex` ❌ (UI only)
4. `binding_site_prediction` ❌ (UI only)
5. `variant_comparison` ❌ (UI only)
6. `drug_discovery` ❌ (UI only)

**Backend Implementation** (in `backend/main.py`):
- Currently only `protein_ligand_binding` fully implemented
- Other tasks need proper handlers and Modal integration

**Implementation Tasks**:
- [ ] Implement task handlers for all 6 task types
- [ ] Update Modal prediction calls for each task
- [ ] Route prediction results to correct UI components
- [ ] Ensure proper input validation for each task type
- [ ] Test end-to-end workflow for each task

#### **Priority 3: Fix UI Component Integration**
**Objective**: Modal prediction results properly displayed in UI

**Current Issues**:
- `.cif download button` not working
- Logs not displayed in UI
- Overview/affinity sections incomplete
- Results not routing to correct UI elements

**Target Components** (in `src/components/Boltz2/OutputSection.tsx`):
```typescript
// Must work properly:
- Overview tab with prediction summary
- Affinity tab with binding scores
- Confidence tab with quality metrics
- Structure tab with .cif download
- Parameters tab with execution details
- Logs tab with Modal execution logs
```

**Implementation Tasks**:
- [ ] Fix .cif file download functionality
- [ ] Implement proper results parsing from Modal
- [ ] Route results to correct UI tabs
- [ ] Display Modal logs in Logs tab
- [ ] Show execution parameters in Parameters tab
- [ ] Test all UI components with real prediction data

### **Phase 2: Production Configuration (Weeks 3-4)**
*Focus: Environment configuration, monitoring, secrets management*

#### **Priority 4: Enhanced Environment Configuration**
**Objective**: Comprehensive production configuration system

**Current Gap**:
```python
# backend/config/environment.py - Basic configuration
# Missing: monitoring, secrets, deployment configs
```

**Target Implementation**:
```python
# backend/config/production_config.py
@dataclass
class ProductionConfig:
    # Database configuration
    database_url: str
    database_pool_size: int = 20
    
    # Monitoring and logging
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_endpoint: str = "/metrics"
    
    # Security
    cors_origins: list
    api_key_required: bool = False
    rate_limit_per_minute: int = 100
    
    # Performance
    max_concurrent_predictions: int = 10
    prediction_timeout_minutes: int = 30
    cache_ttl_seconds: int = 3600
```

**Implementation Tasks**:
- [ ] Create comprehensive production configuration
- [ ] Implement secrets management system
- [ ] Add monitoring and metrics configuration
- [ ] Set up deployment configuration options
- [ ] Add environment validation and health checks

#### **Priority 5: Enhanced Error Handling & Monitoring**
**Objective**: Centralized error handling with comprehensive monitoring

**Implementation Tasks**:
- [ ] Create centralized error handler
- [ ] Implement error classification system
- [ ] Add comprehensive logging with context
- [ ] Integrate with Modal log manager
- [ ] Create error analytics and reporting

### **Phase 3: Performance Optimization (Week 5)**
*Focus: Caching, performance monitoring, optimization*

#### **Priority 6: Performance Optimization**
**Objective**: Implement caching and performance monitoring

**Implementation Tasks**:
- [ ] Implement Redis-based caching system
- [ ] Cache prediction results for identical inputs
- [ ] Add performance monitoring and metrics
- [ ] Optimize database queries
- [ ] Implement request/response compression

## Detailed Implementation Specifications

### **1. Unified Job Management System**

**File**: `backend/database/unified_job_manager.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from backend.database.supabase_models import SupabaseJobManager
from backend.database.job_manager import JobManager
import logging

logger = logging.getLogger(__name__)

class BaseJobManager(ABC):
    """Abstract base class for job management"""
    
    @abstractmethod
    async def create_job(self, job_data: Dict[str, Any]) -> str: pass
    
    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]: pass
    
    @abstractmethod
    async def update_job_status(self, job_id: str, status: str, 
                               result_data: Optional[Dict] = None): pass
    
    @abstractmethod
    async def list_jobs(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]: pass
    
    @abstractmethod
    async def delete_job(self, job_id: str) -> bool: pass

class UnifiedJobManager(BaseJobManager):
    """Unified job manager with Supabase primary + SQLite fallback"""
    
    def __init__(self, use_supabase: bool = True):
        self.supabase_manager = SupabaseJobManager()
        self.sqlite_manager = JobManager()
        self.use_supabase = use_supabase and self.supabase_manager.available
        
        if self.use_supabase:
            logger.info("Using Supabase for job management")
        else:
            logger.info("Using SQLite fallback for job management")
    
    async def create_job(self, job_data: Dict[str, Any]) -> str:
        """Create job with fallback handling"""
        try:
            if self.use_supabase:
                return await self.supabase_manager.create_job(job_data)
            else:
                return self.sqlite_manager.create_job(job_data)
        except Exception as e:
            logger.error(f"Primary job creation failed: {e}")
            # Fallback to SQLite
            logger.info("Falling back to SQLite for job creation")
            return self.sqlite_manager.create_job(job_data)
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job with fallback handling"""
        try:
            if self.use_supabase:
                return await self.supabase_manager.get_job(job_id)
            else:
                return self.sqlite_manager.get_job(job_id)
        except Exception as e:
            logger.error(f"Primary job retrieval failed: {e}")
            # Try fallback
            return self.sqlite_manager.get_job(job_id)
    
    async def update_job_status(self, job_id: str, status: str, 
                               result_data: Optional[Dict] = None):
        """Update job status with fallback handling"""
        try:
            if self.use_supabase:
                await self.supabase_manager.update_job_status(job_id, status, result_data)
            else:
                self.sqlite_manager.update_job_status(job_id, status, result_data)
        except Exception as e:
            logger.error(f"Primary job update failed: {e}")
            # Fallback to SQLite
            self.sqlite_manager.update_job_status(job_id, status, result_data)
    
    async def list_jobs(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """List jobs with fallback handling"""
        try:
            if self.use_supabase:
                return await self.supabase_manager.list_jobs(filters)
            else:
                return self.sqlite_manager.list_jobs(filters)
        except Exception as e:
            logger.error(f"Primary job listing failed: {e}")
            # Fallback to SQLite
            return self.sqlite_manager.list_jobs(filters)
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete job with fallback handling"""
        try:
            if self.use_supabase:
                return await self.supabase_manager.delete_job(job_id)
            else:
                return self.sqlite_manager.delete_job(job_id)
        except Exception as e:
            logger.error(f"Primary job deletion failed: {e}")
            # Fallback to SQLite
            return self.sqlite_manager.delete_job(job_id)

# Global instance
unified_job_manager = UnifiedJobManager()
```

### **2. Complete Task Implementation**

**File**: `backend/tasks/task_handlers.py`

```python
from typing import Dict, Any, List, Optional
from enum import Enum
import logging
from backend.models.model_registry import PredictionTask, model_registry
from backend.services.modal_log_manager import modal_log_manager

logger = logging.getLogger(__name__)

class TaskType(str, Enum):
    PROTEIN_LIGAND_BINDING = "protein_ligand_binding"
    PROTEIN_STRUCTURE = "protein_structure"
    PROTEIN_COMPLEX = "protein_complex"
    BINDING_SITE_PREDICTION = "binding_site_prediction"
    VARIANT_COMPARISON = "variant_comparison"
    DRUG_DISCOVERY = "drug_discovery"

class TaskHandlerRegistry:
    """Registry for handling different prediction tasks"""
    
    def __init__(self):
        self.handlers = {
            TaskType.PROTEIN_LIGAND_BINDING: self.handle_protein_ligand_binding,
            TaskType.PROTEIN_STRUCTURE: self.handle_protein_structure,
            TaskType.PROTEIN_COMPLEX: self.handle_protein_complex,
            TaskType.BINDING_SITE_PREDICTION: self.handle_binding_site_prediction,
            TaskType.VARIANT_COMPARISON: self.handle_variant_comparison,
            TaskType.DRUG_DISCOVERY: self.handle_drug_discovery,
        }
    
    async def process_task(self, task_type: str, input_data: Dict[str, Any], 
                          job_name: str, job_id: str, **kwargs) -> Dict[str, Any]:
        """Process task with appropriate handler"""
        
        if task_type not in self.handlers:
            raise ValueError(f"Unsupported task type: {task_type}")
        
        # Validate inputs
        task_enum = TaskType(task_type)
        validation = model_registry.validate_task_inputs(
            PredictionTask(task_type), input_data
        )
        
        if not validation['valid']:
            raise ValueError(f"Invalid inputs: {validation['errors']}")
        
        # Execute task
        handler = self.handlers[task_enum]
        result = await handler(input_data, job_name, job_id, **kwargs)
        
        return result
    
    async def handle_protein_ligand_binding(self, input_data: Dict[str, Any], 
                                           job_name: str, job_id: str, 
                                           use_msa: bool = True, 
                                           use_potentials: bool = False) -> Dict[str, Any]:
        """Handle protein-ligand binding prediction (existing implementation)"""
        
        # Extract inputs
        protein_sequence = input_data.get('protein_sequence', '')
        ligand_smiles = input_data.get('ligand_smiles', '')
        
        # Call existing Boltz-2 implementation
        from backend.main import run_modal_prediction_subprocess
        
        result = await run_modal_prediction_subprocess(
            protein_sequences=[protein_sequence],
            ligands=[ligand_smiles],
            use_msa_server=use_msa,
            use_potentials=use_potentials
        )
        
        # Format result for UI
        return self.format_binding_result(result, job_id)
    
    async def handle_protein_structure(self, input_data: Dict[str, Any], 
                                     job_name: str, job_id: str, 
                                     use_msa: bool = True) -> Dict[str, Any]:
        """Handle protein structure prediction"""
        
        # Extract inputs
        protein_sequence = input_data.get('protein_sequence', '')
        
        # Use Boltz-2 for structure prediction (without ligand)
        from backend.main import run_modal_prediction_subprocess
        
        result = await run_modal_prediction_subprocess(
            protein_sequences=[protein_sequence],
            ligands=[],  # No ligands for structure prediction
            use_msa_server=use_msa,
            use_potentials=False
        )
        
        # Format result for UI
        return self.format_structure_result(result, job_id)
    
    async def handle_protein_complex(self, input_data: Dict[str, Any], 
                                   job_name: str, job_id: str, 
                                   use_msa: bool = True) -> Dict[str, Any]:
        """Handle protein complex prediction"""
        
        # Extract inputs
        chain_a_sequence = input_data.get('chain_a_sequence', '')
        chain_b_sequence = input_data.get('chain_b_sequence', '')
        
        # Combine sequences for complex prediction
        combined_sequence = f"{chain_a_sequence}:{chain_b_sequence}"
        
        # Use Boltz-2 for complex prediction
        from backend.main import run_modal_prediction_subprocess
        
        result = await run_modal_prediction_subprocess(
            protein_sequences=[combined_sequence],
            ligands=[],  # No ligands for complex prediction
            use_msa_server=use_msa,
            use_potentials=False
        )
        
        # Format result for UI
        return self.format_complex_result(result, job_id)
    
    async def handle_binding_site_prediction(self, input_data: Dict[str, Any], 
                                           job_name: str, job_id: str) -> Dict[str, Any]:
        """Handle binding site prediction"""
        
        # Extract inputs
        protein_sequence = input_data.get('protein_sequence', '')
        
        # Use Boltz-2 to predict structure first, then analyze binding sites
        from backend.main import run_modal_prediction_subprocess
        
        result = await run_modal_prediction_subprocess(
            protein_sequences=[protein_sequence],
            ligands=[],  # No ligands for binding site prediction
            use_msa_server=True,
            use_potentials=False
        )
        
        # Format result for UI
        return self.format_binding_site_result(result, job_id)
    
    async def handle_variant_comparison(self, input_data: Dict[str, Any], 
                                      job_name: str, job_id: str) -> Dict[str, Any]:
        """Handle variant comparison"""
        
        # Extract inputs
        wildtype_sequence = input_data.get('wildtype_sequence', '')
        variants = input_data.get('variants', [])
        
        # Predict structures for wildtype and variants
        results = []
        
        # Wildtype structure
        from backend.main import run_modal_prediction_subprocess
        
        wt_result = await run_modal_prediction_subprocess(
            protein_sequences=[wildtype_sequence],
            ligands=[],
            use_msa_server=True,
            use_potentials=False
        )
        
        results.append({'type': 'wildtype', 'result': wt_result})
        
        # Variant structures
        for variant in variants:
            variant_sequence = variant.get('sequence', '')
            variant_name = variant.get('name', 'Unknown')
            
            variant_result = await run_modal_prediction_subprocess(
                protein_sequences=[variant_sequence],
                ligands=[],
                use_msa_server=True,
                use_potentials=False
            )
            
            results.append({
                'type': 'variant', 
                'name': variant_name,
                'result': variant_result
            })
        
        # Format result for UI
        return self.format_variant_comparison_result(results, job_id)
    
    async def handle_drug_discovery(self, input_data: Dict[str, Any], 
                                  job_name: str, job_id: str) -> Dict[str, Any]:
        """Handle drug discovery workflow"""
        
        # Extract inputs
        protein_sequence = input_data.get('protein_sequence', '')
        compound_library = input_data.get('compound_library', [])
        
        # Screen compounds against protein
        results = []
        
        from backend.main import run_modal_prediction_subprocess
        
        for compound in compound_library:
            compound_smiles = compound.get('smiles', '')
            compound_name = compound.get('name', 'Unknown')
            
            result = await run_modal_prediction_subprocess(
                protein_sequences=[protein_sequence],
                ligands=[compound_smiles],
                use_msa_server=True,
                use_potentials=False
            )
            
            results.append({
                'compound_name': compound_name,
                'smiles': compound_smiles,
                'result': result
            })
        
        # Format result for UI
        return self.format_drug_discovery_result(results, job_id)
    
    def format_binding_result(self, result: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Format binding prediction result for UI"""
        return {
            'job_id': job_id,
            'task_type': 'protein_ligand_binding',
            'status': 'completed',
            'affinity': result.get('affinity', 0.0),
            'affinity_probability': result.get('affinity_probability', 0.0),
            'confidence': result.get('confidence', 0.0),
            'ptm_score': result.get('ptm_score', 0.0),
            'plddt_score': result.get('plddt_score', 0.0),
            'structure_file_base64': result.get('structure_file_base64', ''),
            'structure_file_content': result.get('structure_file_content', ''),
            'execution_time': result.get('execution_time', 0),
            'parameters': result.get('parameters', {}),
            'modal_logs': result.get('modal_logs', [])
        }
    
    def format_structure_result(self, result: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Format structure prediction result for UI"""
        return {
            'job_id': job_id,
            'task_type': 'protein_structure',
            'status': 'completed',
            'confidence': result.get('confidence', 0.0),
            'ptm_score': result.get('ptm_score', 0.0),
            'plddt_score': result.get('plddt_score', 0.0),
            'structure_file_base64': result.get('structure_file_base64', ''),
            'structure_file_content': result.get('structure_file_content', ''),
            'execution_time': result.get('execution_time', 0),
            'parameters': result.get('parameters', {}),
            'modal_logs': result.get('modal_logs', [])
        }
    
    def format_complex_result(self, result: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Format complex prediction result for UI"""
        return {
            'job_id': job_id,
            'task_type': 'protein_complex',
            'status': 'completed',
            'confidence': result.get('confidence', 0.0),
            'ptm_score': result.get('ptm_score', 0.0),
            'iptm_score': result.get('iptm_score', 0.0),
            'plddt_score': result.get('plddt_score', 0.0),
            'structure_file_base64': result.get('structure_file_base64', ''),
            'structure_file_content': result.get('structure_file_content', ''),
            'execution_time': result.get('execution_time', 0),
            'parameters': result.get('parameters', {}),
            'modal_logs': result.get('modal_logs', [])
        }
    
    def format_binding_site_result(self, result: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Format binding site prediction result for UI"""
        return {
            'job_id': job_id,
            'task_type': 'binding_site_prediction',
            'status': 'completed',
            'confidence': result.get('confidence', 0.0),
            'ptm_score': result.get('ptm_score', 0.0),
            'plddt_score': result.get('plddt_score', 0.0),
            'binding_sites': result.get('binding_sites', []),
            'structure_file_base64': result.get('structure_file_base64', ''),
            'structure_file_content': result.get('structure_file_content', ''),
            'execution_time': result.get('execution_time', 0),
            'parameters': result.get('parameters', {}),
            'modal_logs': result.get('modal_logs', [])
        }
    
    def format_variant_comparison_result(self, results: List[Dict[str, Any]], job_id: str) -> Dict[str, Any]:
        """Format variant comparison result for UI"""
        return {
            'job_id': job_id,
            'task_type': 'variant_comparison',
            'status': 'completed',
            'wildtype_result': next((r['result'] for r in results if r['type'] == 'wildtype'), {}),
            'variant_results': [r for r in results if r['type'] == 'variant'],
            'comparison_metrics': self.calculate_variant_metrics(results),
            'execution_time': sum(r.get('result', {}).get('execution_time', 0) for r in results),
            'parameters': results[0].get('result', {}).get('parameters', {}) if results else {}
        }
    
    def format_drug_discovery_result(self, results: List[Dict[str, Any]], job_id: str) -> Dict[str, Any]:
        """Format drug discovery result for UI"""
        # Sort by affinity
        sorted_results = sorted(results, key=lambda x: x.get('result', {}).get('affinity', 0), reverse=True)
        
        return {
            'job_id': job_id,
            'task_type': 'drug_discovery',
            'status': 'completed',
            'compound_results': sorted_results,
            'top_compounds': sorted_results[:10],  # Top 10 compounds
            'screening_summary': self.calculate_screening_metrics(results),
            'execution_time': sum(r.get('result', {}).get('execution_time', 0) for r in results),
            'parameters': results[0].get('result', {}).get('parameters', {}) if results else {}
        }
    
    def calculate_variant_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comparison metrics for variants"""
        # Implement variant comparison logic
        return {
            'stability_changes': [],
            'structural_differences': [],
            'functional_predictions': []
        }
    
    def calculate_screening_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate screening metrics for drug discovery"""
        affinities = [r.get('result', {}).get('affinity', 0) for r in results]
        
        return {
            'total_compounds': len(results),
            'hit_rate': len([a for a in affinities if a > 0.5]) / len(affinities) if affinities else 0,
            'best_affinity': max(affinities) if affinities else 0,
            'average_affinity': sum(affinities) / len(affinities) if affinities else 0
        }

# Global instance
task_handler_registry = TaskHandlerRegistry()
```

### **3. Updated API Integration**

**File**: `backend/api/endpoints.py`

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from backend.database.unified_job_manager import unified_job_manager
from backend.tasks.task_handlers import task_handler_registry, TaskType
import uuid
import time

router = APIRouter()

class PredictionRequest(BaseModel):
    task_type: TaskType = Field(..., description="Type of prediction task")
    input_data: Dict[str, Any] = Field(..., description="Task-specific input data")
    job_name: str = Field(..., description="Job name")
    use_msa: bool = Field(True, description="Whether to use MSA server")
    use_potentials: bool = Field(False, description="Whether to use potentials")

class PredictionResponse(BaseModel):
    job_id: str
    task_type: str
    status: str
    message: str
    estimated_completion_time: Optional[int] = None

@router.post("/predict", response_model=PredictionResponse)
async def submit_prediction(request: PredictionRequest, background_tasks: BackgroundTasks):
    """Submit prediction job with unified job management"""
    
    # Generate job ID
    job_id = f"{request.task_type}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    # Create job record
    job_data = {
        'job_id': job_id,
        'task_type': request.task_type,
        'job_name': request.job_name,
        'status': 'pending',
        'input_data': request.input_data,
        'created_at': time.time(),
        'use_msa': request.use_msa,
        'use_potentials': request.use_potentials
    }
    
    try:
        # Create job in unified manager
        await unified_job_manager.create_job(job_data)
        
        # Start background task
        background_tasks.add_task(
            process_prediction_task,
            job_id,
            request.task_type,
            request.input_data,
            request.job_name,
            request.use_msa,
            request.use_potentials
        )
        
        return PredictionResponse(
            job_id=job_id,
            task_type=request.task_type,
            status="submitted",
            message="Job submitted successfully",
            estimated_completion_time=estimate_completion_time(request.task_type)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")

async def process_prediction_task(job_id: str, task_type: str, input_data: Dict[str, Any], 
                                 job_name: str, use_msa: bool, use_potentials: bool):
    """Background task to process prediction"""
    
    try:
        # Update job status to running
        await unified_job_manager.update_job_status(job_id, "running")
        
        # Process task
        result = await task_handler_registry.process_task(
            task_type=task_type,
            input_data=input_data,
            job_name=job_name,
            job_id=job_id,
            use_msa=use_msa,
            use_potentials=use_potentials
        )
        
        # Update job with results
        await unified_job_manager.update_job_status(job_id, "completed", result)
        
    except Exception as e:
        # Update job with error
        await unified_job_manager.update_job_status(job_id, "failed", {"error": str(e)})

def estimate_completion_time(task_type: str) -> int:
    """Estimate completion time based on task type"""
    times = {
        'protein_ligand_binding': 1200,  # 20 minutes
        'protein_structure': 900,        # 15 minutes
        'protein_complex': 1800,         # 30 minutes
        'binding_site_prediction': 600,  # 10 minutes
        'variant_comparison': 2400,      # 40 minutes (multiple predictions)
        'drug_discovery': 3600,          # 60 minutes (multiple compounds)
    }
    return times.get(task_type, 1200)

@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job details"""
    job = await unified_job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/jobs")
async def list_jobs(limit: int = 50, offset: int = 0):
    """List jobs"""
    jobs = await unified_job_manager.list_jobs({'limit': limit, 'offset': offset})
    return {"jobs": jobs, "total": len(jobs)}
```

## Implementation Timeline

### **Week 1: Core Architecture**
- **Day 1-2**: Create UnifiedJobManager class
- **Day 3-4**: Implement task handlers for all 6 task types
- **Day 5**: Update API endpoints to use unified system
- **Day 6-7**: Testing and debugging

### **Week 2: UI Integration**
- **Day 1-2**: Fix .cif download functionality
- **Day 3-4**: Route prediction results to correct UI components
- **Day 5**: Implement logs display in UI
- **Day 6-7**: Test all UI components with real data

### **Week 3: Production Configuration**
- **Day 1-2**: Create production configuration system
- **Day 3-4**: Implement secrets management
- **Day 5**: Add monitoring and metrics
- **Day 6-7**: Test and deploy configuration

### **Week 4: Error Handling & Monitoring**
- **Day 1-2**: Create centralized error handler
- **Day 3-4**: Implement comprehensive logging
- **Day 5**: Integrate with Modal log manager
- **Day 6-7**: Test and optimize error handling

### **Week 5: Performance Optimization**
- **Day 1-2**: Implement caching system
- **Day 3-4**: Add performance monitoring
- **Day 5**: Optimize database queries
- **Day 6-7**: Performance testing and optimization

## Success Metrics

### **Technical Metrics**
- [ ] All 6 task types work end-to-end
- [ ] .cif download functionality works
- [ ] Modal logs display in UI
- [ ] Unified job management system operational
- [ ] Error rate < 1%
- [ ] Response time < 30 seconds for API calls

### **User Experience Metrics**
- [ ] Complete prediction workflow for all task types
- [ ] Results display in correct UI components
- [ ] File downloads work properly
- [ ] Error messages are user-friendly
- [ ] Loading states work correctly

## Commitment Strategy

Each phase will be committed as working features:
1. **Commit 1**: Unified job management system
2. **Commit 2**: Complete task implementation
3. **Commit 3**: UI component integration fixes
4. **Commit 4**: Production configuration system
5. **Commit 5**: Error handling and monitoring
6. **Commit 6**: Performance optimization

## Risk Mitigation

### **Technical Risks**
- **Database migration issues**: Maintain SQLite fallback
- **Modal API changes**: Implement error handling and retries
- **UI component integration**: Incremental testing approach

### **Implementation Risks**
- **Scope creep**: Focus on core functionality first
- **Performance issues**: Implement caching and monitoring
- **Testing complexity**: Automated testing for each component

---

*This plan provides a systematic approach to optimizing OMTX-Hub's architecture while maintaining production stability and implementing features incrementally.* 