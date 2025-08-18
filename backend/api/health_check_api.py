#!/usr/bin/env python3
"""
Health Check API - Endpoints for system health monitoring and SLO tracking
Provides comprehensive health check and SLO compliance endpoints
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Import health check service
try:
    from monitoring.health_check_service import health_check_service, HealthStatus, SLOStatus
    HEALTH_CHECK_AVAILABLE = True
except ImportError:
    logger.error("❌ Health check service not available")
    HEALTH_CHECK_AVAILABLE = False

# Create router
router = APIRouter(prefix="/api/v3/health", tags=["Health Checks"])

@router.get("/status")
async def get_overall_health_status():
    """Get overall system health status"""
    
    if not HEALTH_CHECK_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check service not available"
        )
    
    try:
        system_health = await health_check_service.get_system_health()
        
        return {
            "status": "success",
            "data": {
                "overall_status": system_health.get('overall_status', 'unknown'),
                "services_count": len(system_health.get('services', {})),
                "slo_summary": system_health.get('slo_summary', {}),
                "uptime_seconds": system_health.get('uptime_seconds', 0),
                "timestamp": system_health.get('timestamp'),
                "system_metrics": system_health.get('system_metrics', {})
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting system health status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get health status: {str(e)}"
        )

@router.get("/services")
async def get_all_services_health():
    """Get detailed health status for all services"""
    
    if not HEALTH_CHECK_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check service not available"
        )
    
    try:
        system_health = await health_check_service.get_system_health()
        
        services_health = {}
        for service_name, service_data in system_health.get('services', {}).items():
            services_health[service_name] = {
                "service_name": service_data.get('service_name'),
                "overall_status": service_data.get('overall_status'),
                "uptime_percentage": service_data.get('uptime_percentage'),
                "health_checks_count": len(service_data.get('health_checks', [])),
                "slo_metrics_count": len(service_data.get('slo_metrics', [])),
                "dependencies": service_data.get('dependencies', []),
                "last_incident": service_data.get('last_incident')
            }
        
        return {
            "status": "success",
            "data": {
                "services": services_health,
                "total_services": len(services_health),
                "timestamp": system_health.get('timestamp')
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting services health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get services health: {str(e)}"
        )

@router.get("/service/{service_name}")
async def get_service_health(service_name: str):
    """Get detailed health status for a specific service"""
    
    if not HEALTH_CHECK_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check service not available"
        )
    
    try:
        service_health = await health_check_service.run_health_check(service_name)
        
        return {
            "status": "success",
            "data": {
                "service_name": service_health.service_name,
                "overall_status": service_health.overall_status.value,
                "uptime_percentage": service_health.uptime_percentage,
                "last_incident": service_health.last_incident,
                "dependencies": service_health.dependencies,
                "health_checks": [
                    {
                        "service": check.service,
                        "status": check.status.value,
                        "response_time_ms": check.response_time_ms,
                        "message": check.message,
                        "details": check.details,
                        "timestamp": check.timestamp,
                        "check_duration_ms": check.check_duration_ms
                    } for check in service_health.health_checks
                ],
                "slo_metrics": [
                    {
                        "metric_name": slo.metric_name,
                        "current_value": slo.current_value,
                        "target_value": slo.target_value,
                        "threshold_warning": slo.threshold_warning,
                        "threshold_critical": slo.threshold_critical,
                        "status": slo.status.value,
                        "measurement_window": slo.measurement_window,
                        "last_updated": slo.last_updated
                    } for slo in service_health.slo_metrics
                ]
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service not found: {service_name}"
        )
    except Exception as e:
        logger.error(f"❌ Error getting service health for {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service health: {str(e)}"
        )

@router.get("/slo")
async def get_slo_status():
    """Get SLO compliance status across all services"""
    
    if not HEALTH_CHECK_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check service not available"
        )
    
    try:
        system_health = await health_check_service.get_system_health()
        
        # Collect all SLO metrics
        all_slo_metrics = []
        slo_status_counts = {status.value: 0 for status in SLOStatus}
        
        for service_name, service_data in system_health.get('services', {}).items():
            for slo_metric in service_data.get('slo_metrics', []):
                slo_status_counts[slo_metric['status']] += 1
                all_slo_metrics.append({
                    "service": service_name,
                    "metric_name": slo_metric['metric_name'],
                    "current_value": slo_metric['current_value'],
                    "target_value": slo_metric['target_value'],
                    "status": slo_metric['status'],
                    "measurement_window": slo_metric['measurement_window'],
                    "last_updated": slo_metric['last_updated']
                })
        
        return {
            "status": "success",
            "data": {
                "slo_summary": system_health.get('slo_summary', {}),
                "slo_status_distribution": slo_status_counts,
                "slo_metrics": all_slo_metrics,
                "total_slos": len(all_slo_metrics),
                "timestamp": system_health.get('timestamp')
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting SLO status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SLO status: {str(e)}"
        )

@router.get("/metrics")
async def get_health_check_metrics():
    """Get health check service performance metrics"""
    
    if not HEALTH_CHECK_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check service not available"
        )
    
    try:
        metrics = health_check_service.get_health_metrics()
        
        return {
            "status": "success",
            "data": {
                "health_check_metrics": metrics,
                "service_enabled": metrics.get('health_check_enabled', False),
                "services_monitored": metrics.get('services_monitored', 0),
                "check_intervals": health_check_service.check_intervals,
                "slo_targets": health_check_service.slo_targets
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting health check metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get health check metrics: {str(e)}"
        )

@router.get("/dependencies")
async def get_service_dependencies():
    """Get service dependency map and health"""
    
    if not HEALTH_CHECK_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check service not available"
        )
    
    try:
        system_health = await health_check_service.get_system_health()
        
        # Build dependency map with health status
        dependency_map = {}
        for service_name, service_data in system_health.get('services', {}).items():
            dependencies = service_data.get('dependencies', [])
            dependency_map[service_name] = {
                "status": service_data.get('overall_status'),
                "dependencies": dependencies,
                "dependent_services": []
            }
        
        # Find dependent services (reverse dependencies)
        for service_name, service_info in dependency_map.items():
            for dependency in service_info['dependencies']:
                if dependency in dependency_map:
                    dependency_map[dependency]['dependent_services'].append(service_name)
        
        return {
            "status": "success",
            "data": {
                "dependency_map": dependency_map,
                "services_count": len(dependency_map),
                "timestamp": system_health.get('timestamp')
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting service dependencies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service dependencies: {str(e)}"
        )

@router.post("/service/{service_name}/check")
async def trigger_health_check(service_name: str):
    """Manually trigger a health check for a specific service"""
    
    if not HEALTH_CHECK_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check service not available"
        )
    
    try:
        service_health = await health_check_service.run_health_check(service_name)
        
        return {
            "status": "success",
            "message": f"Health check completed for {service_name}",
            "data": {
                "service_name": service_health.service_name,
                "overall_status": service_health.overall_status.value,
                "check_count": len(service_health.health_checks),
                "slo_metrics_count": len(service_health.slo_metrics),
                "uptime_percentage": service_health.uptime_percentage
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service not found: {service_name}"
        )
    except Exception as e:
        logger.error(f"❌ Error triggering health check for {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger health check: {str(e)}"
        )

@router.get("/alerts")
async def get_health_alerts(
    severity: Optional[str] = Query(None, description="Filter by alert severity"),
    limit: int = Query(50, description="Maximum number of alerts to return")
):
    """Get health-related alerts and incidents"""
    
    # For now, return basic alert structure
    # In production, this would integrate with a proper alerting system
    
    return {
        "status": "success",
        "data": {
            "alerts": [],
            "total_alerts": 0,
            "active_incidents": 0,
            "message": "Health alerts functionality available - integrate with alerting system",
            "timestamp": health_check_service.metrics.get('last_check_time', 0)
        }
    }

# Health check initialization endpoint
@router.post("/initialize")
async def initialize_health_checks():
    """Initialize or restart health check service"""
    
    if not HEALTH_CHECK_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check service not available"
        )
    
    try:
        await health_check_service.initialize()
        
        return {
            "status": "success",
            "message": "Health check service initialized successfully",
            "data": {
                "services_registered": len(health_check_service.services),
                "check_intervals": health_check_service.check_intervals,
                "enabled": health_check_service.enabled
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error initializing health checks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize health checks: {str(e)}"
        )