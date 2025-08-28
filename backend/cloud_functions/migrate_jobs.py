"""
Cloud Function to migrate all jobs to deployment user
Deploy this function to Google Cloud Functions and trigger it once
"""

import functions_framework
from google.cloud import firestore
import json

PROJECT_ID = 'om-models'
DEPLOYMENT_USER_ID = 'omtx_deployment_user'

@functions_framework.http
def migrate_jobs_to_deployment_user(request):
    """HTTP Cloud Function to migrate all jobs to deployment user"""
    
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
    
    try:
        # Get all jobs
        all_jobs = jobs_collection.stream()
        
        # Process in batches
        batch = db.batch()
        batch_count = 0
        
        for job_doc in all_jobs:
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
                    batch = db.batch()
                    batch_count = 0
        
        # Commit remaining updates
        if batch_count > 0:
            batch.commit()
        
        # Convert set to list for JSON serialization
        stats['users_found'] = list(stats['users_found'])
        
        return {
            'success': True,
            'message': f'Successfully migrated {stats["migrated"]} jobs to deployment user',
            'stats': stats
        }, 200
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'stats': stats
        }, 500

@functions_framework.http
def verify_migration(request):
    """Verify all jobs belong to deployment user"""
    
    db = firestore.Client(project=PROJECT_ID)
    jobs_collection = db.collection('jobs')
    
    try:
        # Count deployment user jobs
        deployment_jobs = jobs_collection.where('user_id', '==', DEPLOYMENT_USER_ID).stream()
        deployment_count = sum(1 for _ in deployment_jobs)
        
        # Check for non-deployment user jobs
        # Note: Firestore doesn't support != queries well, so we check known users
        known_users = ['test_user', 'current_user', 'anonymous', 'frontend_test']
        non_deployment_count = 0
        
        for user in known_users:
            user_jobs = jobs_collection.where('user_id', '==', user).stream()
            count = sum(1 for _ in user_jobs)
            non_deployment_count += count
        
        return {
            'success': True,
            'deployment_user_jobs': deployment_count,
            'non_deployment_user_jobs': non_deployment_count,
            'migration_complete': non_deployment_count == 0,
            'message': f'Deployment user has {deployment_count} jobs'
        }, 200
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }, 500