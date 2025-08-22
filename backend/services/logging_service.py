"""
Logging Service for OMTX-Hub
Structured logging configuration for GKE and Cloud Run
"""

import os
import json
import logging
import logging.handlers
from typing import Dict, Any, Optional
from datetime import datetime
from google.cloud import logging as gcp_logging
from google.cloud.logging.handlers import CloudLoggingHandler

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add service information
        log_entry['service'] = {
            'name': os.getenv('SERVICE_NAME', 'omtx-hub-api'),
            'version': os.getenv('SERVICE_VERSION', '1.0.0'),
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'instance': os.getenv('HOSTNAME', 'unknown')
        }
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'job_id'):
            log_entry['job_id'] = record.job_id
        
        # Add exception information
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        # Add performance metrics
        if hasattr(record, 'duration'):
            log_entry['performance'] = {
                'duration_ms': record.duration,
                'operation': getattr(record, 'operation', 'unknown')
            }
        
        # Add alert data for monitoring
        if hasattr(record, 'alert_data'):
            log_entry['alert'] = record.alert_data
        
        return json.dumps(log_entry, default=str)

class LoggingService:
    """Service for configuring application-wide logging"""
    
    def __init__(self):
        self.project_id = os.getenv('GCP_PROJECT_ID', 'om-models')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.service_name = os.getenv('SERVICE_NAME', 'omtx-hub-api')
        
        self.log_level = self._get_log_level()
        self.use_cloud_logging = self.environment == 'production'
        
        self._setup_logging()
    
    def _get_log_level(self) -> int:
        """Get log level from environment"""
        
        level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        return getattr(logging, level_str, logging.INFO)
    
    def _setup_logging(self):
        """Configure application logging"""
        
        # Remove default handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Set root log level
        root_logger.setLevel(self.log_level)
        
        if self.use_cloud_logging:
            self._setup_cloud_logging()
        else:
            self._setup_local_logging()
        
        # Configure specific loggers
        self._configure_specific_loggers()
        
        # Log startup message
        logger = logging.getLogger(__name__)
        logger.info(
            "📝 Logging service initialized",
            extra={
                'extra_data': {
                    'environment': self.environment,
                    'log_level': logging.getLevelName(self.log_level),
                    'cloud_logging': self.use_cloud_logging,
                    'service': self.service_name
                }
            }
        )
    
    def _setup_cloud_logging(self):
        """Setup Google Cloud Logging for production"""
        
        try:
            # Initialize Cloud Logging client
            client = gcp_logging.Client(project=self.project_id)
            
            # Create Cloud Logging handler
            cloud_handler = CloudLoggingHandler(
                client,
                name=self.service_name,
                labels={
                    'service_name': self.service_name,
                    'environment': self.environment,
                    'version': os.getenv('SERVICE_VERSION', '1.0.0')
                }
            )
            
            # Use structured formatter for Cloud Logging too
            cloud_handler.setFormatter(StructuredFormatter())
            
            # Add to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(cloud_handler)
            
            # Also add console handler for local debugging
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(StructuredFormatter())
            root_logger.addHandler(console_handler)
            
        except Exception as e:
            # Fallback to local logging if Cloud Logging fails
            print(f"Failed to setup Cloud Logging: {e}")
            self._setup_local_logging()
    
    def _setup_local_logging(self):
        """Setup local file and console logging for development"""
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(StructuredFormatter())
        
        # File handler
        log_file = os.path.join(os.getcwd(), 'logs', f'{self.service_name}.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5
        )
        file_handler.setFormatter(StructuredFormatter())
        
        # Add handlers to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    def _configure_specific_loggers(self):
        """Configure specific logger behaviors"""
        
        # Suppress noisy third-party loggers
        noisy_loggers = [
            'urllib3.connectionpool',
            'google.auth.transport.requests',
            'google.cloud.logging_v2.handlers.transports.background_thread',
            'kubernetes.client.rest'
        ]
        
        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)
        
        # Configure our application loggers with appropriate levels
        app_loggers = {
            'services.gpu_worker_service': logging.INFO,
            'services.job_submission_service': logging.INFO,
            'services.monitoring_service': logging.INFO,
            'services.webhook_service': logging.INFO,
            'api.consolidated_api': logging.INFO,
            'database.unified_job_manager': logging.INFO
        }
        
        for logger_name, level in app_loggers.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
    
    def create_logger(self, name: str, extra_context: Optional[Dict[str, Any]] = None) -> logging.Logger:
        """Create a logger with additional context"""
        
        logger = logging.getLogger(name)
        
        if extra_context:
            # Create a custom adapter that adds extra context
            class ContextAdapter(logging.LoggerAdapter):
                def process(self, msg, kwargs):
                    kwargs.setdefault('extra', {}).update(extra_context)
                    return msg, kwargs
            
            return ContextAdapter(logger, extra_context)
        
        return logger

