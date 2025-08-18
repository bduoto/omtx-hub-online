"""
Results Enrichment Service
Enriches lightweight Firestore metadata with full GCP storage data
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Try to import GCP storage service, handle gracefully if not available
try:
    from services.gcp_storage_service import gcp_storage_service
    GCP_AVAILABLE = True
except ImportError as e:
    logging.warning(f"GCP storage service not available: {e}")
    # Create a mock storage service for testing
    class MockStorageService:
        def __init__(self):
            self.storage = MockStorage()

    class MockStorage:
        def __init__(self):
            self.available = False

        def download_file(self, path):
            return None

    gcp_storage_service = MockStorageService()
    GCP_AVAILABLE = False

logger = logging.getLogger(__name__)

class ResultsEnrichmentService:
    """Enriches lightweight Firestore metadata with full GCP storage data"""
    
    def __init__(self):
        self.enrichment_cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes
    
    async def enrich_job_result(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich job with full results from GCP storage"""
        
        job_id = job.get('id') or job.get('job_id')
        if not job_id:
            logger.warning("No job_id found in job data")
            return job
            
        # Check if already enriched
        if job.get('_enriched') or job.get('structure_file_base64'):
            logger.debug(f"Job {job_id} already enriched")
            return job
        
        # Check cache first
        cache_key = f"enriched:{job_id}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Using cached enrichment for {job_id}")
            return cached_result
            
        try:
            logger.info(f"🔄 Enriching job {job_id} with GCP storage data")
            
            # Load full results from GCP storage
            full_results = await self._load_full_results_from_gcp(job_id)
            if full_results:
                # Merge lightweight metadata with full results
                enriched = {
                    **job,  # Keep Firestore metadata (id, status, created_at, etc.)
                    **full_results,  # Add GCP storage data (structure_file_base64, etc.)
                    '_enriched': True,
                    '_enrichment_timestamp': datetime.utcnow().isoformat(),
                    '_enrichment_source': 'gcp_storage'
                }
                
                # Cache the enriched result
                self._set_cache(cache_key, enriched)
                
                logger.info(f"✅ Successfully enriched job {job_id}")
                return enriched
            else:
                logger.warning(f"⚠️ No full results found in GCP for job {job_id}")
                
        except Exception as e:
            logger.warning(f"Failed to enrich job {job_id}: {e}")
            
        return job
    
    async def enrich_multiple_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich multiple jobs efficiently"""
        
        enriched_jobs = []
        for job in jobs:
            enriched_job = await self.enrich_job_result(job)
            enriched_jobs.append(enriched_job)
        
        return enriched_jobs
    
    async def _load_full_results_from_gcp(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Load complete results from GCP storage"""

        if not GCP_AVAILABLE or not gcp_storage_service or not gcp_storage_service.storage.available:
            logger.warning("GCP storage service not available for enrichment")
            return None
        
        # Try multiple storage locations in order of preference
        storage_paths = [
            f"jobs/{job_id}/results.json",      # Primary results location
            f"jobs/{job_id}/modal_output.json", # Raw Modal output
            f"jobs/{job_id}/metadata.json"      # Fallback metadata
        ]
        
        for path in storage_paths:
            try:
                logger.debug(f"Trying to load {path}")
                content = gcp_storage_service.storage.download_file(path)
                if content:
                    result_data = json.loads(content.decode('utf-8'))
                    logger.debug(f"✅ Loaded results from {path}")
                    return result_data
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in {path}: {e}")
            except Exception as e:
                logger.debug(f"Could not load {path}: {e}")
                
        logger.warning(f"No results found in GCP storage for job {job_id}")
        return None
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get item from cache if not expired"""
        
        if key not in self.enrichment_cache:
            return None
            
        cached_item = self.enrichment_cache[key]
        cache_time = cached_item.get('_cache_time', 0)
        
        if datetime.utcnow().timestamp() - cache_time > self.cache_ttl:
            # Cache expired
            del self.enrichment_cache[key]
            return None
            
        return cached_item.get('data')
    
    def _set_cache(self, key: str, data: Dict[str, Any]) -> None:
        """Set item in cache with timestamp"""
        
        self.enrichment_cache[key] = {
            'data': data,
            '_cache_time': datetime.utcnow().timestamp()
        }
        
        # Simple cache cleanup - remove old entries if cache gets too large
        if len(self.enrichment_cache) > 100:
            # Remove oldest 20 entries
            sorted_keys = sorted(
                self.enrichment_cache.keys(),
                key=lambda k: self.enrichment_cache[k]['_cache_time']
            )
            for old_key in sorted_keys[:20]:
                del self.enrichment_cache[old_key]
    
    def clear_cache(self) -> None:
        """Clear the enrichment cache"""
        self.enrichment_cache.clear()
        logger.info("🧹 Cleared enrichment cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self.enrichment_cache),
            'cache_ttl_seconds': self.cache_ttl,
            'gcp_available': GCP_AVAILABLE,
            'storage_available': gcp_storage_service.storage.available if gcp_storage_service else False
        }

# Global instance
results_enrichment_service = ResultsEnrichmentService()
