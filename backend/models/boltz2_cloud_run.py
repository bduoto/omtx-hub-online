#!/usr/bin/env python3
"""
Boltz-2 Cloud Run Execution Script
Distinguished Engineer Implementation - L4 GPU optimized execution replacing Modal
"""

import os
import json
import time
import logging
import subprocess
import tempfile
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional

import torch
import yaml
from google.cloud import storage
from google.cloud import firestore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Boltz2CloudRunner:
    """L4-optimized Boltz-2 execution engine for Cloud Run"""
    
    def __init__(self):
        # Cloud Run environment variables
        self.task_index = int(os.getenv("CLOUD_RUN_TASK_INDEX", "0"))
        self.task_count = int(os.getenv("CLOUD_RUN_TASK_COUNT", "1"))
        self.user_id = os.getenv("USER_ID")
        self.job_id = os.getenv("JOB_ID")
        self.input_path = os.getenv("INPUT_PATH")
        self.output_path = os.getenv("OUTPUT_PATH")
        self.gpu_type = os.getenv("GPU_TYPE", "L4")
        
        # Validate required environment variables
        if not all([self.user_id, self.job_id, self.input_path, self.output_path]):
            raise ValueError("Missing required environment variables")
        
        # Initialize GCP clients
        self.storage_client = storage.Client()
        self.db = firestore.Client()
        
        # L4 GPU optimizations
        self._configure_l4_optimizations()
        
        logger.info(f"🎮 Boltz2CloudRunner initialized for L4 GPU")
        logger.info(f"   Task: {self.task_index}/{self.task_count}")
        logger.info(f"   User: {self.user_id}")
        logger.info(f"   Job: {self.job_id}")
    
    def _configure_l4_optimizations(self):
        """Configure PyTorch for L4 GPU optimization"""
        
        # Enable TF32 for L4 Ada Lovelace architecture
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        
        # Set memory management for 24GB VRAM
        torch.cuda.empty_cache()
        
        # Configure CUDA settings
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
        
        logger.info("✅ L4 GPU optimizations configured")
    
    def run(self):
        """Main execution entry point"""
        
        start_time = time.time()
        
        try:
            logger.info(f"🚀 Starting Boltz-2 execution (task {self.task_index})")
            
            # 1. Load input data
            input_data = self._load_input_data()
            
            # 2. Get ligands for this task (sharding)
            my_ligands = self._get_task_ligands(input_data['ligands'])
            
            if not my_ligands:
                logger.info(f"📭 No ligands assigned to task {self.task_index}")
                self._update_task_status("completed", {"message": "No ligands to process"})
                return
            
            logger.info(f"🧪 Processing {len(my_ligands)} ligands in task {self.task_index}")
            
            # 3. Process each ligand
            results = []
            for i, ligand in enumerate(my_ligands):
                logger.info(f"🔬 Processing ligand {i+1}/{len(my_ligands)}: {ligand['name']}")
                
                result = self._process_ligand(
                    input_data['protein_sequence'],
                    ligand
                )
                results.append(result)
                
                # Update progress in Firestore
                progress = (i + 1) / len(my_ligands) * 100
                self._update_progress(ligand['name'], result, progress)
            
            # 4. Save results to GCS
            self._save_results(results)
            
            # 5. Update final status
            execution_time = time.time() - start_time
            self._update_task_status("completed", {
                "results_count": len(results),
                "execution_time_seconds": execution_time,
                "gpu_type": self.gpu_type
            })
            
            logger.info(f"✅ Task {self.task_index} completed in {execution_time:.1f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Task {self.task_index} failed after {execution_time:.1f}s: {str(e)}")
            
            self._update_task_status("failed", {
                "error": str(e),
                "execution_time_seconds": execution_time
            })
            raise
    
    def _load_input_data(self) -> Dict[str, Any]:
        """Load input data from GCS"""
        
        try:
            # Parse GCS path
            if self.input_path.startswith("gs://"):
                bucket_name = self.input_path.split('/')[2]
                blob_path = '/'.join(self.input_path.split('/')[3:])
            else:
                raise ValueError(f"Invalid GCS path: {self.input_path}")
            
            # Download input data
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            if not blob.exists():
                raise FileNotFoundError(f"Input file not found: {self.input_path}")
            
            input_json = blob.download_as_text()
            input_data = json.loads(input_json)
            
            logger.info(f"📥 Loaded input data: {len(input_data.get('ligands', []))} ligands")
            return input_data
            
        except Exception as e:
            logger.error(f"❌ Failed to load input data: {str(e)}")
            raise
    
    def _get_task_ligands(self, all_ligands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get ligands assigned to this task using round-robin sharding"""
        
        my_ligands = []
        for i, ligand in enumerate(all_ligands):
            if i % self.task_count == self.task_index:
                my_ligands.append(ligand)
        
        return my_ligands
    
    def _process_ligand(self, protein_sequence: str, ligand: Dict[str, Any]) -> Dict[str, Any]:
        """Process single ligand with Boltz-2 optimized for L4"""
        
        start_time = time.time()
        ligand_name = ligand.get('name', f'ligand_{self.task_index}')
        ligand_smiles = ligand.get('smiles', '')
        
        if not ligand_smiles:
            raise ValueError(f"Missing SMILES for ligand: {ligand_name}")
        
        try:
            # Create temporary directories
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create Boltz-2 input YAML
                input_yaml = {
                    "version": 1,
                    "sequences": [
                        {
                            "protein": {
                                "id": "A",
                                "sequence": protein_sequence
                            }
                        },
                        {
                            "ligand": {
                                "id": "B", 
                                "smiles": ligand_smiles
                            }
                        }
                    ]
                }
                
                # Save input file
                input_file = temp_path / f"input_{ligand_name}.yaml"
                with open(input_file, "w") as f:
                    yaml.dump(input_yaml, f)
                
                # Create output directory
                output_dir = temp_path / f"output_{ligand_name}"
                output_dir.mkdir(exist_ok=True)
                
                # Run Boltz-2 with L4 optimizations
                cmd = [
                    "boltz", "predict", str(input_file),
                    "--out_dir", str(output_dir),
                    "--model", "boltz2",
                    "--device", "cuda:0",
                    "--num_workers", "4",  # L4 optimization
                    "--batch_size", "1",   # Conservative for 24GB VRAM
                    "--use_flash_attention",  # L4 optimization
                    "--precision", "16"    # FP16 for memory efficiency
                ]
                
                logger.debug(f"🔧 Running Boltz-2: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True,
                    timeout=1800  # 30 minute timeout per ligand
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"Boltz-2 failed for {ligand_name}: {result.stderr}")
                
                # Parse results
                predictions_dir = output_dir / "predictions"
                if not predictions_dir.exists():
                    raise FileNotFoundError(f"Predictions directory not found for {ligand_name}")
                
                # Find result files
                structure_files = list(predictions_dir.glob("*.cif"))
                confidence_files = list(predictions_dir.glob("*confidence*.json"))
                
                if not structure_files:
                    raise FileNotFoundError(f"No structure files found for {ligand_name}")
                
                # Read structure file
                structure_file = structure_files[0]
                with open(structure_file, "r") as f:
                    structure_content = f.read()
                
                # Read confidence data if available
                confidence_data = {}
                if confidence_files:
                    with open(confidence_files[0], "r") as f:
                        confidence_data = json.load(f)
                
                execution_time = time.time() - start_time
                
                return {
                    "ligand_name": ligand_name,
                    "ligand_smiles": ligand_smiles,
                    "structure_base64": base64.b64encode(structure_content.encode()).decode(),
                    "confidence_score": confidence_data.get('confidence_score', 0.0),
                    "binding_affinity": confidence_data.get('binding_affinity', 0.0),
                    "execution_time_seconds": execution_time,
                    "task_index": self.task_index,
                    "gpu_type": self.gpu_type,
                    "status": "completed"
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Timeout processing ligand: {ligand_name}")
            return {
                "ligand_name": ligand_name,
                "ligand_smiles": ligand_smiles,
                "status": "timeout",
                "error": "Processing timeout (30 minutes)",
                "execution_time_seconds": time.time() - start_time,
                "task_index": self.task_index
            }
        except Exception as e:
            logger.error(f"❌ Error processing ligand {ligand_name}: {str(e)}")
            return {
                "ligand_name": ligand_name,
                "ligand_smiles": ligand_smiles,
                "status": "failed",
                "error": str(e),
                "execution_time_seconds": time.time() - start_time,
                "task_index": self.task_index
            }
    
    def _save_results(self, results: List[Dict[str, Any]]):
        """Save results to GCS"""
        
        try:
            # Parse output path
            if self.output_path.startswith("gs://"):
                bucket_name = self.output_path.split('/')[2]
                blob_prefix = '/'.join(self.output_path.split('/')[3:])
            else:
                raise ValueError(f"Invalid GCS output path: {self.output_path}")
            
            bucket = self.storage_client.bucket(bucket_name)
            
            # Save task results as JSON
            task_results_blob = bucket.blob(f"{blob_prefix}/task_{self.task_index}_results.json")
            task_results_blob.upload_from_string(
                json.dumps(results, indent=2),
                content_type="application/json"
            )
            
            # Save individual structure files
            for result in results:
                if result.get('structure_base64') and result['status'] == 'completed':
                    structure_blob = bucket.blob(
                        f"{blob_prefix}/structures/{result['ligand_name']}.cif"
                    )
                    structure_content = base64.b64decode(result['structure_base64'])
                    structure_blob.upload_from_string(structure_content)
            
            logger.info(f"💾 Saved {len(results)} results to GCS")
            
        except Exception as e:
            logger.error(f"❌ Failed to save results: {str(e)}")
            raise
    
    def _update_progress(self, ligand_name: str, result: Dict[str, Any], progress: float):
        """Update job progress in Firestore"""
        
        try:
            job_ref = self.db.collection('users').document(self.user_id)\
                .collection('jobs').document(self.job_id)
            
            # Update with task-specific progress
            job_ref.update({
                f'task_progress.task_{self.task_index}': {
                    'progress_percent': progress,
                    'current_ligand': ligand_name,
                    'last_updated': firestore.SERVER_TIMESTAMP
                },
                f'results.{ligand_name}': {
                    'status': result['status'],
                    'task_index': self.task_index,
                    'execution_time': result.get('execution_time_seconds', 0)
                },
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to update progress: {str(e)}")
    
    def _update_task_status(self, status: str, metadata: Dict[str, Any]):
        """Update task status in Firestore"""
        
        try:
            job_ref = self.db.collection('users').document(self.user_id)\
                .collection('jobs').document(self.job_id)
            
            update_data = {
                f'task_status.task_{self.task_index}': {
                    'status': status,
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    **metadata
                },
                'last_updated': firestore.SERVER_TIMESTAMP
            }
            
            # If this is the last task, check if job is complete
            if status in ['completed', 'failed']:
                update_data[f'task_completion.task_{self.task_index}'] = True
            
            job_ref.update(update_data)
            
            logger.info(f"📝 Updated task {self.task_index} status: {status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update task status: {str(e)}")

def main():
    """Main entry point for Cloud Run container"""
    
    try:
        runner = Boltz2CloudRunner()
        runner.run()
        
    except Exception as e:
        logger.error(f"💥 Fatal error in Boltz2CloudRunner: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
