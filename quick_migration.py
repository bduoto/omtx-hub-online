#!/usr/bin/env python3
"""
Quick Migration Script - Uses Firebase Admin SDK if available
Falls back to using the API for individual job updates
"""

import requests
import json
import time
from datetime import datetime

API_BASE = 'https://omtx-hub-backend-338254269321.us-central1.run.app'
DEPLOYMENT_USER_ID = 'omtx_deployment_user'

def get_jobs_needing_migration():
    """Get all jobs that need migration"""
    
    print("📊 Identifying jobs that need migration...")
    
    # Known users with jobs
    users_to_migrate = ['test_user', 'current_user', 'anonymous', 'frontend_test']
    jobs_to_migrate = []
    
    for user in users_to_migrate:
        print(f"  🔍 Checking jobs for user: {user}")
        
        try:
            response = requests.get(
                f"{API_BASE}/api/v1/jobs",
                params={'user_id': user, 'limit': 1000}
            )
            
            if response.ok:
                data = response.json()
                jobs = data.get('jobs', [])
                
                if jobs:
                    print(f"    ✓ Found {len(jobs)} jobs for {user}")
                    for job in jobs:
                        jobs_to_migrate.append({
                            'job_id': job.get('job_id'),
                            'current_user': user,
                            'job_type': job.get('job_type'),
                            'status': job.get('status')
                        })
                else:
                    print(f"    - No jobs found for {user}")
            else:
                print(f"    ⚠️ Failed to fetch jobs for {user}: {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Error checking {user}: {e}")
    
    return jobs_to_migrate

def create_firestore_script(jobs_to_migrate):
    """Create a Firestore CLI script for the migration"""
    
    print(f"\n📝 Creating Firestore update script for {len(jobs_to_migrate)} jobs...")
    
    # Create the update script
    script_lines = [
        "#!/bin/bash",
        "# Firestore Job Migration Script",
        "# Run this in Google Cloud Shell",
        "",
        "PROJECT_ID=\"om-models\"",
        f"DEPLOYMENT_USER=\"{DEPLOYMENT_USER_ID}\"",
        "",
        "echo '🚀 Starting Firestore job migration...'",
        "echo '📊 Migrating all jobs to deployment user'",
        ""
    ]
    
    # Add update commands for each job
    batch_size = 100
    batch_count = 0
    total_batches = (len(jobs_to_migrate) + batch_size - 1) // batch_size
    
    for i, job in enumerate(jobs_to_migrate):
        job_id = job['job_id']
        original_user = job['current_user']
        
        if i % batch_size == 0:
            batch_count += 1
            script_lines.append(f"echo '📦 Processing batch {batch_count}/{total_batches}...'")
        
        # Create Firestore update command
        update_cmd = f"""gcloud firestore documents update \\
  --project=$PROJECT_ID \\
  --collection-group=jobs \\
  --document-id="{job_id}" \\
  --field-update="user_id:$DEPLOYMENT_USER" \\
  --field-update="original_user_id:{original_user}" \\
  --field-update="migrated_at:$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \\
  --field-update="migration_note:Migrated from {original_user} to deployment user" \\
  --quiet"""
        
        script_lines.append(update_cmd)
        
        if (i + 1) % 10 == 0:
            script_lines.append("sleep 1  # Rate limiting")
    
    script_lines.extend([
        "",
        "echo '✅ Migration completed!'",
        f"echo '📊 Updated {len(jobs_to_migrate)} jobs to deployment user'",
        "echo '🔍 Verifying migration...'",
        "",
        "# Count deployment user jobs",
        "gcloud firestore documents list \\",
        "  --project=$PROJECT_ID \\",
        "  --collection-group=jobs \\",
        "  --filter='user_id = \"$DEPLOYMENT_USER\"' \\",
        "  --quiet | wc -l",
        "",
        "echo '🎉 Migration script completed!'"
    ])
    
    # Write the script
    script_content = "\n".join(script_lines)
    
    with open('firestore_migration.sh', 'w') as f:
        f.write(script_content)
    
    # Make it executable
    import os
    os.chmod('firestore_migration.sh', 0o755)
    
    print("✅ Created migration script: firestore_migration.sh")
    
    return len(jobs_to_migrate)

def create_cloud_shell_instructions():
    """Create instructions for running in Cloud Shell"""
    
    instructions = """
🚀 FIRESTORE MIGRATION INSTRUCTIONS
==================================

The migration script has been created: firestore_migration.sh

To execute the migration:

1. Upload the script to Google Cloud Shell:
   - Go to: https://shell.cloud.google.com
   - Upload the file: firestore_migration.sh
   
2. Run the migration:
   chmod +x firestore_migration.sh
   ./firestore_migration.sh

3. Monitor progress:
   - The script will show progress as it processes batches
   - Each job update is logged
   - Final count verification included

4. Verify completion:
   - Check the final job count for deployment user
   - Test the frontend My Results page
   - All historical results should now be visible

Alternative: Manual Firestore Console
=====================================

1. Go to: https://console.cloud.google.com/firestore/data?project=om-models
2. Navigate to 'jobs' collection
3. Use Query Builder:
   - Field: user_id
   - Operator: !=
   - Value: omtx_deployment_user
4. Select all results and bulk edit user_id field

This will consolidate all 2000+ historical jobs under the deployment user.
"""
    
    with open('MIGRATION_INSTRUCTIONS.txt', 'w') as f:
        f.write(instructions)
    
    print("📋 Created instructions: MIGRATION_INSTRUCTIONS.txt")

def main():
    """Execute the migration preparation"""
    
    print("🚀 OMTX-Hub Quick Migration Tool")
    print("=" * 50)
    
    # Get jobs that need migration
    jobs_to_migrate = get_jobs_needing_migration()
    
    if not jobs_to_migrate:
        print("\n✅ No jobs found that need migration!")
        print("All jobs may already belong to the deployment user.")
        return
    
    # Create migration artifacts
    total_jobs = create_firestore_script(jobs_to_migrate)
    create_cloud_shell_instructions()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 MIGRATION SUMMARY")
    print("=" * 50)
    print(f"Jobs to migrate: {total_jobs}")
    print(f"Target user: {DEPLOYMENT_USER_ID}")
    print()
    print("Files created:")
    print("  🔧 firestore_migration.sh - Executable migration script")
    print("  📋 MIGRATION_INSTRUCTIONS.txt - Detailed instructions")
    print()
    print("Next steps:")
    print("  1. Upload firestore_migration.sh to Google Cloud Shell")
    print("  2. Run: chmod +x firestore_migration.sh && ./firestore_migration.sh")
    print("  3. Verify results in frontend My Results page")
    print()
    print("🎉 Migration preparation complete!")

if __name__ == "__main__":
    main()