# Context managers for request/job logging
class RequestLoggingContext:
    """Context manager for request-scoped logging"""
    
    def __init__(self, request_id: str, user_id: Optional[str] = None):
        self.request_id = request_id
        self.user_id = user_id
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        logger = logging.getLogger('request')
        logger.info(
            f"Request completed",
            extra={
                'request_id': self.request_id,
                'user_id': self.user_id,
                'duration': duration,
                'operation': 'api_request',
                'success': exc_type is None
            }
        )

class JobLoggingContext:
    """Context manager for job-scoped logging"""
    
    def __init__(self, job_id: str, user_id: str, job_type: str):
        self.job_id = job_id
        self.user_id = user_id
        self.job_type = job_type
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        
        logger = logging.getLogger('job')
        logger.info(
            f"Job started: {self.job_type}",
            extra={
                'job_id': self.job_id,
                'user_id': self.user_id,
                'extra_data': {
                    'job_type': self.job_type,
                    'stage': 'start'
                }
            }
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        logger = logging.getLogger('job')
        
        if exc_type is None:
            logger.info(
                f"Job completed: {self.job_type}",
                extra={
                    'job_id': self.job_id,
                    'user_id': self.user_id,
                    'duration': duration,
                    'operation': 'job_execution',
                    'extra_data': {
                        'job_type': self.job_type,
                        'stage': 'complete',
                        'success': True
                    }
                }
            )
        else:
            logger.error(
                f"Job failed: {self.job_type}",
                extra={
                    'job_id': self.job_id,
                    'user_id': self.user_id,
                    'duration': duration,
                    'operation': 'job_execution',
                    'extra_data': {
                        'job_type': self.job_type,
                        'stage': 'failed',
                        'success': False,
                        'error_type': exc_type.__name__ if exc_type else None
                    }
                },
                exc_info=(exc_type, exc_val, exc_tb)
            )

# Performance logging decorator
def log_performance(operation_name: str):
    """Decorator to log function performance"""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            logger = logging.getLogger(func.__module__)
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                logger.debug(
                    f"Operation completed: {operation_name}",
                    extra={
                        'duration': duration,
                        'operation': operation_name,
                        'function': func.__name__,
                        'success': True
                    }
                )
                
                return result
                
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                logger.error(
                    f"Operation failed: {operation_name}",
                    extra={
                        'duration': duration,
                        'operation': operation_name,
                        'function': func.__name__,
                        'success': False,
                        'error': str(e)
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator

# Security logging functions
def log_security_event(event_type: str, user_id: Optional[str], details: Dict[str, Any]):
    """Log security-related events"""
    
    logger = logging.getLogger('security')
    logger.warning(
        f"Security event: {event_type}",
        extra={
            'user_id': user_id,
            'extra_data': {
                'event_type': event_type,
                'details': details,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
    )

def log_authentication_event(event: str, user_id: Optional[str], success: bool, ip_address: Optional[str] = None):
    """Log authentication events"""
    
    logger = logging.getLogger('auth')
    level = logging.INFO if success else logging.WARNING
    
    logger.log(
        level,
        f"Authentication {event}: {'success' if success else 'failure'}",
        extra={
            'user_id': user_id,
            'extra_data': {
                'auth_event': event,
                'success': success,
                'ip_address': ip_address,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
    )

# Global logging service instance
logging_service = LoggingService()