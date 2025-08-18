"""
Scaling configuration for OMTX-Hub
Optimized for 80+ models with proper resource management
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ModelConfig:
    """Configuration for individual models"""
    model_id: str
    gpu_type: str = "A100-40GB"
    max_concurrent: int = 3
    timeout_seconds: int = 1800  # 30 minutes
    memory_gb: int = 32
    cpu_cores: int = 8
    warm_containers: int = 0
    auto_scaling: bool = True
    max_containers: int = 10

@dataclass
class ScalingConfig:
    """Global scaling configuration"""
    # Database
    max_db_connections: int = 100
    connection_pool_size: int = 20
    db_timeout: int = 30
    
    # Caching
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 3600  # 1 hour
    model_cache_size: int = 1000
    
    # Load Balancing
    max_requests_per_second: int = 1000
    rate_limit_window: int = 60  # seconds
    max_jobs_per_user: int = 10
    max_jobs_per_org: int = 100
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 30  # seconds
    
    # Resource Management
    max_gpu_utilization: float = 0.8
    max_memory_utilization: float = 0.9
    auto_scale_threshold: float = 0.7

class ModelRegistryConfig:
    """Configuration for model registry"""
    
    # Model categories for organization
    CATEGORIES = {
        "Structure Prediction": [
            "Boltz-2", "AlphaFold2", "ESMFold", "OmegaFold",
            "ColabFold", "RoseTTAFold", "I-TASSER"
        ],
        "Protein Design": [
            "ProteinMPNN", "ESM-IF1", "RFDiffusion", "Chroma",
            "ProteinSGM", "DiffDock", "EquiBind"
        ],
        "Docking": [
            "DiffDock", "EquiBind", "TankBind", "GLIDE",
            "AutoDock", "Vina", "GOLD"
        ],
        "Affinity Prediction": [
            "Boltz-2", "DeepDTA", "DeepAffinity", "Pafnucy",
            "AtomNet", "OnionNet", "DeepBind"
        ],
        "Sequence Analysis": [
            "ESM-2", "ProtBERT", "TAPE", "UniRep",
            "SeqVec", "Bepler", "ResNet"
        ]
    }
    
    # GPU requirements by model type
    GPU_REQUIREMENTS = {
        "Structure Prediction": "A100-40GB",
        "Protein Design": "A100-40GB", 
        "Docking": "A100-40GB",
        "Affinity Prediction": "A100-40GB",
        "Sequence Analysis": "V100-16GB"
    }
    
    # Default configurations
    DEFAULT_CONFIGS = {
        "Boltz-2": ModelConfig(
            model_id="Boltz-2_1.0.0",
            gpu_type="A100-40GB",
            max_concurrent=3,
            timeout_seconds=1800,
            memory_gb=32,
            cpu_cores=8
        ),
        "AlphaFold2": ModelConfig(
            model_id="AlphaFold2_2.3.2",
            gpu_type="A100-40GB", 
            max_concurrent=2,
            timeout_seconds=3600,
            memory_gb=64,
            cpu_cores=16
        ),
        "ESMFold": ModelConfig(
            model_id="ESMFold_1.0.0",
            gpu_type="A100-40GB",
            max_concurrent=4,
            timeout_seconds=900,
            memory_gb=24,
            cpu_cores=8
        )
    }

class CacheConfig:
    """Caching configuration for performance"""
    
    # Cache keys
    MODEL_METADATA_CACHE = "model:metadata:{model_id}"
    PREDICTION_RESULT_CACHE = "prediction:result:{job_id}"
    USER_QUOTA_CACHE = "user:quota:{user_id}"
    ORG_QUOTA_CACHE = "org:quota:{org_id}"
    
    # Cache TTLs
    MODEL_METADATA_TTL = 3600  # 1 hour
    PREDICTION_RESULT_TTL = 86400  # 24 hours
    USER_QUOTA_TTL = 300  # 5 minutes
    ORG_QUOTA_TTL = 300  # 5 minutes

class MonitoringConfig:
    """Monitoring and metrics configuration"""
    
    # Metrics names
    METRICS = {
        "prediction_requests_total": "Total prediction requests",
        "prediction_duration_seconds": "Prediction duration in seconds",
        "model_usage_count": "Model usage count",
        "gpu_utilization": "GPU utilization percentage",
        "memory_utilization": "Memory utilization percentage",
        "active_jobs": "Number of active jobs",
        "failed_jobs": "Number of failed jobs"
    }
    
    # Alert thresholds
    ALERTS = {
        "high_gpu_utilization": 0.9,
        "high_memory_utilization": 0.95,
        "high_error_rate": 0.05,
        "long_prediction_time": 3600  # 1 hour
    }

# Environment-based configuration
def get_scaling_config() -> ScalingConfig:
    """Get scaling configuration from environment"""
    return ScalingConfig(
        max_db_connections=int(os.getenv("MAX_DB_CONNECTIONS", "100")),
        connection_pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        max_requests_per_second=int(os.getenv("MAX_RPS", "1000")),
        enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true"
    )

def get_model_config(model_id: str) -> Optional[ModelConfig]:
    """Get configuration for specific model"""
    return ModelRegistryConfig.DEFAULT_CONFIGS.get(model_id)

def get_gpu_requirement(category: str) -> str:
    """Get GPU requirement for model category"""
    return ModelRegistryConfig.GPU_REQUIREMENTS.get(category, "A100-40GB") 