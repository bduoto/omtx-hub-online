"""
Model Discovery API Endpoints
Provides REST API for dynamic model discovery and management
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.model_discovery import (
    model_discovery_service,
    ModelMetadata,
    TaskType,
    ModelProvider
)
from schemas.task_schemas import task_schema_registry

router = APIRouter()

class ModelResponse(BaseModel):
    """Response model for model metadata"""
    id: str
    name: str
    description: str
    version: str
    provider: str
    capabilities: Dict[str, Any]
    resources: Dict[str, Any]
    endpoint_url: Optional[str] = None
    documentation_url: Optional[str] = None
    paper_url: Optional[str] = None
    license: Optional[str] = None
    tags: List[str] = []
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ModelListResponse(BaseModel):
    """Response model for model list"""
    models: List[ModelResponse]
    total: int
    active: int
    inactive: int

class ModelStatisticsResponse(BaseModel):
    """Response model for model statistics"""
    total_models: int
    active_models: int
    inactive_models: int
    provider_distribution: Dict[str, int]
    task_support: Dict[str, int]

class TaskSupportResponse(BaseModel):
    """Response model for task support"""
    task_type: str
    supported_models: List[ModelResponse]
    count: int

def _model_to_response(model: ModelMetadata) -> ModelResponse:
    """Convert ModelMetadata to ModelResponse"""
    return ModelResponse(
        id=model.id,
        name=model.name,
        description=model.description,
        version=model.version,
        provider=model.provider.value,
        capabilities={
            "supported_tasks": [task.value for task in model.capabilities.supported_tasks],
            "input_formats": model.capabilities.input_formats,
            "output_formats": model.capabilities.output_formats,
            "max_sequence_length": model.capabilities.max_sequence_length,
            "max_ligands": model.capabilities.max_ligands,
            "supports_batch": model.capabilities.supports_batch
        },
        resources={
            "gpu_required": model.resources.gpu_required,
            "gpu_memory_gb": model.resources.gpu_memory_gb,
            "cpu_cores": model.resources.cpu_cores,
            "memory_gb": model.resources.memory_gb,
            "estimated_time_seconds": model.resources.estimated_time_seconds
        },
        endpoint_url=model.endpoint_url,
        documentation_url=model.documentation_url,
        paper_url=model.paper_url,
        license=model.license,
        tags=model.tags,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at
    )

@router.get("/models", response_model=ModelListResponse)
async def get_models(
    active_only: bool = Query(True, description="Return only active models"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    task: Optional[str] = Query(None, description="Filter by supported task")
):
    """Get all available models"""
    try:
        models = model_discovery_service.get_all_models(active_only=active_only)
        
        # Filter by provider if specified
        if provider:
            try:
                provider_enum = ModelProvider(provider)
                models = [m for m in models if m.provider == provider_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
        
        # Filter by task if specified
        if task:
            try:
                task_enum = TaskType(task)
                models = [m for m in models if task_enum in m.capabilities.supported_tasks]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid task: {task}")
        
        model_responses = [_model_to_response(model) for model in models]
        
        # Calculate statistics
        all_models = model_discovery_service.get_all_models(active_only=False)
        total = len(all_models)
        active = len([m for m in all_models if m.is_active])
        inactive = total - active
        
        return ModelListResponse(
            models=model_responses,
            total=total,
            active=active,
            inactive=inactive
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve models: {str(e)}")

@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(model_id: str):
    """Get a specific model by ID"""
    try:
        model = model_discovery_service.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
        
        return _model_to_response(model)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve model: {str(e)}")

@router.get("/models/tasks/{task_type}", response_model=TaskSupportResponse)
async def get_models_for_task(
    task_type: str,
    active_only: bool = Query(True, description="Return only active models")
):
    """Get models that support a specific task type"""
    try:
        # Validate task type
        try:
            task_enum = TaskType(task_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid task type: {task_type}")
        
        models = model_discovery_service.get_models_for_task(task_enum, active_only=active_only)
        model_responses = [_model_to_response(model) for model in models]
        
        return TaskSupportResponse(
            task_type=task_type,
            supported_models=model_responses,
            count=len(model_responses)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve models for task: {str(e)}")

@router.get("/models/providers/{provider}", response_model=ModelListResponse)
async def get_models_by_provider(
    provider: str,
    active_only: bool = Query(True, description="Return only active models")
):
    """Get models from a specific provider"""
    try:
        # Validate provider
        try:
            provider_enum = ModelProvider(provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
        
        models = model_discovery_service.get_models_by_provider(provider_enum, active_only=active_only)
        model_responses = [_model_to_response(model) for model in models]
        
        # Calculate statistics
        all_models = model_discovery_service.get_all_models(active_only=False)
        total = len([m for m in all_models if m.provider == provider_enum])
        active = len([m for m in all_models if m.provider == provider_enum and m.is_active])
        inactive = total - active
        
        return ModelListResponse(
            models=model_responses,
            total=total,
            active=active,
            inactive=inactive
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve models by provider: {str(e)}")

@router.get("/models/statistics", response_model=ModelStatisticsResponse)
async def get_model_statistics():
    """Get model registry statistics"""
    try:
        stats = model_discovery_service.get_model_statistics()
        return ModelStatisticsResponse(**stats)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve model statistics: {str(e)}")

@router.get("/tasks")
async def get_available_tasks():
    """Get all available task types"""
    try:
        tasks = [
            {
                "id": task.value,
                "name": task.value.replace("_", " ").title(),
                "description": _get_task_description(task)
            }
            for task in TaskType
        ]
        
        return {
            "tasks": tasks,
            "total": len(tasks)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tasks: {str(e)}")

@router.get("/providers")
async def get_available_providers():
    """Get all available providers"""
    try:
        providers = [
            {
                "id": provider.value,
                "name": provider.value.title(),
                "description": _get_provider_description(provider)
            }
            for provider in ModelProvider
        ]
        
        return {
            "providers": providers,
            "total": len(providers)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve providers: {str(e)}")

@router.get("/tasks/{task_id}/schema")
async def get_task_schema(task_id: str):
    """Get the input/output schema for a specific task"""
    try:
        schema = task_schema_registry.get_schema(task_id)
        if not schema:
            raise HTTPException(status_code=404, detail=f"Task schema not found: {task_id}")
        
        # Convert to dictionary for JSON response
        from dataclasses import asdict
        return asdict(schema)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve task schema: {str(e)}")

@router.get("/tasks/schemas")
async def get_all_task_schemas():
    """Get all available task schemas"""
    try:
        schemas = task_schema_registry.to_dict()
        return {
            "schemas": schemas,
            "total": len(schemas)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve task schemas: {str(e)}")

@router.post("/tasks/{task_id}/validate")
async def validate_task_input(task_id: str, input_data: Dict[str, Any]):
    """Validate input data against task schema"""
    try:
        validation_result = task_schema_registry.validate_input(task_id, input_data)
        return validation_result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate input: {str(e)}")

def _get_task_description(task: TaskType) -> str:
    """Get description for a task type"""
    descriptions = {
        TaskType.PROTEIN_LIGAND_BINDING: "Predict protein-ligand binding affinity and structure",
        TaskType.PROTEIN_STRUCTURE: "Predict protein structure from sequence",
        TaskType.PROTEIN_COMPLEX: "Predict protein-protein complex structures",
        TaskType.BINDING_SITE_PREDICTION: "Identify potential binding sites in proteins",
        TaskType.VARIANT_COMPARISON: "Compare protein variants and their effects",
        TaskType.DRUG_DISCOVERY: "Screen compounds for drug discovery"
    }
    return descriptions.get(task, "Unknown task type")

def _get_provider_description(provider: ModelProvider) -> str:
    """Get description for a provider"""
    descriptions = {
        ModelProvider.MODAL: "Serverless GPU computing platform",
        ModelProvider.HUGGINGFACE: "Open-source AI model repository",
        ModelProvider.LOCAL: "Locally hosted models",
        ModelProvider.BUILTIN: "Built-in model implementations"
    }
    return descriptions.get(provider, "Unknown provider")