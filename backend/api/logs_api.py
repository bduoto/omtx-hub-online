"""
FastAPI endpoints for Modal log management and analysis
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from dataclasses import asdict
import logging

from services.modal_log_manager import modal_log_manager, LogLevel

logger = logging.getLogger(__name__)

# Create router
logs_router = APIRouter(prefix="/logs", tags=["logs"])

# Pydantic models for API responses
class LogEntryResponse(BaseModel):
    timestamp: str
    level: str
    message: str
    source: str
    function_name: Optional[str] = None
    app_id: Optional[str] = None
    execution_id: Optional[str] = None
    raw_line: Optional[str] = None

class ExecutionSummaryResponse(BaseModel):
    app_id: str
    app_name: str
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: Optional[float] = None
    total_logs: int = 0
    error_count: int = 0
    warning_count: int = 0
    last_error: Optional[str] = None
    key_events: List[str] = []

class AppResponse(BaseModel):
    app_id: str
    name: str
    state: str
    tasks: str
    created: str

class ErrorAnalysisResponse(BaseModel):
    error_count: int
    errors: List[LogEntryResponse]
    common_patterns: Dict[str, int]
    suggestions: List[str]

@logs_router.get("/apps", response_model=List[AppResponse])
async def get_apps():
    """Get list of Modal apps"""
    try:
        apps = modal_log_manager.get_app_list()
        return [AppResponse(**app) for app in apps]
    except Exception as e:
        logger.error(f"Error getting apps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@logs_router.get("/apps/{app_id}/logs", response_model=List[LogEntryResponse])
async def get_app_logs(
    app_id: str,
    limit: int = Query(default=1000, ge=1, le=5000, description="Number of log entries to retrieve")
):
    """Get logs for a specific app"""
    try:
        logs = modal_log_manager.get_app_logs(app_id, limit)
        return [
            LogEntryResponse(
                timestamp=log.timestamp,
                level=log.level.value,
                message=log.message,
                source=log.source,
                function_name=log.function_name,
                app_id=log.app_id,
                execution_id=log.execution_id,
                raw_line=log.raw_line
            )
            for log in logs
        ]
    except Exception as e:
        logger.error(f"Error getting logs for {app_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@logs_router.get("/apps/{app_id}/summary", response_model=ExecutionSummaryResponse)
async def get_execution_summary(app_id: str):
    """Get execution summary for a specific app"""
    try:
        summary = modal_log_manager.analyze_execution(app_id)
        return ExecutionSummaryResponse(**asdict(summary))
    except Exception as e:
        logger.error(f"Error analyzing execution {app_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@logs_router.get("/apps/{app_id}/errors", response_model=ErrorAnalysisResponse)
async def get_error_analysis(app_id: str):
    """Get detailed error analysis for an execution"""
    try:
        analysis = modal_log_manager.get_error_analysis(app_id)
        
        # Convert error entries to response format
        error_responses = []
        for error_dict in analysis['errors']:
            error_responses.append(LogEntryResponse(**error_dict))
        
        return ErrorAnalysisResponse(
            error_count=analysis['error_count'],
            errors=error_responses,
            common_patterns=analysis['common_patterns'],
            suggestions=analysis['suggestions']
        )
    except Exception as e:
        logger.error(f"Error analyzing errors for {app_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@logs_router.get("/recent", response_model=List[ExecutionSummaryResponse])
async def get_recent_executions(
    limit: int = Query(default=10, ge=1, le=50, description="Number of recent executions to retrieve")
):
    """Get recent Modal executions with summaries"""
    try:
        summaries = modal_log_manager.get_recent_executions(limit)
        return [ExecutionSummaryResponse(**asdict(summary)) for summary in summaries]
    except Exception as e:
        logger.error(f"Error getting recent executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@logs_router.get("/search", response_model=List[LogEntryResponse])
async def search_logs(
    query: str = Query(..., description="Search query"),
    app_id: Optional[str] = Query(None, description="Specific app to search"),
    level: Optional[str] = Query(None, description="Log level filter (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
):
    """Search logs with filters"""
    try:
        log_level = None
        if level:
            try:
                log_level = LogLevel(level.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid log level: {level}")
        
        logs = modal_log_manager.search_logs(query, app_id, log_level)
        return [
            LogEntryResponse(
                timestamp=log.timestamp,
                level=log.level.value,
                message=log.message,
                source=log.source,
                function_name=log.function_name,
                app_id=log.app_id,
                execution_id=log.execution_id,
                raw_line=log.raw_line
            )
            for log in logs
        ]
    except Exception as e:
        logger.error(f"Error searching logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@logs_router.post("/cache/clear")
async def clear_cache():
    """Clear log cache"""
    try:
        modal_log_manager.clear_cache()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@logs_router.get("/boltz2/latest", response_model=ExecutionSummaryResponse)
async def get_latest_boltz2_execution():
    """Get the latest Boltz-2 execution with detailed analysis"""
    try:
        apps = modal_log_manager.get_app_list()
        
        # Find the most recent boltz2-predictor app
        boltz2_apps = [app for app in apps if 'boltz2-predictor' in app.get('name', '').lower()]
        
        if not boltz2_apps:
            raise HTTPException(status_code=404, detail="No Boltz-2 executions found")
        
        # Get the most recent one
        latest_app = max(boltz2_apps, key=lambda x: x.get('created', ''))
        
        # Get detailed analysis
        summary = modal_log_manager.analyze_execution(latest_app['app_id'])
        summary.app_name = latest_app['name']
        
        return ExecutionSummaryResponse(**asdict(summary))
        
    except Exception as e:
        logger.error(f"Error getting latest Boltz-2 execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@logs_router.get("/boltz2/latest/logs", response_model=List[LogEntryResponse])
async def get_latest_boltz2_logs(
    limit: int = Query(default=500, ge=1, le=2000, description="Number of log entries to retrieve")
):
    """Get logs from the latest Boltz-2 execution"""
    try:
        apps = modal_log_manager.get_app_list()
        
        # Find the most recent boltz2-predictor app
        boltz2_apps = [app for app in apps if 'boltz2-predictor' in app.get('name', '').lower()]
        
        if not boltz2_apps:
            raise HTTPException(status_code=404, detail="No Boltz-2 executions found")
        
        # Get the most recent one
        latest_app = max(boltz2_apps, key=lambda x: x.get('created', ''))
        
        # Get logs
        logs = modal_log_manager.get_app_logs(latest_app['app_id'], limit)
        
        return [
            LogEntryResponse(
                timestamp=log.timestamp,
                level=log.level.value,
                message=log.message,
                source=log.source,
                function_name=log.function_name,
                app_id=log.app_id,
                execution_id=log.execution_id,
                raw_line=log.raw_line
            )
            for log in logs
        ]
        
    except Exception as e:
        logger.error(f"Error getting latest Boltz-2 logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@logs_router.get("/boltz2/latest/errors", response_model=ErrorAnalysisResponse)
async def get_latest_boltz2_errors():
    """Get error analysis from the latest Boltz-2 execution"""
    try:
        apps = modal_log_manager.get_app_list()
        
        # Find the most recent boltz2-predictor app
        boltz2_apps = [app for app in apps if 'boltz2-predictor' in app.get('name', '').lower()]
        
        if not boltz2_apps:
            raise HTTPException(status_code=404, detail="No Boltz-2 executions found")
        
        # Get the most recent one
        latest_app = max(boltz2_apps, key=lambda x: x.get('created', ''))
        
        # Get error analysis
        analysis = modal_log_manager.get_error_analysis(latest_app['app_id'])
        
        # Convert error entries to response format
        error_responses = []
        for error_dict in analysis['errors']:
            error_responses.append(LogEntryResponse(**error_dict))
        
        return ErrorAnalysisResponse(
            error_count=analysis['error_count'],
            errors=error_responses,
            common_patterns=analysis['common_patterns'],
            suggestions=analysis['suggestions']
        )
        
    except Exception as e:
        logger.error(f"Error getting latest Boltz-2 errors: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 