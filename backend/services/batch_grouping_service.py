"""
Batch Grouping Service
Groups individual batch child jobs under their parent batch for hierarchical display
"""

import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict
import re

logger = logging.getLogger(__name__)

class BatchGroupingService:
    """Service to group batch child jobs under parent batches"""
    
    def __init__(self):
        self.batch_pattern = re.compile(r'^(.+?)\s*-\s*(\d+)$')  # Matches "BatchName - 1", "BatchName - 2", etc.
    
    def group_jobs_by_batch(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group jobs by batch parent, creating expandable batch entries"""
        
        try:
            # Separate individual jobs from potential batch children
            batch_groups = defaultdict(list)
            individual_jobs = []
            
            for job in jobs:
                job_name = job.get('job_name', '')
                batch_match = self.batch_pattern.match(job_name)
                
                if batch_match:
                    # This looks like a batch child job
                    batch_name = batch_match.group(1).strip()
                    child_index = int(batch_match.group(2))
                    
                    batch_groups[batch_name].append({
                        **job,
                        'child_index': child_index,
                        'is_batch_child': True
                    })
                else:
                    # Regular individual job
                    individual_jobs.append({
                        **job,
                        'is_batch_child': False
                    })
            
            # Create grouped results
            grouped_results = []
            
            # Add individual jobs first
            grouped_results.extend(individual_jobs)
            
            # Create batch parent entries
            for batch_name, children in batch_groups.items():
                if len(children) > 1:  # Only group if there are multiple children
                    # Sort children by index
                    children.sort(key=lambda x: x.get('child_index', 0))
                    
                    # Create parent batch entry
                    parent_batch = self._create_batch_parent(batch_name, children)
                    grouped_results.append(parent_batch)
                else:
                    # Single child, treat as individual job
                    grouped_results.extend(children)
            
            # Sort results by creation date (newest first)
            grouped_results.sort(
                key=lambda x: x.get('created_at', ''), 
                reverse=True
            )
            
            return grouped_results
            
        except Exception as e:
            logger.error(f"❌ Failed to group jobs by batch: {e}")
            # Return original jobs if grouping fails
            return jobs
    
    def _create_batch_parent(self, batch_name: str, children: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a parent batch entry from child jobs"""
        
        # Calculate batch statistics
        total_children = len(children)
        completed_children = len([c for c in children if c.get('status') == 'completed'])
        failed_children = len([c for c in children if c.get('status') == 'failed'])
        running_children = len([c for c in children if c.get('status') in ['running', 'pending']])
        
        # Use the first child as a template
        template = children[0]
        
        # Determine overall batch status
        if completed_children == total_children:
            batch_status = 'completed'
        elif failed_children == total_children:
            batch_status = 'failed'
        elif running_children > 0:
            batch_status = 'running'
        else:
            batch_status = 'partially_completed'
        
        # Get earliest and latest timestamps
        created_dates = [c.get('created_at') for c in children if c.get('created_at')]
        completed_dates = [c.get('completed_at') for c in children if c.get('completed_at')]
        
        earliest_created = min(created_dates) if created_dates else template.get('created_at')
        latest_completed = max(completed_dates) if completed_dates else None
        
        # Create parent batch entry
        parent_batch = {
            'id': f"batch_{template.get('id', '')[:8]}_{len(children)}jobs",
            'job_id': template.get('job_id', ''),
            'task_type': 'batch_protein_ligand_screening',
            'job_name': f"{batch_name} (Batch of {total_children})",
            'status': batch_status,
            'created_at': earliest_created,
            'completed_at': latest_completed,
            'user_id': template.get('user_id'),
            'model': template.get('model'),
            
            # Batch-specific metadata
            'is_batch_parent': True,
            'batch_info': {
                'batch_name': batch_name,
                'total_jobs': total_children,
                'completed_jobs': completed_children,
                'failed_jobs': failed_children,
                'running_jobs': running_children,
                'success_rate': (completed_children / total_children * 100) if total_children > 0 else 0,
                'children': children,
                'expandable': True
            },
            
            # Display properties
            'has_results': completed_children > 0,
            'storage_source': 'batch_grouped',
            'preview_available': True
        }
        
        return parent_batch
    
    def get_batch_children(self, parent_job: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get children for a batch parent job"""
        
        if not parent_job.get('is_batch_parent'):
            return []
        
        batch_info = parent_job.get('batch_info', {})
        return batch_info.get('children', [])
    
    def is_batch_parent(self, job: Dict[str, Any]) -> bool:
        """Check if a job is a batch parent"""
        return job.get('is_batch_parent', False)
    
    def is_batch_child(self, job: Dict[str, Any]) -> bool:
        """Check if a job is a batch child"""
        return job.get('is_batch_child', False)
    
    def get_batch_summary(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary statistics for batch grouping"""
        
        batch_parents = [j for j in jobs if self.is_batch_parent(j)]
        individual_jobs = [j for j in jobs if not self.is_batch_parent(j) and not self.is_batch_child(j)]
        
        total_batch_children = sum(
            parent.get('batch_info', {}).get('total_jobs', 0) 
            for parent in batch_parents
        )
        
        return {
            'total_jobs': len(jobs),
            'batch_parents': len(batch_parents),
            'individual_jobs': len(individual_jobs),
            'total_batch_children': total_batch_children,
            'grouped': len(batch_parents) > 0
        }

# Global instance
batch_grouping_service = BatchGroupingService()