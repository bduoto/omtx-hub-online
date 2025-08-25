#!/usr/bin/env python3
"""
Cloud Run Job Entry Point for Boltz-2 GPU Processing
Reads job parameters from environment variables and updates Firestore
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_job():
    """Main job execution function"""
    start_time = time.time()
    
    # Get job parameters from environment
    job_id = os.getenv("JOB_ID")
    protein_sequence = os.getenv("PROTEIN_SEQUENCE")
    ligand_smiles = os.getenv("LIGAND_SMILES")
    ligand_name = os.getenv("LIGAND_NAME", "unknown")
    batch_parent_id = os.getenv("BATCH_PARENT_ID")
    project_id = os.getenv("FIRESTORE_PROJECT", "om-models")
    
    logger.info(f"🚀 Starting Cloud Run Job: {job_id}")
    logger.info(f"   Protein length: {len(protein_sequence) if protein_sequence else 0}")
    logger.info(f"   Ligand: {ligand_name} ({ligand_smiles})")
    logger.info(f"   Batch parent: {batch_parent_id or 'None'}")
    
    if not all([job_id, protein_sequence, ligand_smiles]):
        logger.error("❌ Missing required environment variables")
        sys.exit(1)
    
    try:
        # Initialize Firestore
        from google.cloud import firestore
        from google.cloud import storage
        
        db = firestore.Client(project=project_id)
        storage_client = storage.Client(project=project_id)
        
        # Update job status to processing
        db.collection("jobs").document(job_id).update({
            "status": "processing",
            "processing_started_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        # Import and run Boltz-2 predictor
        logger.info("🧬 Loading Boltz-2 predictor...")
        from boltz2_simple import Boltz2Predictor
        
        predictor = Boltz2Predictor()
        logger.info(f"   Boltz-2 available: {predictor.boltz_available}")
        logger.info(f"   GPU available: {predictor.gpu_available}")
        
        # Run prediction
        logger.info("🔬 Running Boltz-2 prediction...")
        result = predictor.predict(
            protein_sequence=protein_sequence,
            ligand_smiles=ligand_smiles,
            ligand_name=ligand_name
        )
        
        processing_time = time.time() - start_time
        
        # Prepare results
        job_results = {
            "job_id": job_id,
            "status": "completed",
            "affinity": result.get("affinity", 0.0),
            "confidence": result.get("confidence", 0.0),
            "boltz_confidence": result.get("boltz_confidence", 0.0),
            "ptm": result.get("ptm", 0.0),
            "iptm": result.get("iptm", 0.0),
            "interface_ptm": result.get("interface_ptm", 0.0),
            "processing_time_seconds": processing_time,
            "model_version": result.get("model_version", "2.1.1"),
            "gpu_used": result.get("gpu_used", False),
            "real_boltz2": result.get("real_boltz2", False)
        }
        
        # Save structure files to GCS if available
        if "structure_files" in result:
            bucket_name = "hub-job-files"
            bucket = storage_client.bucket(bucket_name)
            
            # Save CIF file if present
            if "cif" in result.get("structure_files", {}):
                cif_path = f"jobs/{job_id}/structure.cif"
                blob = bucket.blob(cif_path)
                # For now, save placeholder - real implementation would save actual structure
                blob.upload_from_string(f"# Boltz-2 prediction for {job_id}\n# Placeholder CIF")
                job_results["structure_url"] = f"gs://{bucket_name}/{cif_path}"
                logger.info(f"   ✅ Structure saved to {cif_path}")
        
        # Update job in Firestore with results
        db.collection("jobs").document(job_id).update({
            "status": "completed",
            "results": job_results,
            "completed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "processing_time_seconds": processing_time
        })
        
        logger.info(f"✅ Job completed successfully in {processing_time:.2f}s")
        logger.info(f"   Affinity: {job_results['affinity']:.2f} kcal/mol")
        logger.info(f"   Confidence: {job_results['confidence']:.3f}")
        
        # If part of a batch, update batch status
        if batch_parent_id:
            batch_ref = db.collection("batches").document(batch_parent_id)
            batch_doc = batch_ref.get()
            
            if batch_doc.exists:
                batch_data = batch_doc.to_dict()
                completed = batch_data.get("completed_jobs", 0) + 1
                total = batch_data.get("total_jobs", 1)
                
                batch_ref.update({
                    "completed_jobs": completed,
                    "updated_at": datetime.utcnow()
                })
                
                # Check if batch is complete
                if completed >= total:
                    batch_ref.update({
                        "status": "completed",
                        "completed_at": datetime.utcnow()
                    })
                    logger.info(f"   ✅ Batch {batch_parent_id} completed ({completed}/{total})")
                else:
                    logger.info(f"   📊 Batch progress: {completed}/{total}")
        
        # Exit successfully
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ Job failed: {e}")
        
        # Update job status to failed
        try:
            db.collection("jobs").document(job_id).update({
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "processing_time_seconds": time.time() - start_time
            })
            
            # Update batch if applicable
            if batch_parent_id:
                batch_ref = db.collection("batches").document(batch_parent_id)
                batch_doc = batch_ref.get()
                if batch_doc.exists:
                    batch_data = batch_doc.to_dict()
                    failed = batch_data.get("failed_jobs", 0) + 1
                    batch_ref.update({
                        "failed_jobs": failed,
                        "updated_at": datetime.utcnow()
                    })
        except:
            pass
        
        # Exit with error
        sys.exit(1)

if __name__ == "__main__":
    run_job()