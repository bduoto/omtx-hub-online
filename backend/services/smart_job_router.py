"""
Smart Job Router - QoS lanes and intelligent resource planning
Routes jobs to interactive vs bulk lanes based on resource estimation
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from services.production_modal_service import ProductionModalService, QoSLane
from database.unified_job_manager import unified_job_manager

logger = logging.getLogger(__name__)

@dataclass
class ResourceEstimate:
    """GPU resource estimation for job planning"""
    gpu_seconds: float
    memory_gb: float
    estimated_duration: float
    shard_count: int
    msa_cost: float  # Additional cost for MSA computation
    ligand_count: int
    protein_length: int

@dataclass
class UserQuota:
    """Per-user resource quotas"""
    daily_gpu_minutes: float
    max_concurrent_interactive: int
    max_concurrent_bulk: int
    used_gpu_minutes_today: float
    current_interactive: int
    current_bulk: int
    tier: str = "default"  # default, premium, enterprise

class SmartJobRouter:
    """
    Route jobs to appropriate QoS lanes with resource planning
    
    Key features:
    - Intelligent lane selection (interactive vs bulk)
    - Resource estimation based on protein length and ligand count
    - Per-user quotas and limits
    - Admission control and queueing
    """
    
    def __init__(self):
        self.modal_service = ProductionModalService()
        
        # Lane thresholds for automatic routing
        self.interactive_thresholds = {
            'max_ligands': 10,
            'max_gpu_seconds': 300,  # 5 minutes
            'max_protein_length': 1000,
            'max_concurrent_per_user': 2
        }
        
        self.bulk_thresholds = {
            'min_ligands': 5,  # Below this, force interactive
            'max_gpu_seconds': 1800,  # 30 minutes
            'max_concurrent_per_user': 3
        }
        
        # User quota tiers
        self.quota_tiers = {
            'default': UserQuota(
                daily_gpu_minutes=600,  # 10 hours
                max_concurrent_interactive=2,
                max_concurrent_bulk=1,
                used_gpu_minutes_today=0,
                current_interactive=0,
                current_bulk=0,
                tier="default"
            ),
            'premium': UserQuota(
                daily_gpu_minutes=1800,  # 30 hours
                max_concurrent_interactive=4,
                max_concurrent_bulk=2,
                used_gpu_minutes_today=0,
                current_interactive=0,
                current_bulk=0,
                tier="premium"
            ),
            'enterprise': UserQuota(
                daily_gpu_minutes=7200,  # 120 hours
                max_concurrent_interactive=8,
                max_concurrent_bulk=4,
                used_gpu_minutes_today=0,
                current_interactive=0,
                current_bulk=0,
                tier="enterprise"
            )
        }
        
        # Track user quotas (in production, this would be in Redis/DB)
        self._user_quotas: Dict[str, UserQuota] = {}
        
    async def route_job(
        self,
        user_id: str,
        job_request: Dict[str, Any],
        lane_hint: Optional[str] = None
    ) -> Tuple[QoSLane, ResourceEstimate]:
        """
        Determine optimal lane and validate resource requirements
        
        Args:
            user_id: User identifier
            job_request: Job parameters
            lane_hint: User preference ('interactive', 'bulk', or 'auto')
        
        Returns:
            Tuple of (selected_lane, resource_estimate)
        
        Raises:
            ValueError: If job exceeds quotas or limits
        """
        
        # Get or create user quota
        user_quota = await self._get_user_quota(user_id)
        
        # Estimate resources
        estimate = self._estimate_resources(job_request)
        
        # Select lane based on estimation and hints
        lane = self._select_lane(job_request, estimate, lane_hint, user_quota)
        
        # Enforce quotas and limits
        await self._enforce_limits(user_id, lane, estimate, user_quota)
        
        logger.info(f"🎯 Routed job for {user_id}: {lane.value} lane, "
                   f"{estimate.gpu_seconds:.1f}s GPU, {estimate.ligand_count} ligands")
        
        return lane, estimate
    
    def _estimate_resources(self, job_request: Dict[str, Any]) -> ResourceEstimate:
        """
        Estimate GPU resources needed for job
        
        Based on empirical data from production runs
        """
        protein_sequences = job_request.get('protein_sequences', [])
        ligands = job_request.get('ligands', [])
        use_msa = job_request.get('use_msa_server', True)
        use_potentials = job_request.get('use_potentials', False)
        
        # Calculate dimensions
        protein_length = sum(len(seq) for seq in protein_sequences) if protein_sequences else 0
        ligand_count = len(ligands)
        
        if ligand_count == 0:
            raise ValueError("No ligands provided")
        
        # Empirical coefficients (tune based on actual production data)
        base_overhead = 30  # Model loading, setup
        protein_factor = protein_length * 0.05  # ~0.05s per residue
        ligand_factor = ligand_count * 12  # ~12s per ligand
        msa_overhead = 120 if use_msa else 0  # MSA computation
        potentials_overhead = ligand_count * 3 if use_potentials else 0  # Additional compute
        
        gpu_seconds = (base_overhead + protein_factor + 
                      ligand_factor + msa_overhead + potentials_overhead)
        
        # Memory estimation (A100-40GB limit)
        base_memory = 8  # Base memory for model
        protein_memory = protein_length * 0.01  # Memory scales with protein size
        ligand_memory = ligand_count * 0.2  # Memory per ligand
        memory_gb = min(38, base_memory + protein_memory + ligand_memory)  # Cap at 38GB
        
        # Shard planning for large jobs
        max_ligands_per_shard = 100  # Optimal for A100-40GB
        shard_count = max(1, (ligand_count + max_ligands_per_shard - 1) // max_ligands_per_shard)
        
        # Estimated duration with parallel execution
        estimated_duration = gpu_seconds / shard_count if shard_count > 1 else gpu_seconds
        
        return ResourceEstimate(
            gpu_seconds=gpu_seconds,
            memory_gb=memory_gb,
            estimated_duration=estimated_duration,
            shard_count=shard_count,
            msa_cost=msa_overhead,
            ligand_count=ligand_count,
            protein_length=protein_length
        )
    
    def _select_lane(
        self,
        job_request: Dict[str, Any],
        estimate: ResourceEstimate,
        lane_hint: Optional[str],
        user_quota: UserQuota
    ) -> QoSLane:
        """
        Select appropriate QoS lane based on job characteristics
        """
        
        # Check explicit hint first
        if lane_hint == 'interactive':
            # Validate interactive requirements
            if (estimate.ligand_count <= self.interactive_thresholds['max_ligands'] and
                estimate.gpu_seconds <= self.interactive_thresholds['max_gpu_seconds'] and
                estimate.protein_length <= self.interactive_thresholds['max_protein_length']):
                return QoSLane.INTERACTIVE
            else:
                logger.warning(f"Interactive hint rejected: exceeds thresholds")
        
        elif lane_hint == 'bulk':
            # Force bulk if requested and valid
            if estimate.ligand_count >= self.bulk_thresholds['min_ligands']:
                return QoSLane.BULK
        
        # Automatic selection based on job characteristics
        if (estimate.ligand_count <= self.interactive_thresholds['max_ligands'] and
            estimate.gpu_seconds <= self.interactive_thresholds['max_gpu_seconds'] and
            estimate.protein_length <= self.interactive_thresholds['max_protein_length']):
            return QoSLane.INTERACTIVE
        
        # Default to bulk for larger jobs
        return QoSLane.BULK
    
    async def _enforce_limits(
        self,
        user_id: str,
        lane: QoSLane,
        estimate: ResourceEstimate,
        user_quota: UserQuota
    ):
        """
        Enforce user quotas and system limits
        
        Raises ValueError if limits exceeded
        """
        
        # Check daily GPU quota
        required_minutes = estimate.gpu_seconds / 60
        if user_quota.used_gpu_minutes_today + required_minutes > user_quota.daily_gpu_minutes:
            remaining = user_quota.daily_gpu_minutes - user_quota.used_gpu_minutes_today
            raise ValueError(
                f"Daily GPU quota exceeded. Required: {required_minutes:.1f}m, "
                f"Remaining: {remaining:.1f}m. Quota resets at midnight UTC."
            )
        
        # Check concurrent job limits
        if lane == QoSLane.INTERACTIVE:
            if user_quota.current_interactive >= user_quota.max_concurrent_interactive:
                raise ValueError(
                    f"Interactive lane at capacity ({user_quota.current_interactive}/"
                    f"{user_quota.max_concurrent_interactive}). "
                    f"Please wait for current jobs to complete."
                )
        else:  # BULK
            if user_quota.current_bulk >= user_quota.max_concurrent_bulk:
                raise ValueError(
                    f"Bulk lane at capacity ({user_quota.current_bulk}/"
                    f"{user_quota.max_concurrent_bulk}). "
                    f"Please wait for current jobs to complete."
                )
        
        # Check system-wide lane capacity
        modal_metrics = await self.modal_service.get_metrics()
        lane_metrics = modal_metrics['lanes'][lane.value]
        
        if lane_metrics['utilization'] >= 0.9:  # 90% utilization threshold
            raise ValueError(
                f"{lane.value.title()} lane at {lane_metrics['utilization']:.0%} capacity. "
                f"Please try again in a few minutes."
            )
        
        # Reserve resources (update quotas)
        await self._reserve_resources(user_id, lane, estimate)
    
    async def _get_user_quota(self, user_id: str) -> UserQuota:
        """Get or create user quota (in production, this would query the database)"""
        if user_id not in self._user_quotas:
            # Default to 'default' tier, but in production this would be from user profile
            tier = await self._get_user_tier(user_id)
            self._user_quotas[user_id] = UserQuota(**self.quota_tiers[tier].__dict__)
        
        # Reset daily usage if needed
        await self._reset_daily_usage_if_needed(user_id)
        
        return self._user_quotas[user_id]
    
    async def _get_user_tier(self, user_id: str) -> str:
        """Get user tier from database (placeholder)"""
        # In production, query user profile for tier
        return "default"
    
    async def _reset_daily_usage_if_needed(self, user_id: str):
        """Reset daily usage at midnight UTC"""
        # In production, this would check last reset timestamp
        # For now, implement basic daily reset logic
        pass
    
    async def _reserve_resources(self, user_id: str, lane: QoSLane, estimate: ResourceEstimate):
        """Reserve resources for the job"""
        user_quota = self._user_quotas[user_id]
        
        # Reserve GPU minutes
        user_quota.used_gpu_minutes_today += estimate.gpu_seconds / 60
        
        # Reserve concurrent slot
        if lane == QoSLane.INTERACTIVE:
            user_quota.current_interactive += 1
        else:
            user_quota.current_bulk += 1
    
    async def release_resources(self, user_id: str, lane: QoSLane):
        """Release resources when job completes"""
        if user_id in self._user_quotas:
            user_quota = self._user_quotas[user_id]
            
            if lane == QoSLane.INTERACTIVE:
                user_quota.current_interactive = max(0, user_quota.current_interactive - 1)
            else:
                user_quota.current_bulk = max(0, user_quota.current_bulk - 1)
    
    async def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's current quota and usage status"""
        user_quota = await self._get_user_quota(user_id)
        
        return {
            'tier': user_quota.tier,
            'daily_quota': {
                'limit_minutes': user_quota.daily_gpu_minutes,
                'used_minutes': user_quota.used_gpu_minutes_today,
                'remaining_minutes': user_quota.daily_gpu_minutes - user_quota.used_gpu_minutes_today
            },
            'concurrent_limits': {
                'interactive': {
                    'limit': user_quota.max_concurrent_interactive,
                    'current': user_quota.current_interactive
                },
                'bulk': {
                    'limit': user_quota.max_concurrent_bulk,
                    'current': user_quota.current_bulk
                }
            }
        }
    
    async def estimate_job_cost(self, job_request: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate job cost and requirements without routing"""
        estimate = self._estimate_resources(job_request)
        
        return {
            'estimated_gpu_minutes': estimate.gpu_seconds / 60,
            'estimated_duration_minutes': estimate.estimated_duration / 60,
            'recommended_lane': 'interactive' if estimate.ligand_count <= 10 else 'bulk',
            'shard_count': estimate.shard_count,
            'memory_required_gb': estimate.memory_gb,
            'ligand_count': estimate.ligand_count,
            'protein_length': estimate.protein_length
        }

# Global singleton
smart_job_router = SmartJobRouter()