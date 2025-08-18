"""
Database Performance Indexes for OMTX-Hub
Optimizes Firestore queries for ultra-fast response times
"""

from config.gcp_database import gcp_database
import logging

logger = logging.getLogger(__name__)

class PerformanceIndexes:
    """Manages database indexes for optimal query performance"""
    
    def __init__(self):
        self.indexes_created = False
        
    async def ensure_indexes_exist(self):
        """Create optimized indexes for common query patterns"""
        
        if self.indexes_created:
            return
            
        try:
            logger.info("🔧 Setting up performance indexes...")
            
            # Check if database is available
            if not gcp_database.available:
                logger.warning("⚠️ GCP Database not available, skipping index setup")
                return
                
            # Note: Firestore composite indexes need to be created via 
            # the Firebase Console or gcloud CLI, not programmatically
            # These are the indexes we recommend for optimal performance
            
            recommended_indexes = [
                # Jobs collection indexes for fast queries
                {
                    "collection": "jobs",
                    "fields": [
                        {"field_path": "user_id", "order": "ASCENDING"},
                        {"field_path": "created_at", "order": "DESCENDING"}
                    ],
                    "description": "Fast user job listing ordered by creation date"
                },
                {
                    "collection": "jobs", 
                    "fields": [
                        {"field_path": "user_id", "order": "ASCENDING"},
                        {"field_path": "status", "order": "ASCENDING"},
                        {"field_path": "created_at", "order": "DESCENDING"}
                    ],
                    "description": "Fast user job listing filtered by status"
                },
                {
                    "collection": "jobs",
                    "fields": [
                        {"field_path": "batch_parent_id", "order": "ASCENDING"},
                        {"field_path": "status", "order": "ASCENDING"}
                    ],
                    "description": "Fast batch job counting and status queries"
                },
                
                # My Results collection indexes for ultra-fast loading
                {
                    "collection": "my_results",
                    "fields": [
                        {"field_path": "user_id", "order": "ASCENDING"},
                        {"field_path": "created_at", "order": "DESCENDING"}
                    ],
                    "description": "Ultra-fast results listing for users"
                },
                {
                    "collection": "my_results",
                    "fields": [
                        {"field_path": "user_id", "order": "ASCENDING"},
                        {"field_path": "status", "order": "ASCENDING"},
                        {"field_path": "created_at", "order": "DESCENDING"}
                    ],
                    "description": "Fast results filtering by status"
                },
                {
                    "collection": "my_results",
                    "fields": [
                        {"field_path": "user_id", "order": "ASCENDING"},
                        {"field_path": "task_type", "order": "ASCENDING"},
                        {"field_path": "created_at", "order": "DESCENDING"}
                    ],
                    "description": "Fast results filtering by task type"
                }
            ]
            
            # Print index creation commands for manual setup
            logger.info("📝 To create these indexes manually, run the following gcloud commands:")
            
            for idx in recommended_indexes:
                collection = idx["collection"]
                fields_str = " ".join([
                    f"--index-fields={field['field_path']}:{field['order'].lower()}"
                    for field in idx["fields"]
                ])
                
                command = f"gcloud firestore indexes composite create {fields_str} --collection-group={collection}"
                logger.info(f"   {command}")
                logger.info(f"   # {idx['description']}")
                
            # Create single field indexes (these can be created automatically)
            self._ensure_single_field_indexes()
            
            self.indexes_created = True
            logger.info("✅ Performance indexes configuration complete")
            
        except Exception as e:
            logger.error(f"❌ Failed to configure indexes: {e}")
    
    def _ensure_single_field_indexes(self):
        """Ensure single-field indexes exist (Firestore creates these automatically)"""
        
        # These indexes are automatically created by Firestore when we query them
        single_field_indexes = [
            ("jobs", "user_id"),
            ("jobs", "status"), 
            ("jobs", "created_at"),
            ("jobs", "batch_parent_id"),
            ("jobs", "job_type"),
            ("my_results", "user_id"),
            ("my_results", "status"),
            ("my_results", "created_at"),
            ("my_results", "task_type"),
            ("my_results", "job_id")
        ]
        
        logger.info(f"📋 Single-field indexes will be auto-created for {len(single_field_indexes)} fields")
    
    def get_optimized_query_patterns(self):
        """Return optimized query patterns for common operations"""
        
        return {
            "user_jobs_recent": {
                "description": "Get user's recent jobs",
                "collection": "jobs",
                "filters": [("user_id", "==", "USER_ID")],
                "order_by": [("created_at", "desc")],
                "limit": 50
            },
            "user_jobs_by_status": {
                "description": "Get user's jobs filtered by status",
                "collection": "jobs", 
                "filters": [
                    ("user_id", "==", "USER_ID"),
                    ("status", "==", "STATUS")
                ],
                "order_by": [("created_at", "desc")],
                "limit": 50
            },
            "batch_child_jobs": {
                "description": "Get child jobs for a batch",
                "collection": "jobs",
                "filters": [("batch_parent_id", "==", "BATCH_ID")],
                "order_by": [("created_at", "asc")]
            },
            "user_results_recent": {
                "description": "Get user's recent saved results",
                "collection": "my_results",
                "filters": [("user_id", "==", "USER_ID")],
                "order_by": [("created_at", "desc")],
                "limit": 50
            },
            "user_results_by_status": {
                "description": "Get user's results filtered by status",
                "collection": "my_results",
                "filters": [
                    ("user_id", "==", "USER_ID"),
                    ("status", "==", "STATUS")
                ],
                "order_by": [("created_at", "desc")],
                "limit": 50
            }
        }

# Global instance
performance_indexes = PerformanceIndexes()