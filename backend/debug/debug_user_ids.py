"""
Debug script to check what user_ids exist in the jobs collection
"""

import asyncio
from config.gcp_database import gcp_database

async def debug_user_ids():
    """Check what user_ids exist in the database"""
    
    if not gcp_database.available:
        print("❌ GCP database not available")
        return
    
    try:
        # Get all jobs and check their user_ids
        jobs_ref = gcp_database.db.collection('jobs')
        docs = jobs_ref.limit(100).stream()  # Get first 100 jobs
        
        user_id_counts = {}
        total_jobs = 0
        sample_jobs = []
        
        for doc in docs:
            job_data = doc.to_dict()
            user_id = job_data.get('user_id', 'NULL')
            
            # Count user_ids
            user_id_counts[user_id] = user_id_counts.get(user_id, 0) + 1
            total_jobs += 1
            
            # Keep sample of first 5 jobs
            if len(sample_jobs) < 5:
                sample_jobs.append({
                    'id': doc.id,
                    'user_id': user_id,
                    'job_name': job_data.get('name', 'Unknown'),
                    'status': job_data.get('status', 'Unknown'),
                    'created_at': job_data.get('created_at', 'Unknown')
                })
        
        print(f"\n📊 Found {total_jobs} total jobs")
        print(f"\n👥 User ID distribution:")
        for user_id, count in sorted(user_id_counts.items()):
            print(f"   '{user_id}': {count} jobs")
        
        print(f"\n📋 Sample jobs:")
        for job in sample_jobs:
            print(f"   ID: {job['id'][:8]}... | User: '{job['user_id']}' | Name: {job['job_name']}")
        
        return user_id_counts
        
    except Exception as e:
        print(f"❌ Error checking user IDs: {e}")
        return {}

if __name__ == "__main__":
    asyncio.run(debug_user_ids())