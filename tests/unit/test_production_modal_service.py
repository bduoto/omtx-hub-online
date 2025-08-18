"""
Unit tests for ProductionModalService
Tests the core Modal integration functionality with QoS lanes and resource management
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
import time

# Import the service under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

from services.production_modal_service import (
    ProductionModalService, 
    QoSLane, 
    ModalCall
)

class TestProductionModalService:
    """Test suite for ProductionModalService"""
    
    @pytest.fixture
    def mock_modal_config(self):
        """Mock Modal configuration"""
        return {
            'models': {
                'boltz2': {
                    'app_name': 'test-boltz2-app',
                    'function_name': 'test_predict',
                    'timeout': 3600,
                    'gpu': 'A100-40GB'
                }
            }
        }
    
    @pytest.fixture
    def mock_modal_function(self):
        """Mock Modal function"""
        mock_func = Mock()
        mock_func.spawn = AsyncMock(return_value=Mock(call_id='test-call-123'))
        return mock_func
    
    @pytest.fixture
    def service(self, mock_modal_config):
        """Create ProductionModalService instance with mocked dependencies"""
        with patch('services.production_modal_service.load_modal_config', return_value=mock_modal_config):
            with patch('services.production_modal_service.modal_auth_service') as mock_auth:
                mock_auth.ensure_authenticated.return_value = None
                with patch('services.production_modal_service.unified_job_manager') as mock_job_manager:
                    mock_job_manager.update_job_status = AsyncMock(return_value=True)
                    service = ProductionModalService()
                    return service
    
    def test_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert service.config is not None
        assert service._function_cache == {}
        assert service._active_calls == {}
        assert QoSLane.INTERACTIVE in service.lane_limits
        assert QoSLane.BULK in service.lane_limits
    
    def test_qos_lane_limits(self, service):
        """Test QoS lane configuration"""
        interactive_limits = service.lane_limits[QoSLane.INTERACTIVE]
        bulk_limits = service.lane_limits[QoSLane.BULK]
        
        assert interactive_limits['max_concurrent'] == 4
        assert interactive_limits['max_gpu_minutes'] == 5
        assert bulk_limits['max_concurrent'] == 12
        assert bulk_limits['max_gpu_minutes'] == 30
    
    @pytest.mark.asyncio
    async def test_get_modal_function_caching(self, service, mock_modal_function):
        """Test Modal function caching"""
        with patch('modal.Function.from_name', return_value=mock_modal_function):
            # First call should cache the function
            func1 = await service.get_modal_function('boltz2')
            assert func1 == mock_modal_function
            assert 'boltz2' in service._function_cache
            
            # Second call should return cached function
            func2 = await service.get_modal_function('boltz2')
            assert func2 == mock_modal_function
            assert func1 is func2  # Same object reference
    
    @pytest.mark.asyncio
    async def test_get_modal_function_invalid_model(self, service):
        """Test error handling for invalid model type"""
        with pytest.raises(ValueError, match="Unknown model: invalid_model"):
            await service.get_modal_function('invalid_model')
    
    @pytest.mark.asyncio
    async def test_submit_job_success(self, service, mock_modal_function):
        """Test successful job submission"""
        with patch.object(service, 'get_modal_function', return_value=mock_modal_function):
            modal_call_id = await service.submit_job(
                model_type='boltz2',
                params={'protein_sequences': ['TEST'], 'ligands': ['CCO']},
                job_id='test-job-123',
                lane=QoSLane.INTERACTIVE
            )
            
            assert modal_call_id == 'test-call-123'
            assert modal_call_id in service._active_calls
            assert service._lane_usage[QoSLane.INTERACTIVE] == 1
            
            # Verify call info
            call_info = service._active_calls[modal_call_id]
            assert call_info.job_id == 'test-job-123'
            assert call_info.model_type == 'boltz2'
            assert call_info.lane == QoSLane.INTERACTIVE
    
    @pytest.mark.asyncio
    async def test_submit_job_idempotency(self, service, mock_modal_function):
        """Test job submission idempotency"""
        with patch.object(service, 'get_modal_function', return_value=mock_modal_function):
            # First submission
            modal_call_id1 = await service.submit_job(
                model_type='boltz2',
                params={'protein_sequences': ['TEST']},
                job_id='test-job-123',
                idem_key='unique-key-123'
            )
            
            # Second submission with same idempotency key
            modal_call_id2 = await service.submit_job(
                model_type='boltz2',
                params={'protein_sequences': ['TEST']},
                job_id='test-job-456',  # Different job ID
                idem_key='unique-key-123'  # Same idempotency key
            )
            
            # Should return the same modal call ID
            assert modal_call_id1 == modal_call_id2
            assert len(service._active_calls) == 1  # Only one call registered
    
    @pytest.mark.asyncio
    async def test_submit_job_lane_capacity_exceeded(self, service, mock_modal_function):
        """Test lane capacity enforcement"""
        with patch.object(service, 'get_modal_function', return_value=mock_modal_function):
            # Fill up interactive lane (max 4 concurrent)
            for i in range(4):
                await service.submit_job(
                    model_type='boltz2',
                    params={'protein_sequences': ['TEST']},
                    job_id=f'test-job-{i}',
                    lane=QoSLane.INTERACTIVE
                )
            
            # Fifth submission should fail
            with pytest.raises(ValueError, match="Lane interactive at capacity"):
                await service.submit_job(
                    model_type='boltz2',
                    params={'protein_sequences': ['TEST']},
                    job_id='test-job-overflow',
                    lane=QoSLane.INTERACTIVE
                )
    
    @pytest.mark.asyncio
    async def test_submit_batch_shards(self, service, mock_modal_function):
        """Test batch shard submission"""
        with patch.object(service, 'get_modal_function', return_value=mock_modal_function):
            ligand_groups = [
                ['CCO', 'CC(C)O'],  # Shard 1
                ['C1=CC=CC=C1', 'CC(=O)O']  # Shard 2
            ]
            
            modal_call_ids = await service.submit_batch_shards(
                model_type='boltz2',
                batch_id='test-batch-123',
                protein_sequence='MKTAYIAKQRQISFVKSHFSRQ',
                ligand_groups=ligand_groups,
                lane=QoSLane.BULK
            )
            
            assert len(modal_call_ids) == 2
            assert all(call_id.startswith('test-call-') for call_id in modal_call_ids)
            assert service._lane_usage[QoSLane.BULK] == 2
    
    def test_find_by_idem_key(self, service):
        """Test finding calls by idempotency key"""
        # Add a call with idempotency key
        call_info = ModalCall(
            modal_call_id='test-call-123',
            job_id='test-job-123',
            batch_id=None,
            model_type='boltz2',
            lane=QoSLane.INTERACTIVE,
            submitted_at=time.time(),
            idem_key='unique-key-123',
            shard_index=None
        )
        service._active_calls['test-call-123'] = call_info
        
        # Should find the call
        found_call = service._find_by_idem_key('unique-key-123')
        assert found_call == call_info
        
        # Should not find non-existent key
        not_found = service._find_by_idem_key('non-existent-key')
        assert not_found is None
    
    @pytest.mark.asyncio
    async def test_complete_call(self, service):
        """Test call completion"""
        # Add an active call
        call_info = ModalCall(
            modal_call_id='test-call-123',
            job_id='test-job-123',
            batch_id=None,
            model_type='boltz2',
            lane=QoSLane.INTERACTIVE,
            submitted_at=time.time(),
            idem_key=None,
            shard_index=None
        )
        service._active_calls['test-call-123'] = call_info
        service._lane_usage[QoSLane.INTERACTIVE] = 1
        
        # Complete the call
        await service.complete_call('test-call-123')
        
        # Verify cleanup
        assert 'test-call-123' not in service._active_calls
        assert service._lane_usage[QoSLane.INTERACTIVE] == 0
    
    def test_get_status(self, service):
        """Test status reporting"""
        # Add some active calls
        for i in range(2):
            call_info = ModalCall(
                modal_call_id=f'test-call-{i}',
                job_id=f'test-job-{i}',
                batch_id=None,
                model_type='boltz2',
                lane=QoSLane.INTERACTIVE,
                submitted_at=time.time(),
                idem_key=None,
                shard_index=None
            )
            service._active_calls[f'test-call-{i}'] = call_info
        
        service._lane_usage[QoSLane.INTERACTIVE] = 2
        
        status = service.get_status()
        
        assert status['total_active'] == 2
        assert status['lanes'][QoSLane.INTERACTIVE]['active'] == 2
        assert status['lanes'][QoSLane.INTERACTIVE]['utilization'] == 0.5  # 2/4
        assert 'boltz2' in status['cached_functions']
    
    @pytest.mark.asyncio
    async def test_error_handling_modal_function_failure(self, service):
        """Test error handling when Modal function fails"""
        with patch('modal.Function.from_name', side_effect=Exception("Modal connection failed")):
            with pytest.raises(Exception, match="Modal connection failed"):
                await service.get_modal_function('boltz2')
    
    @pytest.mark.asyncio
    async def test_resource_estimation_integration(self, service, mock_modal_function):
        """Test integration with resource estimation"""
        with patch.object(service, 'get_modal_function', return_value=mock_modal_function):
            # Test with different parameter sizes
            small_params = {'protein_sequences': ['MKTA'], 'ligands': ['CCO']}
            large_params = {'protein_sequences': ['M' * 1000], 'ligands': ['CCO'] * 50}
            
            # Both should succeed but may be routed to different lanes
            small_call_id = await service.submit_job(
                model_type='boltz2',
                params=small_params,
                job_id='small-job',
                lane=QoSLane.INTERACTIVE
            )
            
            large_call_id = await service.submit_job(
                model_type='boltz2',
                params=large_params,
                job_id='large-job',
                lane=QoSLane.BULK
            )
            
            assert small_call_id != large_call_id
            assert len(service._active_calls) == 2
