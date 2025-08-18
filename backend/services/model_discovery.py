"""
Model Discovery Service for OMTX-Hub
Provides dynamic model discovery and registration capabilities
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ModelProvider(str, Enum):
    """Model provider types"""
    MODAL = "modal"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    BUILTIN = "builtin"

class TaskType(str, Enum):
    """Available prediction task types"""
    PROTEIN_LIGAND_BINDING = "protein_ligand_binding"
    PROTEIN_STRUCTURE = "protein_structure"
    PROTEIN_COMPLEX = "protein_complex"
    BINDING_SITE_PREDICTION = "binding_site_prediction"
    VARIANT_COMPARISON = "variant_comparison"
    DRUG_DISCOVERY = "drug_discovery"

@dataclass
class ModelCapabilities:
    """Model capabilities and constraints"""
    supported_tasks: List[TaskType]
    input_formats: List[str]
    output_formats: List[str]
    max_sequence_length: Optional[int] = None
    max_ligands: Optional[int] = None
    supports_batch: bool = False

@dataclass
class ModelResources:
    """Resource requirements for the model"""
    gpu_required: bool = True
    gpu_memory_gb: Optional[int] = None
    cpu_cores: Optional[int] = None
    memory_gb: Optional[int] = None
    estimated_time_seconds: Optional[int] = None

@dataclass
class ModelMetadata:
    """Complete model metadata"""
    id: str
    name: str
    description: str
    version: str
    provider: ModelProvider
    capabilities: ModelCapabilities
    resources: ModelResources
    endpoint_url: Optional[str] = None
    documentation_url: Optional[str] = None
    paper_url: Optional[str] = None
    license: Optional[str] = None
    tags: List[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class ModelDiscoveryService:
    """Service for discovering and managing available models"""
    
    def __init__(self):
        self.models: Dict[str, ModelMetadata] = {}
        self._initialize_builtin_models()
    
    def _initialize_builtin_models(self):
        """Initialize with built-in models"""
        logger.info("🔍 Initializing built-in models")
        
        # Boltz-2 model
        boltz2_model = ModelMetadata(
            id="boltz2",
            name="Boltz-2",
            description="State-of-the-art biomolecular structure prediction model for protein-ligand interactions",
            version="1.0.0",
            provider=ModelProvider.MODAL,
            capabilities=ModelCapabilities(
                supported_tasks=[
                    TaskType.PROTEIN_LIGAND_BINDING,
                    TaskType.PROTEIN_STRUCTURE,
                    TaskType.PROTEIN_COMPLEX,
                    TaskType.BINDING_SITE_PREDICTION,
                    TaskType.VARIANT_COMPARISON,
                    TaskType.DRUG_DISCOVERY
                ],
                input_formats=["fasta", "smiles", "pdb"],
                output_formats=["cif", "pdb", "json"],
                max_sequence_length=2000,
                max_ligands=10,
                supports_batch=True
            ),
            resources=ModelResources(
                gpu_required=True,
                gpu_memory_gb=40,
                cpu_cores=8,
                memory_gb=32,
                estimated_time_seconds=300
            ),
            endpoint_url="modal://omtx-hub-boltz2-persistent/boltz2_predict_modal",
            documentation_url="https://github.com/deepmind/boltz",
            paper_url="https://www.nature.com/articles/s41586-021-03819-2",
            license="Apache-2.0",
            tags=["protein-folding", "ligand-binding", "structure-prediction"],
            is_active=True
        )
        
        # ESMFold model (placeholder for future implementation)
        esmfold_model = ModelMetadata(
            id="esmfold",
            name="ESMFold",
            description="Fast protein structure prediction using language models",
            version="1.0.0",
            provider=ModelProvider.HUGGINGFACE,
            capabilities=ModelCapabilities(
                supported_tasks=[
                    TaskType.PROTEIN_STRUCTURE,
                    TaskType.PROTEIN_COMPLEX
                ],
                input_formats=["fasta"],
                output_formats=["pdb", "cif"],
                max_sequence_length=1000,
                supports_batch=False
            ),
            resources=ModelResources(
                gpu_required=True,
                gpu_memory_gb=16,
                cpu_cores=4,
                memory_gb=16,
                estimated_time_seconds=60
            ),
            endpoint_url="huggingface://facebook/esmfold_v1",
            documentation_url="https://github.com/facebookresearch/esm",
            paper_url="https://www.science.org/doi/10.1126/science.ade2574",
            license="MIT",
            tags=["protein-folding", "fast-prediction", "language-model"],
            is_active=False  # Not yet implemented
        )
        
        # AlphaFold2 model (placeholder for future implementation)
        alphafold2_model = ModelMetadata(
            id="alphafold2",
            name="AlphaFold2",
            description="Highly accurate protein structure prediction using deep learning",
            version="2.0.0",
            provider=ModelProvider.LOCAL,
            capabilities=ModelCapabilities(
                supported_tasks=[
                    TaskType.PROTEIN_STRUCTURE,
                    TaskType.PROTEIN_COMPLEX
                ],
                input_formats=["fasta"],
                output_formats=["pdb", "cif"],
                max_sequence_length=2700,
                supports_batch=False
            ),
            resources=ModelResources(
                gpu_required=True,
                gpu_memory_gb=32,
                cpu_cores=16,
                memory_gb=64,
                estimated_time_seconds=1800
            ),
            documentation_url="https://github.com/deepmind/alphafold",
            paper_url="https://www.nature.com/articles/s41586-021-03819-2",
            license="Apache-2.0",
            tags=["protein-folding", "high-accuracy", "deep-learning"],
            is_active=False  # Not yet implemented
        )
        
        # Register built-in models
        self.models[boltz2_model.id] = boltz2_model
        self.models[esmfold_model.id] = esmfold_model
        self.models[alphafold2_model.id] = alphafold2_model
        
        logger.info(f"✅ Initialized {len(self.models)} built-in models")
    
    def get_all_models(self, active_only: bool = True) -> List[ModelMetadata]:
        """Get all available models"""
        models = list(self.models.values())
        if active_only:
            models = [m for m in models if m.is_active]
        return models
    
    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get a specific model by ID"""
        return self.models.get(model_id)
    
    def get_models_for_task(self, task_type: TaskType, active_only: bool = True) -> List[ModelMetadata]:
        """Get models that support a specific task type"""
        models = []
        for model in self.models.values():
            if active_only and not model.is_active:
                continue
            if task_type in model.capabilities.supported_tasks:
                models.append(model)
        return models
    
    def get_models_by_provider(self, provider: ModelProvider, active_only: bool = True) -> List[ModelMetadata]:
        """Get models from a specific provider"""
        models = []
        for model in self.models.values():
            if active_only and not model.is_active:
                continue
            if model.provider == provider:
                models.append(model)
        return models
    
    def register_model(self, model: ModelMetadata) -> bool:
        """Register a new model"""
        try:
            self.models[model.id] = model
            logger.info(f"✅ Registered model: {model.name} ({model.id})")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to register model {model.id}: {e}")
            return False
    
    def unregister_model(self, model_id: str) -> bool:
        """Unregister a model"""
        try:
            if model_id in self.models:
                del self.models[model_id]
                logger.info(f"✅ Unregistered model: {model_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Failed to unregister model {model_id}: {e}")
            return False
    
    def update_model_status(self, model_id: str, is_active: bool) -> bool:
        """Update model active status"""
        try:
            if model_id in self.models:
                self.models[model_id].is_active = is_active
                logger.info(f"✅ Updated model status: {model_id} -> {'active' if is_active else 'inactive'}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Failed to update model status {model_id}: {e}")
            return False
    
    def get_model_statistics(self) -> Dict[str, Any]:
        """Get model registry statistics"""
        total_models = len(self.models)
        active_models = len([m for m in self.models.values() if m.is_active])
        
        # Count by provider
        provider_counts = {}
        for model in self.models.values():
            provider = model.provider.value
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        # Count by task support
        task_support = {}
        for task_type in TaskType:
            task_support[task_type.value] = len(self.get_models_for_task(task_type, active_only=False))
        
        return {
            "total_models": total_models,
            "active_models": active_models,
            "inactive_models": total_models - active_models,
            "provider_distribution": provider_counts,
            "task_support": task_support
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all models to dictionary format"""
        return {
            model_id: asdict(model) 
            for model_id, model in self.models.items()
        }

# Global instance
model_discovery_service = ModelDiscoveryService()