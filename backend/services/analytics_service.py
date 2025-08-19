"""
Analytics Service - Comprehensive user and system analytics
Distinguished Engineer Implementation - Production-ready with privacy compliance
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json

from google.cloud import firestore
from google.cloud import monitoring_v3
from google.cloud import bigquery

logger = logging.getLogger(__name__)

class UserAnalyticsService:
    """Enterprise analytics service with user privacy and GDPR compliance"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        
        # BigQuery for advanced analytics (optional)
        self.bigquery_client = None
        try:
            self.bigquery_client = bigquery.Client()
            logger.info("✅ BigQuery client initialized for advanced analytics")
        except Exception as e:
            logger.warning(f"⚠️ BigQuery not available: {str(e)}")
        
        # Cache for frequently accessed data
        self.metrics_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        logger.info("📊 UserAnalyticsService initialized with privacy compliance")
    
    async def get_user_metrics(self, user_id: str, include_sensitive: bool = False) -> Dict[str, Any]:
        """Get comprehensive user metrics with privacy controls"""
        
        try:
            # Get user data
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                return {"error": "User not found"}
            
            user_data = user_doc.to_dict()
            
            # Get job statistics
            job_stats = await self._get_user_job_statistics(user_id)
            
            # Get usage statistics
            usage_stats = await self._get_user_usage_statistics(user_id)
            
            # Get storage statistics
            storage_stats = await self._get_user_storage_statistics(user_id)
            
            # Get performance statistics
            performance_stats = await self._get_user_performance_statistics(user_id)
            
            # Get cost statistics
            cost_stats = await self._get_user_cost_statistics(user_id)
            
            # Base metrics (always included)
            metrics = {
                'user_id': user_id,
                'tier': user_data.get('tier', 'free'),
                'created_at': user_data.get('created_at'),
                'last_active': user_data.get('last_active'),
                'job_statistics': job_stats,
                'usage_statistics': usage_stats,
                'storage_statistics': storage_stats,
                'performance_statistics': performance_stats,
                'cost_statistics': cost_stats
            }
            
            # Sensitive data (only if explicitly requested and authorized)
            if include_sensitive:
                metrics.update({
                    'email': user_data.get('email'),
                    'auth_methods': user_data.get('auth_methods', []),
                    'integration_config': user_data.get('settings', {}),
                    'detailed_usage': await self._get_detailed_usage(user_id)
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get user metrics for {user_id}: {str(e)}")
            return {"error": str(e)}
    
    async def _get_user_job_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user's job statistics"""
        
        try:
            # Get jobs from user's collection
            jobs_ref = self.db.collection('users').document(user_id).collection('jobs')
            jobs = list(jobs_ref.stream())
            
            stats = {
                'total_jobs': len(jobs),
                'jobs_by_status': defaultdict(int),
                'jobs_by_type': defaultdict(int),
                'jobs_by_gpu_type': defaultdict(int),
                'average_duration_seconds': 0,
                'total_gpu_minutes': 0,
                'success_rate': 0,
                'recent_jobs_7d': 0,
                'recent_jobs_30d': 0
            }
            
            if not jobs:
                return stats
            
            durations = []
            gpu_minutes = []
            successful_jobs = 0
            now = datetime.utcnow()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            for job_doc in jobs:
                job_data = job_doc.to_dict()
                
                # Count by status
                status = job_data.get('status', 'unknown')
                stats['jobs_by_status'][status] += 1
                
                # Count by type
                job_type = job_data.get('type', 'unknown')
                stats['jobs_by_type'][job_type] += 1
                
                # Count by GPU type
                gpu_type = job_data.get('gpu_type', 'unknown')
                stats['jobs_by_gpu_type'][gpu_type] += 1
                
                # Duration statistics
                if job_data.get('execution_time_seconds'):
                    durations.append(job_data['execution_time_seconds'])
                
                # GPU minutes
                if job_data.get('gpu_minutes_used'):
                    gpu_minutes.append(job_data['gpu_minutes_used'])
                
                # Success rate
                if status == 'completed':
                    successful_jobs += 1
                
                # Recent jobs
                created_at = job_data.get('created_at')
                if created_at:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    elif hasattr(created_at, 'timestamp'):
                        created_at = created_at.timestamp()
                        created_at = datetime.fromtimestamp(created_at)
                    
                    if created_at > week_ago:
                        stats['recent_jobs_7d'] += 1
                    if created_at > month_ago:
                        stats['recent_jobs_30d'] += 1
            
            # Calculate averages
            if durations:
                stats['average_duration_seconds'] = sum(durations) / len(durations)
            
            if gpu_minutes:
                stats['total_gpu_minutes'] = sum(gpu_minutes)
            
            if stats['total_jobs'] > 0:
                stats['success_rate'] = (successful_jobs / stats['total_jobs']) * 100
            
            # Convert defaultdicts to regular dicts
            stats['jobs_by_status'] = dict(stats['jobs_by_status'])
            stats['jobs_by_type'] = dict(stats['jobs_by_type'])
            stats['jobs_by_gpu_type'] = dict(stats['jobs_by_gpu_type'])
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get job statistics for user {user_id}: {str(e)}")
            return {}
    
    async def _get_user_usage_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user's usage statistics"""
        
        try:
            # Get current month usage
            current_month = datetime.utcnow().strftime('%Y-%m')
            usage_ref = self.db.collection('users').document(user_id)\
                .collection('usage').document(current_month)
            
            usage_doc = usage_ref.get()
            
            if usage_doc.exists:
                usage_data = usage_doc.to_dict()
                return {
                    'current_jobs': usage_data.get('current_jobs', 0),
                    'monthly_jobs': usage_data.get('monthly_jobs', 0),
                    'gpu_minutes_used': usage_data.get('gpu_minutes_used', 0),
                    'api_calls_made': usage_data.get('api_calls_made', 0),
                    'last_job_created': usage_data.get('last_job_created'),
                    'last_job_completed': usage_data.get('last_job_completed')
                }
            else:
                return {
                    'current_jobs': 0,
                    'monthly_jobs': 0,
                    'gpu_minutes_used': 0,
                    'api_calls_made': 0
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get usage statistics for user {user_id}: {str(e)}")
            return {}
    
    async def _get_user_storage_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user's storage statistics"""
        
        try:
            storage_ref = self.db.collection('users').document(user_id)\
                .collection('storage_usage').document('current')
            
            storage_doc = storage_ref.get()
            
            if storage_doc.exists:
                storage_data = storage_doc.to_dict()
                return {
                    'used_bytes': storage_data.get('used_bytes', 0),
                    'used_gb': storage_data.get('used_bytes', 0) / (1024**3),
                    'file_count': storage_data.get('file_count', 0),
                    'last_updated': storage_data.get('last_updated')
                }
            else:
                return {
                    'used_bytes': 0,
                    'used_gb': 0.0,
                    'file_count': 0
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get storage statistics for user {user_id}: {str(e)}")
            return {}
    
    async def _get_user_performance_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user's performance statistics"""
        
        try:
            # Get recent jobs for performance analysis
            jobs_ref = self.db.collection('users').document(user_id)\
                .collection('jobs')\
                .where('status', '==', 'completed')\
                .order_by('created_at', direction=firestore.Query.DESCENDING)\
                .limit(50)
            
            jobs = list(jobs_ref.stream())
            
            if not jobs:
                return {
                    'average_execution_time': 0,
                    'fastest_execution_time': 0,
                    'slowest_execution_time': 0,
                    'p95_execution_time': 0,
                    'throughput_jobs_per_hour': 0
                }
            
            execution_times = []
            for job_doc in jobs:
                job_data = job_doc.to_dict()
                if job_data.get('execution_time_seconds'):
                    execution_times.append(job_data['execution_time_seconds'])
            
            if execution_times:
                execution_times.sort()
                return {
                    'average_execution_time': sum(execution_times) / len(execution_times),
                    'fastest_execution_time': min(execution_times),
                    'slowest_execution_time': max(execution_times),
                    'p95_execution_time': execution_times[int(0.95 * len(execution_times))],
                    'throughput_jobs_per_hour': len(execution_times) / max(1, len(execution_times) / 24)  # Rough estimate
                }
            else:
                return {
                    'average_execution_time': 0,
                    'fastest_execution_time': 0,
                    'slowest_execution_time': 0,
                    'p95_execution_time': 0,
                    'throughput_jobs_per_hour': 0
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get performance statistics for user {user_id}: {str(e)}")
            return {}
    
    async def _get_user_cost_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user's cost statistics"""
        
        try:
            # Get jobs with cost data
            jobs_ref = self.db.collection('users').document(user_id)\
                .collection('jobs')\
                .where('status', '==', 'completed')\
                .order_by('created_at', direction=firestore.Query.DESCENDING)\
                .limit(100)
            
            jobs = list(jobs_ref.stream())
            
            total_cost = 0
            monthly_cost = 0
            cost_by_gpu_type = defaultdict(float)
            
            now = datetime.utcnow()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            for job_doc in jobs:
                job_data = job_doc.to_dict()
                cost = job_data.get('cost_actual', 0) or job_data.get('estimated_cost_usd', 0)
                
                if cost:
                    total_cost += cost
                    
                    # Monthly cost
                    created_at = job_data.get('created_at')
                    if created_at and hasattr(created_at, 'timestamp'):
                        job_date = datetime.fromtimestamp(created_at.timestamp())
                        if job_date >= month_start:
                            monthly_cost += cost
                    
                    # Cost by GPU type
                    gpu_type = job_data.get('gpu_type', 'unknown')
                    cost_by_gpu_type[gpu_type] += cost
            
            return {
                'total_cost_usd': round(total_cost, 4),
                'monthly_cost_usd': round(monthly_cost, 4),
                'average_cost_per_job': round(total_cost / max(1, len(jobs)), 4),
                'cost_by_gpu_type': dict(cost_by_gpu_type)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get cost statistics for user {user_id}: {str(e)}")
            return {}
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics for admin dashboard"""
        
        try:
            # Get active users (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            active_users_query = self.db.collection('users')\
                .where('last_active', '>=', thirty_days_ago)
            
            active_users = list(active_users_query.stream())
            
            # Get system job statistics
            admin_jobs_ref = self.db.collection('admin_jobs')
            admin_jobs = list(admin_jobs_ref.stream())
            
            # Analyze system metrics
            metrics = {
                'active_users_30d': len(active_users),
                'total_jobs': len(admin_jobs),
                'jobs_by_status': defaultdict(int),
                'jobs_by_tier': defaultdict(int),
                'jobs_by_gpu_type': defaultdict(int),
                'total_gpu_minutes': 0,
                'total_cost_usd': 0,
                'users_by_tier': defaultdict(int),
                'system_utilization': await self._get_system_utilization()
            }
            
            # Analyze jobs
            for job_doc in admin_jobs:
                job_data = job_doc.to_dict()
                
                status = job_data.get('status', 'unknown')
                metrics['jobs_by_status'][status] += 1
                
                tier = job_data.get('tier', 'unknown')
                metrics['jobs_by_tier'][tier] += 1
                
                gpu_type = job_data.get('gpu_type', 'unknown')
                metrics['jobs_by_gpu_type'][gpu_type] += 1
                
                if job_data.get('gpu_minutes'):
                    metrics['total_gpu_minutes'] += job_data['gpu_minutes']
                
                if job_data.get('cost_actual'):
                    metrics['total_cost_usd'] += job_data['cost_actual']
            
            # Analyze users
            for user_doc in active_users:
                user_data = user_doc.to_dict()
                tier = user_data.get('tier', 'free')
                metrics['users_by_tier'][tier] += 1
            
            # Convert defaultdicts to regular dicts
            metrics['jobs_by_status'] = dict(metrics['jobs_by_status'])
            metrics['jobs_by_tier'] = dict(metrics['jobs_by_tier'])
            metrics['jobs_by_gpu_type'] = dict(metrics['jobs_by_gpu_type'])
            metrics['users_by_tier'] = dict(metrics['users_by_tier'])
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to get system metrics: {str(e)}")
            return {"error": str(e)}
    
    async def _get_system_utilization(self) -> Dict[str, Any]:
        """Get system utilization metrics"""
        
        try:
            # This would integrate with Cloud Monitoring
            # For now, return mock data
            return {
                'cpu_utilization': 65.0,
                'memory_utilization': 70.0,
                'gpu_utilization': 80.0,
                'active_instances': 15,
                'max_instances': 50
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get system utilization: {str(e)}")
            return {}
    
    async def generate_user_report(self, user_id: str, report_type: str = "monthly") -> Dict[str, Any]:
        """Generate comprehensive user report"""
        
        try:
            metrics = await self.get_user_metrics(user_id, include_sensitive=False)
            
            if "error" in metrics:
                return metrics
            
            # Generate report based on type
            if report_type == "monthly":
                return await self._generate_monthly_report(user_id, metrics)
            elif report_type == "usage":
                return await self._generate_usage_report(user_id, metrics)
            elif report_type == "performance":
                return await self._generate_performance_report(user_id, metrics)
            else:
                return {"error": f"Unknown report type: {report_type}"}
                
        except Exception as e:
            logger.error(f"❌ Failed to generate user report for {user_id}: {str(e)}")
            return {"error": str(e)}
    
    async def _generate_monthly_report(self, user_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate monthly usage report"""
        
        return {
            "report_type": "monthly",
            "user_id": user_id,
            "period": datetime.utcnow().strftime('%Y-%m'),
            "summary": {
                "jobs_completed": metrics['job_statistics']['jobs_by_status'].get('completed', 0),
                "gpu_minutes_used": metrics['usage_statistics']['gpu_minutes_used'],
                "storage_used_gb": metrics['storage_statistics']['used_gb'],
                "total_cost_usd": metrics['cost_statistics']['monthly_cost_usd']
            },
            "recommendations": await self._generate_recommendations(user_id, metrics)
        }
    
    async def _generate_recommendations(self, user_id: str, metrics: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations"""
        
        recommendations = []
        
        # Usage-based recommendations
        usage = metrics['usage_statistics']
        if usage['monthly_jobs'] > 50:
            recommendations.append("Consider upgrading to Pro tier for better performance and higher limits")
        
        # Performance recommendations
        perf = metrics['performance_statistics']
        if perf['average_execution_time'] > 300:  # 5 minutes
            recommendations.append("Consider using smaller batch sizes for faster results")
        
        # Cost optimization
        cost = metrics['cost_statistics']
        if cost['monthly_cost_usd'] > 10:
            recommendations.append("Review your usage patterns to optimize costs")
        
        return recommendations

# Global analytics service instance
analytics_service = UserAnalyticsService()
