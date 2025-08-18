"""
Unit tests for SmartJobRouter
Tests intelligent job routing with QoS lanes and resource management
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Import the service under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

from services.smart_job_router import (
    SmartJobRouter,
    QoSLane,
    ResourceEstimate,
    UserQuota
)

class TestResourceEstimate:
    """Test suite for ResourceEstimate"""
    
    def test_initialization(self):
        """Test ResourceEstimate initialization"""
        estimate = ResourceEstimate(
            gpu_seconds=120.5,
            memory_gb=8.0,
            storage_gb=2.5,
            ligand_count=10,
            protein_length=250
        )
        
        assert estimate.gpu_seconds == 120.5
        assert estimate.memory_gb == 8.0
        assert estimate.storage_gb == 2.5
        assert estimate.ligand_count == 10
        assert estimate.protein_length == 250

class TestUserQuota:
    """Test suite for UserQuota"""
    
    def test_initialization(self):
        """Test UserQuota initialization"""
        quota = UserQuota(
            user_id="test-user-123",
            tier="premium",
            daily_gpu_minutes=1800,
            monthly_gpu_minutes=54000,
            concurrent_jobs=10,
            daily_jobs=100
        )
        
        assert quota.user_id == "test-user-123"
        assert quota.tier == "premium"
        assert quota.daily_gpu_minutes == 1800
        assert quota.monthly_gpu_minutes == 54000
        assert quota.concurrent_jobs == 10
        assert quota.daily_jobs == 100
        assert quota.used_daily_gpu_minutes == 0
        assert quota.used_monthly_gpu_minutes == 0
        assert quota.active_jobs == 0
        assert quota.daily_job_count == 0

class TestSmartJobRouter:
    """Test suite for SmartJobRouter"""
    
    @pytest.fixture
    def router(self):
        """Create SmartJobRouter instance"""
        return SmartJobRouter()
    
    def test_initialization(self, router):
        """Test router initialization"""
        assert router is not None
        assert router.user_quotas == {}
        assert 'max_ligands' in router.interactive_thresholds
        assert 'max_gpu_seconds' in router.interactive_thresholds
        assert 'min_ligands' in router.bulk_thresholds
        assert 'min_gpu_seconds' in router.bulk_thresholds
    
    def test_estimate_resources_small_job(self, router):
        """Test resource estimation for small job"""
        job_request = {
            'protein_sequences': ['MKTAYIAKQRQISFVKSHFSRQ'],  # 22 amino acids
            'ligands': ['CCO', 'CC(C)O'],  # 2 ligands
            'use_msa_server': True
        }
        
        estimate = router._estimate_resources(job_request)
        
        assert isinstance(estimate, ResourceEstimate)
        assert estimate.ligand_count == 2
        assert estimate.protein_length == 22
        assert estimate.gpu_seconds > 0
        assert estimate.memory_gb > 0
        assert estimate.storage_gb > 0
    
    def test_estimate_resources_large_job(self, router):
        """Test resource estimation for large job"""
        job_request = {
            'protein_sequences': ['M' * 500],  # 500 amino acids
            'ligands': ['CCO'] * 50,  # 50 ligands
            'use_msa_server': True
        }
        
        estimate = router._estimate_resources(job_request)
        
        assert estimate.ligand_count == 50
        assert estimate.protein_length == 500
        # Large job should require more resources
        assert estimate.gpu_seconds > 100
        assert estimate.memory_gb > 4
    
    def test_estimate_resources_with_msa(self, router):
        """Test resource estimation with MSA enabled"""
        job_request = {
            'protein_sequences': ['MKTAYIAKQRQISFVKSHFSRQ'],
            'ligands': ['CCO'],
            'use_msa_server': True
        }
        
        estimate_with_msa = router._estimate_resources(job_request)
        
        job_request['use_msa_server'] = False
        estimate_without_msa = router._estimate_resources(job_request)
        
        # MSA should increase resource requirements
        assert estimate_with_msa.gpu_seconds > estimate_without_msa.gpu_seconds
        assert estimate_with_msa.memory_gb >= estimate_without_msa.memory_gb
    
    def test_select_lane_interactive(self, router):
        """Test lane selection for interactive jobs"""
        job_request = {
            'protein_sequences': ['MKTAYIAKQRQISFVKSHFSRQ'],
            'ligands': ['CCO', 'CC(C)O']  # Small number of ligands
        }
        
        estimate = ResourceEstimate(
            gpu_seconds=30.0,  # Under interactive threshold
            memory_gb=4.0,
            storage_gb=1.0,
            ligand_count=2,  # Under interactive threshold
            protein_length=22
        )
        
        user_quota = UserQuota(
            user_id="test-user",
            tier="default",
            daily_gpu_minutes=600,
            monthly_gpu_minutes=18000
        )
        
        lane = router._select_lane(job_request, estimate, None, user_quota)
        assert lane == QoSLane.INTERACTIVE
    
    def test_select_lane_bulk(self, router):
        """Test lane selection for bulk jobs"""
        job_request = {
            'protein_sequences': ['M' * 500],
            'ligands': ['CCO'] * 50  # Large number of ligands
        }
        
        estimate = ResourceEstimate(
            gpu_seconds=300.0,  # Over interactive threshold
            memory_gb=8.0,
            storage_gb=5.0,
            ligand_count=50,  # Over interactive threshold
            protein_length=500
        )
        
        user_quota = UserQuota(
            user_id="test-user",
            tier="default",
            daily_gpu_minutes=600,
            monthly_gpu_minutes=18000
        )
        
        lane = router._select_lane(job_request, estimate, None, user_quota)
        assert lane == QoSLane.BULK
    
    def test_select_lane_with_hint_interactive(self, router):
        """Test lane selection with interactive hint"""
        job_request = {'ligands': ['CCO'] * 5}  # Could go either way
        
        estimate = ResourceEstimate(
            gpu_seconds=45.0,  # Borderline
            memory_gb=4.0,
            storage_gb=1.0,
            ligand_count=5,
            protein_length=100
        )
        
        user_quota = UserQuota(
            user_id="test-user",
            tier="premium",  # Premium user
            daily_gpu_minutes=1800,
            monthly_gpu_minutes=54000
        )
        
        # With interactive hint, should prefer interactive
        lane = router._select_lane(job_request, estimate, 'interactive', user_quota)
        assert lane == QoSLane.INTERACTIVE
    
    def test_select_lane_with_hint_bulk(self, router):
        """Test lane selection with bulk hint"""
        job_request = {'ligands': ['CCO'] * 15}  # Bulk-sized job
        
        estimate = ResourceEstimate(
            gpu_seconds=150.0,
            memory_gb=6.0,
            storage_gb=3.0,
            ligand_count=15,
            protein_length=200
        )
        
        user_quota = UserQuota(
            user_id="test-user",
            tier="default",
            daily_gpu_minutes=600,
            monthly_gpu_minutes=18000
        )
        
        # With bulk hint, should use bulk
        lane = router._select_lane(job_request, estimate, 'bulk', user_quota)
        assert lane == QoSLane.BULK
    
    @pytest.mark.asyncio
    async def test_get_user_quota_new_user(self, router):
        """Test getting quota for new user"""
        user_id = "new-user-123"
        
        quota = await router._get_user_quota(user_id)
        
        assert quota.user_id == user_id
        assert quota.tier == "default"  # Default tier for new users
        assert quota.daily_gpu_minutes == 600  # Default daily limit
        assert user_id in router.user_quotas
    
    @pytest.mark.asyncio
    async def test_get_user_quota_existing_user(self, router):
        """Test getting quota for existing user"""
        user_id = "existing-user-123"
        
        # Pre-populate quota
        existing_quota = UserQuota(
            user_id=user_id,
            tier="premium",
            daily_gpu_minutes=1800,
            monthly_gpu_minutes=54000
        )
        router.user_quotas[user_id] = existing_quota
        
        quota = await router._get_user_quota(user_id)
        
        assert quota is existing_quota
        assert quota.tier == "premium"
    
    @pytest.mark.asyncio
    async def test_enforce_limits_within_quota(self, router):
        """Test quota enforcement when within limits"""
        user_id = "test-user"
        lane = QoSLane.INTERACTIVE
        
        estimate = ResourceEstimate(
            gpu_seconds=60.0,  # 1 minute
            memory_gb=4.0,
            storage_gb=1.0,
            ligand_count=5,
            protein_length=100
        )
        
        user_quota = UserQuota(
            user_id=user_id,
            tier="default",
            daily_gpu_minutes=600,
            monthly_gpu_minutes=18000,
            used_daily_gpu_minutes=300,  # Half used
            used_monthly_gpu_minutes=9000  # Half used
        )
        
        # Should not raise any exception
        await router._enforce_limits(user_id, lane, estimate, user_quota)
    
    @pytest.mark.asyncio
    async def test_enforce_limits_daily_quota_exceeded(self, router):
        """Test quota enforcement when daily limit exceeded"""
        user_id = "test-user"
        lane = QoSLane.INTERACTIVE
        
        estimate = ResourceEstimate(
            gpu_seconds=3600.0,  # 60 minutes
            memory_gb=4.0,
            storage_gb=1.0,
            ligand_count=5,
            protein_length=100
        )
        
        user_quota = UserQuota(
            user_id=user_id,
            tier="default",
            daily_gpu_minutes=600,
            monthly_gpu_minutes=18000,
            used_daily_gpu_minutes=580,  # Almost at limit
            used_monthly_gpu_minutes=5000
        )
        
        # Should raise quota exceeded exception
        with pytest.raises(ValueError, match="Daily GPU quota exceeded"):
            await router._enforce_limits(user_id, lane, estimate, user_quota)
    
    @pytest.mark.asyncio
    async def test_enforce_limits_monthly_quota_exceeded(self, router):
        """Test quota enforcement when monthly limit exceeded"""
        user_id = "test-user"
        lane = QoSLane.BULK
        
        estimate = ResourceEstimate(
            gpu_seconds=7200.0,  # 120 minutes
            memory_gb=8.0,
            storage_gb=5.0,
            ligand_count=50,
            protein_length=500
        )
        
        user_quota = UserQuota(
            user_id=user_id,
            tier="default",
            daily_gpu_minutes=600,
            monthly_gpu_minutes=18000,
            used_daily_gpu_minutes=100,
            used_monthly_gpu_minutes=17000  # Almost at monthly limit
        )
        
        # Should raise quota exceeded exception
        with pytest.raises(ValueError, match="Monthly GPU quota exceeded"):
            await router._enforce_limits(user_id, lane, estimate, user_quota)
    
    @pytest.mark.asyncio
    async def test_route_job_success(self, router):
        """Test successful job routing"""
        user_id = "test-user-123"
        job_request = {
            'protein_sequences': ['MKTAYIAKQRQISFVKSHFSRQ'],
            'ligands': ['CCO', 'CC(C)O', 'C1=CC=CC=C1'],
            'use_msa_server': True
        }
        
        lane, estimate = await router.route_job(user_id, job_request)
        
        assert isinstance(lane, QoSLane)
        assert isinstance(estimate, ResourceEstimate)
        assert estimate.ligand_count == 3
        assert estimate.gpu_seconds > 0
        
        # Verify user quota was created/updated
        assert user_id in router.user_quotas
    
    @pytest.mark.asyncio
    async def test_route_job_with_lane_hint(self, router):
        """Test job routing with lane hint"""
        user_id = "test-user-123"
        job_request = {
            'protein_sequences': ['MKTAYIAKQRQISFVKSHFSRQ'],
            'ligands': ['CCO'],
            'use_msa_server': False
        }
        
        # Force bulk lane with hint
        lane, estimate = await router.route_job(user_id, job_request, lane_hint='bulk')
        
        assert lane == QoSLane.BULK
        assert isinstance(estimate, ResourceEstimate)
    
    @pytest.mark.asyncio
    async def test_update_quota_usage(self, router):
        """Test quota usage updates"""
        user_id = "test-user-123"
        
        # Create initial quota
        quota = await router._get_user_quota(user_id)
        initial_daily = quota.used_daily_gpu_minutes
        initial_monthly = quota.used_monthly_gpu_minutes
        
        # Update usage
        await router.update_quota_usage(user_id, gpu_minutes=30.0)
        
        updated_quota = router.user_quotas[user_id]
        assert updated_quota.used_daily_gpu_minutes == initial_daily + 30.0
        assert updated_quota.used_monthly_gpu_minutes == initial_monthly + 30.0
    
    def test_get_quota_status(self, router):
        """Test quota status reporting"""
        user_id = "test-user-123"
        
        # Create quota with some usage
        quota = UserQuota(
            user_id=user_id,
            tier="premium",
            daily_gpu_minutes=1800,
            monthly_gpu_minutes=54000,
            used_daily_gpu_minutes=900,  # 50% used
            used_monthly_gpu_minutes=27000,  # 50% used
            active_jobs=3,
            daily_job_count=15
        )
        router.user_quotas[user_id] = quota
        
        status = router.get_quota_status(user_id)
        
        assert status['user_id'] == user_id
        assert status['tier'] == "premium"
        assert status['daily_gpu_utilization'] == 0.5  # 50%
        assert status['monthly_gpu_utilization'] == 0.5  # 50%
        assert status['active_jobs'] == 3
        assert status['daily_job_count'] == 15
    
    def test_get_system_status(self, router):
        """Test system status reporting"""
        # Add some users with quotas
        for i in range(3):
            user_id = f"user-{i}"
            quota = UserQuota(
                user_id=user_id,
                tier="default",
                daily_gpu_minutes=600,
                monthly_gpu_minutes=18000,
                used_daily_gpu_minutes=300,
                active_jobs=2
            )
            router.user_quotas[user_id] = quota
        
        status = router.get_system_status()
        
        assert status['total_users'] == 3
        assert status['active_jobs'] == 6  # 2 jobs per user
        assert status['total_daily_gpu_usage'] == 900  # 300 per user
        assert 'average_utilization' in status
