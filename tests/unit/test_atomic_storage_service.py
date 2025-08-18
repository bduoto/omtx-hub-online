"""
Unit tests for AtomicStorageService
Tests the atomic storage operations with temp→finalize pattern
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
import json
import time

# Import the service under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

from services.atomic_storage_service import (
    AtomicStorageService,
    StorageTransaction
)

class TestStorageTransaction:
    """Test suite for StorageTransaction"""
    
    def test_initialization(self):
        """Test transaction initialization"""
        transaction = StorageTransaction("test-transaction-123")
        
        assert transaction.transaction_id == "test-transaction-123"
        assert transaction.operations == []
        assert transaction.temp_files == []
        assert transaction.final_files == []
        assert not transaction.committed
        assert not transaction.rolled_back
    
    def test_add_operation(self):
        """Test adding operations to transaction"""
        transaction = StorageTransaction("test-transaction-123")
        
        transaction.add_operation(
            operation_type="write",
            source="temp/file.json",
            destination="jobs/job123/file.json",
            data={"test": "data"}
        )
        
        assert len(transaction.operations) == 1
        operation = transaction.operations[0]
        assert operation['type'] == "write"
        assert operation['source'] == "temp/file.json"
        assert operation['destination'] == "jobs/job123/file.json"
        assert operation['data'] == {"test": "data"}
        assert 'timestamp' in operation

class TestAtomicStorageService:
    """Test suite for AtomicStorageService"""
    
    @pytest.fixture
    def mock_gcp_storage(self):
        """Mock GCP storage service"""
        mock_storage = Mock()
        mock_storage.upload_file = AsyncMock(return_value=True)
        mock_storage.download_file = AsyncMock(return_value=b'{"test": "data"}')
        mock_storage.delete_file = AsyncMock(return_value=True)
        mock_storage.move_file = AsyncMock(return_value=True)
        mock_storage.file_exists = AsyncMock(return_value=True)
        return mock_storage
    
    @pytest.fixture
    def service(self, mock_gcp_storage):
        """Create AtomicStorageService instance with mocked dependencies"""
        with patch('services.atomic_storage_service.gcp_storage_service', mock_gcp_storage):
            service = AtomicStorageService()
            return service
    
    def test_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert service.storage is not None
        assert 'jobs' in service.storage_hierarchy
        assert 'batches' in service.storage_hierarchy
        assert 'temp' in service.storage_hierarchy
    
    def test_generate_transaction_id(self, service):
        """Test transaction ID generation"""
        job_id = "test-job-123"
        transaction_id = service._generate_transaction_id(job_id)
        
        assert transaction_id.startswith(f"{job_id}_")
        assert len(transaction_id) > len(job_id) + 1
        
        # Should generate different IDs for same job
        transaction_id2 = service._generate_transaction_id(job_id)
        assert transaction_id != transaction_id2
    
    @pytest.mark.asyncio
    async def test_start_transaction(self, service):
        """Test transaction initialization"""
        transaction_id = "test-transaction-123"
        transaction = await service._start_transaction(transaction_id)
        
        assert isinstance(transaction, StorageTransaction)
        assert transaction.transaction_id == transaction_id
        assert not transaction.committed
        assert not transaction.rolled_back
    
    def test_determine_storage_paths_individual(self, service):
        """Test storage path determination for individual jobs"""
        paths = service._determine_storage_paths(
            job_id="job123",
            batch_id=None,
            storage_type="individual"
        )
        
        assert paths['base_path'] == "jobs/job123/"
        assert paths['results_file'] == "jobs/job123/results.json"
        assert paths['metadata_file'] == "jobs/job123/metadata.json"
    
    def test_determine_storage_paths_batch_child(self, service):
        """Test storage path determination for batch child jobs"""
        paths = service._determine_storage_paths(
            job_id="job123",
            batch_id="batch456",
            storage_type="batch_child"
        )
        
        assert paths['base_path'] == "batches/batch456/jobs/job123/"
        assert paths['results_file'] == "batches/batch456/jobs/job123/results.json"
        assert paths['metadata_file'] == "batches/batch456/jobs/job123/metadata.json"
    
    def test_determine_storage_paths_batch_parent(self, service):
        """Test storage path determination for batch parent jobs"""
        paths = service._determine_storage_paths(
            job_id="batch456",
            batch_id="batch456",
            storage_type="batch_parent"
        )
        
        assert paths['base_path'] == "batches/batch456/"
        assert paths['batch_index_file'] == "batches/batch456/batch_index.json"
        assert paths['batch_metadata_file'] == "batches/batch456/batch_metadata.json"
    
    @pytest.mark.asyncio
    async def test_write_temp_files(self, service):
        """Test writing files to temporary location"""
        transaction = StorageTransaction("test-transaction-123")
        
        result_data = {
            "job_id": "job123",
            "results": {"affinity": -0.5, "confidence": 0.8},
            "structure_data": "base64encodeddata",
            "metadata": {"execution_time": 120.5}
        }
        
        storage_paths = {
            'base_path': 'jobs/job123/',
            'results_file': 'jobs/job123/results.json',
            'metadata_file': 'jobs/job123/metadata.json',
            'structure_file': 'jobs/job123/structure.cif'
        }
        
        temp_files = await service._write_temp_files(transaction, result_data, storage_paths)
        
        assert len(temp_files) >= 2  # At least results and metadata
        assert any('results.json' in path for path in temp_files.values())
        assert any('metadata.json' in path for path in temp_files.values())
        
        # Verify transaction operations were recorded
        assert len(transaction.operations) > 0
        assert all(op['type'] == 'write' for op in transaction.operations)
    
    @pytest.mark.asyncio
    async def test_validate_temp_files(self, service):
        """Test temporary file validation"""
        temp_files = {
            'results': 'temp/transaction123/results.json',
            'metadata': 'temp/transaction123/metadata.json'
        }
        
        # Should pass validation when files exist
        with patch.object(service.storage, 'file_exists', return_value=True):
            await service._validate_temp_files(temp_files)  # Should not raise
        
        # Should fail validation when files don't exist
        with patch.object(service.storage, 'file_exists', return_value=False):
            with pytest.raises(Exception, match="Temporary file validation failed"):
                await service._validate_temp_files(temp_files)
    
    @pytest.mark.asyncio
    async def test_finalize_files(self, service):
        """Test atomic file finalization"""
        transaction = StorageTransaction("test-transaction-123")
        
        temp_files = {
            'results': 'temp/transaction123/results.json',
            'metadata': 'temp/transaction123/metadata.json'
        }
        
        storage_paths = {
            'results_file': 'jobs/job123/results.json',
            'metadata_file': 'jobs/job123/metadata.json'
        }
        
        final_files = await service._finalize_files(transaction, temp_files, storage_paths)
        
        assert len(final_files) == len(temp_files)
        assert 'results' in final_files
        assert 'metadata' in final_files
        assert final_files['results'] == 'jobs/job123/results.json'
        assert final_files['metadata'] == 'jobs/job123/metadata.json'
        
        # Verify move operations were recorded
        move_operations = [op for op in transaction.operations if op['type'] == 'move']
        assert len(move_operations) == len(temp_files)
    
    @pytest.mark.asyncio
    async def test_commit_transaction(self, service):
        """Test transaction commit"""
        transaction = StorageTransaction("test-transaction-123")
        transaction.temp_files = ['temp/file1.json', 'temp/file2.json']
        
        await service._commit_transaction(transaction)
        
        assert transaction.committed
        assert not transaction.rolled_back
        
        # Verify cleanup operations
        cleanup_operations = [op for op in transaction.operations if op['type'] == 'cleanup']
        assert len(cleanup_operations) > 0
    
    @pytest.mark.asyncio
    async def test_rollback_transaction(self, service):
        """Test transaction rollback"""
        transaction = StorageTransaction("test-transaction-123")
        transaction.temp_files = ['temp/file1.json', 'temp/file2.json']
        transaction.final_files = ['jobs/job123/file1.json']
        
        await service._rollback_transaction(transaction)
        
        assert transaction.rolled_back
        assert not transaction.committed
        
        # Verify rollback operations
        rollback_operations = [op for op in transaction.operations if op['type'] == 'rollback']
        assert len(rollback_operations) > 0
    
    @pytest.mark.asyncio
    async def test_store_job_result_atomic_success(self, service):
        """Test successful atomic job result storage"""
        job_id = "test-job-123"
        result_data = {
            "job_id": job_id,
            "results": {"affinity": -0.5, "confidence": 0.8},
            "structure_data": "base64encodeddata",
            "metadata": {"execution_time": 120.5}
        }
        
        final_files = await service.store_job_result_atomic(
            job_id=job_id,
            result_data=result_data,
            storage_type='individual'
        )
        
        assert isinstance(final_files, dict)
        assert len(final_files) > 0
        assert any('results.json' in path for path in final_files.values())
    
    @pytest.mark.asyncio
    async def test_store_job_result_atomic_batch_child(self, service):
        """Test atomic storage for batch child job"""
        job_id = "test-job-123"
        batch_id = "test-batch-456"
        result_data = {
            "job_id": job_id,
            "batch_id": batch_id,
            "results": {"affinity": -0.5, "confidence": 0.8}
        }
        
        final_files = await service.store_job_result_atomic(
            job_id=job_id,
            result_data=result_data,
            batch_id=batch_id,
            storage_type='batch_child'
        )
        
        assert isinstance(final_files, dict)
        # Verify batch hierarchy paths
        assert any(f'batches/{batch_id}/jobs/{job_id}' in path for path in final_files.values())
    
    @pytest.mark.asyncio
    async def test_store_job_result_atomic_failure_rollback(self, service):
        """Test rollback on storage failure"""
        job_id = "test-job-123"
        result_data = {"job_id": job_id}
        
        # Mock a failure during finalization
        with patch.object(service, '_finalize_files', side_effect=Exception("Storage failure")):
            with patch.object(service, '_rollback_transaction') as mock_rollback:
                with pytest.raises(Exception, match="Storage failure"):
                    await service.store_job_result_atomic(
                        job_id=job_id,
                        result_data=result_data
                    )
                
                # Verify rollback was called
                mock_rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_indexes(self, service):
        """Test index updates after successful storage"""
        job_id = "test-job-123"
        batch_id = "test-batch-456"
        final_files = {
            'results': 'jobs/job123/results.json',
            'metadata': 'jobs/job123/metadata.json'
        }
        result_data = {"job_id": job_id, "results": {"affinity": -0.5}}
        
        # Should not raise any exceptions
        await service._update_indexes(job_id, batch_id, final_files, result_data)
    
    def test_get_transaction_status(self, service):
        """Test transaction status reporting"""
        transaction = StorageTransaction("test-transaction-123")
        transaction.committed = True
        transaction.operations = [{"type": "write"}, {"type": "move"}]
        transaction.temp_files = ["temp/file1.json"]
        transaction.final_files = ["jobs/job123/file1.json"]
        
        status = service.get_transaction_status("test-transaction-123")
        
        assert status['transaction_id'] == "test-transaction-123"
        assert status['committed'] == True
        assert status['rolled_back'] == False
        assert status['operations'] == 2
        assert status['temp_files'] == 1
        assert status['final_files'] == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_transactions(self, service):
        """Test handling multiple concurrent transactions"""
        job_ids = ["job1", "job2", "job3"]
        result_data = {"results": {"affinity": -0.5}}
        
        # Submit multiple concurrent storage operations
        tasks = [
            service.store_job_result_atomic(
                job_id=job_id,
                result_data={**result_data, "job_id": job_id}
            )
            for job_id in job_ids
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        assert len(results) == 3
        assert all(isinstance(result, dict) for result in results)
    
    @pytest.mark.asyncio
    async def test_large_file_handling(self, service):
        """Test handling of large files with compression"""
        job_id = "test-job-large"
        
        # Create large result data
        large_data = {
            "job_id": job_id,
            "results": {"affinity": -0.5},
            "large_structure_data": "x" * 10000,  # 10KB of data
            "metadata": {"size": "large"}
        }
        
        final_files = await service.store_job_result_atomic(
            job_id=job_id,
            result_data=large_data
        )
        
        assert isinstance(final_files, dict)
        assert len(final_files) > 0
