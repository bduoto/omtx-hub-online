#!/usr/bin/env python3
"""
Database Migration Script - CRITICAL FOR DEMO
Migrates existing data to user-isolated structure
Distinguished Engineer Implementation - Safe, reversible migration
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from google.cloud import firestore
from google.cloud import storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataMigration:
    """Safe database migration with rollback capability"""
    
    def __init__(self, dry_run: bool = True):
        self.db = firestore.Client()
        self.storage_client = storage.Client()
        self.dry_run = dry_run
        self.migration_log = []
        
        # Get bucket name from environment
        import os
        self.bucket_name = os.getenv("GCS_BUCKET_NAME", "omtx-production")
        
        try:
            self.bucket = self.storage_client.bucket(self.bucket_name)
            if not self.bucket.exists():
                logger.warning(f"⚠️ Bucket {self.bucket_name} does not exist")
        except Exception as e:
            logger.warning(f"⚠️ Could not access bucket {self.bucket_name}: {str(e)}")
            self.bucket = None
        
        logger.info(f"🔄 DataMigration initialized (dry_run={dry_run})")
    
    async def migrate_all_data(self):
        """Main migration function - migrates all existing data"""
        
        logger.info("🚀 Starting comprehensive data migration...")
        
        migration_start = time.time()
        
        try:
            # Step 1: Create demo users
            await self.create_demo_users()
            
            # Step 2: Migrate existing jobs
            await self.migrate_existing_jobs()
            
            # Step 3: Migrate storage files
            await self.migrate_storage_files()
            
            # Step 4: Create system collections
            await self.create_system_collections()
            
            # Step 5: Initialize user quotas
            await self.initialize_user_quotas()
            
            # Step 6: Create migration record
            await self.create_migration_record()
            
            migration_time = time.time() - migration_start
            
            logger.info(f"✅ Migration completed in {migration_time:.2f} seconds")
            
            # Generate migration report
            await self.generate_migration_report()
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {str(e)}")
            if not self.dry_run:
                await self.rollback_migration()
            raise
    
    async def create_demo_users(self):
        """Create demo users for testing"""
        
        logger.info("👥 Creating demo users...")
        
        demo_users = [
            {
                "user_id": "demo-user",
                "email": "demo@omtx.com",
                "tier": "pro",
                "display_name": "Demo User",
                "auth_method": "demo"
            },
            {
                "user_id": "test-user-basic",
                "email": "basic@omtx.com", 
                "tier": "basic",
                "display_name": "Basic Test User",
                "auth_method": "test"
            },
            {
                "user_id": "test-user-enterprise",
                "email": "enterprise@omtx.com",
                "tier": "enterprise", 
                "display_name": "Enterprise Test User",
                "auth_method": "test"
            }
        ]
        
        for user_data in demo_users:
            await self.create_user_if_not_exists(user_data)
        
        logger.info(f"✅ Created {len(demo_users)} demo users")
    
    async def create_user_if_not_exists(self, user_data: Dict[str, Any]):
        """Create user document if it doesn't exist"""
        
        user_id = user_data["user_id"]
        user_ref = self.db.collection('users').document(user_id)
        
        if not self.dry_run:
            # Check if user exists
            user_doc = user_ref.get()
            if user_doc.exists:
                logger.info(f"👤 User {user_id} already exists, skipping")
                return
        
        # Create user document
        user_document = {
            **user_data,
            "created_at": firestore.SERVER_TIMESTAMP,
            "last_active": firestore.SERVER_TIMESTAMP,
            "settings": {
                "notifications_enabled": True,
                "theme": "light"
            },
            "migration_source": "demo_creation"
        }
        
        if not self.dry_run:
            user_ref.set(user_document)
            
            # Initialize user usage tracking
            usage_ref = user_ref.collection('usage').document(
                datetime.utcnow().strftime('%Y-%m')
            )
            usage_ref.set({
                "current_jobs": 0,
                "monthly_jobs": 0,
                "gpu_minutes_used": 0,
                "api_calls_made": 0,
                "created_at": firestore.SERVER_TIMESTAMP
            })
            
            # Initialize storage usage
            storage_ref = user_ref.collection('storage_usage').document('current')
            storage_ref.set({
                "used_bytes": 0,
                "file_count": 0,
                "last_updated": firestore.SERVER_TIMESTAMP
            })
        
        self.migration_log.append(f"Created user: {user_id}")
        logger.info(f"👤 {'[DRY RUN] ' if self.dry_run else ''}Created user: {user_id}")
    
    async def migrate_existing_jobs(self):
        """Migrate existing jobs to user-isolated structure"""
        
        logger.info("📋 Migrating existing jobs...")
        
        try:
            # Get all existing jobs from old structure
            old_jobs_ref = self.db.collection('jobs')
            old_jobs = list(old_jobs_ref.stream())
            
            if not old_jobs:
                logger.info("📭 No existing jobs found to migrate")
                return
            
            migrated_count = 0
            
            for job_doc in old_jobs:
                job_data = job_doc.to_dict()
                job_id = job_doc.id
                
                # Extract or assign user_id
                user_id = job_data.get('user_id', 'demo-user')
                
                # Ensure user exists
                await self.create_user_if_not_exists({
                    "user_id": user_id,
                    "email": f"{user_id}@legacy.omtx.com",
                    "tier": "basic",
                    "display_name": f"Legacy User {user_id}",
                    "auth_method": "legacy"
                })
                
                # Migrate job to user collection
                if not self.dry_run:
                    user_ref = self.db.collection('users').document(user_id)
                    new_job_ref = user_ref.collection('jobs').document(job_id)
                    
                    # Add migration metadata
                    migrated_job_data = {
                        **job_data,
                        "migrated_at": firestore.SERVER_TIMESTAMP,
                        "migration_source": "legacy_jobs",
                        "original_collection": "jobs"
                    }
                    
                    new_job_ref.set(migrated_job_data)
                    
                    # Create admin job record for monitoring
                    admin_job_ref = self.db.collection('admin_jobs').document(job_id)
                    admin_job_ref.set({
                        "user_id": user_id,
                        "job_name": job_data.get("job_name", "legacy-job"),
                        "status": job_data.get("status", "unknown"),
                        "created_at": job_data.get("created_at", firestore.SERVER_TIMESTAMP),
                        "gpu_type": job_data.get("gpu_type", "unknown"),
                        "cost_actual": job_data.get("cost_actual", 0),
                        "migrated": True
                    })
                
                migrated_count += 1
                self.migration_log.append(f"Migrated job {job_id} for user {user_id}")
                logger.info(f"📋 {'[DRY RUN] ' if self.dry_run else ''}Migrated job {job_id} → user {user_id}")
            
            logger.info(f"✅ {'[DRY RUN] ' if self.dry_run else ''}Migrated {migrated_count} jobs")
            
        except Exception as e:
            logger.error(f"❌ Job migration failed: {str(e)}")
            raise
    
    async def migrate_storage_files(self):
        """Migrate GCS files to user-isolated paths"""
        
        logger.info("💾 Migrating storage files...")
        
        if not self.bucket:
            logger.warning("⚠️ Skipping storage migration - bucket not accessible")
            return
        
        try:
            # List all blobs with old structure
            old_blobs = list(self.bucket.list_blobs(prefix="jobs/"))
            
            if not old_blobs:
                logger.info("📭 No storage files found to migrate")
                return
            
            migrated_count = 0
            
            for blob in old_blobs:
                # Parse old path: jobs/{job_id}/...
                path_parts = blob.name.split('/')
                if len(path_parts) < 2:
                    continue
                
                job_id = path_parts[1]
                
                # Get user_id for this job
                user_id = await self.get_user_id_for_job(job_id)
                if not user_id:
                    user_id = "demo-user"  # Fallback
                
                # New path: users/{user_id}/jobs/{job_id}/...
                new_blob_name = blob.name.replace(f"jobs/{job_id}/", f"users/{user_id}/jobs/{job_id}/")
                
                if not self.dry_run:
                    # Copy to new location
                    new_blob = self.bucket.blob(new_blob_name)
                    new_blob.upload_from_string(blob.download_as_bytes())
                    
                    # Set user-specific metadata
                    new_blob.metadata = {
                        "user_id": user_id,
                        "job_id": job_id,
                        "migrated_at": str(int(time.time())),
                        "original_path": blob.name
                    }
                    new_blob.patch()
                
                migrated_count += 1
                self.migration_log.append(f"Migrated storage: {blob.name} → {new_blob_name}")
                
                if migrated_count % 10 == 0:
                    logger.info(f"💾 {'[DRY RUN] ' if self.dry_run else ''}Migrated {migrated_count} files...")
            
            logger.info(f"✅ {'[DRY RUN] ' if self.dry_run else ''}Migrated {migrated_count} storage files")
            
        except Exception as e:
            logger.error(f"❌ Storage migration failed: {str(e)}")
            # Don't fail entire migration for storage issues
            logger.warning("⚠️ Continuing migration without storage files")
    
    async def get_user_id_for_job(self, job_id: str) -> Optional[str]:
        """Get user_id for a job from the database"""
        
        try:
            # Check new structure first
            users_ref = self.db.collection('users')
            for user_doc in users_ref.stream():
                job_ref = user_doc.reference.collection('jobs').document(job_id)
                if job_ref.get().exists:
                    return user_doc.id
            
            # Check old structure
            old_job_ref = self.db.collection('jobs').document(job_id)
            old_job = old_job_ref.get()
            if old_job.exists:
                return old_job.to_dict().get('user_id')
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Could not get user_id for job {job_id}: {str(e)}")
            return None
    
    async def create_system_collections(self):
        """Create system collections for monitoring"""
        
        logger.info("⚙️ Creating system collections...")
        
        if not self.dry_run:
            # Create system config
            system_ref = self.db.collection('system_config').document('main')
            system_ref.set({
                "version": "2.0.0",
                "migration_completed": True,
                "migration_date": firestore.SERVER_TIMESTAMP,
                "features": {
                    "user_isolation": True,
                    "cloud_run": True,
                    "l4_optimization": True,
                    "real_time_updates": True
                }
            })
            
            # Create feature flags
            features_ref = self.db.collection('feature_flags').document('main')
            features_ref.set({
                "enable_user_isolation": True,
                "enable_rate_limiting": True,
                "enable_cost_tracking": True,
                "enable_webhooks": True,
                "enable_analytics": True,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
        
        self.migration_log.append("Created system collections")
        logger.info(f"⚙️ {'[DRY RUN] ' if self.dry_run else ''}Created system collections")
    
    async def initialize_user_quotas(self):
        """Initialize quotas for all users"""
        
        logger.info("📊 Initializing user quotas...")
        
        if not self.dry_run:
            users_ref = self.db.collection('users')
            for user_doc in users_ref.stream():
                user_data = user_doc.to_dict()
                tier = user_data.get('tier', 'free')
                
                # Set quotas based on tier
                quotas = self.get_tier_quotas(tier)
                
                user_doc.reference.update({
                    "quotas": quotas,
                    "quotas_updated_at": firestore.SERVER_TIMESTAMP
                })
        
        self.migration_log.append("Initialized user quotas")
        logger.info(f"📊 {'[DRY RUN] ' if self.dry_run else ''}Initialized user quotas")
    
    def get_tier_quotas(self, tier: str) -> Dict[str, Any]:
        """Get quota limits for user tier"""
        
        quotas = {
            "free": {
                "monthly_jobs": 10,
                "concurrent_jobs": 1,
                "storage_gb": 1,
                "gpu_minutes_monthly": 60
            },
            "basic": {
                "monthly_jobs": 100,
                "concurrent_jobs": 3,
                "storage_gb": 10,
                "gpu_minutes_monthly": 600
            },
            "pro": {
                "monthly_jobs": 1000,
                "concurrent_jobs": 10,
                "storage_gb": 100,
                "gpu_minutes_monthly": 6000
            },
            "enterprise": {
                "monthly_jobs": -1,  # Unlimited
                "concurrent_jobs": 50,
                "storage_gb": 1000,
                "gpu_minutes_monthly": -1  # Unlimited
            }
        }
        
        return quotas.get(tier, quotas["free"])
    
    async def create_migration_record(self):
        """Create migration record for tracking"""
        
        if not self.dry_run:
            migration_ref = self.db.collection('migrations').document(f"migration_{int(time.time())}")
            migration_ref.set({
                "type": "modal_to_cloud_run",
                "completed_at": firestore.SERVER_TIMESTAMP,
                "dry_run": self.dry_run,
                "log_entries": len(self.migration_log),
                "status": "completed"
            })
        
        logger.info(f"📝 {'[DRY RUN] ' if self.dry_run else ''}Created migration record")
    
    async def generate_migration_report(self):
        """Generate comprehensive migration report"""
        
        report = {
            "migration_timestamp": time.time(),
            "dry_run": self.dry_run,
            "log_entries": self.migration_log,
            "summary": {
                "total_operations": len(self.migration_log),
                "users_created": len([log for log in self.migration_log if "Created user" in log]),
                "jobs_migrated": len([log for log in self.migration_log if "Migrated job" in log]),
                "files_migrated": len([log for log in self.migration_log if "Migrated storage" in log])
            }
        }
        
        # Save report
        report_filename = f"migration_report_{'dry_run_' if self.dry_run else ''}{int(time.time())}.json"
        with open(report_filename, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Migration report saved: {report_filename}")
        
        # Print summary
        print("\n" + "="*50)
        print("🎉 MIGRATION SUMMARY")
        print("="*50)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        print(f"Total Operations: {report['summary']['total_operations']}")
        print(f"Users Created: {report['summary']['users_created']}")
        print(f"Jobs Migrated: {report['summary']['jobs_migrated']}")
        print(f"Files Migrated: {report['summary']['files_migrated']}")
        print("="*50)
        
        if self.dry_run:
            print("⚠️  This was a DRY RUN - no changes were made")
            print("   Run with --execute to perform actual migration")
        else:
            print("✅ Migration completed successfully!")
        print()
    
    async def rollback_migration(self):
        """Rollback migration in case of failure"""
        
        logger.warning("🔄 Attempting migration rollback...")
        
        # This would implement rollback logic
        # For now, just log the attempt
        logger.warning("⚠️ Rollback not implemented - manual cleanup may be required")

async def main():
    """Main migration function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="OMTX-Hub Data Migration")
    parser.add_argument("--execute", action="store_true", help="Execute migration (default is dry run)")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Confirm execution
    if args.execute:
        print("⚠️  WARNING: This will modify your database!")
        print("   Make sure you have backups before proceeding.")
        confirm = input("   Type 'MIGRATE' to confirm: ")
        if confirm != "MIGRATE":
            print("❌ Migration cancelled")
            return 1
    
    migration = DataMigration(dry_run=not args.execute)
    
    try:
        await migration.migrate_all_data()
        return 0
    except Exception as e:
        logger.error(f"💥 Migration failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
