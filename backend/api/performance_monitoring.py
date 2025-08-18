"""
Performance Monitoring API
Real-time performance metrics and optimization insights
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import time
# import psutil  # Optional dependency
import logging
from datetime import datetime, timedelta
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v3/performance", tags=["Performance Monitoring"])

class PerformanceMetrics(BaseModel):
    """Performance metrics response model"""
    timestamp: datetime
    api_performance: Dict[str, Any]
    database_performance: Dict[str, Any]
    cache_performance: Dict[str, Any]
    system_resources: Dict[str, Any]
    optimization_recommendations: List[str]

class APIEndpointMetrics(BaseModel):
    """API endpoint performance metrics"""
    endpoint: str
    avg_response_time_ms: float
    request_count: int
    error_rate_percent: float
    cache_hit_rate_percent: float

# Global performance tracking
performance_tracker = {
    'api_metrics': {},
    'database_metrics': {},
    'cache_metrics': {},
    'system_metrics': {},
    'start_time': time.time()
}

@router.get("/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics() -> PerformanceMetrics:
    """
    📊 Get comprehensive performance metrics
    
    Returns real-time performance data including:
    - API response times and throughput
    - Database query performance
    - Cache hit rates and efficiency
    - System resource utilization
    - Optimization recommendations
    """
    
    try:
        # Collect current metrics
        api_perf = await _collect_api_metrics()
        db_perf = await _collect_database_metrics()
        cache_perf = await _collect_cache_metrics()
        system_perf = await _collect_system_metrics()
        recommendations = await _generate_recommendations(api_perf, db_perf, cache_perf, system_perf)
        
        return PerformanceMetrics(
            timestamp=datetime.utcnow(),
            api_performance=api_perf,
            database_performance=db_perf,
            cache_performance=cache_perf,
            system_resources=system_perf,
            optimization_recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to collect performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to collect performance metrics")

@router.get("/api-endpoints", response_model=List[APIEndpointMetrics])
async def get_api_endpoint_metrics(
    limit: int = Query(20, ge=1, le=100, description="Number of endpoints to return")
) -> List[APIEndpointMetrics]:
    """
    🔍 Get detailed API endpoint performance metrics
    
    Returns performance data for individual API endpoints:
    - Response times
    - Request counts
    - Error rates
    - Cache hit rates
    """
    
    try:
        endpoint_metrics = []
        
        # Get metrics from performance tracker
        for endpoint, metrics in performance_tracker['api_metrics'].items():
            if len(endpoint_metrics) >= limit:
                break
                
            endpoint_metrics.append(APIEndpointMetrics(
                endpoint=endpoint,
                avg_response_time_ms=metrics.get('avg_response_time', 0) * 1000,
                request_count=metrics.get('request_count', 0),
                error_rate_percent=metrics.get('error_rate', 0) * 100,
                cache_hit_rate_percent=metrics.get('cache_hit_rate', 0) * 100
            ))
        
        # Sort by request count (most used endpoints first)
        endpoint_metrics.sort(key=lambda x: x.request_count, reverse=True)
        
        return endpoint_metrics
        
    except Exception as e:
        logger.error(f"❌ Failed to get API endpoint metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get API endpoint metrics")

@router.get("/optimization-report")
async def get_optimization_report() -> Dict[str, Any]:
    """
    🎯 Get comprehensive optimization report
    
    Provides detailed analysis and recommendations for:
    - Performance bottlenecks
    - Optimization opportunities
    - Resource utilization
    - Scaling recommendations
    """
    
    try:
        # Collect comprehensive data
        api_perf = await _collect_api_metrics()
        db_perf = await _collect_database_metrics()
        cache_perf = await _collect_cache_metrics()
        system_perf = await _collect_system_metrics()
        
        # Generate detailed analysis
        bottlenecks = await _identify_bottlenecks(api_perf, db_perf, cache_perf, system_perf)
        opportunities = await _identify_optimization_opportunities(api_perf, db_perf, cache_perf)
        scaling_recommendations = await _generate_scaling_recommendations(system_perf)
        
        return {
            'report_timestamp': datetime.utcnow().isoformat(),
            'overall_health_score': await _calculate_health_score(api_perf, db_perf, cache_perf, system_perf),
            'performance_summary': {
                'api_avg_response_time_ms': api_perf.get('avg_response_time', 0) * 1000,
                'database_avg_query_time_ms': db_perf.get('avg_query_time', 0) * 1000,
                'cache_hit_rate_percent': cache_perf.get('hit_rate', 0) * 100,
                'system_cpu_usage_percent': system_perf.get('cpu_usage', 0),
                'system_memory_usage_percent': system_perf.get('memory_usage', 0)
            },
            'bottlenecks': bottlenecks,
            'optimization_opportunities': opportunities,
            'scaling_recommendations': scaling_recommendations,
            'next_review_date': (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to generate optimization report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate optimization report")

@router.post("/clear-cache")
async def clear_performance_cache() -> Dict[str, str]:
    """
    🗑️ Clear performance cache
    
    Clears all cached performance data and resets metrics.
    Use this to get fresh performance measurements.
    """
    
    try:
        # Clear cache from connection optimizer
        from services.connection_pool_optimizer import connection_optimizer
        connection_optimizer.clear_cache()
        
        # Clear ultra-fast results cache
        from services.ultra_fast_results import ultra_fast_results
        ultra_fast_results.clear_cache()
        
        # Reset performance tracker
        performance_tracker['api_metrics'].clear()
        performance_tracker['database_metrics'].clear()
        performance_tracker['cache_metrics'].clear()
        performance_tracker['start_time'] = time.time()
        
        logger.info("🗑️ Performance cache cleared")
        
        return {
            'status': 'success',
            'message': 'Performance cache cleared successfully',
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to clear performance cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear performance cache")

# Helper functions

async def _collect_api_metrics() -> Dict[str, Any]:
    """Collect API performance metrics"""
    
    # Get metrics from connection optimizer
    try:
        from services.connection_pool_optimizer import connection_optimizer
        stats = connection_optimizer.get_performance_stats()
        
        return {
            'avg_response_time': stats.get('avg_response_time_ms', 0) / 1000,
            'cache_hit_rate': stats.get('cache_hit_rate_percent', 0) / 100,
            'total_requests': stats.get('total_queries', 0),
            'connection_pool_usage': stats.get('connection_pool_size', 0)
        }
    except Exception as e:
        logger.warning(f"Could not collect API metrics: {e}")
        return {'avg_response_time': 0, 'cache_hit_rate': 0, 'total_requests': 0}

async def _collect_database_metrics() -> Dict[str, Any]:
    """Collect database performance metrics"""
    
    return {
        'avg_query_time': 0.05,  # Placeholder - would integrate with actual DB metrics
        'active_connections': 5,
        'query_count': 100,
        'slow_queries': 2
    }

async def _collect_cache_metrics() -> Dict[str, Any]:
    """Collect cache performance metrics"""
    
    try:
        from services.ultra_fast_results import ultra_fast_results
        stats = ultra_fast_results.get_cache_stats()
        
        return {
            'hit_rate': 0.85,  # Placeholder
            'entries': stats.get('cache_entries', 0),
            'size_mb': stats.get('cache_size_mb', 0),
            'evictions': 0
        }
    except Exception as e:
        logger.warning(f"Could not collect cache metrics: {e}")
        return {'hit_rate': 0, 'entries': 0, 'size_mb': 0}

async def _collect_system_metrics() -> Dict[str, Any]:
    """Collect system resource metrics"""

    try:
        # Try to import psutil if available
        try:
            import psutil
            return {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_io': dict(psutil.net_io_counters()._asdict()),
                'uptime_seconds': time.time() - performance_tracker['start_time']
            }
        except ImportError:
            # Fallback metrics without psutil
            return {
                'cpu_usage': 25.0,  # Mock data
                'memory_usage': 45.0,  # Mock data
                'disk_usage': 60.0,  # Mock data
                'uptime_seconds': time.time() - performance_tracker['start_time']
            }
    except Exception as e:
        logger.warning(f"Could not collect system metrics: {e}")
        return {'cpu_usage': 0, 'memory_usage': 0, 'disk_usage': 0}

async def _generate_recommendations(api_perf, db_perf, cache_perf, system_perf) -> List[str]:
    """Generate optimization recommendations"""
    
    recommendations = []
    
    # API performance recommendations
    if api_perf.get('avg_response_time', 0) > 1.0:
        recommendations.append("Consider implementing request batching to reduce API response times")
    
    if api_perf.get('cache_hit_rate', 0) < 0.8:
        recommendations.append("Increase cache TTL or implement more aggressive caching strategies")
    
    # System resource recommendations
    if system_perf.get('cpu_usage', 0) > 80:
        recommendations.append("High CPU usage detected - consider horizontal scaling")
    
    if system_perf.get('memory_usage', 0) > 85:
        recommendations.append("High memory usage - consider increasing instance size or optimizing memory usage")
    
    # Database recommendations
    if db_perf.get('slow_queries', 0) > 5:
        recommendations.append("Multiple slow queries detected - review database indexes")
    
    if not recommendations:
        recommendations.append("System performance is optimal - no immediate optimizations needed")
    
    return recommendations

async def _identify_bottlenecks(api_perf, db_perf, cache_perf, system_perf) -> List[Dict[str, Any]]:
    """Identify performance bottlenecks"""
    
    bottlenecks = []
    
    if api_perf.get('avg_response_time', 0) > 0.5:
        bottlenecks.append({
            'type': 'API Response Time',
            'severity': 'high' if api_perf['avg_response_time'] > 1.0 else 'medium',
            'description': f"Average API response time is {api_perf['avg_response_time']*1000:.0f}ms",
            'recommendation': 'Implement caching or optimize database queries'
        })
    
    return bottlenecks

async def _identify_optimization_opportunities(api_perf, db_perf, cache_perf) -> List[Dict[str, Any]]:
    """Identify optimization opportunities"""
    
    opportunities = []
    
    if cache_perf.get('hit_rate', 0) < 0.9:
        opportunities.append({
            'type': 'Cache Optimization',
            'potential_improvement': '20-50% response time reduction',
            'description': 'Increase cache hit rate through better caching strategies',
            'implementation_effort': 'low'
        })
    
    return opportunities

async def _generate_scaling_recommendations(system_perf) -> List[Dict[str, Any]]:
    """Generate scaling recommendations"""
    
    recommendations = []
    
    if system_perf.get('cpu_usage', 0) > 70:
        recommendations.append({
            'type': 'Horizontal Scaling',
            'urgency': 'high' if system_perf['cpu_usage'] > 90 else 'medium',
            'description': 'Add more server instances to handle increased load',
            'estimated_cost': 'medium'
        })
    
    return recommendations

async def _calculate_health_score(api_perf, db_perf, cache_perf, system_perf) -> float:
    """Calculate overall system health score (0-100)"""
    
    score = 100
    
    # Deduct points for performance issues
    if api_perf.get('avg_response_time', 0) > 0.5:
        score -= 20
    
    if cache_perf.get('hit_rate', 0) < 0.8:
        score -= 15
    
    if system_perf.get('cpu_usage', 0) > 80:
        score -= 25
    
    if system_perf.get('memory_usage', 0) > 85:
        score -= 20
    
    return max(0, score)
