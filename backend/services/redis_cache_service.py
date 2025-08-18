#!/usr/bin/env python3
"""
Production Redis Caching Service
Senior Principal Engineer Implementation

High-performance caching layer for the unified batch processing system
with intelligent cache invalidation, compression, and distributed locking.
"""

import json
import gzip
import logging
import hashlib
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)

class CacheConfig:
    """Cache configuration with intelligent defaults"""
    
    # Cache TTL (Time To Live) in seconds
    BATCH_STATUS_TTL = 30          # 30 seconds for batch status (high frequency)
    BATCH_RESULTS_TTL = 3600       # 1 hour for batch results (expensive to compute)
    BATCH_LIST_TTL = 300           # 5 minutes for batch listings
    USER_PROFILE_TTL = 1800        # 30 minutes for user profiles
    MODEL_SCHEMA_TTL = 86400       # 24 hours for model schemas (rarely change)
    
    # Cache keys prefixes
    BATCH_STATUS_PREFIX = "batch:status:"
    BATCH_RESULTS_PREFIX = "batch:results:"
    BATCH_LIST_PREFIX = "batch:list:"
    USER_PROFILE_PREFIX = "user:profile:"
    MODEL_SCHEMA_PREFIX = "model:schema:"
    
    # Compression settings
    COMPRESSION_MIN_SIZE = 1024    # Compress data larger than 1KB
    MAX_CACHE_SIZE = 10 * 1024 * 1024  # 10MB max cache size per key

class DistributedLock:
    """Redis-based distributed lock for cache consistency"""
    
    def __init__(self, redis_client, key: str, timeout: int = 30):
        self.redis = redis_client
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.lock_value = None
    
    async def acquire(self) -> bool:
        """Acquire distributed lock"""
        if not self.redis:
            return True  # Fallback mode
        
        import uuid
        self.lock_value = str(uuid.uuid4())
        
        result = await self.redis.set(
            self.key, 
            self.lock_value, 
            nx=True, 
            ex=self.timeout
        )
        return bool(result)
    
    async def release(self) -> bool:
        """Release distributed lock"""
        if not self.redis or not self.lock_value:
            return True
        
        # Use Lua script to ensure atomic check-and-delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self.redis.eval(script, 1, self.key, self.lock_value)
        return bool(result)

