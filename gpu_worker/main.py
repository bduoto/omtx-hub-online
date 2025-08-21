"""
GPU Worker Service for Cloud Run Jobs
Processes Boltz-2 predictions with GPU acceleration
"""

import os
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify
from google.cloud import firestore, storage
from google.auth.exceptions import DefaultCredentialsError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables for lazy initialization
db = None
storage_client = None
bucket = None
predictor = None

def initialize_services():
    """Initialize GCP services and model"""
    global db, storage_client, bucket, predictor
    
    try:
        # Initialize Firestore
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'om-models')
        db = firestore.Client(project=project_id)
        logger.info(f"✅ Connected to Firestore: {project_id}")
        
        # Initialize Cloud Storage
        storage_client = storage.Client(project=project_id)
        bucket_name = os.getenv('GCS_BUCKET_NAME', 'hub-job-files')
        bucket = storage_client.bucket(bucket_name)
        logger.info(f"✅ Connected to Cloud Storage bucket: {bucket_name}")
        
        # Initialize Boltz-2 model (placeholder for now)
        predictor = MockBoltz2Predictor()  # Will replace with real model
        logger.info("✅ Boltz-2 model initialized")
        
        return True
        
    except DefaultCredentialsError:
        logger.warning("⚠️ GCP authentication not available. Running in degraded mode.")
        # Initialize mock services for testing
        predictor = MockBoltz2Predictor()
        return False
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize services: {e}. Running in degraded mode.")
        # Initialize mock services for testing  
        predictor = MockBoltz2Predictor()
        return False

class MockBoltz2Predictor:
    """
    Mock Boltz-2 predictor for testing
    Replace with actual model implementation
    """
    
    def predict(self, protein_sequence: str, ligand_smiles: str, **kwargs) -> Dict[str, Any]:
        """
        Mock prediction - returns realistic-looking results
        Replace with actual Boltz-2 inference
        """
        import time
        import random
        
        # Simulate processing time (15-45 seconds)
        processing_time = random.uniform(15, 45)
        logger.info(f"🧬 Processing prediction (simulated {processing_time:.1f}s)...")
        time.sleep(min(processing_time, 5))  # Cap simulation time for testing
        
        # Generate mock results
        affinity = random.uniform(-12.0, -6.0)  # Binding affinity in kcal/mol
        confidence = random.uniform(0.6, 0.95)   # Model confidence
        rmsd = random.uniform(0.5, 3.0)         # RMSD from reference
        
        # Mock CIF structure file content
        mock_cif = f"""data_complex
_entry.id complex
_cell.length_a 100.0
_cell.length_b 100.0
_cell.length_c 100.0
_cell.angle_alpha 90.0
_cell.angle_beta 90.0
_cell.angle_gamma 90.0
_symmetry.space_group_name_H-M 'P 1'
# Mock structure for ligand: {ligand_smiles}
# Protein sequence length: {len(protein_sequence)} residues
# Generated at: {datetime.utcnow().isoformat()}
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.type_symbol
_atom_site.label_atom_id
_atom_site.label_alt_id
_atom_site.label_comp_id
_atom_site.label_asym_id
_atom_site.label_entity_id
_atom_site.label_seq_id
_atom_site.pdbx_PDB_ins_code
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
_atom_site.occupancy
_atom_site.B_iso_or_equiv
_atom_site.pdbx_formal_charge
_atom_site.auth_seq_id
_atom_site.auth_comp_id
_atom_site.auth_asym_id
_atom_site.auth_atom_id
_atom_site.pdbx_PDB_model_num
ATOM 1 N N . MET A 1 1 ? 20.154 6.718 22.271 1.00 25.00 ? 1 MET A N 1
ATOM 2 C CA . MET A 1 1 ? 21.618 6.736 22.594 1.00 25.00 ? 1 MET A CA 1
ATOM 3 C C . MET A 1 1 ? 22.216 8.079 22.201 1.00 25.00 ? 1 MET A C 1
# ... more atoms would follow in real structure
"""
        
        return {
            "affinity": affinity,
            "confidence": confidence,
            "rmsd": rmsd,
            "structure_cif": mock_cif,
            "processing_time_seconds": processing_time,
            "model_version": "mock-boltz2-v1.0",
            "parameters_used": kwargs,
            "additional_metrics": {
                "ptm_score": random.uniform(0.4, 0.9),
                "iptm_score": random.uniform(0.5, 0.95),
                "plddt_score": random.uniform(0.6, 0.9)
            }
        }

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    
    # Check service status
    services_ok = db is not None and storage_client is not None
    
    return jsonify({
        "status": "healthy" if services_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "gpu-worker",
        "model": "boltz2",
        "services": {
            "database": db is not None,
            "storage": storage_client is not None,
            "predictor": predictor is not None
        },
        "gpu_available": os.getenv('NVIDIA_VISIBLE_DEVICES') is not None,
        "environment": os.getenv('ENVIRONMENT', 'unknown')
    }), 200

