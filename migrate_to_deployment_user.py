#!/usr/bin/env python3
"""
Migrate all existing jobs to the deployment user
This consolidates all results under a single user for deployment
"""

import os
import json
from google.cloud import firestore
from datetime import datetime
import time

# Set up Firestore client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.expanduser('~/Desktop/omtx-hub-online/om-models-427cb95a3133.json')
PROJECT_ID = 'om-models'
DEPLOYMENT_USER_ID = 'omtx_deployment_user'

def migrate_jobs_to_deployment_user():
    """Migrate all jobs to the deployment user"""
    
    print(f"🚀 Starting migration to deployment user: {DEPLOYMENT_USER_ID}")
    print("=" * 60)
    
    # Initialize Firestore client
    db = firestore.Client(project=PROJECT_ID)
    jobs_collection = db.collection('jobs')
    
    # Get all jobs
    print("📊 Fetching all jobs from Firestore...")
    all_jobs = jobs_collection.stream()
    
    # Track statistics
    stats = {
        'total': 0,
        'migrated': 0,
        'already_deployment_user': 0,
        'individual': 0,
        'batch_parent': 0,
        'batch_child': 0,
        'completed': 0,
        'failed': 0,
        'users_found': set()
    }
    
    # Process each job
    batch = db.batch()
    batch_count = 0
    
    for job_doc in all_jobs:
        job_data = job_doc.to_dict()
        job_id = job_doc.id
        stats['total'] += 1
        
        # Track original user
        original_user = job_data.get('user_id', 'unknown')
        stats['users_found'].add(original_user)
        
        # Track job types
        job_type = job_data.get('job_type', 'unknown')
        if job_type == 'INDIVIDUAL':
            stats['individual'] += 1
        elif job_type == 'BATCH_PARENT':
            stats['batch_parent'] += 1
        elif job_type == 'BATCH_CHILD':
            stats['batch_child'] += 1
            
        # Track status
        status = job_data.get('status', 'unknown')
        if status == 'completed':
            stats['completed'] += 1
        elif status == 'failed':
            stats['failed'] += 1
        
        # Check if already deployment user
        if original_user == DEPLOYMENT_USER_ID:
            stats['already_deployment_user'] += 1
            print(f"  ✓ Job {job_id} already belongs to deployment user")
        else:
            # Update to deployment user
            job_ref = jobs_collection.document(job_id)
            batch.update(job_ref, {
                'user_id': DEPLOYMENT_USER_ID,
                'original_user_id': original_user,  # Keep track of original user
                'migrated_at': firestore.SERVER_TIMESTAMP,
                'migration_note': f'Migrated from {original_user} to deployment user'
            })
            stats['migrated'] += 1
            batch_count += 1
            
            print(f"  🔄 Migrating job {job_id} from '{original_user}' to '{DEPLOYMENT_USER_ID}'")
            
            # Commit batch every 100 updates
            if batch_count >= 100:
                batch.commit()
                print(f"  💾 Committed batch of {batch_count} updates")
                batch = db.batch()
                batch_count = 0
    
    # Commit remaining updates
    if batch_count > 0:
        batch.commit()
        print(f"  💾 Committed final batch of {batch_count} updates")
    
    # Print summary
    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 60)
    print(f"📊 Migration Statistics:")
    print(f"  Total jobs: {stats['total']}")
    print(f"  Jobs migrated: {stats['migrated']}")
    print(f"  Already deployment user: {stats['already_deployment_user']}")
    print(f"\n📈 Job Types:")
    print(f"  Individual: {stats['individual']}")
    print(f"  Batch Parent: {stats['batch_parent']}")
    print(f"  Batch Child: {stats['batch_child']}")
    print(f"\n📉 Job Status:")
    print(f"  Completed: {stats['completed']}")
    print(f"  Failed: {stats['failed']}")
    print(f"\n👥 Original Users Found:")
    for user in stats['users_found']:
        print(f"  - {user}")
    
    return stats

def verify_migration():
    """Verify all jobs now belong to deployment user"""
    print("\n🔍 Verifying migration...")
    
    db = firestore.Client(project=PROJECT_ID)
    jobs_collection = db.collection('jobs')
    
    # Check for any jobs not belonging to deployment user
    non_deployment_jobs = jobs_collection.where('user_id', '!=', DEPLOYMENT_USER_ID).stream()
    
    count = 0
    for job in non_deployment_jobs:
        count += 1
        job_data = job.to_dict()
        print(f"  ⚠️ Found job {job.id} with user_id: {job_data.get('user_id')}")
    
    if count == 0:
        print("  ✅ All jobs successfully migrated to deployment user!")
        
        # Count total deployment user jobs
        deployment_jobs = jobs_collection.where('user_id', '==', DEPLOYMENT_USER_ID).stream()
        total = sum(1 for _ in deployment_jobs)
        print(f"  📊 Total jobs for deployment user: {total}")
    else:
        print(f"  ⚠️ Found {count} jobs not belonging to deployment user")
    
    return count == 0

def main():
    """Main migration process"""
    print("🚀 OMTX-Hub Job Migration Tool")
    print(f"📍 Target: All jobs → {DEPLOYMENT_USER_ID}")
    print("=" * 60)
    
    # Run migration
    stats = migrate_jobs_to_deployment_user()
    
    # Verify migration
    success = verify_migration()
    
    if success:
        print("\n🎉 Migration successful! All jobs now belong to deployment user.")
        print(f"🔑 You can now access all {stats['total']} jobs through the deployment user.")
        
        # Print API test command
        print("\n📝 Test with this command:")
        print(f'curl "https://omtx-hub-backend-338254269321.us-central1.run.app/api/v1/jobs?user_id={DEPLOYMENT_USER_ID}&limit=10" | jq')
    else:
        print("\n⚠️ Migration may be incomplete. Please check the warnings above.")
    
    print("\n✨ Done!")

if __name__ == "__main__":
    main()