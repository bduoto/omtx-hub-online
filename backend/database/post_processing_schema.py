"""
Database schema extensions for Boltz-2 post-processing results.
Adds derived scientific metrics while maintaining backward compatibility.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class PostProcessingSchema:
    """
    Manages database schema for post-processed Boltz-2 results.
    
    Extends existing job records with derived scientific metrics:
    - Protein-ligand contact analysis
    - Binding mode clustering
    - Chemical scaffold diversity
    - Hotspot residue aggregation
    """
    
    @staticmethod
    def get_job_extensions() -> Dict[str, str]:
        """
        Returns field extensions for job records.
        These should be added to your existing job collection/table.
        """
        return {
            # Post-processing results
            "contacts_json": "TEXT",  # JSON array of contacted residues
            "contact_count": "INTEGER",  # Number of unique residues contacted
            "cluster_id": "INTEGER",  # Binding mode cluster assignment
            "cluster_label": "VARCHAR(100)",  # Human-readable cluster label
            "scaffold_smiles": "VARCHAR(500)",  # Bemis-Murcko scaffold
            "ensemble_sd_calculated": "FLOAT",  # Calculated ensemble standard deviation
            
            # Processing metadata
            "post_processed_at": "TIMESTAMP",  # When post-processing completed
            "post_processing_version": "VARCHAR(50)",  # Version of post-processor
            "post_processing_success": "BOOLEAN",  # Whether post-processing succeeded
            "post_processing_error": "TEXT",  # Error message if failed
            
            # Structure analysis metadata
            "ligand_atoms": "INTEGER",  # Number of ligand atoms
            "protein_atoms": "INTEGER",  # Number of protein atoms
            "contact_cutoff": "FLOAT"  # Distance cutoff used for contacts
        }
    
    @staticmethod
    def get_batch_analysis_schema() -> Dict[str, str]:
        """
        Returns schema for batch-level analysis results.
        This should be a separate collection/table.
        """
        return {
            "batch_id": "VARCHAR(255) PRIMARY KEY",
            "hotspot_residues": "JSON",  # Top hotspot residues with percentages
            "binding_mode_counts": "JSON",  # Counts per binding mode category
            "scaffold_diversity": "JSON",  # Chemical diversity metrics
            "cluster_summary": "JSON",  # Clustering analysis summary
            "total_jobs": "INTEGER",  # Total jobs in batch
            "processed_jobs": "INTEGER",  # Successfully processed jobs
            "processing_completed_at": "TIMESTAMP",
            "processing_version": "VARCHAR(50)"
        }

class JobPostProcessingModel:
    """
    Data model for individual job post-processing results.
    Compatible with both SQL and NoSQL backends.
    """
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.contacts_json: Optional[str] = None
        self.contact_count: int = 0
        self.cluster_id: Optional[int] = None
        self.cluster_label: Optional[str] = None
        self.scaffold_smiles: Optional[str] = None
        self.ensemble_sd_calculated: float = 0.0
        self.post_processed_at: Optional[datetime] = None
        self.post_processing_version: str = "1.0"
        self.post_processing_success: bool = False
        self.post_processing_error: Optional[str] = None
        self.ligand_atoms: int = 0
        self.protein_atoms: int = 0
        self.contact_cutoff: float = 4.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "job_id": self.job_id,
            "contacts_json": self.contacts_json,
            "contact_count": self.contact_count,
            "cluster_id": self.cluster_id,
            "cluster_label": self.cluster_label,
            "scaffold_smiles": self.scaffold_smiles,
            "ensemble_sd_calculated": self.ensemble_sd_calculated,
            "post_processed_at": self.post_processed_at.isoformat() if self.post_processed_at else None,
            "post_processing_version": self.post_processing_version,
            "post_processing_success": self.post_processing_success,
            "post_processing_error": self.post_processing_error,
            "ligand_atoms": self.ligand_atoms,
            "protein_atoms": self.protein_atoms,
            "contact_cutoff": self.contact_cutoff
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobPostProcessingModel':
        """Create from dictionary (database record)"""
        instance = cls(data["job_id"])
        for key, value in data.items():
            if hasattr(instance, key):
                if key == "post_processed_at" and isinstance(value, str):
                    instance.post_processed_at = datetime.fromisoformat(value)
                else:
                    setattr(instance, key, value)
        return instance

class BatchAnalysisModel:
    """
    Data model for batch-level analysis results.
    """
    
    def __init__(self, batch_id: str):
        self.batch_id = batch_id
        self.hotspot_residues: List[Dict] = []
        self.binding_mode_counts: Dict[str, int] = {}
        self.scaffold_diversity: Dict[str, Any] = {}
        self.cluster_summary: Dict[str, Any] = {}
        self.total_jobs: int = 0
        self.processed_jobs: int = 0
        self.processing_completed_at: Optional[datetime] = None
        self.processing_version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "batch_id": self.batch_id,
            "hotspot_residues": json.dumps(self.hotspot_residues),
            "binding_mode_counts": json.dumps(self.binding_mode_counts),
            "scaffold_diversity": json.dumps(self.scaffold_diversity),
            "cluster_summary": json.dumps(self.cluster_summary),
            "total_jobs": self.total_jobs,
            "processed_jobs": self.processed_jobs,
            "processing_completed_at": self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            "processing_version": self.processing_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchAnalysisModel':
        """Create from dictionary (database record)"""
        instance = cls(data["batch_id"])
        
        # Parse JSON fields
        json_fields = ["hotspot_residues", "binding_mode_counts", "scaffold_diversity", "cluster_summary"]
        for field in json_fields:
            if field in data and data[field]:
                try:
                    setattr(instance, field, json.loads(data[field]))
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Could not parse {field} for batch {data['batch_id']}")
        
        # Set simple fields
        for key, value in data.items():
            if hasattr(instance, key) and key not in json_fields:
                if key == "processing_completed_at" and isinstance(value, str):
                    instance.processing_completed_at = datetime.fromisoformat(value)
                else:
                    setattr(instance, key, value)
        
        return instance

# GCP Firestore integration helpers
class FirestorePostProcessingService:
    """
    Service for storing post-processing results in GCP Firestore.
    Extends existing unified_job_manager functionality.
    """
    
    def __init__(self, firestore_client):
        self.db = firestore_client
        self.jobs_collection = "jobs"
        self.batch_analysis_collection = "batch_analysis"
    
    async def store_job_post_processing(self, job_id: str, results: Dict[str, Any]) -> bool:
        """
        Store post-processing results for a single job.
        Updates existing job document with new fields.
        """
        try:
            job_ref = self.db.collection(self.jobs_collection).document(job_id)
            
            # Create post-processing model
            model = JobPostProcessingModel(job_id)
            model.contacts_json = results.get("contacts_json")
            model.contact_count = results.get("contact_count", 0)
            model.ensemble_sd_calculated = results.get("ensemble_sd", 0.0)
            model.post_processed_at = datetime.now()
            model.post_processing_success = results.get("success", False)
            model.post_processing_error = results.get("error")
            model.ligand_atoms = results.get("ligand_atoms", 0)
            model.protein_atoms = results.get("protein_atoms", 0)
            
            # Update job document
            update_data = {k: v for k, v in model.to_dict().items() if k != "job_id"}
            await job_ref.update(update_data)
            
            logger.info(f"Stored post-processing results for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store post-processing results for job {job_id}: {e}")
            return False
    
    async def store_batch_analysis(self, batch_id: str, analysis_results: Dict[str, Any]) -> bool:
        """
        Store batch-level analysis results.
        """
        try:
            batch_ref = self.db.collection(self.batch_analysis_collection).document(batch_id)
            
            # Create batch analysis model
            model = BatchAnalysisModel(batch_id)
            model.hotspot_residues = analysis_results.get("hotspot_residues", [])
            model.binding_mode_counts = analysis_results.get("binding_modes", {})
            model.scaffold_diversity = analysis_results.get("scaffold_diversity", {})
            model.cluster_summary = analysis_results.get("cluster_summary", {})
            model.total_jobs = analysis_results.get("total_jobs", 0)
            model.processed_jobs = analysis_results.get("processed_jobs", 0)
            model.processing_completed_at = datetime.now()
            
            # Store batch analysis
            await batch_ref.set(model.to_dict())
            
            logger.info(f"Stored batch analysis for batch {batch_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store batch analysis for batch {batch_id}: {e}")
            return False
    
    async def get_batch_analysis(self, batch_id: str) -> Optional[BatchAnalysisModel]:
        """
        Retrieve batch analysis results.
        """
        try:
            batch_ref = self.db.collection(self.batch_analysis_collection).document(batch_id)
            doc = await batch_ref.get()
            
            if doc.exists:
                return BatchAnalysisModel.from_dict(doc.to_dict())
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve batch analysis for batch {batch_id}: {e}")
            return None

# Migration script for existing databases
FIRESTORE_MIGRATION_SCRIPT = """
# Add these fields to existing job documents:
# This can be done gradually as jobs are post-processed

# For each job document, add:
{
    "contacts_json": null,
    "contact_count": 0,
    "cluster_id": null,
    "cluster_label": null,
    "scaffold_smiles": null,
    "ensemble_sd_calculated": 0.0,
    "post_processed_at": null,
    "post_processing_version": "1.0",
    "post_processing_success": false,
    "post_processing_error": null,
    "ligand_atoms": 0,
    "protein_atoms": 0,
    "contact_cutoff": 4.0
}

# Create new collection: batch_analysis
# Documents will be created as batches are processed
"""