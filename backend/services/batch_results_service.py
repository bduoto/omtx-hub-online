"""
Batch Results Service
Handles batch job results aggregation and display
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Try to import services, handle gracefully if not available
try:
    from services.batch_relationship_manager import batch_relationship_manager
    from services.gcp_storage_service import gcp_storage_service
    GCP_AVAILABLE = True
except ImportError as e:
    logging.warning(f"GCP services not available: {e}")

    # Create mock services for testing
    class MockBatchRelationshipManager:
        async def _get_batch_index(self, batch_id):
            return None

    class MockStorageService:
        def __init__(self):
            self.storage = MockStorage()

    class MockStorage:
        def __init__(self):
            self.available = False

        def download_file(self, path):
            return None

    batch_relationship_manager = MockBatchRelationshipManager()
    gcp_storage_service = MockStorageService()
    GCP_AVAILABLE = False

logger = logging.getLogger(__name__)

class BatchResultsService:
    """Handles batch job results aggregation and display"""
    
    def __init__(self):
        self.batch_cache = {}  # Cache for batch results
        self.cache_ttl = 600  # 10 minutes for batch results
    
    async def get_batch_with_children(self, batch_id: str) -> Dict[str, Any]:
        """Get batch job with all child results"""
        
        # Check cache first
        cache_key = f"batch_full:{batch_id}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Using cached batch results for {batch_id}")
            return cached_result
        
        try:
            logger.info(f"🔄 Loading batch {batch_id} with all children")

            if not GCP_AVAILABLE or not batch_relationship_manager:
                raise ValueError("Batch services not available")

            # Get batch metadata from relationship manager
            batch_index = await batch_relationship_manager._get_batch_index(batch_id)
            if not batch_index:
                raise ValueError(f"Batch {batch_id} not found")
            
            # Load all child job results
            child_results = []
            failed_children = []
            
            for child_entry in batch_index.get('individual_jobs', []):
                child_job_id = child_entry['job_id']
                
                try:
                    # Load child results from GCP
                    child_result = await self._load_child_result(batch_id, child_job_id)
                    if child_result:
                        child_results.append({
                            **child_result,
                            'batch_id': batch_id,
                            'child_metadata': child_entry.get('metadata', {}),
                            'batch_index': child_entry.get('batch_index', len(child_results))
                        })
                    else:
                        failed_children.append(child_job_id)
                        
                except Exception as e:
                    logger.warning(f"Failed to load child {child_job_id}: {e}")
                    failed_children.append(child_job_id)
            
            # Create aggregated batch result
            batch_result = {
                'batch_id': batch_id,
                'batch_metadata': batch_index.get('metadata', {}),
                'storage_structure': batch_index.get('storage_structure', {}),
                'total_children': len(batch_index.get('individual_jobs', [])),
                'completed_children': len(child_results),
                'failed_children': len(failed_children),
                'child_results': sorted(child_results, key=lambda x: x.get('batch_index', 0)),
                'failed_child_ids': failed_children,
                'aggregated_metrics': self._calculate_batch_metrics(child_results),
                'status': self._determine_batch_status(batch_index, child_results, failed_children),
                'created_at': batch_index.get('created_at'),
                'last_updated': datetime.utcnow().isoformat()
            }
            
            # Cache the result
            self._set_cache(cache_key, batch_result)
            
            logger.info(f"✅ Loaded batch {batch_id}: {len(child_results)} completed, {len(failed_children)} failed")
            return batch_result
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch with children {batch_id}: {e}")
            raise
    
    async def _load_child_result(self, batch_id: str, child_job_id: str) -> Optional[Dict[str, Any]]:
        """Load individual child job result from GCP storage"""

        if not GCP_AVAILABLE or not gcp_storage_service:
            logger.warning("GCP storage service not available for loading child results")
            return None

        # Try multiple storage locations for child results
        storage_paths = [
            f"batches/{batch_id}/individual_jobs/{child_job_id}/results.json",
            f"jobs/{child_job_id}/results.json",  # Fallback to flat structure
            f"jobs/{child_job_id}/modal_output.json"
        ]

        for path in storage_paths:
            try:
                content = gcp_storage_service.storage.download_file(path)
                if content:
                    result_data = json.loads(content.decode('utf-8'))
                    # Add job_id to result if not present
                    result_data['job_id'] = child_job_id
                    return result_data
            except Exception as e:
                logger.debug(f"Could not load child result from {path}: {e}")

        return None
    
    def _calculate_batch_metrics(self, child_results: List[Dict]) -> Dict[str, Any]:
        """Calculate aggregated metrics for batch"""
        
        if not child_results:
            return {
                'total_results': 0,
                'success_rate': 0,
                'average_confidence': 0,
                'average_affinity': 0,
                'best_affinity': None,
                'worst_affinity': None,
                'total_execution_time': 0
            }
        
        # Extract metrics from results
        affinities = []
        confidences = []
        execution_times = []
        successful_results = 0
        
        for result in child_results:
            if result.get('status') == 'completed':
                successful_results += 1
                
            if result.get('affinity') is not None:
                affinities.append(float(result['affinity']))
                
            if result.get('confidence') is not None:
                confidences.append(float(result['confidence']))
                
            if result.get('execution_time') is not None:
                execution_times.append(float(result['execution_time']))
        
        return {
            'total_results': len(child_results),
            'successful_results': successful_results,
            'success_rate': successful_results / len(child_results) if child_results else 0,
            'average_confidence': sum(confidences) / len(confidences) if confidences else 0,
            'average_affinity': sum(affinities) / len(affinities) if affinities else 0,
            'best_affinity': max(affinities) if affinities else None,
            'worst_affinity': min(affinities) if affinities else None,
            'total_execution_time': sum(execution_times),
            'average_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0
        }
    
    def _determine_batch_status(self, batch_index: Dict, child_results: List[Dict], failed_children: List[str]) -> str:
        """Determine overall batch status"""
        
        total_expected = len(batch_index.get('individual_jobs', []))
        completed = len(child_results)
        failed = len(failed_children)
        
        if completed + failed == 0:
            return 'pending'
        elif completed + failed < total_expected:
            return 'running'
        elif failed == 0:
            return 'completed'
        elif completed == 0:
            return 'failed'
        else:
            return 'partially_completed'
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get item from cache if not expired"""
        
        if key not in self.batch_cache:
            return None
            
        cached_item = self.batch_cache[key]
        cache_time = cached_item.get('_cache_time', 0)
        
        if datetime.utcnow().timestamp() - cache_time > self.cache_ttl:
            del self.batch_cache[key]
            return None
            
        return cached_item.get('data')
    
    def _set_cache(self, key: str, data: Dict[str, Any]) -> None:
        """Set item in cache with timestamp"""
        
        self.batch_cache[key] = {
            'data': data,
            '_cache_time': datetime.utcnow().timestamp()
        }
    
    def clear_cache(self, batch_id: Optional[str] = None) -> None:
        """Clear batch cache (all or specific batch)"""
        
        if batch_id:
            cache_key = f"batch_full:{batch_id}"
            if cache_key in self.batch_cache:
                del self.batch_cache[cache_key]
                logger.info(f"🧹 Cleared cache for batch {batch_id}")
        else:
            self.batch_cache.clear()
            logger.info("🧹 Cleared all batch cache")

# Global instance
batch_results_service = BatchResultsService()
