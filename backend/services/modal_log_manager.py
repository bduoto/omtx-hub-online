"""
Modal Log Management System
Provides fast retrieval, caching, and analysis of Modal execution logs
"""

import json
import re
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with timestamp"""
    data: Any
    timestamp: float

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class LogEntry:
    """Structured log entry from Modal"""
    timestamp: str
    level: LogLevel
    message: str
    source: str
    function_name: Optional[str] = None
    app_id: Optional[str] = None
    execution_id: Optional[str] = None
    raw_line: Optional[str] = None

@dataclass
class ExecutionSummary:
    """Summary of a Modal execution"""
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
    key_events: Optional[List[str]] = None

    def __post_init__(self):
        if self.key_events is None:
            self.key_events = []

class ModalLogManager:
    """
    High-performance Modal log manager with caching and analysis
    """
    
    def __init__(self, cache_dir: str = "/tmp/modal_logs"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.log_cache: Dict[str, CacheEntry] = {}
        self.execution_cache: Dict[str, CacheEntry] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def _run_modal_command(self, command: List[str], timeout: int = 30) -> Tuple[int, str, str]:
        """Run Modal CLI command with timeout"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path.cwd())
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Modal command timed out: {' '.join(command)}")
            return 1, "", "Command timed out"
        except Exception as e:
            logger.error(f"Error running modal command: {e}")
            return 1, "", str(e)
    
    def _parse_log_line(self, line: str, app_id: str) -> Optional[LogEntry]:
        """Parse a single log line from Modal"""
        if not line.strip():
            return None
            
        # Try to parse timestamp and level
        timestamp_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z?)'
        level_pattern = r'(DEBUG|INFO|WARNING|ERROR|CRITICAL)'
        
        # Look for structured log format
        structured_match = re.search(
            rf'{timestamp_pattern}\s+{level_pattern}:([^:]+):(.*)', 
            line
        )
        
        if structured_match:
            timestamp = structured_match.group(1)
            level_str = structured_match.group(2)
            source = structured_match.group(3)
            message = structured_match.group(4).strip()
            
            try:
                level = LogLevel(level_str)
            except ValueError:
                level = LogLevel.INFO
                
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                source=source,
                app_id=app_id,
                raw_line=line
            )
        
        # Fallback: try to extract basic info patterns
        basic_patterns = [
            (r'INFO:([^:]+):(.*)', LogLevel.INFO),
            (r'ERROR:([^:]+):(.*)', LogLevel.ERROR),
            (r'WARNING:([^:]+):(.*)', LogLevel.WARNING),
            (r'DEBUG:([^:]+):(.*)', LogLevel.DEBUG),
        ]
        
        for pattern, level in basic_patterns:
            match = re.search(pattern, line)
            if match:
                source = match.group(1)
                message = match.group(2).strip()
                
                return LogEntry(
                    timestamp=datetime.utcnow().isoformat(),
                    level=level,
                    message=message,
                    source=source,
                    app_id=app_id,
                    raw_line=line
                )
        
        # If no pattern matches, create a generic entry
        return LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=LogLevel.INFO,
            message=line.strip(),
            source="unknown",
            app_id=app_id,
            raw_line=line
        )
    
    def get_app_list(self) -> List[Dict[str, Any]]:
        """Get list of Modal apps"""
        returncode, stdout, stderr = self._run_modal_command(['modal', 'app', 'list'])
        
        if returncode != 0:
            logger.error(f"Failed to get app list: {stderr}")
            return []
        
        apps = []
        lines = stdout.strip().split('\n')
        
        # Skip header lines and parse app data
        for line in lines:
            if line.strip() and not line.startswith('┃') and not line.startswith('┏'):
                # Parse app line - format: │ app_id │ description │ state │ tasks │ created │ stopped │
                parts = [p.strip() for p in line.split('│') if p.strip()]
                if len(parts) >= 4:
                    app_id = parts[0]
                    description = parts[1]
                    state = parts[2]
                    tasks = parts[3]
                    created = parts[4] if len(parts) > 4 else ""
                    
                    apps.append({
                        'app_id': app_id,
                        'name': description,
                        'state': state,
                        'tasks': tasks,
                        'created': created
                    })
        
        return apps
    
    def get_app_logs(self, app_identifier: str, limit: int = 1000) -> List[LogEntry]:
        """Get logs for a specific app"""
        cache_key = f"{app_identifier}_{limit}"
        
        # Check cache first
        if cache_key in self.log_cache:
            cache_entry = self.log_cache[cache_key]
            if time.time() - cache_entry.timestamp < 30:  # Cache for 30 seconds
                return cache_entry.data
        
        # Get logs from Modal
        returncode, stdout, stderr = self._run_modal_command([
            'modal', 'app', 'logs', app_identifier, '--timestamps'
        ], timeout=60)
        
        if returncode != 0:
            logger.error(f"Failed to get logs for {app_identifier}: {stderr}")
            return []
        
        # Parse logs
        logs = []
        lines = stdout.strip().split('\n')
        
        for line in lines[-limit:]:  # Get last N lines
            log_entry = self._parse_log_line(line, app_identifier)
            if log_entry:
                logs.append(log_entry)
        
        # Cache the results
        self.log_cache[cache_key] = CacheEntry(data=logs, timestamp=time.time())
        
        return logs
    
    def analyze_execution(self, app_identifier: str) -> ExecutionSummary:
        """Analyze a Modal execution and provide summary"""
        if app_identifier in self.execution_cache:
            cache_entry = self.execution_cache[app_identifier]
            if time.time() - cache_entry.timestamp < 60:  # Cache for 1 minute
                return cache_entry.data
        
        # Get logs for analysis
        logs = self.get_app_logs(app_identifier, limit=2000)
        
        if not logs:
            return ExecutionSummary(
                app_id=app_identifier,
                app_name="Unknown",
                status="no_logs",
                total_logs=0,
                error_count=0,
                warning_count=0
            )
        
        # Analyze logs
        error_count = sum(1 for log in logs if log.level == LogLevel.ERROR)
        warning_count = sum(1 for log in logs if log.level == LogLevel.WARNING)
        
        # Find key events
        key_events = []
        last_error = None
        
        for log in logs:
            if log.level == LogLevel.ERROR:
                last_error = log.message
                key_events.append(f"ERROR: {log.message[:100]}...")
            elif "Starting" in log.message or "started" in log.message.lower():
                key_events.append(f"STARTED: {log.message[:100]}...")
            elif "completed" in log.message.lower() or "finished" in log.message.lower():
                key_events.append(f"COMPLETED: {log.message[:100]}...")
            elif "failed" in log.message.lower():
                key_events.append(f"FAILED: {log.message[:100]}...")
        
        # Determine status
        if error_count > 0:
            status = "failed"
        elif any("completed" in event.lower() for event in key_events):
            status = "completed"
        elif any("started" in event.lower() for event in key_events):
            status = "running"
        else:
            status = "unknown"
        
        # Calculate timing
        start_time = logs[0].timestamp if logs else None
        end_time = logs[-1].timestamp if logs else None
        duration = None
        
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration = (end_dt - start_dt).total_seconds()
            except Exception:
                pass
        
        summary = ExecutionSummary(
            app_id=app_identifier,
            app_name=app_identifier,
            status=status,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            total_logs=len(logs),
            error_count=error_count,
            warning_count=warning_count,
            last_error=last_error,
            key_events=key_events[-10:]  # Keep last 10 key events
        )
        
        # Cache the summary
        self.execution_cache[app_identifier] = CacheEntry(data=summary, timestamp=time.time())
        
        return summary
    
    def get_recent_executions(self, limit: int = 10) -> List[ExecutionSummary]:
        """Get recent Modal executions with summaries"""
        apps = self.get_app_list()
        
        # Sort by creation time (most recent first)
        apps.sort(key=lambda x: x.get('created', ''), reverse=True)
        
        summaries = []
        for app in apps[:limit]:
            app_id = app['app_id']
            summary = self.analyze_execution(app_id)
            summary.app_name = app['name']
            summaries.append(summary)
        
        return summaries
    
    def search_logs(self, query: str, app_identifier: Optional[str] = None, 
                   level: Optional[LogLevel] = None) -> List[LogEntry]:
        """Search logs with filters"""
        if app_identifier:
            logs = self.get_app_logs(app_identifier)
        else:
            # Search across recent apps
            logs = []
            recent_apps = self.get_app_list()[:5]  # Search last 5 apps
            for app in recent_apps:
                logs.extend(self.get_app_logs(app['app_id'], limit=500))
        
        # Filter logs
        filtered_logs = []
        for log in logs:
            if level and log.level != level:
                continue
            if query.lower() in log.message.lower():
                filtered_logs.append(log)
        
        return filtered_logs
    
    def get_error_analysis(self, app_identifier: str) -> Dict[str, Any]:
        """Get detailed error analysis for an execution"""
        logs = self.get_app_logs(app_identifier)
        errors = [log for log in logs if log.level == LogLevel.ERROR]
        
        if not errors:
            return {
                'error_count': 0,
                'errors': [],
                'common_patterns': [],
                'suggestions': []
            }
        
        # Analyze error patterns
        error_patterns = {}
        for error in errors:
            # Extract error type from message
            if 'KeyError' in error.message:
                error_patterns['KeyError'] = error_patterns.get('KeyError', 0) + 1
            elif 'FileNotFoundError' in error.message:
                error_patterns['FileNotFoundError'] = error_patterns.get('FileNotFoundError', 0) + 1
            elif 'sequences' in error.message:
                error_patterns['Schema Error'] = error_patterns.get('Schema Error', 0) + 1
            elif 'RuntimeError' in error.message:
                error_patterns['Runtime Error'] = error_patterns.get('Runtime Error', 0) + 1
            else:
                error_patterns['Other'] = error_patterns.get('Other', 0) + 1
        
        # Generate suggestions
        suggestions = []
        if 'KeyError' in error_patterns and 'sequences' in str(errors):
            suggestions.append("Check YAML schema format - use 'sequences' instead of 'molecules'")
        if 'FileNotFoundError' in error_patterns:
            suggestions.append("Check file paths and ensure all required files exist")
        if 'Schema Error' in error_patterns:
            suggestions.append("Verify input format matches expected schema")
        
        return {
            'error_count': len(errors),
            'errors': [asdict(error) for error in errors[-10:]],  # Last 10 errors
            'common_patterns': error_patterns,
            'suggestions': suggestions
        }
    
    async def get_logs_async(self, app_identifier: str, limit: int = 1000) -> List[LogEntry]:
        """Async version of get_app_logs"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self.get_app_logs, 
            app_identifier, 
            limit
        )
    
    def clear_cache(self):
        """Clear all caches"""
        self.log_cache.clear()
        self.execution_cache.clear()
        logger.info("Log cache cleared")

# Global instance
modal_log_manager = ModalLogManager() 