@app.route('/process', methods=['POST'])
def process_job():
    """
    Main job processing endpoint
    Called by Cloud Tasks to process individual predictions
    """
    
    # Initialize services if not done
    if db is None:
        if not initialize_services():
            return jsonify({
                "status": "error", 
                "error": "Service initialization failed"
            }), 500
    
    try:
        # Parse request
        data = request.get_json()
        if not data:
            raise ValueError("Invalid JSON payload")
        
        job_id = data.get('job_id')
        job_type = data.get('job_type', 'INDIVIDUAL')
        batch_id = data.get('batch_id')
        
        if not job_id:
            raise ValueError("Missing required 'job_id' field")
        
        logger.info(f"🚀 Processing {job_type} job: {job_id}")
        
        # Update job status to running
        job_ref = db.collection('jobs').document(job_id)
        job_ref.update({
            'status': 'running',
            'started_at': firestore.SERVER_TIMESTAMP,
            'cloud_run_job': {
                'execution_id': os.environ.get('CLOUD_RUN_EXECUTION', 'unknown'),
                'task_name': os.environ.get('CLOUD_RUN_TASK_NAME', 'unknown'),
                'region': 'us-central1',
                'updated_at': firestore.SERVER_TIMESTAMP
            }
        })
        
        # Get job data
        job_doc = job_ref.get()
        if not job_doc.exists:
            raise ValueError(f"Job {job_id} not found in database")
        
        job_data = job_doc.to_dict()
        input_data = job_data.get('input_data', {})
        
        # Validate input
        protein_sequence = input_data.get('protein_sequence')
        ligand_smiles = input_data.get('ligand_smiles')
        
        if not protein_sequence or not ligand_smiles:
            raise ValueError("Missing protein_sequence or ligand_smiles in job data")
        
        logger.info(f"🧬 Running Boltz-2 prediction for ligand: {input_data.get('ligand_name', 'unnamed')}")
        
        # Run prediction
        result = predictor.predict(
            protein_sequence=protein_sequence,
            ligand_smiles=ligand_smiles,
            **input_data.get('parameters', {})
        )
        
        # Save results to Cloud Storage
        storage_success = save_job_results(job_id, job_type, batch_id, result, input_data)
        
        if not storage_success:
            raise Exception("Failed to save results to Cloud Storage")
        
        # Update job with results
        results_data = {
            'affinity': result['affinity'],
            'confidence': result['confidence'],
            'rmsd': result.get('rmsd', 0),
            'processing_time': result.get('processing_time_seconds', 0),
            'model_version': result.get('model_version', 'unknown'),
            'additional_metrics': result.get('additional_metrics', {})
        }
        
        # Add storage paths
        base_path = get_storage_path(job_id, job_type, batch_id)
        results_data.update({
            'structure_file': f"gs://hub-job-files/{base_path}/structure.cif",
            'results_file': f"gs://hub-job-files/{base_path}/results.json",
            'input_file': f"gs://hub-job-files/{base_path}/input.json"
        })
        
        job_ref.update({
            'status': 'completed',
            'completed_at': firestore.SERVER_TIMESTAMP,
            'results': results_data,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"✅ Job {job_id} completed successfully")
        
        # Update batch progress if this is a child job
        if job_type == 'BATCH_CHILD' and batch_id:
            update_batch_progress(batch_id, job_id)
        
        return jsonify({
            'status': 'success',
            'job_id': job_id,
            'results': results_data
        }), 200
        
    except Exception as e:
        error_message = str(e)
        error_traceback = traceback.format_exc()
        
        logger.error(f"❌ Job {job_id} failed: {error_message}")
        logger.error(f"Traceback: {error_traceback}")
        
        # Update job as failed
        if job_id and db:
            try:
                job_ref = db.collection('jobs').document(job_id)
                job_ref.update({
                    'status': 'failed',
                    'error': error_message,
                    'error_traceback': error_traceback,
                    'completed_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                
                # Update batch progress if this is a child job
                if job_type == 'BATCH_CHILD' and batch_id:
                    update_batch_progress(batch_id, job_id)
                    
            except Exception as update_error:
                logger.error(f"Failed to update job status: {update_error}")
        
        return jsonify({
            'status': 'error',
            'job_id': job_id,
            'error': error_message
        }), 500

def get_storage_path(job_id: str, job_type: str, batch_id: Optional[str] = None) -> str:
    """Get the Cloud Storage path for job results"""
    
    if job_type == 'BATCH_CHILD' and batch_id:
        return f"batches/{batch_id}/jobs/{job_id}"
    else:
        return f"jobs/{job_id}"

def save_job_results(
    job_id: str, 
    job_type: str, 
    batch_id: Optional[str], 
    result: Dict[str, Any],
    input_data: Dict[str, Any]
) -> bool:
    """Save job results to Cloud Storage"""
    
    try:
        base_path = get_storage_path(job_id, job_type, batch_id)
        
        # Save structure file
        structure_path = f"{base_path}/structure.cif"
        structure_blob = bucket.blob(structure_path)
        structure_blob.upload_from_string(
            result['structure_cif'],
            content_type='chemical/x-cif'
        )
        logger.info(f"💾 Saved structure file: {structure_path}")
        
        # Save full results
        results_path = f"{base_path}/results.json"
        results_blob = bucket.blob(results_path)
        results_blob.upload_from_string(
            json.dumps(result, indent=2),
            content_type='application/json'
        )
        logger.info(f"💾 Saved results file: {results_path}")
        
        # Save input data
        input_path = f"{base_path}/input.json"
        input_blob = bucket.blob(input_path)
        input_blob.upload_from_string(
            json.dumps(input_data, indent=2),
            content_type='application/json'
        )
        logger.info(f"💾 Saved input file: {input_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save results to storage: {e}")
        return False

def update_batch_progress(batch_id: str, completed_job_id: str):
    """Update batch parent progress when a child job completes"""
    
    try:
        logger.info(f"📊 Updating batch progress for {batch_id}")
        
        # Get all child jobs for this batch
        children_query = db.collection('jobs').where(
            'batch_parent_id', '==', batch_id
        )
        
        status_counts = {
            'completed': 0,
            'failed': 0, 
            'running': 0,
            'pending': 0,
            'queued': 0
        }
        
        completed_results = []
        total_children = 0
        
        for child_doc in children_query.stream():
            child_data = child_doc.to_dict()
            status = child_data.get('status', 'unknown')
            total_children += 1
            
            if status in status_counts:
                status_counts[status] += 1
            
            # Collect results from completed jobs
            if status == 'completed' and 'results' in child_data:
                completed_results.append({
                    'job_id': child_data['job_id'],
                    'ligand_name': child_data['input_data'].get('ligand_name'),
                    'ligand_smiles': child_data['input_data'].get('ligand_smiles'),
                    'affinity': child_data['results']['affinity'],
                    'confidence': child_data['results']['confidence'],
                    'batch_index': child_data.get('batch_index', 0)
                })
        
        # Update batch parent
        batch_ref = db.collection('jobs').document(batch_id)
        update_data = {
            'progress': status_counts,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        logger.info(f"📊 Batch {batch_id} progress: {status_counts}")
        
        # Check if batch is complete
        active_jobs = status_counts['running'] + status_counts['pending'] + status_counts['queued']
        
        if active_jobs == 0 and total_children > 0:
            # Batch is complete
            update_data['status'] = 'completed'
            update_data['completed_at'] = firestore.SERVER_TIMESTAMP
            
            if completed_results:
                # Generate batch summary
                batch_summary = generate_batch_summary(completed_results)
                update_data['batch_results'] = batch_summary
                
                # Save batch results to storage
                save_batch_results(batch_id, completed_results, batch_summary)
            
            logger.info(f"🎉 Batch {batch_id} completed with {len(completed_results)} successful predictions")
        
        batch_ref.update(update_data)
        
        # Queue next jobs if there are pending ones and running capacity
        if status_counts['pending'] > 0 and status_counts['running'] < 10:
            queue_next_batch_jobs(batch_id, min(5, 10 - status_counts['running']))
        
    except Exception as e:
        logger.error(f"❌ Failed to update batch progress: {e}")

def generate_batch_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate statistical summary of batch results"""
    
    if not results:
        return {}
    
    # Sort by affinity (best first)
    results.sort(key=lambda x: x['affinity'])
    
    affinities = [r['affinity'] for r in results]
    confidences = [r['confidence'] for r in results]
    
    return {
        'total_predictions': len(results),
        'successful_predictions': len([r for r in results if r['confidence'] > 0.7]),
        'best_prediction': {
            'ligand_name': results[0]['ligand_name'],
            'ligand_smiles': results[0]['ligand_smiles'],
            'affinity': results[0]['affinity'],
            'confidence': results[0]['confidence']
        },
        'top_10_predictions': results[:10],
        'statistics': {
            'mean_affinity': sum(affinities) / len(affinities),
            'best_affinity': min(affinities),
            'worst_affinity': max(affinities),
            'mean_confidence': sum(confidences) / len(confidences),
            'high_confidence_count': len([c for c in confidences if c > 0.8])
        },
        'generated_at': datetime.utcnow().isoformat()
    }

def save_batch_results(batch_id: str, results: List[Dict[str, Any]], summary: Dict[str, Any]):
    """Save batch aggregated results to storage"""
    
    try:
        # Save detailed results as JSON
        results_path = f"batches/{batch_id}/batch_results.json"
        results_blob = bucket.blob(results_path)
        results_blob.upload_from_string(
            json.dumps({
                'batch_id': batch_id,
                'summary': summary,
                'detailed_results': results
            }, indent=2),
            content_type='application/json'
        )
        
        # Generate CSV for easy analysis
        csv_content = generate_batch_csv(results)
        csv_path = f"batches/{batch_id}/batch_results.csv"
        csv_blob = bucket.blob(csv_path)
        csv_blob.upload_from_string(csv_content, content_type='text/csv')
        
        logger.info(f"💾 Saved batch results: {results_path} and {csv_path}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save batch results: {e}")

def generate_batch_csv(results: List[Dict[str, Any]]) -> str:
    """Generate CSV content for batch results"""
    
    csv_lines = [
        "rank,job_id,ligand_name,ligand_smiles,affinity,confidence,batch_index"
    ]
    
    for idx, result in enumerate(results, 1):
        csv_lines.append(
            f"{idx},{result['job_id']},{result['ligand_name']},"
            f"\"{result['ligand_smiles']}\",{result['affinity']:.4f},"
            f"{result['confidence']:.4f},{result['batch_index']}"
        )
    
    return "\n".join(csv_lines)

def queue_next_batch_jobs(batch_id: str, count: int):
    """Queue next set of pending jobs for a batch"""
    
    try:
        # This would normally use Cloud Tasks, but for now just log
        logger.info(f"📤 Would queue {count} more jobs for batch {batch_id}")
        
        # In production, this would:
        # 1. Get pending jobs from Firestore
        # 2. Create Cloud Tasks for next {count} jobs
        # 3. Update job statuses to 'queued'
        
    except Exception as e:
        logger.error(f"❌ Failed to queue next batch jobs: {e}")

# Module-level initialization removed - handled by startup script
# For gunicorn compatibility (services initialized externally)
if __name__ == '__main__':
    # Start Flask app (development mode only)
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🌐 Starting Flask app on 0.0.0.0:{port}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ Flask app failed to start: {e}")
        exit(1)