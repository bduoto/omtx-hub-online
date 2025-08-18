"""
Rate Limiter for Running Job Queries
Prevents excessive "Retrieved X jobs with status 'running'" database queries
"""

import time
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RunningJobRateLimiter:
    """Rate limits running job status queries to prevent database overload"""
    
    def __init__(self):
        self.last_query_times = {}  # user_id -> timestamp
        self.cached_running_jobs = {}  # user_id -> {'jobs': [...], 'timestamp': float}
        self.query_interval = 30  # seconds between queries
        self.cache_ttl = 60  # seconds to cache running job data
        
    def should_query_running_jobs(self, user_id: str) -> bool:
        """Check if we should query for running jobs or use cached data"""
        now = time.time()
        last_query = self.last_query_times.get(user_id, 0)
        
        # Rate limit: only query every 30 seconds per user
        if now - last_query < self.query_interval:
            logger.debug(f"🚫 Rate limited running job query for {user_id} - {self.query_interval - (now - last_query):.1f}s remaining")
            return False
            
        return True
    
    def get_cached_running_jobs(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached running jobs if available and not expired"""
        now = time.time()
        cached_data = self.cached_running_jobs.get(user_id)
        
        if cached_data:
            cache_age = now - cached_data['timestamp']
            if cache_age < self.cache_ttl:
                logger.debug(f"📋 Using cached running jobs for {user_id} (age: {cache_age:.1f}s)")
                return cached_data['jobs']
                
        return None
    
    def cache_running_jobs(self, user_id: str, jobs: List[Dict[str, Any]]) -> None:
        """Cache running jobs data and update query timestamp"""
        now = time.time()
        
        # Update query timestamp
        self.last_query_times[user_id] = now
        
        # Cache the jobs data
        self.cached_running_jobs[user_id] = {
            'jobs': jobs,
            'timestamp': now
        }
        
        logger.info(f"💾 Cached {len(jobs)} running jobs for {user_id}")
    
    def force_refresh(self, user_id: str) -> None:
        """Force refresh for a user (clears cache and rate limit)"""
        self.last_query_times.pop(user_id, None)
        self.cached_running_jobs.pop(user_id, None)
        logger.info(f"🔄 Forced refresh for {user_id}")
    
    def cleanup_old_entries(self) -> None:
        """Remove old cache entries to prevent memory bloat"""
        now = time.time()
        max_age = 300  # 5 minutes
        
        # Clean query timestamps
        old_users = [
            user_id for user_id, timestamp in self.last_query_times.items()
            if now - timestamp > max_age
        ]
        
        # Clean cached jobs
        old_cached_users = [
            user_id for user_id, data in self.cached_running_jobs.items()
            if now - data['timestamp'] > max_age
        ]
        
        for user_id in old_users:
            self.last_query_times.pop(user_id, None)
            
        for user_id in old_cached_users:
            self.cached_running_jobs.pop(user_id, None)
            
        if old_users or old_cached_users:
            logger.info(f"🧹 Cleaned up {len(old_users + old_cached_users)} old rate limiter entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        now = time.time()
        
        # Count active entries
        active_query_limits = sum(
            1 for timestamp in self.last_query_times.values()
            if now - timestamp < self.query_interval
        )
        
        active_cached_jobs = sum(
            1 for data in self.cached_running_jobs.values()
            if now - data['timestamp'] < self.cache_ttl
        )
        
        return {
            'query_interval_seconds': self.query_interval,
            'cache_ttl_seconds': self.cache_ttl,
            'total_users_tracked': len(self.last_query_times),
            'active_query_limits': active_query_limits,
            'cached_job_entries': len(self.cached_running_jobs),
            'active_cached_entries': active_cached_jobs,
            'last_cleanup': 'not_tracked'  # TODO: Track cleanup times
        }

# Global instance
running_job_rate_limiter = RunningJobRateLimiter()