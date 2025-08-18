"""
Parent-Level Batch Results Schema

Simple, fast batch results structure for efficient lookups.
Stored at: hub-job-files/batches/{batch_id}/batch_results.json
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class JobResult(BaseModel):
    """Individual job result - comprehensive field set for table display"""
    job_id: str
    ligand_name: str  # Sequential: "1", "2", "3", etc.
    ligand_smiles: str
    affinity: Optional[float] = None  # Primary affinity
    confidence: Optional[float] = None  # Primary confidence
    has_results: bool = False  # Quick boolean check
    has_structure: bool = False  # Structure file available
    status: str = "failed"  # "completed", "failed", "running"
    
    # COMPREHENSIVE TABLE FIELDS matching frontend requirements
    affinity_prob: Optional[float] = None      # Affinity Prob
    ens_affinity: Optional[float] = None       # Ens. Affinity
    ens_prob: Optional[float] = None           # Ens. Prob
    ens_aff_2: Optional[float] = None          # Ens. Aff 2
    ens_prob_2: Optional[float] = None         # Ens. Prob 2
    ens_aff_1: Optional[float] = None          # Ens. Aff 1
    ens_prob_1: Optional[float] = None         # Ens. Prob 1
    iptm_score: Optional[float] = None         # iPTM
    ligand_iptm: Optional[float] = None        # Ligand iPTM
    complex_iplddt: Optional[float] = None     # Complex ipLDDT
    complex_ipde: Optional[float] = None       # Complex iPDE
    complex_plddt: Optional[float] = None      # Complex pLDDT
    ptm_score: Optional[float] = None          # PTM
    plddt_score: Optional[float] = None        # For backward compatibility

class BatchResultsSummary(BaseModel):
    """Batch-level summary statistics"""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    running_jobs: int
    success_rate: float
    mean_affinity: Optional[float] = None  # Mean of non-null affinities
    mean_confidence: Optional[float] = None  # Mean of non-null confidences
    best_affinity: Optional[float] = None
    worst_affinity: Optional[float] = None

class ParentBatchResults(BaseModel):
    """Parent-level batch results for fast API lookups"""
    
    # Metadata
    batch_id: str
    created_at: datetime
    updated_at: datetime
    version: str = "1.0"  # Schema version for future compatibility
    
    # Job results - all jobs included (with nulls for failed)
    jobs: List[JobResult]
    
    # Summary statistics
    summary: BatchResultsSummary
    
    # Quick lookup maps for API efficiency
    job_count: int  # Total jobs
    completed_count: int  # Jobs with actual results
    
    # Optional: Pre-computed rankings for dashboard
    top_predictions: List[JobResult] = []  # Top 10 by affinity
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

def create_batch_results_from_jobs(
    batch_id: str,
    job_results: List[Dict[str, Any]],
    created_at: Optional[datetime] = None
) -> ParentBatchResults:
    """Create parent batch results from individual job data"""
    
    if created_at is None:
        created_at = datetime.utcnow()
    
    # Convert to JobResult objects
    jobs = []
    completed_jobs = 0
    affinities = []
    confidences = []
    
    for job_data in job_results:
        job_result = JobResult(
            job_id=job_data['job_id'],
            ligand_name=job_data.get('ligand_name', f"Ligand {len(jobs) + 1}"),
            ligand_smiles=job_data.get('ligand_smiles', ''),
            affinity=job_data.get('affinity'),
            confidence=job_data.get('confidence'),
            has_results=job_data.get('has_results', False),
            has_structure=job_data.get('has_structure', False),
            status=job_data.get('status', 'failed'),
            
            # COMPREHENSIVE TABLE FIELDS - extract from BatchFileScanner output
            affinity_prob=job_data.get('affinity_prob'),
            ens_affinity=job_data.get('ens_affinity'),
            ens_prob=job_data.get('ens_prob'),
            ens_aff_2=job_data.get('ens_aff_2'),
            ens_prob_2=job_data.get('ens_prob_2'),
            ens_aff_1=job_data.get('ens_aff_1'),
            ens_prob_1=job_data.get('ens_prob_1'),
            iptm_score=job_data.get('iptm_score'),
            ligand_iptm=job_data.get('ligand_iptm'),
            complex_iplddt=job_data.get('complex_iplddt'),
            complex_ipde=job_data.get('complex_ipde'),
            complex_plddt=job_data.get('complex_plddt'),
            ptm_score=job_data.get('ptm_score'),
            plddt_score=job_data.get('plddt_score')
        )
        
        jobs.append(job_result)
        
        if job_result.has_results:
            completed_jobs += 1
            if job_result.affinity is not None:
                affinities.append(job_result.affinity)
            if job_result.confidence is not None:
                confidences.append(job_result.confidence)
    
    # Calculate summary statistics
    total_jobs = len(jobs)
    failed_jobs = total_jobs - completed_jobs
    running_jobs = 0  # For now, assume all are either completed or failed
    
    summary = BatchResultsSummary(
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        running_jobs=running_jobs,
        success_rate=completed_jobs / total_jobs if total_jobs > 0 else 0.0,
        mean_affinity=sum(affinities) / len(affinities) if affinities else None,
        mean_confidence=sum(confidences) / len(confidences) if confidences else None,
        best_affinity=max(affinities) if affinities else None,
        worst_affinity=min(affinities) if affinities else None
    )
    
    # Get top predictions (by affinity)
    jobs_with_affinity = [j for j in jobs if j.affinity is not None]
    top_predictions = sorted(jobs_with_affinity, key=lambda x: x.affinity, reverse=True)[:10]
    
    return ParentBatchResults(
        batch_id=batch_id,
        created_at=created_at,
        updated_at=datetime.utcnow(),
        jobs=jobs,
        summary=summary,
        job_count=total_jobs,
        completed_count=completed_jobs,
        top_predictions=top_predictions
    )