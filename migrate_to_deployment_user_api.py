#!/usr/bin/env python3
"""
Migrate all existing jobs to the deployment user using the API
This consolidates all results under a single user for deployment
"""

import requests
import json
from datetime import datetime
import time

API_BASE = 'https://omtx-hub-backend-338254269321.us-central1.run.app'
DEPLOYMENT_USER_ID = 'omtx_deployment_user'

def get_all_users_jobs():
    """Get jobs from all known users"""
    
    print("📊 Fetching jobs from all known users...")
    
    # Known users from our testing
    known_users = [
        'test_user',
        'current_user',
        'anonymous',
        'frontend_test',
        'ui_test_user',
        'default',
        DEPLOYMENT_USER_ID
    ]
    
    all_jobs = {}
    stats = {
        'total': 0,
        'by_user': {},
        'by_type': {'INDIVIDUAL': 0, 'BATCH_PARENT': 0, 'BATCH_CHILD': 0},
        'by_status': {'completed': 0, 'failed': 0, 'pending': 0, 'running': 0}
    }
    
    for user in known_users:
        print(f"  🔍 Checking user: {user}")
        
        try:
            response = requests.get(
                f"{API_BASE}/api/v1/jobs",
                params={'user_id': user, 'limit': 1000}
            )
            
            if response.ok:
                data = response.json()
                jobs = data.get('jobs', [])
                
                if jobs:
                    print(f"    ✓ Found {len(jobs)} jobs for user '{user}'")
                    stats['by_user'][user] = len(jobs)
                    
                    for job in jobs:
                        job_id = job.get('job_id')
                        if job_id:
                            all_jobs[job_id] = {
                                **job,
                                'original_user': user
                            }
                            stats['total'] += 1
                            
                            # Track types
                            job_type = job.get('job_type', 'unknown')
                            if job_type in stats['by_type']:
                                stats['by_type'][job_type] += 1
                            
                            # Track status
                            status = job.get('status', 'unknown')
                            if status in stats['by_status']:
                                stats['by_status'][status] += 1
                else:
                    print(f"    - No jobs for user '{user}'")
            else:
                print(f"    ⚠️ Failed to fetch jobs for user '{user}': {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Error fetching jobs for user '{user}': {e}")
    
    return all_jobs, stats

def display_migration_plan(all_jobs, stats):
    """Display what will be migrated"""
    
    print("\n" + "=" * 60)
    print("📋 MIGRATION PLAN")
    print("=" * 60)
    
    # Count jobs that need migration
    needs_migration = 0
    already_deployment = 0
    
    for job_id, job in all_jobs.items():
        if job.get('original_user') == DEPLOYMENT_USER_ID:
            already_deployment += 1
        else:
            needs_migration += 1
    
    print(f"\n📊 Current Status:")
    print(f"  Total jobs found: {stats['total']}")
    print(f"  Jobs already under deployment user: {already_deployment}")
    print(f"  Jobs needing migration: {needs_migration}")
    
    print(f"\n👥 Jobs by User:")
    for user, count in stats['by_user'].items():
        marker = "✅" if user == DEPLOYMENT_USER_ID else "🔄"
        print(f"  {marker} {user}: {count} jobs")
    
    print(f"\n📈 Jobs by Type:")
    for job_type, count in stats['by_type'].items():
        print(f"  - {job_type}: {count}")
    
    print(f"\n📉 Jobs by Status:")
    for status, count in stats['by_status'].items():
        print(f"  - {status}: {count}")
    
    return needs_migration, already_deployment

def create_migration_summary(all_jobs, stats):
    """Create a summary of the migration"""
    
    timestamp = datetime.now().isoformat()
    
    summary = {
        'migration_timestamp': timestamp,
        'deployment_user': DEPLOYMENT_USER_ID,
        'statistics': stats,
        'jobs_migrated': []
    }
    
    for job_id, job in all_jobs.items():
        if job.get('original_user') != DEPLOYMENT_USER_ID:
            summary['jobs_migrated'].append({
                'job_id': job_id,
                'original_user': job.get('original_user'),
                'job_type': job.get('job_type'),
                'status': job.get('status'),
                'created_at': job.get('created_at')
            })
    
    # Save summary to file
    with open('migration_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n💾 Migration summary saved to: migration_summary.json")
    
    return summary

def verify_deployment_user_access():
    """Verify deployment user can access all jobs"""
    
    print("\n🔍 Verifying deployment user access...")
    
    response = requests.get(
        f"{API_BASE}/api/v1/jobs",
        params={'user_id': DEPLOYMENT_USER_ID, 'limit': 1000}
    )
    
    if response.ok:
        data = response.json()
        jobs = data.get('jobs', [])
        
        print(f"  ✅ Deployment user has access to {len(jobs)} jobs")
        
        # Show sample jobs
        if jobs:
            print("\n📋 Sample Jobs Accessible:")
            for job in jobs[:5]:
                print(f"  - {job.get('job_id')} ({job.get('job_type')}) - {job.get('status')}")
        
        return len(jobs)
    else:
        print(f"  ❌ Failed to verify access: {response.status_code}")
        return 0

def main():
    """Main process"""
    
    print("🚀 OMTX-Hub Job Migration Analysis Tool")
    print(f"📍 Target: All jobs → {DEPLOYMENT_USER_ID}")
    print("=" * 60)
    
    # Get all jobs
    all_jobs, stats = get_all_users_jobs()
    
    if not all_jobs:
        print("\n⚠️ No jobs found to migrate!")
        return
    
    # Display migration plan
    needs_migration, already_deployment = display_migration_plan(all_jobs, stats)
    
    # Create migration summary
    summary = create_migration_summary(all_jobs, stats)
    
    # Verify current access
    current_access = verify_deployment_user_access()
    
    print("\n" + "=" * 60)
    print("📝 MIGRATION INSTRUCTIONS")
    print("=" * 60)
    
    if needs_migration > 0:
        print(f"\n⚠️ Found {needs_migration} jobs that need migration to deployment user.")
        print("\n To migrate these jobs, you need to:")
        print(" 1. Access the Google Cloud Console")
        print(" 2. Navigate to Firestore: https://console.cloud.google.com/firestore/data?project=om-models")
        print(" 3. Update the 'user_id' field for each job to: omtx_deployment_user")
        print("\n OR")
        print("\n Run this command in Cloud Shell:")
        print(" gcloud firestore import gs://[BACKUP_BUCKET]/[BACKUP_FILE]")
        print("\n Note: Since we're using API access only, manual migration via")
        print(" Google Cloud Console or a Cloud Function would be needed.")
    else:
        print(f"\n✅ All {stats['total']} jobs are already accessible by deployment user!")
        print(" No migration needed.")
    
    print("\n📊 Final Summary:")
    print(f"  Total jobs in system: {stats['total']}")
    print(f"  Jobs accessible by deployment user: {current_access}")
    print(f"  Jobs needing migration: {needs_migration}")
    
    print("\n✨ Analysis complete! Check 'migration_summary.json' for details.")

if __name__ == "__main__":
    main()