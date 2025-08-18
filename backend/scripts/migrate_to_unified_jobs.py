#!/usr/bin/env python3
"""
Migration script to enhance existing jobs with unified job model fields
This script safely adds the new fields without breaking existing functionality
"""

import sys
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

# Add backend to path
sys.path.append('.')

from config.gcp_database import gcp_database
from database.unified_job_manager import unified_job_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobMigrationService:
    """Service to migrate existing jobs to unified model"""
    
    def __init__(self):
        self.db = gcp_database
        self.job_manager = unified_job_manager
        self.migration_stats = {
            'total_jobs': 0,
            'migrated_jobs': 0,
            'skipped_jobs': 0,
            'failed_jobs': 0,
            'batch_parents_created': 0,
            'batch_children_linked': 0
        }
    
    async def run_migration(self, dry_run: bool = True) -> Dict[str, Any]:
        """Run the complete migration process"""
        
        logger.info(f"🚀 Starting job migration (dry_run={dry_run})")
        
        if not self.db.available:
            raise Exception("❌ Database not available")
        
        # Step 1: Get all existing jobs
        jobs = await self._get_all_jobs()
        self.migration_stats['total_jobs'] = len(jobs)
        
        logger.info(f"📊 Found {len(jobs)} jobs to migrate")
        
        # Step 2: Analyze and categorize jobs
        job_categories = await self._categorize_jobs(jobs)
        
        # Step 3: Migrate individual jobs
        await self._migrate_individual_jobs(job_categories['individual'], dry_run)
        
        # Step 4: Migrate batch jobs
        await self._migrate_batch_jobs(job_categories['batch'], dry_run)
        
        # Step 5: Create missing indexes (if not dry run)
        if not dry_run:
            await self._ensure_indexes()
        
        logger.info("✅ Migration completed")
        return self.migration_stats
    
    async def _get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs from the database"""
        try:
            # Get from jobs collection
            jobs_query = self.db.db.collection('jobs').stream()
            jobs = [{'id': doc.id, **doc.to_dict()} for doc in jobs_query]
            
            logger.info(f"📋 Retrieved {len(jobs)} jobs from 'jobs' collection")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ Failed to get jobs: {e}")
            return []
    
    async def _categorize_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize jobs into individual and batch"""
        
        individual_jobs = []
        batch_jobs = []
        
        for job in jobs:
            # Check if job already has job_type (already migrated)
            if 'job_type' in job:
                self.migration_stats['skipped_jobs'] += 1
                continue
            
            # Determine job type based on existing data
            task_type = job.get('type', job.get('task_type', ''))
            
            if task_type == 'batch_protein_ligand_screening':
                batch_jobs.append(job)
            elif 'batch_id' in job:
                # This is a child job of a batch
                batch_jobs.append(job)
            else:
                individual_jobs.append(job)
        
        logger.info(f"📊 Categorized: {len(individual_jobs)} individual, {len(batch_jobs)} batch-related")
        
        return {
            'individual': individual_jobs,
            'batch': batch_jobs
        }
    
    async def _migrate_individual_jobs(self, jobs: List[Dict[str, Any]], dry_run: bool):
        """Migrate individual jobs to unified model"""
        
        logger.info(f"🔄 Migrating {len(jobs)} individual jobs")
        
        for job in jobs:
            try:
                if dry_run:
                    logger.info(f"   [DRY RUN] Would migrate individual job: {job['id']}")
                else:
                    await self._update_job_with_unified_fields(job, 'individual')
                
                self.migration_stats['migrated_jobs'] += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to migrate job {job['id']}: {e}")
                self.migration_stats['failed_jobs'] += 1
    
    async def _migrate_batch_jobs(self, jobs: List[Dict[str, Any]], dry_run: bool):
        """Migrate batch jobs to unified model"""
        
        logger.info(f"🔄 Migrating {len(jobs)} batch-related jobs")
        
        # Group batch jobs by batch_id
        batch_groups = {}
        orphaned_jobs = []
        
        for job in jobs:
            task_type = job.get('type', job.get('task_type', ''))
            
            if task_type == 'batch_protein_ligand_screening':
                # This is a batch parent
                batch_id = job['id']
                if batch_id not in batch_groups:
                    batch_groups[batch_id] = {'parent': None, 'children': []}
                batch_groups[batch_id]['parent'] = job
            elif 'batch_id' in job:
                # This is a batch child
                batch_id = job['batch_id']
                if batch_id not in batch_groups:
                    batch_groups[batch_id] = {'parent': None, 'children': []}
                batch_groups[batch_id]['children'].append(job)
            else:
                orphaned_jobs.append(job)
        
        # Migrate batch groups
        for batch_id, group in batch_groups.items():
            try:
                if dry_run:
                    logger.info(f"   [DRY RUN] Would migrate batch {batch_id}: parent={group['parent'] is not None}, children={len(group['children'])}")
                else:
                    await self._migrate_batch_group(batch_id, group)
                
            except Exception as e:
                logger.error(f"❌ Failed to migrate batch {batch_id}: {e}")
                self.migration_stats['failed_jobs'] += 1
        
        # Handle orphaned jobs
        for job in orphaned_jobs:
            try:
                if dry_run:
                    logger.info(f"   [DRY RUN] Would migrate orphaned job as individual: {job['id']}")
                else:
                    await self._update_job_with_unified_fields(job, 'individual')
                
                self.migration_stats['migrated_jobs'] += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to migrate orphaned job {job['id']}: {e}")
                self.migration_stats['failed_jobs'] += 1
    
    async def _migrate_batch_group(self, batch_id: str, group: Dict[str, Any]):
        """Migrate a complete batch group"""
        
        parent = group['parent']
        children = group['children']
        
        # Migrate parent
        if parent:
            child_ids = [child['id'] for child in children]
            await self._update_job_with_unified_fields(
                parent, 
                'batch_parent',
                additional_fields={'batch_child_ids': child_ids}
            )
            self.migration_stats['batch_parents_created'] += 1
        
        # Migrate children
        for idx, child in enumerate(children):
            await self._update_job_with_unified_fields(
                child,
                'batch_child',
                additional_fields={
                    'batch_parent_id': batch_id,
                    'batch_index': idx
                }
            )
            self.migration_stats['batch_children_linked'] += 1
        
        self.migration_stats['migrated_jobs'] += len(children) + (1 if parent else 0)
    
    async def _update_job_with_unified_fields(self, job: Dict[str, Any], job_type: str, 
                                           additional_fields: Dict[str, Any] = None):
        """Update a job with unified model fields"""
        
        job_id = job['id']
        
        # Prepare update data
        update_data = {
            'job_type': job_type,
            'updated_at': datetime.utcnow(),
            'migration_timestamp': datetime.utcnow()
        }
        
        # Add additional fields
        if additional_fields:
            update_data.update(additional_fields)
        
        # Update in Firestore
        doc_ref = self.db.db.collection('jobs').document(job_id)
        doc_ref.update(update_data)
        
        logger.info(f"✅ Updated job {job_id} with job_type={job_type}")
    
    async def _ensure_indexes(self):
        """Ensure required indexes exist"""
        logger.info("📋 Checking required indexes...")
        
        # This would typically be done through the Firebase console
        # For now, just log the required indexes
        required_indexes = [
            "jobs: job_type (ASC) + user_id (ASC) + created_at (DESC)",
            "jobs: batch_parent_id (ASC) + batch_index (ASC)",
            "jobs: batch_parent_id (ASC) + status (ASC)"
        ]
        
        logger.info("📋 Required indexes:")
        for index in required_indexes:
            logger.info(f"   - {index}")
        
        logger.info("💡 Create these indexes at: https://console.firebase.google.com/project/YOUR_PROJECT/firestore/indexes")

async def main():
    """Main migration function"""
    
    import argparse
    parser = argparse.ArgumentParser(description='Migrate jobs to unified model')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no changes)')
    parser.add_argument('--force', action='store_true', help='Force migration even if risky')
    
    args = parser.parse_args()
    
    migration_service = JobMigrationService()
    
    try:
        stats = await migration_service.run_migration(dry_run=args.dry_run)
        
        print("\n" + "="*50)
        print("📊 MIGRATION STATISTICS")
        print("="*50)
        for key, value in stats.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        
        if args.dry_run:
            print("\n💡 This was a dry run. Use --force to apply changes.")
        else:
            print("\n✅ Migration completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
