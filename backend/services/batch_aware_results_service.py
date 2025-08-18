"""
Batch-Aware Results Service
Integrates batch job relationships with My Results for hierarchical display
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from services.gcp_results_indexer_optimized import streamlined_gcp_results_indexer
from services.batch_relationship_manager import batch_relationship_manager

logger = logging.getLogger(__name__)

class BatchAwareResultsService:
    """Enhanced results service that understands batch job hierarchies"""
    
    def __init__(self):
        self.batch_cache = {}  # Cache for batch summaries
    
    async def get_user_results_with_batches(
        self, 
        user_id: str = "current_user", 
        limit: int = 50, 
        page: int = 1, 
        filters: Optional[Dict] = None,
        group_batches: bool = True
    ) -> Dict[str, Any]:
        """Get user results with batch job grouping and hierarchy"""
        
        try:
            # Get base results from optimized indexer
            base_results = await streamlined_gcp_results_indexer.get_user_results_optimized(
                user_id=user_id,
                limit=limit * 2,  # Get more to account for grouping
                page=page,
                filters=filters
            )
            
            if not group_batches:
                return base_results
            
            # Separate individual jobs from batch jobs
            individual_jobs = []
            batch_jobs = []
            batch_parent_ids = set()
            
            for result in base_results.get('results', []):
                task_type = result.get('task_type', '')
                job_id = result.get('job_id', '')
                
                if 'batch' in task_type.lower():
                    # This is a batch job
                    batch_jobs.append(result)
                    batch_parent_ids.add(job_id)
                else:
                    # Check if this is a child of a batch
                    parent_batch_id = await self._find_parent_batch(job_id)
                    if parent_batch_id and parent_batch_id in batch_parent_ids:
                        # This is a child job, will be grouped under parent
                        continue
                    else:
                        # This is an individual job
                        individual_jobs.append(result)
            
            # Enhance batch jobs with child information
            enhanced_batch_jobs = []
            for batch_job in batch_jobs:
                enhanced_batch = await self._enhance_batch_job(batch_job)
                enhanced_batch_jobs.append(enhanced_batch)
            
            # Combine and sort results
            all_results = individual_jobs + enhanced_batch_jobs
            all_results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Apply final pagination
            start_idx = 0  # We already got the right page from indexer
            end_idx = limit
            paginated_results = all_results[start_idx:end_idx]
            
            return {
                **base_results,
                'results': paginated_results,
                'grouping_info': {
                    'individual_jobs': len(individual_jobs),
                    'batch_jobs': len(enhanced_batch_jobs),
                    'grouped': group_batches,
                    'total_before_grouping': len(base_results.get('results', []))
                },
                'batch_aware': True
            }
            
        except Exception as e:
            logger.error(f"❌ Batch-aware results failed for {user_id}: {e}")
            
            # Fallback to regular results
            return await streamlined_gcp_results_indexer.get_user_results_optimized(
                user_id=user_id, limit=limit, page=page, filters=filters
            )
    
    async def _find_parent_batch(self, job_id: str) -> Optional[str]:
        """Find if a job is a child of a batch"""
        
        try:
            # This would need to be implemented based on how batch relationships are stored
            # For now, we can check if the job_id appears in any batch index files
            # This is a simplified implementation
            return None
            
        except Exception as e:
            logger.debug(f"Could not find parent batch for {job_id}: {e}")
            return None
    
    async def _enhance_batch_job(self, batch_job: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance batch job with child job information and summary"""
        
        try:
            batch_id = batch_job.get('job_id', '')
            
            # Get batch results with child information
            batch_results = await batch_relationship_manager.get_batch_results(batch_id)
            
            if not batch_results:
                return batch_job
            
            # Enhance the batch job with summary information
            enhanced_batch = batch_job.copy()
            
            # Add batch summary to the job
            summary = batch_results.get('summary', {})
            individual_results = batch_results.get('individual_results', [])
            
            enhanced_batch['batch_info'] = {
                'is_batch': True,
                'total_ligands': summary.get('total_ligands', 0),
                'completed_jobs': summary.get('completed_jobs', 0),
                'failed_jobs': summary.get('failed_jobs', 0),
                'success_rate': summary.get('success_rate', 0),
                'top_affinity': summary.get('top_affinity', 0),
                'avg_affinity': summary.get('avg_affinity', 0),
                'child_count': len(individual_results),
                'batch_status': batch_results.get('status', 'unknown')
            }
            
            # Add preview of top results
            top_results = sorted(
                [r for r in individual_results if r.get('results', {}).get('affinity')],
                key=lambda x: x['results']['affinity'],
                reverse=True
            )[:3]
            
            enhanced_batch['batch_info']['top_results_preview'] = [
                {
                    'ligand_name': r.get('metadata', {}).get('ligand_name', 'Unknown'),
                    'affinity': r.get('results', {}).get('affinity'),
                    'confidence': r.get('results', {}).get('confidence')
                }
                for r in top_results
            ]
            
            # Update display name to include batch info
            original_name = enhanced_batch.get('job_name', 'Batch Job')
            enhanced_batch['job_name'] = f"{original_name} ({summary.get('total_ligands', 0)} ligands)"
            
            return enhanced_batch
            
        except Exception as e:
            logger.warning(f"Could not enhance batch job {batch_job.get('job_id', 'unknown')}: {e}")
            return batch_job
    
    async def get_batch_hierarchy(self, batch_id: str) -> Dict[str, Any]:
        """Get complete batch hierarchy for detailed view"""
        
        try:
            batch_results = await batch_relationship_manager.get_batch_results(batch_id)
            
            if not batch_results:
                return {'error': 'Batch not found'}
            
            # Format for hierarchical display
            hierarchy = {
                'batch_id': batch_id,
                'batch_metadata': batch_results.get('metadata', {}),
                'batch_status': batch_results.get('status', 'unknown'),
                'summary': batch_results.get('summary', {}),
                'children': []
            }
            
            # Format child jobs
            for result in batch_results.get('individual_results', []):
                child = {
                    'job_id': result.get('job_id'),
                    'ligand_name': result.get('metadata', {}).get('ligand_name', 'Unknown'),
                    'ligand_smiles': result.get('metadata', {}).get('ligand_smiles', ''),
                    'status': 'completed' if result.get('results') else 'failed',
                    'affinity': result.get('results', {}).get('affinity'),
                    'confidence': result.get('results', {}).get('confidence'),
                    'has_structure': bool(result.get('results', {}).get('structure_file_base64'))
                }
                hierarchy['children'].append(child)
            
            # Sort children by affinity (best first)
            hierarchy['children'].sort(
                key=lambda x: x.get('affinity', float('-inf')), 
                reverse=True
            )
            
            return hierarchy
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch hierarchy for {batch_id}: {e}")
            return {'error': str(e)}
    
    async def get_batch_status_summary(self, user_id: str = "current_user") -> Dict[str, Any]:
        """Get summary of all batch jobs for user"""
        
        try:
            # Get user results
            results = await streamlined_gcp_results_indexer.get_user_results_optimized(
                user_id=user_id,
                limit=100,  # Get more to analyze batches
                filters={'task_type': 'batch_protein_ligand_screening'}
            )
            
            batch_summaries = []
            total_ligands = 0
            total_completed = 0
            total_failed = 0
            
            for result in results.get('results', []):
                if 'batch' in result.get('task_type', '').lower():
                    batch_id = result.get('job_id', '')
                    
                    # Get batch details
                    batch_results = await batch_relationship_manager.get_batch_results(batch_id)
                    if batch_results:
                        summary = batch_results.get('summary', {})
                        
                        batch_summary = {
                            'batch_id': batch_id,
                            'batch_name': result.get('job_name', 'Unnamed Batch'),
                            'created_at': result.get('created_at'),
                            'status': batch_results.get('status', 'unknown'),
                            'total_ligands': summary.get('total_ligands', 0),
                            'completed_jobs': summary.get('completed_jobs', 0),
                            'failed_jobs': summary.get('failed_jobs', 0),
                            'success_rate': summary.get('success_rate', 0),
                            'top_affinity': summary.get('top_affinity', 0)
                        }
                        
                        batch_summaries.append(batch_summary)
                        total_ligands += summary.get('total_ligands', 0)
                        total_completed += summary.get('completed_jobs', 0)
                        total_failed += summary.get('failed_jobs', 0)
            
            return {
                'user_id': user_id,
                'total_batches': len(batch_summaries),
                'total_ligands_processed': total_ligands,
                'total_completed_jobs': total_completed,
                'total_failed_jobs': total_failed,
                'overall_success_rate': (total_completed / total_ligands * 100) if total_ligands > 0 else 0,
                'batch_summaries': batch_summaries
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch status summary for {user_id}: {e}")
            return {'error': str(e)}

# Global instance
batch_aware_results_service = BatchAwareResultsService()