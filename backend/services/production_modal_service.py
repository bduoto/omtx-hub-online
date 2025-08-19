"""
Production Modal Service - Direct function handles without subprocess
Optimized for GKE + Modal architecture with no keep-warm needed
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import modal
from enum import Enum

from services.modal_auth_service import modal_auth_service
from config.modal_models import load_modal_config
from database.unified_job_manager import unified_job_manager

logger = logging.getLogger(__name__)

class QoSLane(Enum):
    """Quality of Service lanes"""
    INTERACTIVE = "interactive"  # p95 TTFB < 90s
    BULK = "bulk"               # Throughput optimized

@dataclass
class ModalCall:
    """Track Modal function call"""
    modal_call_id: str
    job_id: str
    batch_id: Optional[str]
    model_type: str
    lane: QoSLane
    submitted_at: float
    idem_key: Optional[str]
    shard_index: Optional[int]

class ProductionModalService:
    """
    Production Modal service with direct function calls (no subprocess)
    
    Key improvements:
    - Direct Modal function invocation via .spawn()
    - Two-lane QoS (interactive vs bulk)
    - Idempotency support
    - No keep-warm needed (cold starts negligible)
    """
    
    def __init__(self):
        self.config = load_modal_config()
        self._function_cache: Dict[str, modal.Function] = {}
        self._active_calls: Dict[str, ModalCall] = {}
        
        # QoS lane limits
        self.lane_limits = {
            QoSLane.INTERACTIVE: {'max_concurrent': 4, 'max_gpu_minutes': 5},
            QoSLane.BULK: {'max_concurrent': 12, 'max_gpu_minutes': 30}
        }
        
        # Track lane usage
        self._lane_usage = {
            QoSLane.INTERACTIVE: 0,
            QoSLane.BULK: 0
        }
        
        # Initialize Modal auth once (gracefully handle failures)
        try:
            modal_auth_service.ensure_authenticated()
        except Exception as e:
            logger.warning(f"⚠️ Modal authentication not available during startup: {e}")
            logger.info("Modal services will be unavailable until authentication is configured")
    
    async def get_modal_function(self, model_type: str) -> modal.Function:
        """Get cached Modal function handle - no subprocess needed"""
        if model_type not in self._function_cache:
            config = self.config['models'].get(model_type)
            if not config:
                raise ValueError(f"Unknown model: {model_type}")
            
            # Direct function reference - no subprocess!
            self._function_cache[model_type] = modal.Function.from_name(
                config['app_name'],
                config['function_name']
            )
            logger.info(f"✅ Cached Modal function for {model_type}")
            
        return self._function_cache[model_type]
    
    async def submit_job(
        self,
        model_type: str,
        params: Dict[str, Any],
        job_id: str,
        batch_id: Optional[str] = None,
        lane: QoSLane = QoSLane.BULK,
        idem_key: Optional[str] = None
    ) -> str:
        """
        Submit job to Modal using native .spawn()
        
        Returns modal_call_id for tracking
        """
        
        # Check idempotency
        if idem_key:
            existing = self._find_by_idem_key(idem_key)
            if existing:
                logger.info(f"🔄 Idempotent request: {idem_key}")
                return existing.modal_call_id
        
        # Check lane capacity
        if self._lane_usage[lane] >= self.lane_limits[lane]['max_concurrent']:
            raise ValueError(f"Lane {lane.value} at capacity")
        
        # Get function
        modal_func = await self.get_modal_function(model_type)
        
        # Add metadata
        params['_metadata'] = {
            'job_id': job_id,
            'batch_id': batch_id,
            'lane': lane.value,
            'idem_key': idem_key,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Submit with spawn() - direct Modal call, no subprocess!
        modal_call = modal_func.spawn(**params)
        modal_call_id = modal_call.object_id
        
        # Track call
        call_info = ModalCall(
            modal_call_id=modal_call_id,
            job_id=job_id,
            batch_id=batch_id,
            model_type=model_type,
            lane=lane,
            submitted_at=time.time(),
            idem_key=idem_key,
            shard_index=params.get('shard_index')
        )
        
        self._active_calls[modal_call_id] = call_info
        self._lane_usage[lane] += 1
        
        # Update job status
        await unified_job_manager.update_job_status(
            job_id, 
            status='running',
            metadata={'modal_call_id': modal_call_id}
        )
        
        logger.info(f"🚀 Submitted {model_type}: {modal_call_id} (lane: {lane.value})")
        return modal_call_id
    
    async def submit_batch_shards(
        self,
        model_type: str,
        batch_id: str,
        protein_sequence: str,
        ligand_groups: List[List[str]],
        lane: QoSLane = QoSLane.BULK,
        **kwargs
    ) -> List[str]:
        """
        Submit batch as optimized shards
        
        Key optimizations:
        - MSA computed once and cached
        - Ligands grouped into optimal shard sizes
        - Parallel submission with concurrency control
        """
        
        modal_call_ids = []
        max_concurrent = self.lane_limits[lane]['max_concurrent']
        
        for shard_idx, ligand_shard in enumerate(ligand_groups):
            # Wait if at capacity
            while self._lane_usage[lane] >= max_concurrent:
                await asyncio.sleep(1)
            
            # Prepare shard params
            shard_params = {
                'batch_id': batch_id,
                'protein_sequence': protein_sequence,
                'ligands': ligand_shard,
                'shard_index': shard_idx,
                'use_msa_server': kwargs.get('use_msa_server', True),
                'cache_msa': shard_idx == 0,  # First shard computes MSA
                **kwargs
            }
            
            # Submit shard
            job_id = f"{batch_id}_shard_{shard_idx}"
            modal_call_id = await self.submit_job(
                model_type=model_type,
                params=shard_params,
                job_id=job_id,
                batch_id=batch_id,
                lane=lane
            )
            
            modal_call_ids.append(modal_call_id)
        
        logger.info(f"✅ Submitted {len(modal_call_ids)} shards for batch {batch_id}")
        return modal_call_ids
    
    async def on_completion(self, modal_call_id: str, result: Dict[str, Any]):
        """Handle job completion (called by webhook or poller)"""
        if modal_call_id not in self._active_calls:
            logger.warning(f"Unknown call: {modal_call_id}")
            return
        
        call_info = self._active_calls.pop(modal_call_id)
        self._lane_usage[call_info.lane] -= 1
        
        # Update job status
        await unified_job_manager.update_job_status(
            call_info.job_id,
            status='completed',
            result=result
        )
        
        logger.info(f"✅ Completed: {modal_call_id} (lane: {call_info.lane.value})")
    
    async def on_failure(self, modal_call_id: str, error: Dict[str, Any]):
        """Handle job failure"""
        if modal_call_id not in self._active_calls:
            return
        
        call_info = self._active_calls.pop(modal_call_id)
        self._lane_usage[call_info.lane] -= 1
        
        await unified_job_manager.update_job_status(
            call_info.job_id,
            status='failed',
            error=error
        )
        
        logger.error(f"❌ Failed: {modal_call_id} - {error}")
    
    def _find_by_idem_key(self, idem_key: str) -> Optional[ModalCall]:
        """Find existing call by idempotency key"""
        for call in self._active_calls.values():
            if call.idem_key == idem_key:
                return call
        return None
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        return {
            'lanes': {
                lane.value: {
                    'active': self._lane_usage[lane],
                    'max': self.lane_limits[lane]['max_concurrent'],
                    'utilization': self._lane_usage[lane] / self.lane_limits[lane]['max_concurrent']
                }
                for lane in QoSLane
            },
            'total_active': sum(self._lane_usage.values()),
            'cached_functions': list(self._function_cache.keys())
        }

# Global singleton
production_modal_service = ProductionModalService()