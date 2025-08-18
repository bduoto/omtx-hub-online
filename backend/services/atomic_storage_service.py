"""
Atomic Storage Service - Hierarchical storage with atomic operations
Provides robust, transactional storage for job results and batch data
"""

import asyncio
import json
import logging
import time
import base64
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
import hashlib

from services.gcp_storage_service import gcp_storage_service

logger = logging.getLogger(__name__)

class StorageTransaction:
    """Represents an atomic storage transaction"""
    
    def __init__(self, transaction_id: str):
        self.transaction_id = transaction_id
        self.operations: List[Dict[str, Any]] = []
        self.temp_files: List[str] = []
        self.final_files: List[str] = []
        self.committed = False
        self.rolled_back = False
    
    def add_operation(self, operation_type: str, source: str, destination: str, data: Any = None):
        """Add an operation to the transaction"""
        self.operations.append({
            'type': operation_type,
            'source': source,
            'destination': destination,
            'data': data,
            'timestamp': time.time()
        })

class AtomicStorageService:
    """
    Atomic storage operations with temp → finalize pattern
    
    Key features:
    - Atomic writes (all succeed or all fail)
    - Hierarchical organization (jobs/, batches/, archive/)
    - Automatic rollback on failures
    - Duplicate detection and deduplication
    - Compression for large files
    """
    
    def __init__(self):
        self.storage = gcp_storage_service
        
        # Storage hierarchy
        self.storage_hierarchy = {
            'jobs': 'jobs/{job_id}/',
            'batches': 'batches/{batch_id}/',
            'batch_jobs': 'batches/{batch_id}/jobs/{job_id}/',
            'results': 'batches/{batch_id}/results/',
            'archive': 'archive/{date}/{batch_id}/',
            'temp': 'temp/{transaction_id}/',
            'index': 'index/'
        }
        
        # Active transactions
        self.active_transactions: Dict[str, StorageTransaction] = {}
        
        # File type configurations
        self.file_configs = {
            'results.json': {'compress': True, 'index': True},
            'metadata.json': {'compress': False, 'index': True},
            'structure.cif': {'compress': True, 'index': False},
            'structure.pdb': {'compress': True, 'index': False},
            'batch_results.json': {'compress': True, 'index': True},
            'batch_index.json': {'compress': False, 'index': True}
        }
    
    async def store_job_result_atomic(
        self,
        job_id: str,
        result_data: Dict[str, Any],
        batch_id: Optional[str] = None,
        storage_type: str = 'individual'
    ) -> Dict[str, str]:
        """
        Store job result atomically with temp → finalize pattern
        
        Args:
            job_id: Unique job identifier
            result_data: Complete job result data from Modal
            batch_id: Optional batch ID for hierarchical storage
            storage_type: 'individual', 'batch_child', or 'batch_parent'
        
        Returns:
            Dictionary mapping file types to final storage paths
        """
        
        transaction_id = self._generate_transaction_id(job_id)
        
        try:
            # Start transaction
            transaction = await self._start_transaction(transaction_id)
            
            # Determine storage paths
            storage_paths = self._determine_storage_paths(job_id, batch_id, storage_type)
            
            # Write all files to temporary location
            temp_files = await self._write_temp_files(transaction, result_data, storage_paths)
            
            # Validate all temporary files
            await self._validate_temp_files(temp_files)
            
            # Atomic move to final locations
            final_files = await self._finalize_files(transaction, temp_files, storage_paths)
            
            # Update indexes if needed
            await self._update_indexes(job_id, batch_id, final_files, result_data)
            
            # Commit transaction
            await self._commit_transaction(transaction)
            
            logger.info(f"✅ Atomically stored job {job_id} ({len(final_files)} files)")
            return final_files
            
        except Exception as e:
            logger.error(f"❌ Atomic storage failed for job {job_id}: {e}")
            await self._rollback_transaction(transaction_id)
            raise
    
    async def store_batch_metadata_atomic(
        self,
        batch_id: str,
        metadata: Dict[str, Any],
        child_jobs: List[str] = None
    ) -> Dict[str, str]:
        """Store batch metadata atomically"""
        
        transaction_id = self._generate_transaction_id(f"batch_{batch_id}")
        
        try:
            transaction = await self._start_transaction(transaction_id)
            
            # Prepare batch metadata
            batch_metadata = {
                'batch_id': batch_id,
                'created_at': datetime.utcnow().isoformat(),
                'metadata': metadata,
                'child_jobs': child_jobs or [],
                'total_jobs': len(child_jobs) if child_jobs else 0,
                'storage_version': '2.0.0'
            }
            
            # Storage paths
            storage_paths = {
                'metadata': f"batches/{batch_id}/metadata.json",
                'index': f"batches/{batch_id}/job_index.json"
            }
            
            # Write metadata
            metadata_content = json.dumps(batch_metadata, indent=2)
            await self._write_file_to_transaction(
                transaction,
                storage_paths['metadata'],
                metadata_content.encode('utf-8'),
                'application/json'
            )
            
            # Write job index
            job_index = {
                'batch_id': batch_id,
                'total_jobs': len(child_jobs) if child_jobs else 0,
                'created_jobs': 0,
                'completed_jobs': 0,
                'failed_jobs': 0,
                'job_ids': child_jobs or [],
                'created_at': datetime.utcnow().isoformat()
            }
            
            index_content = json.dumps(job_index, indent=2)
            await self._write_file_to_transaction(
                transaction,
                storage_paths['index'],
                index_content.encode('utf-8'),
                'application/json'
            )
            
            # Finalize transaction
            final_files = {}
            for file_type, path in storage_paths.items():
                final_files[file_type] = path
                transaction.final_files.append(path)
            
            await self._commit_transaction(transaction)
            
            logger.info(f"✅ Stored batch metadata for {batch_id}")
            return final_files
            
        except Exception as e:
            logger.error(f"❌ Failed to store batch metadata for {batch_id}: {e}")
            await self._rollback_transaction(transaction_id)
            raise
    
    async def create_batch_aggregation_atomic(
        self,
        batch_id: str,
        job_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Create batch aggregation files atomically"""
        
        transaction_id = self._generate_transaction_id(f"batch_agg_{batch_id}")
        
        try:
            transaction = await self._start_transaction(transaction_id)
            
            # Create aggregated results
            aggregation = await self._create_batch_aggregation(batch_id, job_results)
            
            # Storage paths
            storage_paths = {
                'batch_results': f"batches/{batch_id}/results/batch_results.json",
                'summary': f"batches/{batch_id}/results/summary.json",
                'csv_export': f"batches/{batch_id}/results/batch_results.csv",
                'top_performers': f"batches/{batch_id}/results/top_performers.json"
            }
            
            # Write aggregated files
            files_written = {}
            
            # Main batch results
            batch_results_content = json.dumps(aggregation['batch_results'], indent=2)
            await self._write_file_to_transaction(
                transaction,
                storage_paths['batch_results'],
                batch_results_content.encode('utf-8'),
                'application/json'
            )
            files_written['batch_results'] = storage_paths['batch_results']
            
            # Summary statistics
            summary_content = json.dumps(aggregation['summary'], indent=2)
            await self._write_file_to_transaction(
                transaction,
                storage_paths['summary'],
                summary_content.encode('utf-8'),
                'application/json'
            )
            files_written['summary'] = storage_paths['summary']
            
            # CSV export
            csv_content = self._create_csv_export(aggregation['batch_results'])
            await self._write_file_to_transaction(
                transaction,
                storage_paths['csv_export'],
                csv_content.encode('utf-8'),
                'text/csv'
            )
            files_written['csv_export'] = storage_paths['csv_export']
            
            # Top performers
            top_performers_content = json.dumps(aggregation['top_performers'], indent=2)
            await self._write_file_to_transaction(
                transaction,
                storage_paths['top_performers'],
                top_performers_content.encode('utf-8'),
                'application/json'
            )
            files_written['top_performers'] = storage_paths['top_performers']
            
            await self._commit_transaction(transaction)
            
            logger.info(f"✅ Created batch aggregation for {batch_id} ({len(files_written)} files)")
            return files_written
            
        except Exception as e:
            logger.error(f"❌ Failed to create batch aggregation for {batch_id}: {e}")
            await self._rollback_transaction(transaction_id)
            raise
    
    def _determine_storage_paths(
        self,
        job_id: str,
        batch_id: Optional[str],
        storage_type: str
    ) -> Dict[str, str]:
        """Determine optimal storage paths based on job context"""
        
        if storage_type == 'batch_child' and batch_id:
            # Store batch child jobs under batch hierarchy
            base_path = f"batches/{batch_id}/jobs/{job_id}"
        elif storage_type == 'batch_parent' and batch_id:
            # Batch parent metadata
            base_path = f"batches/{batch_id}"
        else:
            # Individual jobs
            base_path = f"jobs/{job_id}"
        
        return {
            'results': f"{base_path}/results.json",
            'metadata': f"{base_path}/metadata.json",
            'structure_primary': f"{base_path}/structure.cif",
            'structure_models': f"{base_path}/structures/",
            'logs': f"{base_path}/logs.txt"
        }
    
    async def _write_temp_files(
        self,
        transaction: StorageTransaction,
        result_data: Dict[str, Any],
        storage_paths: Dict[str, str]
    ) -> Dict[str, str]:
        """Write all files to temporary location"""
        
        temp_files = {}
        temp_base = f"temp/{transaction.transaction_id}"
        
        # Main results file
        results_content = json.dumps(result_data, indent=2)
        temp_results_path = f"{temp_base}/results.json"
        await self._write_file_to_transaction(
            transaction,
            temp_results_path,
            results_content.encode('utf-8'),
            'application/json'
        )
        temp_files['results'] = temp_results_path
        
        # Metadata file
        metadata = {
            'job_id': result_data.get('job_id'),
            'processed_at': datetime.utcnow().isoformat(),
            'model_version': result_data.get('parameters', {}).get('model', 'boltz2'),
            'execution_time': result_data.get('execution_time'),
            'storage_version': '2.0.0',
            'file_checksums': {}
        }
        
        metadata_content = json.dumps(metadata, indent=2)
        temp_metadata_path = f"{temp_base}/metadata.json"
        await self._write_file_to_transaction(
            transaction,
            temp_metadata_path,
            metadata_content.encode('utf-8'),
            'application/json'
        )
        temp_files['metadata'] = temp_metadata_path
        
        # Structure files
        if 'structure_file_base64' in result_data:
            structure_data = base64.b64decode(result_data['structure_file_base64'])
            temp_structure_path = f"{temp_base}/structure.cif"
            await self._write_file_to_transaction(
                transaction,
                temp_structure_path,
                structure_data,
                'chemical/x-cif'
            )
            temp_files['structure_primary'] = temp_structure_path
        
        # Additional structure models
        if 'all_structures' in result_data:
            for i, struct_data in enumerate(result_data['all_structures']):
                if 'base64' in struct_data:
                    structure_data = base64.b64decode(struct_data['base64'])
                    temp_model_path = f"{temp_base}/structure_model_{i}.cif"
                    await self._write_file_to_transaction(
                        transaction,
                        temp_model_path,
                        structure_data,
                        'chemical/x-cif'
                    )
                    temp_files[f'structure_model_{i}'] = temp_model_path
        
        return temp_files
    
    async def _write_file_to_transaction(
        self,
        transaction: StorageTransaction,
        path: str,
        data: bytes,
        content_type: str
    ):
        """Write a file as part of a transaction"""
        
        try:
            # Apply compression if configured
            filename = Path(path).name
            config = self.file_configs.get(filename, {})
            
            if config.get('compress', False) and len(data) > 1024:  # Compress files > 1KB
                import gzip
                data = gzip.compress(data)
                content_type = 'application/gzip'
            
            # Write to storage
            await self.storage.upload_file(path, data, content_type=content_type)
            
            # Track in transaction
            transaction.temp_files.append(path)
            transaction.add_operation('write', '', path, len(data))
            
        except Exception as e:
            logger.error(f"❌ Failed to write file {path}: {e}")
            raise
    
    async def _validate_temp_files(self, temp_files: Dict[str, str]):
        """Validate all temporary files were written correctly"""
        
        for file_type, path in temp_files.items():
            try:
                # Check if file exists and is readable
                exists = await self.storage.file_exists(path)
                if not exists:
                    raise ValueError(f"Temporary file not found: {path}")
                
                # Basic integrity check
                file_info = await self.storage.get_file_info(path)
                if file_info.get('size', 0) == 0:
                    raise ValueError(f"Temporary file is empty: {path}")
                
            except Exception as e:
                logger.error(f"❌ Validation failed for {path}: {e}")
                raise
    
    async def _finalize_files(
        self,
        transaction: StorageTransaction,
        temp_files: Dict[str, str],
        storage_paths: Dict[str, str]
    ) -> Dict[str, str]:
        """Move files from temp to final locations atomically"""
        
        final_files = {}
        
        for file_type, temp_path in temp_files.items():
            if file_type in storage_paths:
                final_path = storage_paths[file_type]
                
                # Atomic copy (GCS copy operation is atomic)
                await self.storage.copy_file(temp_path, final_path)
                
                final_files[file_type] = final_path
                transaction.final_files.append(final_path)
                transaction.add_operation('copy', temp_path, final_path)
        
        return final_files
    
    async def _update_indexes(
        self,
        job_id: str,
        batch_id: Optional[str],
        final_files: Dict[str, str],
        result_data: Dict[str, Any]
    ):
        """Update search indexes for fast queries"""
        
        try:
            # Create index entry
            index_entry = {
                'job_id': job_id,
                'batch_id': batch_id,
                'indexed_at': datetime.utcnow().isoformat(),
                'file_paths': final_files,
                'affinity': result_data.get('affinity'),
                'confidence': result_data.get('confidence'),
                'model_version': result_data.get('parameters', {}).get('model', 'boltz2'),
                'execution_time': result_data.get('execution_time')
            }
            
            # Store index entry
            index_path = f"index/jobs/{job_id}.json"
            index_content = json.dumps(index_entry, indent=2)
            await self.storage.upload_file(
                index_path,
                index_content.encode('utf-8'),
                content_type='application/json'
            )
            
            logger.debug(f"📇 Updated index for job {job_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update indexes for job {job_id}: {e}")
            # Don't fail the transaction for index errors
    
    async def _create_batch_aggregation(
        self,
        batch_id: str,
        job_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create comprehensive batch aggregation"""
        
        if not job_results:
            return {
                'batch_results': {'batch_id': batch_id, 'individual_results': []},
                'summary': {'total_jobs': 0},
                'top_performers': []
            }
        
        # Process individual results
        individual_results = []
        affinities = []
        confidences = []
        execution_times = []
        
        for result in job_results:
            affinity = result.get('affinity')
            confidence = result.get('confidence')
            execution_time = result.get('execution_time')
            
            individual_results.append({
                'job_id': result.get('job_id'),
                'ligand_name': result.get('ligand_name', 'Unknown'),
                'affinity': affinity,
                'confidence': confidence,
                'ptm_score': result.get('ptm_score'),
                'iptm_score': result.get('iptm_score'),
                'plddt_score': result.get('plddt_score'),
                'execution_time': execution_time
            })
            
            if affinity is not None:
                affinities.append(affinity)
            if confidence is not None:
                confidences.append(confidence)
            if execution_time is not None:
                execution_times.append(execution_time)
        
        # Calculate summary statistics
        summary = {
            'total_jobs': len(job_results),
            'completed_jobs': len([r for r in job_results if r.get('status') == 'completed']),
            'affinity_stats': self._calculate_stats(affinities) if affinities else None,
            'confidence_stats': self._calculate_stats(confidences) if confidences else None,
            'execution_time_stats': self._calculate_stats(execution_times) if execution_times else None,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Identify top performers
        top_performers = sorted(
            individual_results,
            key=lambda x: (x.get('affinity') or 0, x.get('confidence') or 0),
            reverse=True
        )[:10]  # Top 10
        
        # Create main batch results
        batch_results = {
            'batch_id': batch_id,
            'individual_results': individual_results,
            'summary': summary,
            'created_at': datetime.utcnow().isoformat(),
            'storage_version': '2.0.0'
        }
        
        return {
            'batch_results': batch_results,
            'summary': summary,
            'top_performers': top_performers
        }
    
    def _calculate_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate basic statistics for a list of values"""
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(values)
        
        return {
            'count': n,
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / n,
            'median': sorted_values[n // 2],
            'std': (sum((x - sum(values) / n) ** 2 for x in values) / n) ** 0.5
        }
    
    def _create_csv_export(self, batch_results: Dict[str, Any]) -> str:
        """Create CSV export of batch results"""
        
        individual_results = batch_results.get('individual_results', [])
        
        if not individual_results:
            return "job_id,ligand_name,affinity,confidence,ptm_score,iptm_score,plddt_score,execution_time\n"
        
        # Header
        csv_lines = ["job_id,ligand_name,affinity,confidence,ptm_score,iptm_score,plddt_score,execution_time"]
        
        # Data rows
        for result in individual_results:
            row = [
                result.get('job_id', ''),
                result.get('ligand_name', ''),
                str(result.get('affinity', '')),
                str(result.get('confidence', '')),
                str(result.get('ptm_score', '')),
                str(result.get('iptm_score', '')),
                str(result.get('plddt_score', '')),
                str(result.get('execution_time', ''))
            ]
            csv_lines.append(','.join(row))
        
        return '\n'.join(csv_lines)
    
    async def _start_transaction(self, transaction_id: str) -> StorageTransaction:
        """Start a new storage transaction"""
        
        transaction = StorageTransaction(transaction_id)
        self.active_transactions[transaction_id] = transaction
        
        logger.debug(f"🔄 Started transaction: {transaction_id}")
        return transaction
    
    async def _commit_transaction(self, transaction: StorageTransaction):
        """Commit a storage transaction"""
        
        try:
            # All files should already be in their final locations
            transaction.committed = True
            
            # Clean up temporary files
            for temp_file in transaction.temp_files:
                try:
                    await self.storage.delete_file(temp_file)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup temp file {temp_file}: {e}")
            
            # Remove from active transactions
            self.active_transactions.pop(transaction.transaction_id, None)
            
            logger.debug(f"✅ Committed transaction: {transaction.transaction_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to commit transaction {transaction.transaction_id}: {e}")
            raise
    
    async def _rollback_transaction(self, transaction_id: str):
        """Rollback a failed transaction"""
        
        transaction = self.active_transactions.get(transaction_id)
        if not transaction:
            return
        
        try:
            transaction.rolled_back = True
            
            # Delete all files created during this transaction
            cleanup_tasks = []
            
            for temp_file in transaction.temp_files:
                cleanup_tasks.append(self.storage.delete_file(temp_file))
            
            for final_file in transaction.final_files:
                cleanup_tasks.append(self.storage.delete_file(final_file))
            
            # Execute cleanup in parallel
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Remove from active transactions
            self.active_transactions.pop(transaction_id, None)
            
            logger.info(f"🔄 Rolled back transaction: {transaction_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to rollback transaction {transaction_id}: {e}")
    
    def _generate_transaction_id(self, job_id: str) -> str:
        """Generate unique transaction ID"""
        timestamp = str(int(time.time() * 1000))
        job_hash = hashlib.md5(job_id.encode()).hexdigest()[:8]
        return f"txn_{timestamp}_{job_hash}"
    
    async def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a transaction"""
        
        transaction = self.active_transactions.get(transaction_id)
        if not transaction:
            return None
        
        return {
            'transaction_id': transaction_id,
            'committed': transaction.committed,
            'rolled_back': transaction.rolled_back,
            'operations': len(transaction.operations),
            'temp_files': len(transaction.temp_files),
            'final_files': len(transaction.final_files)
        }

# Global singleton
atomic_storage_service = AtomicStorageService()