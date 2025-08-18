"""
Dynamic Model Registry for OMTX-Hub
Handles registration, discovery, and management of 80+ models
"""

import importlib
import inspect
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseModelHandler(ABC):
    """Base class for all model handlers"""
    
    @abstractmethod
    async def predict(self, **kwargs):
        """Run model prediction"""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model name"""
        pass
    
    @property
    @abstractmethod
    def model_version(self) -> str:
        """Model version"""
        pass
    
    @property
    @abstractmethod
    def model_category(self) -> str:
        """Model category (Structure Prediction, Protein Design, etc.)"""
        pass
    
    @property
    @abstractmethod
    def supported_inputs(self) -> List[str]:
        """List of supported input types"""
        pass

class PredictionTask(str, Enum):
    """Different types of prediction tasks supported"""
    PROTEIN_LIGAND_BINDING = "protein_ligand_binding"
    PROTEIN_STRUCTURE = "protein_structure"
    PROTEIN_COMPLEX = "protein_complex"
    BINDING_SITE_PREDICTION = "binding_site_prediction"
    VARIANT_COMPARISON = "variant_comparison"
    DRUG_DISCOVERY = "drug_discovery"
    PROTEIN_DESIGN = "protein_design"

class ModelCapability(str, Enum):
    """Different capabilities that models can have"""
    STRUCTURE_PREDICTION = "structure_prediction"
    BINDING_AFFINITY = "binding_affinity"
    CAVITY_DETECTION = "cavity_detection"
    CONFORMATIONAL_ANALYSIS = "conformational_analysis"
    SEQUENCE_OPTIMIZATION = "sequence_optimization"
    DRUG_SCREENING = "drug_screening"

@dataclass
class ModelMetadata:
    """Enhanced metadata for models"""
    name: str
    version: str
    description: str
    tasks: List[PredictionTask]
    capabilities: List[ModelCapability]
    input_types: List[str]  # ["protein_sequence", "smiles", "pdb", "fasta"]
    output_types: List[str]  # ["structure", "affinity", "binding_sites", "report"]
    gpu_required: bool = True
    gpu_memory_gb: int = 40
    max_batch_size: int = 1
    estimated_runtime_minutes: int = 30
    citation: Optional[str] = None
    url: Optional[str] = None

class TaskWorkflow:
    """Defines workflow for different prediction tasks"""
    
    @staticmethod
    def get_workflow_steps(task: PredictionTask) -> List[str]:
        """Get the steps required for a specific task"""
        workflows = {
            PredictionTask.PROTEIN_LIGAND_BINDING: [
                "validate_inputs",
                "prepare_structures",
                "predict_binding",
                "calculate_affinity",
                "generate_structure",
                "create_report"
            ],
            PredictionTask.PROTEIN_STRUCTURE: [
                "validate_sequence",
                "fold_protein",
                "assess_quality",
                "generate_structure",
                "create_report"
            ],
            PredictionTask.PROTEIN_COMPLEX: [
                "validate_sequences",
                "predict_interfaces",
                "dock_subunits",
                "optimize_complex",
                "generate_structure",
                "create_report"
            ],
            PredictionTask.BINDING_SITE_PREDICTION: [
                "validate_structure",
                "detect_cavities",
                "analyze_druggability",
                "rank_sites",
                "generate_visualization",
                "create_report"
            ],
            PredictionTask.VARIANT_COMPARISON: [
                "validate_variants",
                "predict_structures",
                "compare_properties",
                "assess_stability",
                "generate_comparison",
                "create_report"
            ]
        }
        return workflows.get(task, ["validate_inputs", "process", "create_report"])
    
    @staticmethod
    def get_required_inputs(task: PredictionTask) -> Dict[str, Any]:
        """Get required inputs for a specific task"""
        input_requirements = {
            PredictionTask.PROTEIN_LIGAND_BINDING: {
                "protein_sequence": {"type": "string", "required": True, "description": "Protein sequence in FASTA format"},
                "ligand_smiles": {"type": "string", "required": True, "description": "Ligand in SMILES format"},
                "binding_site": {"type": "string", "required": False, "description": "Specific binding site residues"}
            },
            PredictionTask.PROTEIN_STRUCTURE: {
                "protein_sequence": {"type": "string", "required": True, "description": "Protein sequence in FASTA format"},
                "template_structure": {"type": "file", "required": False, "description": "Template PDB structure"}
            },
            PredictionTask.PROTEIN_COMPLEX: {
                "protein_sequences": {"type": "array", "required": True, "description": "Multiple protein sequences"},
                "stoichiometry": {"type": "string", "required": False, "description": "Subunit stoichiometry"}
            },
            PredictionTask.BINDING_SITE_PREDICTION: {
                "protein_structure": {"type": "file", "required": True, "description": "Protein structure in PDB format"},
                "cavity_detection_method": {"type": "string", "required": False, "description": "Method for cavity detection"}
            },
            PredictionTask.VARIANT_COMPARISON: {
                "reference_sequence": {"type": "string", "required": True, "description": "Reference protein sequence"},
                "variant_sequences": {"type": "array", "required": True, "description": "Variant protein sequences"},
                "mutation_positions": {"type": "array", "required": False, "description": "Specific mutation positions"}
            }
        }
        return input_requirements.get(task, {})

class EnhancedModelRegistry:
    """Enhanced model registry supporting multiple task types"""
    
    def __init__(self):
        self.models: Dict[str, ModelMetadata] = {}
        self.task_models: Dict[PredictionTask, List[str]] = {}
        self._register_default_models()
    
    def _register_default_models(self):
        """Register default models"""
        # Boltz-2 for protein-ligand binding
        boltz2_metadata = ModelMetadata(
            name="boltz2",
            version="1.0.0",
            description="Boltz-2 model for protein-ligand binding prediction",
            tasks=[PredictionTask.PROTEIN_LIGAND_BINDING],
            capabilities=[ModelCapability.STRUCTURE_PREDICTION, ModelCapability.BINDING_AFFINITY],
            input_types=["protein_sequence", "smiles"],
            output_types=["structure", "affinity", "confidence"],
            gpu_required=True,
            gpu_memory_gb=40,
            max_batch_size=1,
            estimated_runtime_minutes=30,
            citation="Boltz-2 model for biomolecular structure prediction",
            url="https://github.com/example/boltz2"
        )
        self.register_model(boltz2_metadata)
        
        # ESMFold for protein structure prediction
        esmfold_metadata = ModelMetadata(
            name="esmfold",
            version="1.0.0",
            description="ESMFold model for protein structure prediction",
            tasks=[PredictionTask.PROTEIN_STRUCTURE],
            capabilities=[ModelCapability.STRUCTURE_PREDICTION],
            input_types=["protein_sequence"],
            output_types=["structure", "confidence"],
            gpu_required=True,
            gpu_memory_gb=16,
            max_batch_size=4,
            estimated_runtime_minutes=10,
            citation="ESMFold: Fast and accurate protein structure prediction",
            url="https://github.com/facebookresearch/esm"
        )
        self.register_model(esmfold_metadata)
        
        # AlphaFold2 for protein structure prediction
        alphafold2_metadata = ModelMetadata(
            name="alphafold2",
            version="2.3.0",
            description="AlphaFold2 model for high-accuracy protein structure prediction",
            tasks=[PredictionTask.PROTEIN_STRUCTURE],
            capabilities=[ModelCapability.STRUCTURE_PREDICTION],
            input_types=["protein_sequence"],
            output_types=["structure", "confidence"],
            gpu_required=True,
            gpu_memory_gb=40,
            max_batch_size=1,
            estimated_runtime_minutes=120,
            citation="Highly accurate protein structure prediction with AlphaFold",
            url="https://github.com/deepmind/alphafold"
        )
        self.register_model(alphafold2_metadata)
        
        # ColabFold for protein complex prediction
        colabfold_metadata = ModelMetadata(
            name="colabfold",
            version="1.5.0",
            description="ColabFold model for protein complex structure prediction",
            tasks=[PredictionTask.PROTEIN_COMPLEX],
            capabilities=[ModelCapability.STRUCTURE_PREDICTION],
            input_types=["protein_sequence"],
            output_types=["structure", "confidence"],
            gpu_required=True,
            gpu_memory_gb=40,
            max_batch_size=1,
            estimated_runtime_minutes=45,
            citation="ColabFold: making protein folding accessible to all",
            url="https://github.com/deepmind/alphafold"
        )
        self.register_model(colabfold_metadata)
        
        # CASTp for binding site prediction
        castp_metadata = ModelMetadata(
            name="castp",
            version="3.0",
            description="CASTp model for binding site and cavity prediction",
            tasks=[PredictionTask.BINDING_SITE_PREDICTION],
            capabilities=[ModelCapability.CAVITY_DETECTION],
            input_types=["pdb"],
            output_types=["binding_sites", "cavities"],
            gpu_required=False,
            gpu_memory_gb=0,
            max_batch_size=10,
            estimated_runtime_minutes=5,
            citation="CASTp 3.0: computed atlas of surface topography of proteins",
            url="http://sts.bioe.uic.edu/castp/"
        )
        self.register_model(castp_metadata)
    
    def register_model(self, metadata: ModelMetadata):
        """Register a new model"""
        self.models[metadata.name] = metadata
        
        # Index by tasks
        for task in metadata.tasks:
            if task not in self.task_models:
                self.task_models[task] = []
            if metadata.name not in self.task_models[task]:
                self.task_models[task].append(metadata.name)
    
    def get_model(self, name: str) -> Optional[ModelMetadata]:
        """Get model metadata by name"""
        return self.models.get(name)
    
    def get_models_for_task(self, task: PredictionTask) -> List[ModelMetadata]:
        """Get all models that support a specific task"""
        model_names = self.task_models.get(task, [])
        return [self.models[name] for name in model_names if name in self.models]
    
    def get_available_tasks(self) -> List[PredictionTask]:
        """Get all available prediction tasks"""
        return list(self.task_models.keys())
    
    def get_task_requirements(self, task: PredictionTask) -> Dict[str, Any]:
        """Get input requirements for a task"""
        return TaskWorkflow.get_required_inputs(task)
    
    def get_task_workflow(self, task: PredictionTask) -> List[str]:
        """Get workflow steps for a task"""
        return TaskWorkflow.get_workflow_steps(task)
    
    def validate_task_inputs(self, task: PredictionTask, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate inputs for a specific task"""
        requirements = self.get_task_requirements(task)
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        for field_name, field_spec in requirements.items():
            if field_spec.get("required", False) and field_name not in inputs:
                validation_results["valid"] = False
                validation_results["errors"].append(f"Required field '{field_name}' is missing")
            
            if field_name in inputs:
                value = inputs[field_name]
                field_type = field_spec.get("type", "string")
                
                # Basic type validation
                if field_type == "string" and not isinstance(value, str):
                    validation_results["valid"] = False
                    validation_results["errors"].append(f"Field '{field_name}' must be a string")
                elif field_type == "array" and not isinstance(value, list):
                    validation_results["valid"] = False
                    validation_results["errors"].append(f"Field '{field_name}' must be an array")
        
        return validation_results
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about registered models"""
        stats = {
            "total_models": len(self.models),
            "models_by_task": {},
            "gpu_required_models": 0,
            "average_runtime": 0
        }
        
        for task in PredictionTask:
            models = self.get_models_for_task(task)
            stats["models_by_task"][task.value] = len(models)
        
        gpu_models = [m for m in self.models.values() if m.gpu_required]
        stats["gpu_required_models"] = len(gpu_models)
        
        if self.models:
            total_runtime = sum(m.estimated_runtime_minutes for m in self.models.values())
            stats["average_runtime"] = total_runtime / len(self.models)
        
        return stats

# Global registry instance
model_registry = EnhancedModelRegistry()

# Export for backward compatibility
def get_available_models():
    """Get all available models (backward compatibility)"""
    return list(model_registry.models.keys())

def get_model_info(model_name: str):
    """Get model information (backward compatibility)"""
    model = model_registry.get_model(model_name)
    if model:
        return {
            "name": model.name,
            "version": model.version,
            "description": model.description,
            "gpu_required": model.gpu_required,
            "estimated_runtime": model.estimated_runtime_minutes
        }
    return None 