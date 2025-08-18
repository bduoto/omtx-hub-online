"""
Job Classifier Service
Centralized logic for classifying and identifying job types
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class JobType(str, Enum):
    """Job type classifications"""
    INDIVIDUAL = "individual"
    BATCH_PARENT = "batch_parent"
    BATCH_CHILD = "batch_child"

class JobClassifier:
    """Centralized job type classification logic"""
    
    # Define all batch task types
    BATCH_TASK_TYPES = {
        'batch_protein_ligand_screening',
        'batch_antibody_optimization',
        'batch_variant_analysis',
        'batch_drug_discovery',
        'batch_structure_prediction'
    }
    
    # Task types that are always individual (never batch)
    INDIVIDUAL_ONLY_TASK_TYPES = {
        'protein_protein_complex',
        'multimer_prediction',
        'nanobody_design',
        'cdr_optimization',
        'epitope_targeted_design',
        'antibody_de_novo_design'
    }
    
    @staticmethod
    def is_batch_job(job: Dict[str, Any]) -> bool:
        """
        Definitive batch job identification
        Returns True if job is a batch parent
        """
        # Check explicit batch task types
        if job.get('task_type') in JobClassifier.BATCH_TASK_TYPES:
            return True
        
        # Check if job is in batches/ folder (GCP bucket structure)
        bucket_path = job.get('bucket_path', '')
        if bucket_path.startswith('batches/'):
            return True
        
        # Check explicit batch flags
        if job.get('is_batch_job', False) or job.get('is_batch_parent', False):
            return True
        
        # Check for child jobs
        if job.get('child_job_ids') and len(job.get('child_job_ids', [])) > 0:
            return True
        
        # Check for batch metadata
        if job.get('total_children', 0) > 0:
            return True
        
        # Check for batch-specific fields
        if job.get('individual_jobs') or job.get('individual_job_ids'):
            return True
        
        # Check batch info structure
        batch_info = job.get('batch_info', {})
        if batch_info.get('is_batch') or batch_info.get('total_ligands', 0) > 0:
            return True
        
        return False
    
    @staticmethod
    def is_batch_child(job: Dict[str, Any]) -> bool:
        """
        Check if job is a child of a batch
        """
        # Check explicit batch child flags
        if job.get('is_batch_child', False):
            return True
        
        # Check for parent batch reference
        if job.get('batch_id') or job.get('parent_batch_id'):
            return True
        
        # Check for batch index (child jobs have an index within the batch)
        if 'batch_index' in job and job.get('batch_index') is not None:
            return True
        
        return False
    
    @staticmethod
    def classify_job(job: Dict[str, Any]) -> JobType:
        """
        Returns job classification: 'individual', 'batch_parent', or 'batch_child'
        """
        # First check if it's a batch child
        if JobClassifier.is_batch_child(job):
            return JobType.BATCH_CHILD
        
        # Then check if it's a batch parent
        if JobClassifier.is_batch_job(job):
            return JobType.BATCH_PARENT
        
        # Otherwise it's an individual job
        return JobType.INDIVIDUAL
    
    @staticmethod
    def extract_batch_metadata(job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract batch-specific metadata from a job
        """
        if not JobClassifier.is_batch_job(job):
            return {}
        
        metadata = {
            'batch_id': job.get('id') or job.get('job_id'),
            'batch_type': job.get('task_type'),
            'total_children': 0,
            'completed_children': 0,
            'failed_children': 0,
            'child_job_ids': []
        }
        
        # Extract child counts
        if job.get('total_children'):
            metadata['total_children'] = job['total_children']
        elif job.get('individual_jobs'):
            metadata['total_children'] = len(job['individual_jobs'])
        elif job.get('individual_job_ids'):
            metadata['total_children'] = len(job['individual_job_ids'])
        elif job.get('batch_info', {}).get('total_ligands'):
            metadata['total_children'] = job['batch_info']['total_ligands']
        
        # Extract completion status
        metadata['completed_children'] = job.get('completed_children', 0) or \
                                        job.get('completed_jobs', 0) or \
                                        job.get('batch_info', {}).get('completed', 0)
        
        metadata['failed_children'] = job.get('failed_children', 0) or \
                                     job.get('failed_jobs', 0) or \
                                     job.get('batch_info', {}).get('failed', 0)
        
        # Extract child IDs if available
        metadata['child_job_ids'] = job.get('individual_job_ids', []) or \
                                   job.get('child_job_ids', []) or \
                                   [j.get('job_id') for j in job.get('individual_jobs', []) if j.get('job_id')]
        
        return metadata
    
    @staticmethod
    def filter_jobs_by_type(jobs: List[Dict[str, Any]], job_type: JobType) -> List[Dict[str, Any]]:
        """
        Filter a list of jobs by type
        """
        filtered = []
        for job in jobs:
            classification = JobClassifier.classify_job(job)
            if classification == job_type:
                filtered.append(job)
        
        return filtered
    
    @staticmethod
    def separate_jobs(jobs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Separate jobs into categories
        Returns dict with keys: 'individual', 'batch_parent', 'batch_child'
        """
        separated = {
            JobType.INDIVIDUAL: [],
            JobType.BATCH_PARENT: [],
            JobType.BATCH_CHILD: []
        }
        
        for job in jobs:
            classification = JobClassifier.classify_job(job)
            separated[classification].append(job)
        
        return separated
    
    @staticmethod
    def enhance_job_with_type(job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add job type classification to job data
        """
        classification = JobClassifier.classify_job(job)
        job['_job_classification'] = classification.value
        
        if classification == JobType.BATCH_PARENT:
            job['_batch_metadata'] = JobClassifier.extract_batch_metadata(job)
        
        return job
    
    @staticmethod
    def get_display_name(job: Dict[str, Any]) -> str:
        """
        Get appropriate display name based on job type
        """
        classification = JobClassifier.classify_job(job)
        base_name = job.get('job_name', '') or job.get('name', '') or f"Job {job.get('id', '')[:8]}"
        
        if classification == JobType.BATCH_PARENT:
            batch_meta = JobClassifier.extract_batch_metadata(job)
            total = batch_meta.get('total_children', 0)
            if total > 0:
                return f"{base_name} (Batch of {total})"
            return f"{base_name} (Batch)"
        
        elif classification == JobType.BATCH_CHILD:
            batch_id = job.get('batch_id', '')[:8] if job.get('batch_id') else 'batch'
            index = job.get('batch_index', '?')
            return f"{base_name} [Child {index} of {batch_id}]"
        
        return base_name

# Global instance for convenience
job_classifier = JobClassifier()