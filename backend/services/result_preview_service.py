"""
Result Preview Service - Lightweight result previews without full file loading
Generates essential preview data for My Results page performance
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from config.gcp_storage import gcp_storage
from config.gcp_database import gcp_database

logger = logging.getLogger(__name__)

class ResultPreviewService:
    """Lightweight result previews without full file loading"""
    
    def __init__(self):
        self.storage = gcp_storage
        self.db = gcp_database
        self.preview_cache = {}
        self.cache_ttl = 300  # 5 minutes for previews
    
    async def generate_preview(self, job_id: str, task_type: str) -> Dict[str, Any]:
        """Generate lightweight preview data"""
        
        # Check cache first
        cache_key = f"preview:{job_id}"
        if self._is_preview_cached(cache_key):
            return self.preview_cache[cache_key]['data']
        
        try:
            # Load only essential metadata
            metadata = await self._load_metadata_only(f"jobs/{job_id}/metadata.json")
            
            preview = {
                'job_id': job_id,
                'task_type': task_type,
                'status': metadata.get('status', 'unknown'),
                'created_at': metadata.get('created_at'),
                'execution_time': metadata.get('execution_time'),
                'model': metadata.get('model'),
                'has_structure': await self._check_file_exists(f"jobs/{job_id}/structure.cif"),
                'has_results': await self._check_file_exists(f"jobs/{job_id}/results.json"),
                'file_count': metadata.get('file_count', 0),
                'preview_generated_at': asyncio.get_event_loop().time()
            }
            
            # Add task-specific preview data
            if task_type == 'protein_ligand_binding':
                preview.update(await self._get_binding_preview(job_id))
            elif task_type == 'batch_protein_ligand_screening':
                preview.update(await self._get_batch_preview(job_id))
            elif task_type == 'rf_antibody_design':
                preview.update(await self._get_antibody_preview(job_id))
            
            # Cache the preview
            self._cache_preview(cache_key, preview)
            
            return preview
            
        except Exception as e:
            logger.error(f"Preview generation failed for {job_id}: {e}")
            return {
                'job_id': job_id, 
                'error': 'Preview unavailable',
                'task_type': task_type,
                'status': 'unknown'
            }
    
    async def _load_metadata_only(self, file_path: str) -> Dict[str, Any]:
        """Load only metadata.json without other files"""
        try:
            content = self.storage.download_file(file_path)
            if content:
                return json.loads(content.decode('utf-8'))
            return {}
        except Exception as e:
            logger.debug(f"Failed to load metadata from {file_path}: {e}")
            return {}
    
    async def _check_file_exists(self, file_path: str) -> bool:
        """Quick check if file exists without downloading"""
        try:
            blob = self.storage.bucket.blob(file_path)
            return blob.exists()
        except:
            return False
    
    async def _get_binding_preview(self, job_id: str) -> Dict[str, Any]:
        """Get protein-ligand binding specific preview data"""
        try:
            # Load only small affinity file, not full results
            affinity_data = await self._load_small_file(f"jobs/{job_id}/affinity.json")
            if affinity_data:
                return {
                    'affinity': affinity_data.get('affinity_pred_value'),
                    'confidence': affinity_data.get('confidence_score'),
                    'binding_preview': True
                }
            return {'binding_preview': False}
        except:
            return {'binding_preview': False}
    
    async def _get_batch_preview(self, job_id: str) -> Dict[str, Any]:
        """Get batch screening specific preview data"""
        try:
            # Get batch statistics from database (faster than file parsing)
            batch_children = self.db.get_batch_jobs_optimized(job_id, limit=1000)
            
            if batch_children:
                total = len(batch_children)
                completed = len([j for j in batch_children if j.get('status') == 'completed'])
                failed = len([j for j in batch_children if j.get('status') == 'failed'])
                
                # Get top results preview (just first few)
                top_results = []
                completed_children = [j for j in batch_children if j.get('status') == 'completed'][:3]
                
                for child in completed_children:
                    child_preview = await self._get_binding_preview(child['id'])
                    if child_preview.get('affinity'):
                        top_results.append({
                            'ligand_id': child.get('batch_index', 0),
                            'affinity': child_preview['affinity'],
                            'confidence': child_preview.get('confidence', 0)
                        })
                
                return {
                    'batch_total': total,
                    'batch_completed': completed,
                    'batch_failed': failed,
                    'batch_progress': (completed / total * 100) if total > 0 else 0,
                    'top_results': sorted(top_results, key=lambda x: x.get('affinity', 0))[:3],
                    'batch_preview': True
                }
            
            return {'batch_preview': False}
        except Exception as e:
            logger.debug(f"Failed to get batch preview for {job_id}: {e}")
            return {'batch_preview': False}
    
    async def _get_antibody_preview(self, job_id: str) -> Dict[str, Any]:
        """Get antibody design specific preview data"""
        try:
            # Load minimal antibody results
            results_data = await self._load_small_file(f"jobs/{job_id}/results.json")
            if results_data:
                return {
                    'antibody_sequence_length': len(results_data.get('sequence', '')),
                    'confidence_score': results_data.get('confidence', 0),
                    'design_quality': results_data.get('quality_score', 0),
                    'antibody_preview': True
                }
            return {'antibody_preview': False}
        except:
            return {'antibody_preview': False}
    
    async def _load_small_file(self, file_path: str, max_size: int = 10240) -> Optional[Dict[str, Any]]:
        """Load small files (< 10KB) for preview data"""
        try:
            # Check file size first
            blob = self.storage.bucket.blob(file_path)
            if not blob.exists():
                return None
            
            blob.reload()  # Get metadata
            if blob.size and blob.size > max_size:
                logger.debug(f"File {file_path} too large for preview ({blob.size} bytes)")
                return None
            
            # Download and parse
            content = self.storage.download_file(file_path)
            if content:
                return json.loads(content.decode('utf-8'))
                
        except Exception as e:
            logger.debug(f"Failed to load small file {file_path}: {e}")
        
        return None
    
    def _is_preview_cached(self, cache_key: str) -> bool:
        """Check if preview is cached and valid"""
        if cache_key not in self.preview_cache:
            return False
        
        cached_data = self.preview_cache[cache_key]
        age = asyncio.get_event_loop().time() - cached_data['timestamp']
        
        if age > self.cache_ttl:
            del self.preview_cache[cache_key]
            return False
        
        return True
    
    def _cache_preview(self, cache_key: str, preview_data: Dict[str, Any]):
        """Cache preview data with timestamp"""
        self.preview_cache[cache_key] = {
            'data': preview_data,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        # Cleanup old entries
        if len(self.preview_cache) > 200:
            # Remove oldest 50 entries
            sorted_entries = sorted(
                self.preview_cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            for key, _ in sorted_entries[:50]:
                del self.preview_cache[key]
    
    async def generate_batch_previews(self, job_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Generate previews for multiple jobs in parallel"""
        
        # Create tasks for parallel processing
        tasks = []
        for job_id in job_ids:
            # Get task type from database first
            job_data = self.db.get_job(job_id)
            task_type = job_data.get('type', 'unknown') if job_data else 'unknown'
            
            task = self.generate_preview(job_id, task_type)
            tasks.append((job_id, task))
        
        # Process in parallel
        results = {}
        if tasks:
            completed_tasks = await asyncio.gather(
                *[task for _, task in tasks], 
                return_exceptions=True
            )
            
            for (job_id, _), result in zip(tasks, completed_tasks):
                if isinstance(result, dict):
                    results[job_id] = result
                else:
                    results[job_id] = {
                        'job_id': job_id,
                        'error': str(result),
                        'preview_failed': True
                    }
        
        return results
    
    def invalidate_preview_cache(self, job_id: Optional[str] = None):
        """Invalidate preview cache entries"""
        if job_id:
            cache_key = f"preview:{job_id}"
            if cache_key in self.preview_cache:
                del self.preview_cache[cache_key]
                logger.info(f"🗑️ Invalidated preview cache for {job_id}")
        else:
            self.preview_cache.clear()
            logger.info("🗑️ Cleared all preview cache entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get preview cache statistics"""
        return {
            'cached_previews': len(self.preview_cache),
            'cache_size_estimate': sum(len(str(v)) for v in self.preview_cache.values()),
            'ttl_seconds': self.cache_ttl
        }

# Global instance
result_preview_service = ResultPreviewService()