class ProductionCacheService:
    """
    Enterprise Redis Caching Service
    
    Features:
    - Intelligent cache key generation with collision avoidance
    - Automatic compression for large payloads
    - Cache warming and preloading strategies
    - Distributed locking for consistency
    - Circuit breaker pattern for Redis failures
    - Metrics and monitoring integration
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", **kwargs):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.connected = False
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 60  # seconds
        self.last_failure_time = None
        
        # Performance metrics
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_errors = 0
        
        # Fallback in-memory cache for when Redis is unavailable
        self.fallback_cache: Dict[str, tuple] = {}  # key -> (data, expiry)
        self.max_fallback_size = 1000
    
    async def initialize(self) -> bool:
        """Initialize Redis connection with retry logic"""
        if not REDIS_AVAILABLE:
            logger.warning("⚠️ Redis not available, using in-memory fallback cache")
            return False
        
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We handle our own encoding
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self.connected = True
            self.circuit_breaker_failures = 0
            logger.info("✅ Redis cache service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self.connected = False
            return False
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open (too many failures)"""
        if self.circuit_breaker_failures < self.circuit_breaker_threshold:
            return False
        
        if self.last_failure_time is None:
            return False
        
        time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
        return time_since_failure < self.circuit_breaker_timeout
    
    def _record_failure(self):
        """Record cache failure for circuit breaker"""
        self.circuit_breaker_failures += 1
        self.last_failure_time = datetime.now()
        self.cache_errors += 1
    
    def _record_success(self):
        """Record cache success"""
        if self.circuit_breaker_failures > 0:
            self.circuit_breaker_failures = max(0, self.circuit_breaker_failures - 1)
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate unique cache key with collision avoidance"""
        # Create a unique string from all arguments
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_data += ":" + ":".join(f"{k}={v}" for k, v in sorted_kwargs)
        
        # Hash for consistent length and collision avoidance
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"{prefix}{key_hash}"
    
    def _compress_data(self, data: bytes) -> tuple[bytes, bool]:
        """Compress data if beneficial"""
        if len(data) < CacheConfig.COMPRESSION_MIN_SIZE:
            return data, False
        
        compressed = gzip.compress(data, compresslevel=6)
        if len(compressed) < len(data) * 0.8:  # Only use if 20%+ savings
            return compressed, True
        return data, False
    
    def _decompress_data(self, data: bytes, compressed: bool) -> bytes:
        """Decompress data if needed"""
        return gzip.decompress(data) if compressed else data
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value with metadata"""
        serialized = json.dumps(value, default=str, separators=(',', ':')).encode('utf-8')
        compressed, is_compressed = self._compress_data(serialized)
        
        # Add metadata header
        metadata = {
            'compressed': is_compressed,
            'timestamp': datetime.utcnow().isoformat(),
            'size_original': len(serialized),
            'size_stored': len(compressed)
        }
        
        header = json.dumps(metadata, separators=(',', ':')).encode('utf-8')
        header_size = len(header).to_bytes(4, byteorder='big')
        
        return header_size + header + compressed
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value with metadata"""
        if not data:
            return None
        
        # Extract header size and header
        header_size = int.from_bytes(data[:4], byteorder='big')
        header = json.loads(data[4:4+header_size].decode('utf-8'))
        payload = data[4+header_size:]
        
        # Decompress if needed
        decompressed = self._decompress_data(payload, header.get('compressed', False))
        
        return json.loads(decompressed.decode('utf-8'))
    
    async def _fallback_get(self, key: str) -> Optional[Any]:
        """Get value from fallback in-memory cache"""
        if key not in self.fallback_cache:
            return None
        
        data, expiry = self.fallback_cache[key]
        if datetime.now() > expiry:
            del self.fallback_cache[key]
            return None
        
        return data
    
    async def _fallback_set(self, key: str, value: Any, ttl: int):
        """Set value in fallback in-memory cache"""
        # Limit fallback cache size
        if len(self.fallback_cache) >= self.max_fallback_size:
            # Remove oldest entries
            sorted_items = sorted(
                self.fallback_cache.items(),
                key=lambda x: x[1][1]  # Sort by expiry time
            )
            for old_key, _ in sorted_items[:self.max_fallback_size // 2]:
                del self.fallback_cache[old_key]
        
        expiry = datetime.now() + timedelta(seconds=ttl)
        self.fallback_cache[key] = (value, expiry)
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get cached value with fallback support"""
        try:
            # Check circuit breaker
            if self._is_circuit_breaker_open():
                logger.debug(f"🔴 Circuit breaker open, using fallback for key: {key}")
                result = await self._fallback_get(key)
                if result is not None:
                    self.cache_hits += 1
                    return result
                self.cache_misses += 1
                return default
            
            # Try Redis first
            if self.connected and self.redis_client:
                data = await self.redis_client.get(key)
                if data:
                    value = self._deserialize_value(data)
                    self._record_success()
                    self.cache_hits += 1
                    return value
            
            # Try fallback cache
            result = await self._fallback_get(key)
            if result is not None:
                self.cache_hits += 1
                return result
            
            self.cache_misses += 1
            return default
            
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            self._record_failure()
            
            # Try fallback
            result = await self._fallback_get(key)
            if result is not None:
                self.cache_hits += 1
                return result
            
            self.cache_misses += 1
            return default
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set cached value with fallback support"""
        try:
            # Always set in fallback cache for resilience
            await self._fallback_set(key, value, ttl)
            
            # Check circuit breaker
            if self._is_circuit_breaker_open():
                logger.debug(f"🔴 Circuit breaker open, using fallback only for key: {key}")
                return True
            
            # Try Redis
            if self.connected and self.redis_client:
                serialized = self._serialize_value(value)
                
                # Enforce max cache size
                if len(serialized) > CacheConfig.MAX_CACHE_SIZE:
                    logger.warning(f"Cache value too large for key {key}: {len(serialized)} bytes")
                    return False
                
                await self.redis_client.setex(key, ttl, serialized)
                self._record_success()
                return True
            
            return True  # Fallback cache succeeded
            
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            self._record_failure()
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        try:
            # Remove from fallback cache
            self.fallback_cache.pop(key, None)
            
            # Remove from Redis
            if self.connected and self.redis_client and not self._is_circuit_breaker_open():
                result = await self.redis_client.delete(key)
                self._record_success()
                return bool(result)
            
            return True
            
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            self._record_failure()
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        try:
            if not self.connected or not self.redis_client or self._is_circuit_breaker_open():
                # Clear matching keys from fallback cache
                matching_keys = [k for k in self.fallback_cache.keys() if pattern in k]
                for key in matching_keys:
                    del self.fallback_cache[key]
                return len(matching_keys)
            
            # Use Redis SCAN for efficient pattern matching
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                self._record_success()
                return deleted
            
            return 0
            
        except Exception as e:
            logger.warning(f"Cache pattern invalidation error for pattern {pattern}: {e}")
            self._record_failure()
            return 0
    
    @asynccontextmanager
    async def distributed_lock(self, lock_key: str, timeout: int = 30):
        """Distributed lock context manager"""
        lock = DistributedLock(self.redis_client, lock_key, timeout)
        acquired = await lock.acquire()
        
        if not acquired:
            raise RuntimeError(f"Failed to acquire lock: {lock_key}")
        
        try:
            yield lock
        finally:
            await lock.release()
    
    async def cache_warming_batch_status(self, batch_ids: List[str]):
        """Pre-warm cache with batch status data"""
        logger.info(f"🔥 Warming cache for {len(batch_ids)} batch statuses")
        
        # This would integrate with your batch processor
        # from services.unified_batch_processor import unified_batch_processor
        
        tasks = []
        for batch_id in batch_ids:
            cache_key = self._generate_cache_key(CacheConfig.BATCH_STATUS_PREFIX, batch_id)
            
            async def warm_single_batch(bid: str, ckey: str):
                try:
                    # Get fresh data (implement this based on your batch processor)
                    # status = await unified_batch_processor.get_batch_status(bid)
                    # await self.set(ckey, status, CacheConfig.BATCH_STATUS_TTL)
                    pass
                except Exception as e:
                    logger.warning(f"Failed to warm cache for batch {bid}: {e}")
            
            tasks.append(warm_single_batch(batch_id, cache_key))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("✅ Cache warming completed")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_errors': self.cache_errors,
            'hit_rate_percentage': round(hit_rate, 2),
            'circuit_breaker_failures': self.circuit_breaker_failures,
            'circuit_breaker_open': self._is_circuit_breaker_open(),
            'connected_to_redis': self.connected,
            'fallback_cache_size': len(self.fallback_cache)
        }

# Global cache service instance
cache_service = ProductionCacheService()

# Decorators for easy cache integration
def cached(ttl: int = 3600, key_prefix: str = "api"):
    """Decorator to cache function results"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = cache_service._generate_cache_key(key_prefix, func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator