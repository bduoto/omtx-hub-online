"""
Migration script to assign all jobs to 'current_user'
Since you're the sole user, this will make all saved jobs accessible
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v2"

def check_current_data():
    """Check what data exists before migration"""
    
    print("🔍 Checking current data distribution...")
    
    try:
        # Use the debug endpoint
        response = requests.get(f"{BASE_URL}/debug/my-results")
        
        if response.status_code == 200:
            data = response.json()
            
            current_user_count = data.get('current_user_results', {}).get('count', 0)
            default_user_count = data.get('default_user_results', {}).get('count', 0)
            
            print(f"📊 Current data distribution:")
            print(f"   'current_user': {current_user_count} jobs")
            print(f"   'default_user': {default_user_count} jobs")
            
            # Show samples
            if data.get('current_user_results', {}).get('results'):
                print(f"\n📋 Sample 'current_user' jobs:")
                for job in data['current_user_results']['results'][:3]:
                    print(f"   - {job.get('job_name', 'Unknown')} ({job.get('status', 'Unknown')})")
            
            if data.get('default_user_results', {}).get('results'):
                print(f"\n📋 Sample 'default_user' jobs:")
                for job in data['default_user_results']['results'][:3]:
                    print(f"   - {job.get('job_name', 'Unknown')} ({job.get('status', 'Unknown')})")
            
            return {
                'current_user': current_user_count,
                'default_user': default_user_count
            }
        else:
            print(f"❌ Debug endpoint failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking current data: {e}")
        return None

def migrate_to_current_user():
    """Create a migration endpoint and instructions"""
    
    print("\n🔄 Creating migration instructions...")
    
    migration_script = '''
# Add this temporary endpoint to unified_endpoints.py for migration:

@router.post("/admin/migrate-user-ids")
async def migrate_user_ids_to_current_user():
    """TEMPORARY: Migrate all jobs to current_user"""
    
    try:
        if not gcp_database.available:
            raise HTTPException(status_code=500, detail="Database not available")
        
        # Get all jobs
        jobs_ref = gcp_database.db.collection('jobs')
        docs = list(jobs_ref.stream())
        
        updated_count = 0
        
        for doc in docs:
            job_data = doc.to_dict()
            current_user_id = job_data.get('user_id')
            
            # Update if user_id is not 'current_user'
            if current_user_id != 'current_user':
                doc.reference.update({'user_id': 'current_user'})
                updated_count += 1
        
        return {
            "status": "success",
            "message": f"Updated {updated_count} jobs to user_id='current_user'",
            "total_jobs": len(docs),
            "updated_jobs": updated_count
        }
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
'''
    
    print("📝 Migration Steps:")
    print("1. Add the above endpoint to your unified_endpoints.py")
    print("2. Restart your FastAPI server")
    print("3. Call: POST http://localhost:8000/api/v2/admin/migrate-user-ids")
    print("4. Remove the endpoint after migration")
    
    return migration_script

if __name__ == "__main__":
    print("🚀 User ID Migration Tool")
    print("="*50)
    
    # Check current data
    current_data = check_current_data()
    
    if current_data:
        total_jobs = current_data.get('current_user', 0) + current_data.get('default_user', 0)
        print(f"\n📊 Total jobs found: {total_jobs}")
        
        if current_data.get('current_user', 0) == 0 and current_data.get('default_user', 0) > 0:
            print("\n✅ Migration needed: All jobs are under 'default_user'")
            migrate_to_current_user()
        elif total_jobs == 0:
            print("\n⚠️ No jobs found in either user category")
        else:
            print(f"\n✅ Jobs already distributed correctly")
    else:
        print("\n❌ Could not check current data distribution")