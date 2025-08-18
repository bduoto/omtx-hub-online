#!/usr/bin/env python3
"""
Migrate existing jobs to the new format with job_type field
This ensures all jobs have the required fields for the new system
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def migrate_jobs_to_new_format():
    """Migrate all jobs in the database to have the new format with job_type field"""
    
    try:
        from database.gcp_job_manager import gcp_job_manager
        from config.gcp_database import gcp_database
        
        if not gcp_database.available:
            print("❌ GCP Database not available")
            return False
        
        print("🚀 Starting job migration to new format")
        print("=" * 50)
        
        # Get all jobs from the jobs collection
        print("\n📊 Fetching all jobs from database...")
        all_jobs = []
        
        try:
            # Get jobs collection
            jobs_ref = gcp_database.db.collection('jobs')
            docs = jobs_ref.stream()
            
            for doc in docs:
                job_data = doc.to_dict()
                job_data['id'] = doc.id
                all_jobs.append(job_data)
                
            print(f"   Found {len(all_jobs)} total jobs")
            
        except Exception as e:
            print(f"❌ Failed to fetch jobs: {e}")
            return False
        
        # Categorize jobs
        new_format_jobs = []
        legacy_jobs = []
        
        for job in all_jobs:
            if 'job_type' in job:
                new_format_jobs.append(job)
            else:
                legacy_jobs.append(job)
        
        print(f"\n📊 Job Analysis:")
        print(f"   ✅ New format jobs (with job_type): {len(new_format_jobs)}")
        print(f"   ⚠️ Legacy jobs (need migration): {len(legacy_jobs)}")
        
        if len(legacy_jobs) == 0:
            print("\n✨ All jobs are already in the new format!")
            return True
        
        # Ask for confirmation (auto-yes if running in non-interactive mode)
        print(f"\n⚠️ This will migrate {len(legacy_jobs)} legacy jobs to the new format")
        
        # Check if we're in an interactive terminal
        import sys
        if sys.stdin.isatty():
            response = input("Continue with migration? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Migration cancelled")
                return False
        else:
            print("   Auto-confirming migration (non-interactive mode)...")
            response = 'yes'
        
        # Migrate legacy jobs
        print(f"\n🔄 Migrating {len(legacy_jobs)} legacy jobs...")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, job in enumerate(legacy_jobs):
            job_id = job.get('id')
            print(f"\n   [{i+1}/{len(legacy_jobs)}] Processing job {job_id}...")
            
            try:
                # Determine job_type based on existing data
                task_type = job.get('type', job.get('task_type', 'unknown'))
                
                # Skip if no valid task type
                if task_type == 'unknown':
                    print(f"      ⚠️ Skipping - no task type found")
                    skip_count += 1
                    continue
                
                # Determine job_type
                if task_type == 'batch_protein_ligand_screening':
                    job_type = 'batch_parent'
                elif job.get('batch_parent_id') or job.get('input_data', {}).get('parent_batch_id'):
                    job_type = 'batch_child'
                else:
                    job_type = 'individual'
                
                # Build update data
                update_data = {
                    'job_type': job_type,
                    'task_type': task_type,
                    'updated_at': datetime.utcnow()
                }
                
                # Ensure required fields
                if not job.get('name'):
                    update_data['name'] = f"Job_{job_id[:8]}"
                
                if not job.get('status'):
                    update_data['status'] = 'completed'  # Assume old jobs are completed
                
                if not job.get('user_id'):
                    update_data['user_id'] = 'current_user'
                
                # Update the job in Firestore
                doc_ref = gcp_database.db.collection('jobs').document(job_id)
                doc_ref.update(update_data)
                
                print(f"      ✅ Migrated as {job_type}")
                success_count += 1
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
                error_count += 1
        
        # Summary
        print(f"\n" + "=" * 50)
        print(f"📊 Migration Summary:")
        print(f"   ✅ Successfully migrated: {success_count}")
        print(f"   ⚠️ Skipped (invalid data): {skip_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   📊 Total processed: {len(legacy_jobs)}")
        
        if success_count > 0:
            print(f"\n✨ Migration complete! {success_count} jobs now have the new format.")
        
        return success_count > 0 or skip_count == len(legacy_jobs)
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_migration():
    """Verify that all jobs now have the new format"""
    
    try:
        from database.gcp_job_manager import gcp_job_manager
        from config.gcp_database import gcp_database
        
        print("\n🔍 Verifying migration...")
        
        # Check a sample of jobs
        jobs_ref = gcp_database.db.collection('jobs').limit(10)
        docs = jobs_ref.stream()
        
        all_have_job_type = True
        for doc in docs:
            job_data = doc.to_dict()
            if 'job_type' not in job_data:
                print(f"   ❌ Job {doc.id} missing job_type")
                all_have_job_type = False
            else:
                print(f"   ✅ Job {doc.id} has job_type: {job_data['job_type']}")
        
        if all_have_job_type:
            print("\n✅ All sampled jobs have the new format!")
        else:
            print("\n⚠️ Some jobs still missing job_type field")
        
        return all_have_job_type
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🔄 OMTX-Hub Job Format Migration Tool")
    print("=" * 50)
    
    # Run migration
    success = migrate_jobs_to_new_format()
    
    if success:
        # Verify the migration
        verify_migration()
        
        print("\n💡 Next Steps:")
        print("   1. Restart the backend to use the new format")
        print("   2. Test the My Results page")
        print("   3. Monitor for any issues")
    else:
        print("\n❌ Migration failed or was cancelled")
        sys.exit(1)