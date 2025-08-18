"""
Batch Status Cache Service
Caches expensive batch status calculations to prevent repeated 1000+ job queries
"""

import time
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BatchStatusCache:
    """Caches batch status calculations to prevent expensive repeated queries"""
    
    def __init__(self):
        self.batch_status_cache = {}  # batch_id -> {'status': ..., 'timestamp': ..., 'data': ...}
        self.cache_ttl = 60  # 1 minute cache for batch status
        self.large_batch_cache_ttl = 300  # 5 minutes cache for large batches (>100 jobs)
        
    def get_cached_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get cached batch status if available and not expired"""
        cached_data = self.batch_status_cache.get(batch_id)
        
        if not cached_data:
            return None
            
        now = time.time()
        cache_age = now - cached_data['timestamp']
        
        # Use different TTL based on batch size
        job_count = cached_data.get('data', {}).get('total_jobs', 0)
        ttl = self.large_batch_cache_ttl if job_count > 100 else self.cache_ttl
        
        if cache_age < ttl:
            logger.debug(f"📋 Using cached batch status for {batch_id} (age: {cache_age:.1f}s, jobs: {job_count})")
            return cached_data['data']
            
        # Expired, remove from cache
        self.batch_status_cache.pop(batch_id, None)
        return None
    
    def cache_batch_status(self, batch_id: str, status_data: Dict[str, Any]) -> None:
        """Cache batch status data"""
        now = time.time()
        job_count = status_data.get('total_jobs', 0)
        
        self.batch_status_cache[batch_id] = {
            'data': status_data,
            'timestamp': now
        }
        
        ttl = self.large_batch_cache_ttl if job_count > 100 else self.cache_ttl
        logger.info(f"💾 Cached batch status for {batch_id} ({job_count} jobs, TTL: {ttl}s)")
    
    def invalidate_batch_status(self, batch_id: str) -> None:
        """Invalidate cached batch status (e.g., when jobs complete)"""
        if batch_id in self.batch_status_cache:
            self.batch_status_cache.pop(batch_id, None)
            logger.info(f"🗑️ Invalidated cache for batch {batch_id}")
    
    def should_use_cache(self, batch_id: str, force_refresh: bool = False) -> bool:
        """Determine if we should use cached data or refresh"""
        if force_refresh:
            return False
            
        return self.get_cached_batch_status(batch_id) is not None
    
    def cleanup_old_entries(self) -> None:
        """Remove old cache entries to prevent memory bloat"""
        now = time.time()
        max_age = 900  # 15 minutes absolute maximum
        
        old_batches = [
            batch_id for batch_id, data in self.batch_status_cache.items()
            if now - data['timestamp'] > max_age
        ]
        
        for batch_id in old_batches:
            self.batch_status_cache.pop(batch_id, None)
            
        if old_batches:
            logger.info(f"🧹 Cleaned up {len(old_batches)} old batch status cache entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = time.time()
        
        # Count active vs expired entries
        active_entries = 0
        expired_entries = 0
        total_jobs_cached = 0
        
        for batch_id, data in self.batch_status_cache.items():
            cache_age = now - data['timestamp']
            job_count = data.get('data', {}).get('total_jobs', 0)
            ttl = self.large_batch_cache_ttl if job_count > 100 else self.cache_ttl
            
            if cache_age < ttl:
                active_entries += 1
                total_jobs_cached += job_count
            else:
                expired_entries += 1
        
        return {
            'total_cached_batches': len(self.batch_status_cache),
            'active_entries': active_entries,
            'expired_entries': expired_entries,
            'total_jobs_cached': total_jobs_cached,
            'cache_ttl_seconds': self.cache_ttl,
            'large_batch_ttl_seconds': self.large_batch_cache_ttl,
            'memory_usage_estimate_kb': len(str(self.batch_status_cache)) // 1024
        }
    
    def force_refresh_all(self) -> None:
        """Force refresh all cached data (clears everything)"""
        count = len(self.batch_status_cache)
        self.batch_status_cache.clear()
        logger.info(f"🔄 Force refreshed all batch status cache ({count} entries cleared)")

# Global instance
batch_status_cache = BatchStatusCache()