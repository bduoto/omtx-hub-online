"""
Connection Pool Optimizer for Production Performance
Optimizes GCP connections, caching, and resource management
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pooling"""
    max_connections: int = 50
    min_connections: int = 5
    connection_timeout: int = 30
    idle_timeout: int = 300  # 5 minutes
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class CacheConfig:
    """Configuration for caching"""
    default_ttl: int = 300  # 5 minutes
    max_cache_size: int = 1000
    cleanup_interval: int = 60  # 1 minute
    enable_compression: bool = True

class ConnectionPoolOptimizer:
    """Optimizes database connections and caching for production performance"""
    
    def __init__(self, 
                 pool_config: Optional[ConnectionPoolConfig] = None,
                 cache_config: Optional[CacheConfig] = None):
        self.pool_config = pool_config or ConnectionPoolConfig()
        self.cache_config = cache_config or CacheConfig()
        
        # Connection pool
        self.connection_pool = ThreadPoolExecutor(
            max_workers=self.pool_config.max_connections,
            thread_name_prefix="gcp_pool"
        )
        
        # Multi-level cache
        self.l1_cache = {}  # In-memory cache
        self.l2_cache = {}  # Compressed cache
        self.cache_timestamps = {}
        self.cache_access_count = {}
        
        # Performance metrics
        self.metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'connection_pool_usage': 0,
            'query_count': 0,
            'avg_response_time': 0.0
        }
        
        # Background tasks
        self.cleanup_task = None
        self.metrics_task = None
        self._start_background_tasks()
        
        logger.info("🚀 Connection Pool Optimizer initialized")
    
    def _start_background_tasks(self):
        """Start background optimization tasks"""
        
        def cache_cleanup():
            """Clean up expired cache entries"""
            while True:
                try:
                    current_time = time.time()
                    expired_keys = []
                    
                    for key, timestamp in self.cache_timestamps.items():
                        if current_time - timestamp > self.cache_config.default_ttl:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        self._remove_from_cache(key)
                    
                    if expired_keys:
                        logger.debug(f"🗑️ Cleaned up {len(expired_keys)} expired cache entries")
                    
                    time.sleep(self.cache_config.cleanup_interval)
                    
                except Exception as e:
                    logger.error(f"❌ Cache cleanup error: {e}")
                    time.sleep(self.cache_config.cleanup_interval)
        
        def metrics_reporter():
            """Report performance metrics"""
            while True:
                try:
                    time.sleep(300)  # Report every 5 minutes
                    self._report_metrics()
                except Exception as e:
                    logger.error(f"❌ Metrics reporting error: {e}")
        
        # Start background threads
        self.cleanup_task = threading.Thread(target=cache_cleanup, daemon=True)
        self.cleanup_task.start()
        
        self.metrics_task = threading.Thread(target=metrics_reporter, daemon=True)
        self.metrics_task.start()
    
    async def execute_optimized_query(self, 
                                    query_func,
                                    cache_key: Optional[str] = None,
                                    ttl: Optional[int] = None) -> Any:
        """Execute query with connection pooling and caching"""
        
        start_time = time.time()
        self.metrics['query_count'] += 1
        
        # Check cache first
        if cache_key and self._is_cached(cache_key):
            self.metrics['cache_hits'] += 1
            result = self._get_from_cache(cache_key)
            
            elapsed = time.time() - start_time
            self._update_avg_response_time(elapsed)
            
            logger.debug(f"⚡ Cache hit for {cache_key}: {elapsed*1000:.1f}ms")
            return result
        
        # Execute query with connection pool
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.connection_pool,
                query_func
            )
            
            # Cache result
            if cache_key:
                self._set_cache(cache_key, result, ttl)
                self.metrics['cache_misses'] += 1
            
            elapsed = time.time() - start_time
            self._update_avg_response_time(elapsed)
            
            logger.debug(f"🔍 Query executed: {elapsed*1000:.1f}ms")
            return result
            
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            raise
    
    def _is_cached(self, key: str) -> bool:
        """Check if key is in cache and not expired"""
        if key not in self.cache_timestamps:
            return False
        
        age = time.time() - self.cache_timestamps[key]
        return age < self.cache_config.default_ttl
    
    def _get_from_cache(self, key: str) -> Any:
        """Get value from cache"""
        self.cache_access_count[key] = self.cache_access_count.get(key, 0) + 1
        
        # Try L1 cache first
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # Try L2 cache (compressed)
        if key in self.l2_cache:
            # Move to L1 cache for faster access
            value = self.l2_cache[key]
            self.l1_cache[key] = value
            return value
        
        return None
    
    def _set_cache(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with TTL"""
        current_time = time.time()
        
        # Store in L1 cache
        self.l1_cache[key] = value
        self.cache_timestamps[key] = current_time
        
        # Manage cache size
        if len(self.l1_cache) > self.cache_config.max_cache_size:
            self._evict_lru_entries()
    
    def _remove_from_cache(self, key: str):
        """Remove key from all cache levels"""
        self.l1_cache.pop(key, None)
        self.l2_cache.pop(key, None)
        self.cache_timestamps.pop(key, None)
        self.cache_access_count.pop(key, None)
    
    def _evict_lru_entries(self):
        """Evict least recently used entries"""
        # Sort by access count and timestamp
        sorted_keys = sorted(
            self.cache_access_count.keys(),
            key=lambda k: (self.cache_access_count.get(k, 0), self.cache_timestamps.get(k, 0))
        )
        
        # Remove 20% of entries
        evict_count = max(1, len(sorted_keys) // 5)
        for key in sorted_keys[:evict_count]:
            # Move to L2 cache instead of removing
            if key in self.l1_cache:
                self.l2_cache[key] = self.l1_cache[key]
                del self.l1_cache[key]
    
    def _update_avg_response_time(self, elapsed: float):
        """Update average response time"""
        current_avg = self.metrics['avg_response_time']
        query_count = self.metrics['query_count']
        
        # Exponential moving average
        alpha = 0.1
        self.metrics['avg_response_time'] = (1 - alpha) * current_avg + alpha * elapsed
    
    def _report_metrics(self):
        """Report performance metrics"""
        cache_hit_rate = 0
        if self.metrics['cache_hits'] + self.metrics['cache_misses'] > 0:
            cache_hit_rate = self.metrics['cache_hits'] / (self.metrics['cache_hits'] + self.metrics['cache_misses']) * 100
        
        logger.info(f"📊 Performance Metrics:")
        logger.info(f"   Cache hit rate: {cache_hit_rate:.1f}%")
        logger.info(f"   Avg response time: {self.metrics['avg_response_time']*1000:.1f}ms")
        logger.info(f"   Total queries: {self.metrics['query_count']}")
        logger.info(f"   Cache entries: L1={len(self.l1_cache)}, L2={len(self.l2_cache)}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        cache_hit_rate = 0
        if self.metrics['cache_hits'] + self.metrics['cache_misses'] > 0:
            cache_hit_rate = self.metrics['cache_hits'] / (self.metrics['cache_hits'] + self.metrics['cache_misses']) * 100
        
        return {
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'avg_response_time_ms': round(self.metrics['avg_response_time'] * 1000, 2),
            'total_queries': self.metrics['query_count'],
            'cache_entries': {
                'l1_cache': len(self.l1_cache),
                'l2_cache': len(self.l2_cache),
                'total': len(self.l1_cache) + len(self.l2_cache)
            },
            'connection_pool_size': self.pool_config.max_connections
        }
    
    def clear_cache(self):
        """Clear all cache entries"""
        self.l1_cache.clear()
        self.l2_cache.clear()
        self.cache_timestamps.clear()
        self.cache_access_count.clear()
        logger.info("🗑️ All cache entries cleared")

# Global instance
connection_optimizer = ConnectionPoolOptimizer()
