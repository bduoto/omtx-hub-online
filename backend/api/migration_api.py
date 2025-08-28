"""
Migration API for consolidating jobs under deployment user
Add this to your main.py to enable migration endpoint
"""

from fastapi import APIRouter, HTTPException
from google.cloud import firestore
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/migration", tags=["migration"])

PROJECT_ID = 'om-models'
DEPLOYMENT_USER_ID = 'omtx_deployment_user'

@router.post("/migrate-to-deployment-user")
async def migrate_all_jobs_to_deployment_user() -> Dict[str, Any]:
    """
    Migrate all jobs to the deployment user
    This consolidates all results under a single user
    """
    
    try:
        # Initialize Firestore
        db = firestore.Client(project=PROJECT_ID)
        jobs_collection = db.collection('jobs')
        
        # Track statistics
        stats = {
            'total': 0,
            'migrated': 0,
            'already_deployment_user': 0,
            'errors': 0,
            'users_found': set()
        }
        
        logger.info(f"Starting migration to deployment user: {DEPLOYMENT_USER_ID}")
        
        # Get all jobs
        all_jobs = jobs_collection.stream()
        
        # Process in batches for efficiency
        batch = db.batch()
        batch_count = 0
        
        for job_doc in all_jobs:
            try:
                job_data = job_doc.to_dict()
                job_id = job_doc.id
                stats['total'] += 1
                
                # Track original user
                original_user = job_data.get('user_id', 'unknown')
                stats['users_found'].add(original_user)
                
                # Check if already deployment user
                if original_user == DEPLOYMENT_USER_ID:
                    stats['already_deployment_user'] += 1
                else:
                    # Update to deployment user
                    job_ref = jobs_collection.document(job_id)
                    batch.update(job_ref, {
                        'user_id': DEPLOYMENT_USER_ID,
                        'original_user_id': original_user,
                        'migrated_at': firestore.SERVER_TIMESTAMP,
                        'migration_note': f'Migrated from {original_user} to deployment user'
                    })
                    stats['migrated'] += 1
                    batch_count += 1
                    
                    # Commit every 100 updates (Firestore limit is 500)
                    if batch_count >= 100:
                        batch.commit()
                        logger.info(f"Committed batch of {batch_count} updates")
                        batch = db.batch()
                        batch_count = 0
                        
            except Exception as e:
                logger.error(f"Error processing job {job_doc.id}: {e}")
                stats['errors'] += 1
        
        # Commit remaining updates
        if batch_count > 0:
            batch.commit()
            logger.info(f"Committed final batch of {batch_count} updates")
        
        # Convert set to list for JSON serialization
        stats['users_found'] = list(stats['users_found'])
        
        logger.info(f"Migration complete: {stats}")
        
        return {
            'success': True,
            'message': f'Successfully migrated {stats["migrated"]} jobs to deployment user',
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/verify-migration")
async def verify_migration_status() -> Dict[str, Any]:
    """
    Verify that all jobs belong to deployment user
    """
    
    try:
        db = firestore.Client(project=PROJECT_ID)
        jobs_collection = db.collection('jobs')
        
        # Count deployment user jobs
        deployment_jobs = jobs_collection.where('user_id', '==', DEPLOYMENT_USER_ID).stream()
        deployment_count = sum(1 for _ in deployment_jobs)
        
        # Check for non-deployment user jobs
        # Note: Firestore doesn't support != queries well, so we check known users
        known_users = ['test_user', 'current_user', 'anonymous', 'frontend_test', 'ui_test_user', 'default']
        non_deployment_count = 0
        other_users_breakdown = {}
        
        for user in known_users:
            user_jobs = jobs_collection.where('user_id', '==', user).stream()
            count = sum(1 for _ in user_jobs)
            if count > 0:
                other_users_breakdown[user] = count
                non_deployment_count += count
        
        migration_complete = non_deployment_count == 0
        
        return {
            'success': True,
            'deployment_user_jobs': deployment_count,
            'non_deployment_user_jobs': non_deployment_count,
            'other_users_breakdown': other_users_breakdown,
            'migration_complete': migration_complete,
            'message': f'Deployment user has {deployment_count} jobs. Migration {"complete" if migration_complete else "needed"}.'
        }
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/migration-status")
async def get_migration_status() -> Dict[str, Any]:
    """
    Get current migration status without performing migration
    """
    
    try:
        # Use the API to check current status
        import requests
        
        API_BASE = 'https://omtx-hub-backend-338254269321.us-central1.run.app'
        
        # Get deployment user jobs
        response = requests.get(
            f"{API_BASE}/api/v1/jobs",
            params={'user_id': DEPLOYMENT_USER_ID, 'limit': 1000}
        )
        
        deployment_jobs = 0
        if response.ok:
            data = response.json()
            deployment_jobs = len(data.get('jobs', []))
        
        # Check known other users
        other_users = {}
        known_users = ['test_user', 'current_user', 'anonymous', 'frontend_test']
        
        for user in known_users:
            response = requests.get(
                f"{API_BASE}/api/v1/jobs",
                params={'user_id': user, 'limit': 1}
            )
            if response.ok:
                data = response.json()
                count = data.get('count', 0)
                if count > 0:
                    other_users[user] = count
        
        total_other = sum(other_users.values())
        
        return {
            'deployment_user': DEPLOYMENT_USER_ID,
            'deployment_user_jobs': deployment_jobs,
            'other_users': other_users,
            'total_other_users_jobs': total_other,
            'migration_needed': total_other > 0,
            'message': f'{total_other} jobs need migration to deployment user' if total_other > 0 else 'All jobs belong to deployment user'
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))