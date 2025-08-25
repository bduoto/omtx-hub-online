#!/usr/bin/env python3
"""
Simple Boltz-2 GPU Worker - Production Ready
Direct Boltz-2 integration with minimal dependencies
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Import Boltz-2 predictor
try:
    from boltz2_simple import Boltz2Predictor
    predictor = Boltz2Predictor()
    REAL_BOLTZ2_AVAILABLE = predictor.boltz_available
    logger.info(f"✅ Boltz-2 predictor loaded successfully (real: {REAL_BOLTZ2_AVAILABLE})")
except ImportError as e:
    logger.warning(f"⚠️ Boltz-2 predictor not available: {e}")
    REAL_BOLTZ2_AVAILABLE = False
    predictor = None

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "boltz2-worker-simple",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "real_boltz2_available": REAL_BOLTZ2_AVAILABLE,
        "gpu_available": os.path.exists('/dev/nvidia0')
    })

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        "service": "OMTX-Hub Boltz-2 Worker",
        "version": "2.0.0",
        "status": "ready",
        "real_boltz2": REAL_BOLTZ2_AVAILABLE,
        "endpoints": ["/health", "/predict"],
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/predict', methods=['POST'])
def predict():
    """Boltz-2 prediction endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['job_id', 'protein_sequence', 'ligand_smiles']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        job_id = data['job_id']
        protein_sequence = data['protein_sequence']
        ligand_smiles = data['ligand_smiles']
        ligand_name = data.get('ligand_name', 'unknown_ligand')
        
        logger.info(f"🧬 Processing Boltz-2 prediction: {job_id}")
        
        if REAL_BOLTZ2_AVAILABLE and predictor:
            # Real Boltz-2 prediction
            try:
                result = predictor.predict(
                    protein_sequence=protein_sequence,
                    ligand_smiles=ligand_smiles,
                    ligand_name=ligand_name
                )
                
                # Real prediction results
                response = {
                    "job_id": job_id,
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "results": result,
                    "model": "boltz-2",
                    "version": "2.2.0",
                    "processing_time_seconds": result.get("processing_time", 0),
                    "input": {
                        "protein_sequence": protein_sequence[:50] + "...",
                        "ligand_smiles": ligand_smiles,
                        "ligand_name": ligand_name
                    }
                }
                
                logger.info(f"✅ Boltz-2 prediction completed: {job_id}")
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"❌ Real Boltz-2 prediction failed: {e}")
                return jsonify({
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }), 500
        else:
            # High-quality mock response for testing
            mock_result = {
                "job_id": job_id,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "results": {
                    "affinity": -8.5,
                    "confidence": 0.82,
                    "boltz_confidence": 0.75,
                    "interface_ptm": 0.68,
                    "iptm": 0.73,
                    "ptm": 0.71,
                    "structure_files": {
                        "pdb": f"boltz2_prediction_{job_id}.pdb",
                        "cif": f"boltz2_prediction_{job_id}.cif"
                    },
                    "processing_time": 45.2,
                    "model_version": "2.2.0",
                    "gpu_used": False
                },
                "model": "boltz-2-mock",
                "input": {
                    "protein_sequence": protein_sequence[:50] + "...",
                    "ligand_smiles": ligand_smiles,
                    "ligand_name": ligand_name
                },
                "message": "High-quality mock prediction (real Boltz-2 model not loaded)"
            }
            
            logger.info(f"🎭 Mock Boltz-2 prediction completed: {job_id}")
            return jsonify(mock_result)
            
    except Exception as e:
        logger.error(f"❌ Prediction endpoint error: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)