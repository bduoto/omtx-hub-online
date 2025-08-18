"""
Temporary migration endpoint to add to unified_endpoints.py
This will find ALL jobs regardless of user_id and assign them to 'current_user'
"""

MIGRATION_ENDPOINT = '''
@router.post("/admin/migrate-all-jobs-to-current-user")
async def migrate_all_jobs_to_current_user():
    """TEMPORARY MIGRATION: Assign all jobs to current_user"""
    
    try:
        # Import here to avoid circular imports
        from config.gcp_database import gcp_database
        
        if not gcp_database.available:
            raise HTTPException(status_code=500, detail="GCP Database not available")
        
        # Get ALL jobs regardless of user_id
        jobs_ref = gcp_database.db.collection('jobs')
        docs = list(jobs_ref.stream())
        
        updated_count = 0
        user_id_distribution = {}
        
        for doc in docs:
            job_data = doc.to_dict()
            current_user_id = job_data.get('user_id', 'NULL')
            
            # Count distribution
            user_id_distribution[current_user_id] = user_id_distribution.get(current_user_id, 0) + 1
            
            # Update ALL jobs to 'current_user'
            if current_user_id != 'current_user':
                doc.reference.update({'user_id': 'current_user'})
                updated_count += 1
                logger.info(f"Updated job {doc.id} from '{current_user_id}' to 'current_user'")
        
        # Clear any caches after migration
        try:
            from services.gcp_results_indexer_optimized import streamlined_gcp_results_indexer
            streamlined_gcp_results_indexer.clear_cache()
        except:
            pass
        
        return {
            "status": "success",
            "message": f"Migration complete! Updated {updated_count} jobs",
            "total_jobs_found": len(docs),
            "updated_jobs": updated_count,
            "original_user_id_distribution": user_id_distribution,
            "note": "All jobs now assigned to 'current_user'"
        }
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@router.get("/admin/check-all-jobs")
async def check_all_jobs():
    """TEMPORARY DEBUG: Check all jobs and their user_ids"""
    
    try:
        from config.gcp_database import gcp_database
        
        if not gcp_database.available:
            raise HTTPException(status_code=500, detail="GCP Database not available")
        
        # Get ALL jobs
        jobs_ref = gcp_database.db.collection('jobs')
        docs = list(jobs_ref.limit(100).stream())  # Limit to first 100 for debugging
        
        user_id_distribution = {}
        sample_jobs = []
        
        for doc in docs:
            job_data = doc.to_dict()
            user_id = job_data.get('user_id', 'NULL')
            
            # Count distribution
            user_id_distribution[user_id] = user_id_distribution.get(user_id, 0) + 1
            
            # Sample jobs
            if len(sample_jobs) < 10:
                sample_jobs.append({
                    'id': doc.id,
                    'user_id': user_id,
                    'name': job_data.get('name', 'Unknown'),
                    'status': job_data.get('status', 'Unknown'),
                    'type': job_data.get('type', 'Unknown'),
                    'created_at': str(job_data.get('created_at', 'Unknown'))[:19]
                })
        
        return {
            "total_jobs": len(docs),
            "user_id_distribution": user_id_distribution,
            "sample_jobs": sample_jobs,
            "debug_info": "This shows ALL jobs in the database"
        }
        
    except Exception as e:
        logger.error(f"❌ Debug check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Debug check failed: {str(e)}")
'''

print("🔧 MIGRATION INSTRUCTIONS")
print("="*50)
print()
print("1. Add these temporary endpoints to your unified_endpoints.py file:")
print()
print(MIGRATION_ENDPOINT)
print()
print("2. Restart your FastAPI server")
print()
print("3. First, check what data exists:")
print("   GET http://localhost:8000/api/v2/admin/check-all-jobs")
print()
print("4. Then run the migration:")
print("   POST http://localhost:8000/api/v2/admin/migrate-all-jobs-to-current-user")
print()
print("5. Verify results:")
print("   GET http://localhost:8000/api/v2/my-results-optimized")
print()
print("6. Remove the admin endpoints after successful migration")
print()
print("🚨 IMPORTANT: These are temporary admin endpoints - remove them after migration!")