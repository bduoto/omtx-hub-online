#!/usr/bin/env python3
"""
Modal Volume Manager - Optimized storage using Modal Volumes
Provides high-performance storage for batch results
"""

import modal
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class ModalVolumeManager:
    """
    Manages Modal Volumes for high-performance batch result storage
    Modal Volumes are optimized for write-once, read-many ML workloads
    """
    
    def __init__(self):
        self.volume_name = "omtx-batch-results"
        self._volume = None
    
    @property
    def volume(self):
        """Lazy load the Modal Volume"""
        if self._volume is None:
            self._volume = modal.Volume.from_name(
                self.volume_name,
                create_if_missing=True
            )
        return self._volume
    
    async def store_batch_results(
        self,
        batch_id: str,
        results: List[Dict[str, Any]]
    ) -> bool:
        """
        Store batch results in Modal Volume with optimized structure
        """
        try:
            # Modal Volumes are perfect for batch results - write once, read many
            batch_path = f"/batches/{batch_id}"
            
            with self.volume.batch_upload() as batch:
                # Store aggregated results
                aggregated = {
                    'batch_id': batch_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'total_results': len(results),
                    'results': results
                }
                
                batch.put_file(
                    json.dumps(aggregated, indent=2).encode(),
                    f"{batch_path}/aggregated.json"
                )
                
                # Store individual results for quick access
                for idx, result in enumerate(results):
                    batch.put_file(
                        json.dumps(result, indent=2).encode(),
                        f"{batch_path}/jobs/{idx}/result.json"
                    )
                
                # Store structure files if present
                for idx, result in enumerate(results):
                    if result.get('structure_file_base64'):
                        batch.put_file(
                            result['structure_file_base64'].encode(),
                            f"{batch_path}/jobs/{idx}/structure.cif"
                        )
            
            # Commit changes to make them visible
            self.volume.commit()
            logger.info(f"✅ Stored {len(results)} results in Modal Volume for batch {batch_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store results in Modal Volume: {e}")
            return False
    
    async def get_batch_results(
        self,
        batch_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve batch results from Modal Volume
        """
        try:
            # Try to load aggregated results first (fastest)
            aggregated_path = f"/batches/{batch_id}/aggregated.json"
            
            # Read from Volume
            for entry in self.volume.listdir(f"/batches/{batch_id}"):
                if entry.path == aggregated_path:
                    content = self.volume.read_file(aggregated_path)
                    return json.loads(content)
            
            # If no aggregated results, build from individual files
            results = []
            jobs_path = f"/batches/{batch_id}/jobs"
            
            for entry in self.volume.listdir(jobs_path):
                if entry.is_dir():
                    result_path = f"{entry.path}/result.json"
                    try:
                        content = self.volume.read_file(result_path)
                        results.append(json.loads(content))
                    except:
                        continue
            
            if results:
                return {
                    'batch_id': batch_id,
                    'results': results,
                    'from_cache': False
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve results from Modal Volume: {e}")
            return None
    
    async def list_batches(self) -> List[str]:
        """
        List all batch IDs in the Volume
        """
        try:
            batches = []
            for entry in self.volume.listdir("/batches"):
                if entry.is_dir():
                    batch_id = entry.path.split('/')[-1]
                    batches.append(batch_id)
            
            return batches
            
        except Exception as e:
            logger.error(f"Failed to list batches: {e}")
            return []
    
    async def cleanup_old_batches(self, days_old: int = 30):
        """
        Clean up batches older than specified days
        Modal Volumes have a 500k file limit, so cleanup is important
        """
        try:
            cutoff_date = datetime.utcnow().timestamp() - (days_old * 86400)
            cleaned = 0
            
            for batch_id in await self.list_batches():
                try:
                    # Check batch age
                    metadata_path = f"/batches/{batch_id}/aggregated.json"
                    content = self.volume.read_file(metadata_path)
                    data = json.loads(content)
                    
                    batch_time = datetime.fromisoformat(data['timestamp']).timestamp()
                    if batch_time < cutoff_date:
                        # Delete old batch
                        self.volume.remove(f"/batches/{batch_id}", recursive=True)
                        cleaned += 1
                        logger.info(f"🧹 Cleaned up old batch {batch_id}")
                
                except:
                    continue
            
            if cleaned > 0:
                self.volume.commit()
                logger.info(f"✅ Cleaned up {cleaned} old batches")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup old batches: {e}")
            return 0

# Singleton instance
modal_volume_manager = ModalVolumeManager()