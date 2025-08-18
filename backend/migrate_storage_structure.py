#!/usr/bin/env python3
"""
Storage Migration Script
Migrates existing batch data to new standardized structure
"""

import asyncio
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

# Import GCP storage service
from services.gcp_storage_service import gcp_storage_service
from database.unified_job_manager import unified_job_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StorageMigrator:
    """Migrates existing batch storage to standardized structure"""
    
    def __init__(self):
        self.migrated_count = 0
        self.failed_count = 0
        self.batch_mapping = {}
    
    async def migrate_all_batches(self):
        """Main migration function"""
        logger.info("🚀 Starting storage migration to standardized structure")
        
        try:
            # Step 1: List all batch directories
            batches = await self._list_existing_batches()
            logger.info(f"Found {len(batches)} batches to migrate")
            
            # Step 2: Migrate each batch
            for batch_id in batches:
                success = await self._migrate_batch(batch_id)
                if success:
                    self.migrated_count += 1
                else:
                    self.failed_count += 1
            
            # Step 3: Clean up old structures
            if self.migrated_count > 0:
                await self._cleanup_old_structures()
            
            logger.info(f"✅ Migration complete: {self.migrated_count} successful, {self.failed_count} failed")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
    
    async def _list_existing_batches(self) -> List[str]:
        """List all existing batch IDs from storage"""
        batch_ids = []
        
        try:
            # List batches/ directory
            batches_prefix = "batches/"
            blobs = gcp_storage_service.storage.client.list_blobs(
                gcp_storage_service.storage.bucket_name,
                prefix=batches_prefix,
                delimiter="/"
            )
            
            # Extract batch IDs
            for page in blobs.pages:
                for prefix in page.prefixes:
                    batch_id = prefix.replace(batches_prefix, "").rstrip("/")
                    if batch_id:
                        batch_ids.append(batch_id)
            
            # Also check jobs/ directory for batch children
            jobs_prefix = "jobs/"
            blobs = gcp_storage_service.storage.client.list_blobs(
                gcp_storage_service.storage.bucket_name,
                prefix=jobs_prefix
            )
            
            for blob in blobs:
                # Check if job has parent_batch_id in metadata
                if "results.json" in blob.name:
                    job_id = blob.name.replace(jobs_prefix, "").split("/")[0]
                    content = blob.download_as_text()
                    
                    try:
                        data = json.loads(content)
                        parent_batch_id = data.get("parent_batch_id")
                        if parent_batch_id and parent_batch_id not in batch_ids:
                            batch_ids.append(parent_batch_id)
                    except:
                        pass
            
            return batch_ids
            
        except Exception as e:
            logger.error(f"Failed to list batches: {e}")
            return []
    
    async def _migrate_batch(self, batch_id: str) -> bool:
        """Migrate a single batch to standardized structure"""
        logger.info(f"Migrating batch: {batch_id}")
        
        try:
            # Create new standardized structure
            new_structure = {
                'batch_root': f"batches/{batch_id}",
                'batch_metadata': f"batches/{batch_id}/batch_metadata.json",
                'batch_index': f"batches/{batch_id}/batch_index.json",
                'jobs_root': f"batches/{batch_id}/jobs",
                'results_root': f"batches/{batch_id}/results",
                'aggregated_results': f"batches/{batch_id}/results/aggregated.json",
                'batch_summary': f"batches/{batch_id}/summary.json"
            }
            
            # Load existing batch index if available
            old_index_paths = [
                f"batches/{batch_id}/batch_index.json",
                f"batches/{batch_id}/index.json",
                f"batches/{batch_id}/metadata.json"
            ]
            
            batch_index = None
            for path in old_index_paths:
                content = gcp_storage_service.storage.download_file(path)
                if content:
                    batch_index = json.loads(content.decode('utf-8'))
                    break
            
            if not batch_index:
                logger.warning(f"No batch index found for {batch_id}, creating from scratch")
                batch_index = await self._reconstruct_batch_index(batch_id)
            
            # Migrate individual job files
            individual_jobs = batch_index.get('individual_jobs', [])
            for job_entry in individual_jobs:
                job_id = job_entry.get('job_id')
                if not job_id:
                    continue
                
                # Find and migrate job results
                old_paths = [
                    f"batches/{batch_id}/individual_jobs/{job_id}/results.json",
                    f"jobs/{job_id}/results.json",
                    f"jobs/{job_id}/modal_output.json"
                ]
                
                for old_path in old_paths:
                    content = gcp_storage_service.storage.download_file(old_path)
                    if content:
                        # Store in new standardized location
                        new_path = f"batches/{batch_id}/jobs/{job_id}/results.json"
                        await gcp_storage_service.storage.upload_file(
                            new_path, content, 'application/json'
                        )
                        
                        # Also migrate structure file if present
                        results_data = json.loads(content.decode('utf-8'))
                        if results_data.get('structure_file_base64'):
                            structure_path = f"batches/{batch_id}/jobs/{job_id}/structure.cif"
                            structure_content = results_data['structure_file_base64'].encode('utf-8')
                            await gcp_storage_service.storage.upload_file(
                                structure_path, structure_content, 'text/plain'
                            )
                        
                        # Create metadata file
                        metadata = {
                            'job_id': job_id,
                            'migrated_from': old_path,
                            'migrated_at': datetime.utcnow().isoformat(),
                            'affinity': results_data.get('affinity'),
                            'confidence': results_data.get('confidence')
                        }
                        metadata_path = f"batches/{batch_id}/jobs/{job_id}/metadata.json"
                        metadata_content = json.dumps(metadata, indent=2).encode('utf-8')
                        await gcp_storage_service.storage.upload_file(
                            metadata_path, metadata_content, 'application/json'
                        )
                        
                        logger.info(f"  ✅ Migrated job {job_id}")
                        break
            
            # Update batch index with new structure
            batch_index['storage_structure'] = new_structure
            batch_index['migrated_at'] = datetime.utcnow().isoformat()
            
            # Store updated batch index
            index_content = json.dumps(batch_index, indent=2).encode('utf-8')
            await gcp_storage_service.storage.upload_file(
                new_structure['batch_index'], index_content, 'application/json'
            )
            
            # Create aggregated results if batch is complete
            if self._is_batch_complete(batch_index):
                await self._create_aggregated_results(batch_id, batch_index)
            
            logger.info(f"✅ Successfully migrated batch {batch_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to migrate batch {batch_id}: {e}")
            return False
    
    async def _reconstruct_batch_index(self, batch_id: str) -> Dict[str, Any]:
        """Reconstruct batch index from available data"""
        
        # Try to get batch info from database
        batch_job = unified_job_manager.get_job(batch_id)
        
        if batch_job:
            return {
                'batch_id': batch_id,
                'created_at': batch_job.get('created_at', datetime.utcnow().isoformat()),
                'status': batch_job.get('status', 'unknown'),
                'metadata': batch_job.get('input_data', {}),
                'individual_jobs': []
            }
        
        # Fallback to minimal structure
        return {
            'batch_id': batch_id,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'unknown',
            'metadata': {},
            'individual_jobs': []
        }
    
    def _is_batch_complete(self, batch_index: Dict[str, Any]) -> bool:
        """Check if batch is complete"""
        jobs = batch_index.get('individual_jobs', [])
        if not jobs:
            return False
        
        for job in jobs:
            if job.get('status') not in ['completed', 'failed']:
                return False
        
        return True
    
    async def _create_aggregated_results(self, batch_id: str, batch_index: Dict[str, Any]):
        """Create aggregated results for completed batch"""
        
        try:
            individual_results = []
            
            for job_entry in batch_index['individual_jobs']:
                if job_entry.get('status') == 'completed':
                    job_id = job_entry['job_id']
                    results_path = f"batches/{batch_id}/jobs/{job_id}/results.json"
                    content = gcp_storage_service.storage.download_file(results_path)
                    
                    if content:
                        result_data = json.loads(content.decode('utf-8'))
                        individual_results.append({
                            'job_id': job_id,
                            'affinity': result_data.get('affinity', 0),
                            'confidence': result_data.get('confidence', 0),
                            'has_structure': bool(result_data.get('structure_file_base64'))
                        })
            
            # Create aggregated results
            aggregated = {
                'batch_id': batch_id,
                'status': 'completed',
                'created_at': batch_index.get('created_at'),
                'aggregated_at': datetime.utcnow().isoformat(),
                'results': individual_results,
                'statistics': {
                    'total_jobs': len(batch_index['individual_jobs']),
                    'completed_jobs': len(individual_results),
                    'avg_affinity': sum(r['affinity'] for r in individual_results) / len(individual_results) if individual_results else 0
                }
            }
            
            # Store aggregated results
            aggregated_path = f"batches/{batch_id}/results/aggregated.json"
            content = json.dumps(aggregated, indent=2).encode('utf-8')
            await gcp_storage_service.storage.upload_file(
                aggregated_path, content, 'application/json'
            )
            
            logger.info(f"  ✅ Created aggregated results for batch {batch_id}")
            
        except Exception as e:
            logger.error(f"Failed to create aggregated results: {e}")
    
    async def _cleanup_old_structures(self):
        """Clean up old storage structures after successful migration"""
        logger.info("🧹 Cleaning up old storage structures...")
        
        # List of old paths to remove
        old_patterns = [
            "batches/*/individual_jobs/",  # Old individual jobs path
            "batches/*/batch_results/",     # Old batch results path
            "batches/*/aggregated/"          # Old aggregated path (not /results/)
        ]
        
        # Note: Implement cleanup carefully to avoid data loss
        logger.info("⚠️ Manual cleanup recommended for safety")

async def main():
    """Run the migration"""
    migrator = StorageMigrator()
    await migrator.migrate_all_batches()

if __name__ == "__main__":
    asyncio.run(main())