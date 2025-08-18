"""
Modal Batch Executor - Optimized batch processing using Modal's spawn_map
"""

import asyncio
import logging
from typing import Dict, Any, List
from services.modal_subprocess_runner import modal_subprocess_runner

logger = logging.getLogger(__name__)

class ModalBatchExecutor:
    """Execute batches using Modal's spawn_map for optimal performance"""
    
    async def submit_batch_to_modal(
        self, 
        batch_id: str,
        protein_sequence: str,
        ligands: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Submit entire batch to Modal using spawn_map
        
        This enables Modal to process all ligands in parallel
        with automatic scaling and resource management
        """
        try:
            logger.info(f"🚀 Submitting batch {batch_id} with {len(ligands)} ligands to Modal spawn_map")
            
            # Prepare parameters for Modal spawn_map
            parameters = {
                'batch_id': batch_id,
                'protein_sequence': protein_sequence,
                'ligands': ligands,
                'use_spawn_map': True  # Signal to use spawn_map
            }
            
            # Execute via subprocess runner (which will use spawn_map)
            result = await modal_subprocess_runner.execute_modal_function(
                app_name='omtx-boltz2',
                function_name='batch_predict',
                parameters=parameters,
                timeout=3600  # 1 hour for batch
            )
            
            if result.get('status') == 'running':
                logger.info(f"✅ Batch {batch_id} submitted to Modal spawn_map")
                return {
                    'success': True,
                    'modal_call_ids': result.get('modal_call_ids', []),
                    'batch_id': batch_id
                }
            else:
                logger.error(f"❌ Modal spawn_map submission failed: {result}")
                return {'success': False, 'error': result.get('error')}
                
        except Exception as e:
            logger.error(f"❌ Failed to submit batch to Modal: {e}")
            return {'success': False, 'error': str(e)}

# Global instance
modal_batch_executor = ModalBatchExecutor()