"""
Minimal Working GPU Worker for Cloud Run
This version will deploy successfully and can be enhanced later
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from google.cloud import firestore, storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize clients
try:
    db = firestore.Client()
    storage_client = storage.Client()
    logger.info("✅ Google Cloud clients initialized")
except Exception as e:
    logger.warning(f"⚠️ Could not initialize GCP clients: {e}")
    db = None
    storage_client = None

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "boltz2-worker",
        "version": "1.0.0",
        "gpu_available": False,  # Will be true when GPU is added
        "gcp_connected": db is not None
    })

@app.route('/predict', methods=['POST'])
def predict():
    """Process prediction request"""
    try:
        data = request.json
        job_id = data.get('job_id', 'test-job')
        
        logger.info(f"📥 Received prediction request for job {job_id}")
        
        # For now, return a mock response
        # This will be replaced with actual Boltz-2 prediction later
        response = {
            "job_id": job_id,
            "status": "processing",
            "message": "Boltz-2 prediction queued (mock response)",
            "timestamp": datetime.utcnow().isoformat(),
            "input": {
                "protein_sequence": data.get('protein_sequence', 'N/A')[:50] + "...",
                "ligand_smiles": data.get('ligand_smiles', 'N/A')
            }
        }
        
        # If Firestore is available, update job status
        if db:
            try:
                job_ref = db.collection('jobs').document(job_id)
                job_ref.set({
                    'status': 'processing',
                    'updated_at': datetime.utcnow(),
                    'worker': 'gpu-worker',
                    'request_data': data
                }, merge=True)
                logger.info(f"✅ Updated job {job_id} in Firestore")
            except Exception as e:
                logger.error(f"❌ Failed to update Firestore: {e}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Prediction error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get job status"""
    try:
        if db:
            doc = db.collection('jobs').document(job_id).get()
            if doc.exists:
                return jsonify(doc.to_dict())
        
        return jsonify({
            "job_id": job_id,
            "status": "unknown",
            "message": "Job status not available"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        "service": "Boltz-2 GPU Worker",
        "status": "ready",
        "endpoints": [
            "/health - Health check",
            "/predict - Submit prediction",
            "/status/<job_id> - Get job status"
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Starting GPU worker on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
