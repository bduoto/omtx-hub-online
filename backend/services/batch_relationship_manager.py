"""
Batch Job Relationship Manager
Handles parent-child relationships for batch jobs with efficient storage and retrieval
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from database.unified_job_manager import unified_job_manager
from services.gcp_storage_service import gcp_storage_service

logger = logging.getLogger(__name__)

class BatchRelationshipManager:
    """Manages parent-child relationships for batch jobs"""
    
    def __init__(self):
        self.relationship_cache = {}  # In-memory cache for active batches
    
    def _get_standardized_batch_structure(self, batch_id: str) -> Dict[str, str]:
        """Get standardized batch storage structure"""
        return {
            'batch_root': f"batches/{batch_id}",
            'batch_metadata': f"batches/{batch_id}/batch_metadata.json",
            'batch_index': f"batches/{batch_id}/batch_index.json",
            'jobs_root': f"batches/{batch_id}/jobs",
            'results_root': f"batches/{batch_id}/results",
            'aggregated_results': f"batches/{batch_id}/results/aggregated.json",
            'batch_summary': f"batches/{batch_id}/summary.json"
        }
    
    def _get_standardized_job_paths(self, batch_id: str, job_id: str) -> Dict[str, str]:
        """Get standardized paths for individual job within batch"""
        return {
            'job_root': f"batches/{batch_id}/jobs/{job_id}",
            'results': f"batches/{batch_id}/jobs/{job_id}/results.json",
            'structure': f"batches/{batch_id}/jobs/{job_id}/structure.cif",
            'metadata': f"batches/{batch_id}/jobs/{job_id}/metadata.json",
            'logs': f"batches/{batch_id}/jobs/{job_id}/logs.txt"
        }
    
    async def _store_child_results_unified(self, storage_paths: Dict[str, str], 
                                          job_id: str, results: Dict[str, Any], 
                                          task_type: str) -> bool:
        """Store child results in unified standardized location"""
        try:
            # Store main results file
            results_path = storage_paths['results']
            results_content = json.dumps(results, indent=2).encode('utf-8')
            success = gcp_storage_service.storage.upload_file(
                results_path, results_content, 'application/json'
            )
            
            # Store structure file if present (decode from base64)
            if results.get('structure_file_base64'):
                structure_path = storage_paths['structure']
                # Decode base64 to get actual CIF content
                import base64
                try:
                    structure_content = base64.b64decode(results['structure_file_base64'])
                    structure_success = gcp_storage_service.storage.upload_file(
                        structure_path, structure_content, 'chemical/x-cif'
                    )
                    success = success and structure_success
                    logger.info(f"✅ Stored structure.cif for job {job_id}")
                except Exception as e:
                    logger.error(f"Failed to decode/store structure for {job_id}: {e}")
                    success = False
            
            # Store metadata (enhanced to match individual jobs)
            metadata_path = storage_paths['metadata']
            metadata = {
                'job_id': job_id,
                'task_type': task_type,
                'model': 'boltz2',
                'stored_at': datetime.utcnow().isoformat(),
                'has_structure': bool(results.get('structure_file_base64')),
                'affinity': results.get('affinity', 0),
                'confidence': results.get('confidence', 0),
                'ptm_score': results.get('ptm_score', 0),
                'plddt_score': results.get('plddt_score', 0),
                'iptm_score': results.get('iptm_score', 0),
                'execution_time': results.get('execution_time', 0),
                'modal_call_id': results.get('modal_call_id'),
                'ligand_name': results.get('ligand_name', 'Unknown'),
                'protein_name': results.get('protein_name', 'Unknown')
            }
            metadata_content = json.dumps(metadata, indent=2).encode('utf-8')
            metadata_success = gcp_storage_service.storage.upload_file(
                metadata_path, metadata_content, 'application/json'
            )
            success = success and metadata_success
            logger.info(f"✅ Stored metadata.json for job {job_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to store unified results for {job_id}: {e}")
            return False
    
    async def create_batch_structure(self, batch_id: str, batch_metadata: Dict[str, Any]) -> bool:
        """Create batch job structure with standardized paths"""
        
        try:
            # Create batch index file in GCP with STANDARDIZED structure
            batch_index = {
                'batch_id': batch_id,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'created',
                'metadata': batch_metadata,
                'individual_jobs': [],
                'storage_structure': self._get_standardized_batch_structure(batch_id)
            }
            
            # Store batch index
            success = await self._store_batch_index(batch_id, batch_index)
            if success:
                self.relationship_cache[batch_id] = batch_index
                logger.info(f"✅ Created batch structure: {batch_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to create batch structure {batch_id}: {e}")
            return False
    
    async def register_child_job(self, batch_id: str, child_job_id: str, 
                                child_metadata: Dict[str, Any]) -> bool:
        """Register a child job with its parent batch"""
        
        try:
            # Get or create batch index
            batch_index = await self._get_batch_index(batch_id)
            if not batch_index:
                logger.error(f"❌ Batch {batch_id} not found for child registration")
                return False
            
            # Add child job to batch index with STANDARDIZED paths
            child_entry = {
                'job_id': child_job_id,
                'registered_at': datetime.utcnow().isoformat(),
                'metadata': child_metadata,
                'status': 'registered',
                'storage_paths': self._get_standardized_job_paths(batch_id, child_job_id)
            }
            
            batch_index['individual_jobs'].append(child_entry)
            
            # Update batch index
            success = await self._store_batch_index(batch_id, batch_index)
            if success:
                self.relationship_cache[batch_id] = batch_index
                logger.info(f"✅ Registered child job {child_job_id} with batch {batch_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to register child job {child_job_id} with batch {batch_id}: {e}")
            return False
    
    async def store_child_results(self, batch_id: str, child_job_id: str, 
                                 results: Dict[str, Any], task_type: str) -> bool:
        """Store child job results with proper batch relationship"""
        
        try:
            # Get batch index
            batch_index = await self._get_batch_index(batch_id)
            if not batch_index:
                logger.warning(f"⚠️ Batch {batch_id} not found, storing child {child_job_id} independently")
                # Fallback to independent storage
                return await gcp_storage_service.store_job_results(child_job_id, results, task_type)
            
            # Find child job entry
            child_entry = None
            for job in batch_index['individual_jobs']:
                if job['job_id'] == child_job_id:
                    child_entry = job
                    break
            
            if not child_entry:
                logger.warning(f"⚠️ Child job {child_job_id} not registered with batch {batch_id}")
                # Register it now
                await self.register_child_job(batch_id, child_job_id, {'task_type': task_type})
                batch_index = await self._get_batch_index(batch_id)
                child_entry = batch_index['individual_jobs'][-1]
            
            # Store results in SINGLE standardized location
            storage_paths = child_entry['storage_paths']
            
            # Store ONLY in standardized batch hierarchy
            success = await self._store_child_results_unified(
                storage_paths, child_job_id, results, task_type
            )
            
            # Update child status in batch index
            child_entry['status'] = 'completed'
            child_entry['completed_at'] = datetime.utcnow().isoformat()
            child_entry['results_summary'] = {
                'affinity': results.get('affinity'),
                'confidence': results.get('confidence'),
                'has_structure': bool(results.get('structure_file_base64'))
            }
            
            # Update batch index
            await self._store_batch_index(batch_id, batch_index)
            self.relationship_cache[batch_id] = batch_index
            
            # Check if batch is complete and trigger aggregation
            await self._check_batch_completion(batch_id, batch_index)
            
            logger.info(f"✅ Stored child results {child_job_id} for batch {batch_id}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to store child results {child_job_id} for batch {batch_id}: {e}")
            return False
    
    async def update_batch_progress_realtime(self, batch_id: str, job_id: str, status: str) -> bool:
        """Update batch progress in real-time - proactive tracking"""
        try:
            batch_index = await self._get_batch_index(batch_id)
            if not batch_index:
                return False
            
            # Update specific job status
            job_updated = False
            for job in batch_index['individual_jobs']:
                if job['job_id'] == job_id:
                    job['status'] = status
                    job['updated_at'] = datetime.utcnow().isoformat()
                    if status == 'completed':
                        job['completed_at'] = datetime.utcnow().isoformat()
                    elif status == 'failed':
                        job['failed_at'] = datetime.utcnow().isoformat()
                    job_updated = True
                    break
            
            if not job_updated:
                logger.warning(f"Job {job_id} not found in batch {batch_id}")
                return False
            
            # Recalculate batch progress statistics
            total_jobs = len(batch_index['individual_jobs'])
            completed = len([j for j in batch_index['individual_jobs'] if j['status'] == 'completed'])
            failed = len([j for j in batch_index['individual_jobs'] if j['status'] == 'failed'])
            running = len([j for j in batch_index['individual_jobs'] if j['status'] == 'running'])
            pending = len([j for j in batch_index['individual_jobs'] if j['status'] in ['pending', 'registered']])
            
            # Update batch progress
            batch_index['progress'] = {
                'total': total_jobs,
                'completed': completed,
                'failed': failed,
                'running': running,
                'pending': pending,
                'percentage': (completed / total_jobs * 100) if total_jobs > 0 else 0,
                'success_rate': (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Update batch status
            if completed + failed >= total_jobs:
                batch_index['status'] = 'completed' if failed == 0 else 'partially_completed'
            elif running > 0 or completed > 0:
                batch_index['status'] = 'running'
            else:
                batch_index['status'] = 'pending'
            
            # Store updated index
            success = await self._store_batch_index(batch_id, batch_index)
            
            # Trigger aggregation if batch is complete
            if completed + failed >= total_jobs:
                await self._create_aggregated_results(batch_id, batch_index)
            
            # Update cache
            if success:
                self.relationship_cache[batch_id] = batch_index
            
            logger.info(f"✅ Updated batch progress: {batch_id} - {completed}/{total_jobs} completed, {failed} failed")
            return success
            
        except Exception as e:
            logger.error(f"Failed to update batch progress for {batch_id}: {e}")
            return False
    
    async def get_batch_results(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Optimized batch result retrieval with single standardized path"""
        
        try:
            # FIRST: Try to load pre-aggregated results (fastest)
            aggregated_path = f"batches/{batch_id}/results/aggregated.json"
            aggregated_data = await self._load_json_from_gcp(aggregated_path)
            
            if aggregated_data:
                logger.info(f"✅ Loaded pre-aggregated results for batch {batch_id}")
                return aggregated_data
            
            # SECOND: Load batch index to build results
            batch_index = await self._get_batch_index(batch_id)
            if not batch_index:
                logger.error(f"Batch index not found for {batch_id}")
                return None
            
            # Build from individual jobs using SINGLE standardized path
            individual_results = []
            for job_entry in batch_index['individual_jobs']:
                if job_entry['status'] == 'completed':
                    # Use ONLY standardized path - no fallbacks
                    results_path = f"batches/{batch_id}/jobs/{job_entry['job_id']}/results.json"
                    result_content = await self._load_json_from_gcp(results_path)
                    
                    if result_content:
                        individual_results.append({
                            'job_id': job_entry['job_id'],
                            'ligand_name': job_entry.get('metadata', {}).get('ligand_name', 'Unknown'),
                            'ligand_smiles': job_entry.get('metadata', {}).get('ligand_smiles', ''),
                            'affinity': result_content.get('affinity', 0),
                            'confidence': result_content.get('confidence', 0),
                            'has_structure': bool(result_content.get('structure_file_base64')),
                            'results': result_content,
                            'metadata': job_entry['metadata'],
                            'summary': job_entry.get('results_summary', {})
                        })
            
            # Create complete batch results
            batch_results = {
                'batch_id': batch_id,
                'batch_name': batch_index.get('metadata', {}).get('job_name', 'Batch'),
                'status': batch_index.get('status', self._calculate_batch_status(batch_index)),
                'created_at': batch_index.get('created_at'),
                'progress': batch_index.get('progress', {}),
                'metadata': batch_index['metadata'],
                'individual_results': individual_results,
                'statistics': {
                    'total_jobs': len(batch_index['individual_jobs']),
                    'completed_jobs': len([j for j in batch_index['individual_jobs'] if j['status'] == 'completed']),
                    'failed_jobs': len([j for j in batch_index['individual_jobs'] if j['status'] == 'failed']),
                    'avg_affinity': sum(r['affinity'] for r in individual_results) / len(individual_results) if individual_results else 0,
                    'avg_confidence': sum(r['confidence'] for r in individual_results) / len(individual_results) if individual_results else 0,
                    'best_hit': min(individual_results, key=lambda x: x['affinity'], default=None)
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Cache the aggregated results for future use
            asyncio.create_task(self._cache_batch_results(batch_id, batch_results))
            
            return batch_results
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch results {batch_id}: {e}")
            return None
    
    async def _cache_batch_results(self, batch_id: str, batch_results: Dict[str, Any]) -> bool:
        """Cache batch results for future retrieval"""
        try:
            # Store as aggregated results
            aggregated_path = f"batches/{batch_id}/results/aggregated.json"
            content = json.dumps(batch_results, indent=2).encode('utf-8')
            success = gcp_storage_service.storage.upload_file(
                aggregated_path, content, 'application/json'
            )
            
            if success:
                logger.info(f"✅ Cached batch results for {batch_id}")
            
            return success
        except Exception as e:
            logger.error(f"Failed to cache batch results for {batch_id}: {e}")
            return False
    
    async def get_child_jobs(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all child jobs for a batch"""
        
        try:
            batch_index = await self._get_batch_index(batch_id)
            if not batch_index:
                return []
            
            return batch_index.get('individual_jobs', [])
            
        except Exception as e:
            logger.error(f"❌ Failed to get child jobs for batch {batch_id}: {e}")
            return []
    
    # Private helper methods
    
    async def _get_batch_index(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch index from cache or storage"""
        
        # Check cache first
        if batch_id in self.relationship_cache:
            return self.relationship_cache[batch_id]
        
        # Load from GCP
        index_path = f"batches/{batch_id}/batch_index.json"
        batch_index = await self._load_json_from_gcp(index_path)
        
        if batch_index:
            self.relationship_cache[batch_id] = batch_index
        
        return batch_index
    
    async def _store_batch_index(self, batch_id: str, batch_index: Dict[str, Any]) -> bool:
        """Store batch index to GCP"""
        
        index_path = f"batches/{batch_id}/batch_index.json"
        index_json = json.dumps(batch_index, indent=2)
        
        if gcp_storage_service.storage.available:
            return gcp_storage_service.storage.upload_file(
                index_path, index_json.encode('utf-8'), "application/json"
            )
        return False
    
    async def _load_json_from_gcp(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load JSON file from GCP storage"""
        
        if not gcp_storage_service.storage.available:
            return None
        
        try:
            content = gcp_storage_service.storage.download_file(file_path)
            if content:
                return json.loads(content.decode('utf-8'))
        except Exception as e:
            logger.debug(f"Could not load {file_path}: {e}")
        
        return None
    
    async def _store_child_results_at_path(self, base_path: str, job_id: str, 
                                          results: Dict[str, Any], task_type: str) -> bool:
        """Store child results at specific path"""
        
        if not gcp_storage_service.storage.available:
            return False
        
        try:
            # Store results JSON
            results_json = json.dumps(results, indent=2)
            success = gcp_storage_service.storage.upload_file(
                f"{base_path}/results.json", results_json.encode('utf-8'), "application/json"
            )
            
            # Store structure file if present
            if results.get('structure_file_base64'):
                import base64
                structure_content = base64.b64decode(results['structure_file_base64'])
                gcp_storage_service.storage.upload_file(
                    f"{base_path}/structure.cif", structure_content, "chemical/x-cif"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to store child results at {base_path}: {e}")
            return False
    
    async def _create_aggregated_results(self, batch_id: str, batch_index: Dict[str, Any]) -> bool:
        """Create and store aggregated batch results"""
        try:
            # Load all completed job results
            individual_results = []
            for job_entry in batch_index['individual_jobs']:
                if job_entry['status'] == 'completed':
                    # Load from standardized path
                    results_path = f"batches/{batch_id}/jobs/{job_entry['job_id']}/results.json"
                    result_content = await self._load_json_from_gcp(results_path)
                    
                    if result_content:
                        individual_results.append({
                            'job_id': job_entry['job_id'],
                            'ligand_name': job_entry.get('metadata', {}).get('ligand_name', 'Unknown'),
                            'ligand_smiles': job_entry.get('metadata', {}).get('ligand_smiles', ''),
                            'affinity': result_content.get('affinity', 0),
                            'confidence': result_content.get('confidence', 0),
                            'has_structure': bool(result_content.get('structure_file_base64')),
                            'completed_at': job_entry.get('completed_at')
                        })
            
            # Calculate aggregated statistics
            aggregated = {
                'batch_id': batch_id,
                'batch_name': batch_index.get('metadata', {}).get('job_name', 'Batch'),
                'status': batch_index['status'],
                'created_at': batch_index['created_at'],
                'aggregated_at': datetime.utcnow().isoformat(),
                'progress': batch_index.get('progress', {}),
                'results': individual_results,
                'statistics': {
                    'total_jobs': len(batch_index['individual_jobs']),
                    'completed_jobs': len([j for j in batch_index['individual_jobs'] if j['status'] == 'completed']),
                    'failed_jobs': len([j for j in batch_index['individual_jobs'] if j['status'] == 'failed']),
                    'avg_affinity': sum(r['affinity'] for r in individual_results) / len(individual_results) if individual_results else 0,
                    'avg_confidence': sum(r['confidence'] for r in individual_results) / len(individual_results) if individual_results else 0,
                    'best_affinity': min((r['affinity'] for r in individual_results), default=0),
                    'worst_affinity': max((r['affinity'] for r in individual_results), default=0)
                },
                'metadata': batch_index.get('metadata', {})
            }
            
            # Store aggregated results
            aggregated_path = f"batches/{batch_id}/results/aggregated.json"
            content = json.dumps(aggregated, indent=2).encode('utf-8')
            success = gcp_storage_service.storage.upload_file(
                aggregated_path, content, 'application/json'
            )
            
            # Also store summary
            summary_path = f"batches/{batch_id}/summary.json"
            summary = {
                'batch_id': batch_id,
                'status': batch_index['status'],
                'statistics': aggregated['statistics'],
                'top_hits': sorted(individual_results, key=lambda x: x['affinity'])[:10] if individual_results else []
            }
            summary_content = json.dumps(summary, indent=2).encode('utf-8')
            gcp_storage_service.storage.upload_file(
                summary_path, summary_content, 'application/json'
            )
            
            logger.info(f"✅ Created aggregated results for batch {batch_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to create aggregated results for {batch_id}: {e}")
            return False
    
    def _get_child_archive_path(self, batch_id: str, child_job_id: str, 
                               child_metadata: Dict[str, Any]) -> str:
        """Generate archive path for child job"""
        
        task_type = child_metadata.get('task_type', 'unknown')
        ligand_name = child_metadata.get('ligand_name', child_job_id[:8])
        
        # Clean ligand name for filesystem
        clean_ligand = ''.join(c for c in ligand_name if c.isalnum() or c in '-_')
        
        return f"archive/Batches/{batch_id}/{clean_ligand}_{child_job_id}"
    
    async def _load_child_results(self, batch_id: str, child_job_id: str) -> Optional[Dict[str, Any]]:
        """Load child job results"""
        
        # Try standardized batch path first
        standardized_path = f"batches/{batch_id}/jobs/{child_job_id}/results.json"
        results = await self._load_json_from_gcp(standardized_path)
        
        if not results:
            # Try legacy individual path for backward compatibility
            legacy_path = f"batches/{batch_id}/individual_jobs/{child_job_id}/results.json"
            results = await self._load_json_from_gcp(legacy_path)
        
        if not results:
            # Fallback to flat structure
            flat_path = f"jobs/{child_job_id}/results.json"
            results = await self._load_json_from_gcp(flat_path)
        
        return results
    
    async def initialize_batch_relationships(self, batch_id: str, batch_name: str, 
                                           batch_metadata: Dict[str, Any]) -> bool:
        """
        Initialize batch relationship structure with proper index
        
        Args:
            batch_id: Batch identifier
            batch_name: Human-readable batch name
            batch_metadata: Batch metadata and configuration
            
        Returns:
            Success status
        """
        try:
            logger.info(f"🔧 Initializing batch relationships for {batch_id}")
            
            # Create initial batch index structure
            batch_index = {
                'batch_id': batch_id,
                'batch_name': batch_name,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'status': 'created',
                'individual_jobs': [],  # Will be populated as jobs are registered
                'batch_metadata': batch_metadata,
                'storage_structure': self._get_standardized_batch_structure(batch_id)
            }
            
            # Store batch index in GCP
            success = await self._store_batch_index(batch_id, batch_index)
            if success:
                # Cache the index
                self.relationship_cache[batch_id] = batch_index
                logger.info(f"✅ Initialized batch relationships for {batch_id}")
            else:
                logger.error(f"❌ Failed to store batch index for {batch_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize batch relationships for {batch_id}: {e}")
            return False

    def _calculate_batch_status(self, batch_index: Dict[str, Any]) -> str:
        """Calculate overall batch status from individual jobs"""
        
        individual_jobs = batch_index.get('individual_jobs', [])
        if not individual_jobs:
            return 'empty'
        
        statuses = [job.get('status', 'unknown') for job in individual_jobs]
        
        if all(s == 'completed' for s in statuses):
            return 'completed'
        elif any(s == 'running' for s in statuses):
            return 'running'
        elif any(s in ['completed', 'running'] for s in statuses):
            return 'partially_completed'
        else:
            return 'failed'
    
    def _calculate_batch_summary(self, individual_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate batch summary statistics"""
        
        if not individual_results:
            return {
                'total_ligands': 0,
                'completed_jobs': 0,
                'failed_jobs': 0,
                'avg_affinity': 0,
                'top_affinity': 0,
                'success_rate': 0
            }
        
        completed = [r for r in individual_results if r.get('results')]
        affinities = [r['results'].get('affinity') for r in completed if r['results'].get('affinity')]
        
        return {
            'total_ligands': len(individual_results),
            'completed_jobs': len(completed),
            'failed_jobs': len(individual_results) - len(completed),
            'avg_affinity': sum(affinities) / len(affinities) if affinities else 0,
            'top_affinity': max(affinities) if affinities else 0,
            'success_rate': len(completed) / len(individual_results) * 100 if individual_results else 0
        }
    
    async def _check_batch_completion(self, batch_id: str, batch_index: Dict[str, Any]):
        """Check if batch is complete and trigger aggregation"""
        
        batch_status = self._calculate_batch_status(batch_index)
        
        if batch_status == 'completed':
            logger.info(f"🎉 Batch {batch_id} completed, creating aggregated results")
            await self._create_aggregated_results(batch_id, batch_index)
    
    async def _create_aggregated_results(self, batch_id: str, batch_index: Dict[str, Any]):
        """Create comprehensive aggregated batch results with enhanced Modal data"""
        
        try:
            logger.info(f"📊 Creating enhanced aggregated results for batch {batch_id}")
            
            # Get all child job IDs from batch index
            individual_jobs = batch_index.get('individual_jobs', [])
            job_ids = [job['job_id'] for job in individual_jobs]
            
            if not job_ids:
                logger.warning(f"No child jobs found for batch {batch_id}")
                return
            
            # Create enhanced aggregated results (using logic from batch fix API)
            aggregated_results = {
                'batch_id': batch_id,
                'created_at': datetime.utcnow().isoformat(),
                'total_jobs': len(job_ids),
                'completed_jobs': 0,
                'results': []
            }
            
            total_affinity = 0
            total_confidence = 0
            completed_count = 0
            
            # Process each job to get comprehensive results
            for job_id in job_ids:
                try:
                    # Get job results and metadata
                    results_path = f"batches/{batch_id}/jobs/{job_id}/results.json"
                    metadata_path = f"batches/{batch_id}/jobs/{job_id}/metadata.json"
                    
                    try:
                        results_data = gcp_storage_service.storage.download_file(results_path)
                        if isinstance(results_data, bytes):
                            results_data = results_data.decode('utf-8')
                        results = json.loads(results_data)
                        
                        metadata_data = gcp_storage_service.storage.download_file(metadata_path)
                        if isinstance(metadata_data, bytes):
                            metadata_data = metadata_data.decode('utf-8')
                        metadata = json.loads(metadata_data)
                        
                        completed_count += 1
                    except Exception as e:
                        logger.warning(f"Could not load results for job {job_id}: {e}")
                        continue
                    
                    # Extract actual values from raw modal result
                    raw_modal = results.get('raw_modal_result', {})
                    actual_affinity = raw_modal.get('affinity', metadata.get('affinity', 0))
                    actual_confidence = raw_modal.get('confidence', metadata.get('confidence', 0))
                    actual_ptm = raw_modal.get('ptm_score', metadata.get('ptm_score', 0))
                    actual_plddt = raw_modal.get('plddt_score', metadata.get('plddt_score', 0))
                    actual_iptm = raw_modal.get('iptm_score', metadata.get('iptm_score', 0))
                    
                    # Create comprehensive job summary with full Modal results
                    job_summary = {
                        'job_id': job_id,
                        'ligand_name': metadata.get('ligand_name', 'Unknown'),
                        'protein_name': metadata.get('protein_name', 'Unknown'),
                        'task_type': metadata.get('task_type', 'protein_ligand_binding'),
                        'model': metadata.get('model', 'boltz2'),
                        'stored_at': metadata.get('stored_at'),
                        'has_structure': metadata.get('has_structure', False),
                        'execution_time': metadata.get('execution_time', 0),
                        'modal_call_id': metadata.get('modal_call_id'),
                        
                        # Core prediction metrics (use actual values from raw modal result)
                        'affinity': actual_affinity,
                        'confidence': actual_confidence,
                        'ptm_score': actual_ptm,
                        'plddt_score': actual_plddt,
                        'iptm_score': actual_iptm,
                        
                        # Include full Modal result data for comprehensive analysis
                        'raw_modal_result': raw_modal,
                        
                        # Detailed prediction data
                        'structure_data': results.get('structure_data', {}),
                        'prediction_confidence': results.get('prediction_confidence', {}),
                        'binding_affinity': results.get('binding_affinity', {}),
                        
                        # Ensemble data if available
                        'affinity_ensemble': raw_modal.get('affinity_ensemble', {}),
                        'confidence_metrics': raw_modal.get('confidence_metrics', {}),
                    }
                    
                    aggregated_results['results'].append(job_summary)
                    total_affinity += actual_affinity
                    total_confidence += actual_confidence
                    
                except Exception as e:
                    logger.error(f"Error processing job {job_id} for aggregation: {e}")
            
            aggregated_results['completed_jobs'] = completed_count
            
            # Calculate comprehensive summary statistics
            affinities = [r['affinity'] for r in aggregated_results['results'] if r['affinity']]
            confidences = [r['confidence'] for r in aggregated_results['results'] if r['confidence']]
            ptm_scores = [r['ptm_score'] for r in aggregated_results['results'] if r['ptm_score']]
            plddt_scores = [r['plddt_score'] for r in aggregated_results['results'] if r['plddt_score']]
            iptm_scores = [r['iptm_score'] for r in aggregated_results['results'] if r['iptm_score']]
            execution_times = [r['execution_time'] for r in aggregated_results['results'] if r['execution_time']]
            
            # Find best and worst performers
            best_result = max(aggregated_results['results'], key=lambda x: x['affinity'], default={})
            worst_result = min(aggregated_results['results'], key=lambda x: x['affinity'], default={})
            
            aggregated_results['summary'] = {
                # Basic statistics
                'total_jobs': len(job_ids),
                'completed_jobs': completed_count,
                'success_rate': completed_count / len(job_ids) * 100 if job_ids else 0,
                
                # Affinity analysis
                'affinity_stats': {
                    'average': sum(affinities) / len(affinities) if affinities else 0,
                    'min': min(affinities) if affinities else 0,
                    'max': max(affinities) if affinities else 0,
                    'median': sorted(affinities)[len(affinities)//2] if affinities else 0,
                    'std_dev': (sum([(x - sum(affinities)/len(affinities))**2 for x in affinities]) / len(affinities))**0.5 if len(affinities) > 1 else 0
                },
                
                # Confidence analysis  
                'confidence_stats': {
                    'average': sum(confidences) / len(confidences) if confidences else 0,
                    'min': min(confidences) if confidences else 0,
                    'max': max(confidences) if confidences else 0,
                    'median': sorted(confidences)[len(confidences)//2] if confidences else 0
                },
                
                # Structure quality metrics
                'structure_quality': {
                    'avg_ptm': sum(ptm_scores) / len(ptm_scores) if ptm_scores else 0,
                    'avg_plddt': sum(plddt_scores) / len(plddt_scores) if plddt_scores else 0,
                    'avg_iptm': sum(iptm_scores) / len(iptm_scores) if iptm_scores else 0
                },
                
                # Performance metrics
                'performance': {
                    'avg_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0,
                    'total_execution_time': sum(execution_times) if execution_times else 0,
                    'structures_generated': len([r for r in aggregated_results['results'] if r['has_structure']])
                },
                
                # Best and worst performers
                'top_performer': {
                    'job_id': best_result.get('job_id', 'N/A'),
                    'ligand_name': best_result.get('ligand_name', 'N/A'),
                    'affinity': best_result.get('affinity', 0),
                    'confidence': best_result.get('confidence', 0)
                },
                'worst_performer': {
                    'job_id': worst_result.get('job_id', 'N/A'),
                    'ligand_name': worst_result.get('ligand_name', 'N/A'),
                    'affinity': worst_result.get('affinity', 0),
                    'confidence': worst_result.get('confidence', 0)
                },
                
                # Analysis insights
                'insights': {
                    'high_affinity_count': len([a for a in affinities if a > 0.8]),
                    'medium_affinity_count': len([a for a in affinities if 0.4 <= a <= 0.8]),
                    'low_affinity_count': len([a for a in affinities if a < 0.4]),
                    'high_confidence_count': len([c for c in confidences if c > 0.7]),
                    'recommended_ligands': [r['ligand_name'] for r in aggregated_results['results'] 
                                          if r['affinity'] > 0.6 and r['confidence'] > 0.5][:5]  # Top 5
                }
            }
            
            # Store aggregated results
            aggregated_path = f"batches/{batch_id}/results/aggregated.json"
            aggregated_content = json.dumps(aggregated_results, indent=2).encode('utf-8')
            gcp_storage_service.storage.upload_file(
                aggregated_path, aggregated_content, 'application/json'
            )
            logger.info(f"✅ Created enhanced aggregated.json for batch {batch_id}")
            
            # Create summary.json
            summary_path = f"batches/{batch_id}/results/summary.json"
            summary_content = json.dumps(aggregated_results['summary'], indent=2).encode('utf-8')
            gcp_storage_service.storage.upload_file(
                summary_path, summary_content, 'application/json'
            )
            logger.info(f"✅ Created enhanced summary.json for batch {batch_id}")
            
            # Create comprehensive batch results (parent-level results)
            batch_results_path = f"batches/{batch_id}/batch_results.json"
            batch_results = {
                'batch_id': batch_id,
                'batch_type': 'protein_ligand_binding_screen',
                'model': 'boltz2',
                'created_at': datetime.utcnow().isoformat(),
                'total_ligands_screened': len(job_ids),
                'successful_predictions': completed_count,
                
                # Overall batch statistics
                'batch_statistics': aggregated_results['summary'],
                
                # Individual job results with full Modal data
                'individual_results': aggregated_results['results'],
                
                # Ranking and recommendations
                'ligand_ranking': sorted(aggregated_results['results'], 
                                       key=lambda x: x['affinity'], reverse=True),
                
                # Export metadata for further analysis
                'export_info': {
                    'generated_at': datetime.utcnow().isoformat(),
                    'format_version': '2.0',
                    'data_source': 'modal_boltz2_predictions',
                    'includes_raw_modal_results': True,
                    'includes_structure_files': True
                }
            }
            
            batch_results_content = json.dumps(batch_results, indent=2).encode('utf-8')
            gcp_storage_service.storage.upload_file(
                batch_results_path, batch_results_content, 'application/json'
            )
            logger.info(f"✅ Created comprehensive batch_results.json for batch {batch_id}")
            
            # Create CSV export
            self._create_batch_csv_export(batch_id, aggregated_results['results'])
            
            logger.info(f"✅ Created complete enhanced aggregated results structure for batch {batch_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to create enhanced aggregated results for batch {batch_id}: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    async def _create_batch_summary(self, batch_id: str, batch_index: Dict[str, Any], 
                                  batch_results: Dict[str, Any]):
        """Create batch summary with key datapoints"""
        
        try:
            individual_results = batch_results.get('individual_results', [])
            
            # Calculate key statistics
            total_jobs = len(individual_results)
            completed_jobs = len([r for r in individual_results if r.get('status') == 'completed'])
            failed_jobs = total_jobs - completed_jobs
            
            # Extract key datapoints from results
            affinities = []
            confidences = []
            ptm_scores = []
            iptm_scores = []
            plddt_scores = []
            
            for result in individual_results:
                results_data = result.get('results', {})
                if results_data:
                    if results_data.get('affinity') is not None:
                        affinities.append(results_data['affinity'])
                    if results_data.get('confidence') is not None:
                        confidences.append(results_data['confidence'])
                    if results_data.get('ptm_score') is not None:
                        ptm_scores.append(results_data['ptm_score'])
                    if results_data.get('iptm_score') is not None:
                        iptm_scores.append(results_data['iptm_score'])
                    if results_data.get('plddt_score') is not None:
                        plddt_scores.append(results_data['plddt_score'])
            
            # Build comprehensive summary
            summary = {
                'batch_id': batch_id,
                'batch_name': batch_index.get('batch_name'),
                'created_at': batch_index.get('created_at'),
                'completed_at': datetime.utcnow().isoformat(),
                'processing_stats': {
                    'total_jobs': total_jobs,
                    'completed_jobs': completed_jobs,
                    'failed_jobs': failed_jobs,
                    'success_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
                },
                'prediction_summary': {
                    'affinity_stats': {
                        'count': len(affinities),
                        'mean': sum(affinities) / len(affinities) if affinities else None,
                        'min': min(affinities) if affinities else None,
                        'max': max(affinities) if affinities else None,
                        'best_affinity': min(affinities) if affinities else None,  # Lower is better
                        'worst_affinity': max(affinities) if affinities else None
                    },
                    'confidence_stats': {
                        'count': len(confidences),
                        'mean': sum(confidences) / len(confidences) if confidences else None,
                        'min': min(confidences) if confidences else None,
                        'max': max(confidences) if confidences else None,
                        'highest_confidence': max(confidences) if confidences else None
                    },
                    'structure_quality': {
                        'ptm_mean': sum(ptm_scores) / len(ptm_scores) if ptm_scores else None,
                        'iptm_mean': sum(iptm_scores) / len(iptm_scores) if iptm_scores else None,
                        'plddt_mean': sum(plddt_scores) / len(plddt_scores) if plddt_scores else None
                    }
                },
                'top_predictions': self._get_top_predictions(individual_results),
                'batch_metadata': batch_index.get('batch_metadata', {}),
                'files_generated': {
                    'structure_files': len([r for r in individual_results 
                                          if r.get('results', {}).get('structure_file_base64')]),
                    'total_files': total_jobs * 3  # results.json, metadata.json, structure.cif
                }
            }
            
            # Store summary
            summary_path = f"batches/{batch_id}/summary.json"
            summary_json = json.dumps(summary, indent=2)
            
            gcp_storage_service.storage.upload_file(
                summary_path, summary_json.encode('utf-8'), "application/json"
            )
            
            # Also store in results folder
            results_summary_path = f"batches/{batch_id}/results/summary.json"
            gcp_storage_service.storage.upload_file(
                results_summary_path, summary_json.encode('utf-8'), "application/json"
            )
            
            logger.info(f"✅ Created batch summary for {batch_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create batch summary for {batch_id}: {e}")
    
    def _get_top_predictions(self, individual_results: List[Dict[str, Any]], top_n: int = 5):
        """Get top N predictions by affinity and confidence"""
        
        try:
            # Filter results with affinity scores
            scored_results = []
            for result in individual_results:
                results_data = result.get('results', {})
                if results_data.get('affinity') is not None:
                    scored_results.append({
                        'job_id': result.get('job_id'),
                        'ligand_name': result.get('metadata', {}).get('ligand_name'),
                        'ligand_smiles': result.get('metadata', {}).get('ligand_smiles'),
                        'affinity': results_data.get('affinity'),
                        'confidence': results_data.get('confidence'),
                        'ptm_score': results_data.get('ptm_score'),
                        'iptm_score': results_data.get('iptm_score'),
                        'plddt_score': results_data.get('plddt_score')
                    })
            
            # Sort by affinity (lower is better) and confidence (higher is better)
            top_by_affinity = sorted(scored_results, key=lambda x: x['affinity'])[:top_n]
            top_by_confidence = sorted(scored_results, key=lambda x: x['confidence'], reverse=True)[:top_n]
            
            return {
                'best_affinity': top_by_affinity,
                'highest_confidence': top_by_confidence
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get top predictions: {e}")
            return {'best_affinity': [], 'highest_confidence': []}
    
    async def _create_job_index(self, batch_id: str, batch_results: Dict[str, Any]):
        """Create individual job index for easy lookup"""
        
        try:
            job_index = {
                'batch_id': batch_id,
                'created_at': datetime.utcnow().isoformat(),
                'total_jobs': len(batch_results.get('individual_results', [])),
                'jobs': {}
            }
            
            for result in batch_results.get('individual_results', []):
                job_id = result.get('job_id')
                if job_id:
                    job_index['jobs'][job_id] = {
                        'status': result.get('status'),
                        'ligand_name': result.get('metadata', {}).get('ligand_name'),
                        'ligand_smiles': result.get('metadata', {}).get('ligand_smiles'),
                        'affinity': result.get('results', {}).get('affinity'),
                        'confidence': result.get('results', {}).get('confidence'),
                        'has_structure': bool(result.get('results', {}).get('structure_file_base64')),
                        'storage_path': f"batches/{batch_id}/jobs/{job_id}/"
                    }
            
            # Store job index
            index_path = f"batches/{batch_id}/results/job_index.json"
            index_json = json.dumps(job_index, indent=2)
            
            gcp_storage_service.storage.upload_file(
                index_path, index_json.encode('utf-8'), "application/json"
            )
            
            logger.info(f"✅ Created job index for {batch_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create job index for {batch_id}: {e}")
    
    async def _store_batch_metadata_copy(self, batch_id: str, batch_index: Dict[str, Any]):
        """Store batch metadata copy in results folder"""
        
        try:
            metadata_copy = {
                'batch_metadata': batch_index.get('batch_metadata', {}),
                'storage_structure': batch_index.get('storage_structure', {}),
                'copied_at': datetime.utcnow().isoformat()
            }
            
            metadata_path = f"batches/{batch_id}/results/batch_metadata.json"
            metadata_json = json.dumps(metadata_copy, indent=2)
            
            gcp_storage_service.storage.upload_file(
                metadata_path, metadata_json.encode('utf-8'), "application/json"
            )
            
            logger.info(f"✅ Stored batch metadata copy for {batch_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store batch metadata copy for {batch_id}: {e}")

    def _create_batch_csv_export(self, batch_id: str, results_list: List[Dict[str, Any]]):
        """Create CSV export of batch results"""
        
        try:
            import io
            import csv
            
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Enhanced header with all key datapoints
            writer.writerow([
                'job_id', 'ligand_name', 'protein_name', 'affinity', 'confidence', 
                'ptm_score', 'iptm_score', 'plddt_score', 'execution_time', 'has_structure',
                'stored_at', 'affinity_probability', 'complex_plddt', 'ligand_iptm', 'protein_iptm'
            ])
            
            # Data rows
            for result in results_list:
                writer.writerow([
                    result.get('job_id', ''),
                    result.get('ligand_name', 'Unknown'),
                    result.get('protein_name', 'Unknown'),
                    result.get('affinity', 0),
                    result.get('confidence', 0),
                    result.get('ptm_score', 0),
                    result.get('iptm_score', 0),
                    result.get('plddt_score', 0),
                    result.get('execution_time', 0),
                    result.get('has_structure', False),
                    result.get('stored_at', ''),
                    result.get('raw_modal_result', {}).get('affinity_probability', ''),
                    result.get('raw_modal_result', {}).get('confidence_metrics', {}).get('complex_plddt', ''),
                    result.get('raw_modal_result', {}).get('ligand_iptm_score', ''),
                    result.get('raw_modal_result', {}).get('protein_iptm_score', ''),
                ])
            
            # Store CSV
            csv_path = f"batches/{batch_id}/results/batch_export.csv"
            csv_content = output.getvalue()
            
            gcp_storage_service.storage.upload_file(
                csv_path, csv_content.encode('utf-8'), "text/csv"
            )
            
            logger.info(f"✅ Created enhanced CSV export for batch {batch_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create CSV export for batch {batch_id}: {e}")

# Global instance
batch_relationship_manager = BatchRelationshipManager()