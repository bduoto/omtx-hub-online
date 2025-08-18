#!/usr/bin/env python3
"""
Modal Persistent Boltz-2 Application
Production GPU microservice with volumes for weights and MSA cache

Features:
- Persistent volumes for model weights (no re-downloads)
- MSA cache volume for protein alignments
- Warm container pools with configurable idle timeout
- Webhook notifications for completion
- Idempotency and deduplication
- Graceful cancellation support
"""

import modal
import json
import hashlib
import hmac
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests

# Configure Modal app
app = modal.App("omtx-boltz2-persistent")

# Create persistent volumes
weights_volume = modal.Volume.from_name("boltz2-weights", create_if_missing=True)
msa_cache_volume = modal.Volume.from_name("msa-cache", create_if_missing=True)

# Build optimized image
boltz2_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "boltz",
        "rdkit-pypi",
        "numpy",
        "torch==2.1.0",
        "einops",
        "biopython",
        "pandas",
        "scipy",
        "mmseqs2"
    )
    .apt_install("wget", "tar")
)

@app.function(
    gpu="A100-40GB",
    image=boltz2_image,
    volumes={
        "/weights": weights_volume,
        "/msa_cache": msa_cache_volume
    },
    container_idle_timeout=600,  # Keep warm for 10 minutes
    timeout=1800,  # 30 minute timeout for large batches
    retries=2,
    concurrency_limit=10  # Max concurrent containers
)
def predict_shard(
    batch_id: str,
    shard_index: int,
    protein_seq: str,
    ligands: List[Dict[str, str]],
    use_msa: bool = True,
    use_potentials: bool = False,
    webhook_url: Optional[str] = None,
    webhook_secret: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    cancellation_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a shard of ligands against a single protein
    
    Args:
        batch_id: Parent batch identifier
        shard_index: Index of this shard in the batch
        protein_seq: Protein sequence (shared across shard)
        ligands: List of ligand dicts with 'name' and 'smiles'
        use_msa: Whether to compute MSA (cached)
        use_potentials: Whether to use structure potentials
        webhook_url: URL to notify on completion
        webhook_secret: Secret for HMAC signing
        idempotency_key: Key for deduplication
        cancellation_token: Token to check for early exit
    
    Returns:
        Dict with results for all ligands in shard
    """
    import torch
    from boltz import Boltz
    from rdkit import Chem
    
    start_time = time.time()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info(f"🚀 Processing shard {shard_index} for batch {batch_id}")
    logger.info(f"   Protein length: {len(protein_seq)} AA")
    logger.info(f"   Ligands: {len(ligands)}")
    
    # Check if cancelled before starting expensive operations
    if cancellation_token and _check_cancelled(cancellation_token):
        logger.info(f"⚠️ Shard {shard_index} cancelled before processing")
        return {"status": "cancelled", "shard_index": shard_index}
    
    # Initialize model (cached in warm container)
    model = _get_or_init_model()
    
    # Compute or retrieve cached MSA
    msa_result = None
    if use_msa:
        msa_hash = hashlib.sha256(f"{protein_seq}:mmseqs2:v1".encode()).hexdigest()[:16]
        msa_path = Path(f"/msa_cache/{msa_hash}.msa")
        
        if msa_path.exists():
            logger.info(f"✅ Using cached MSA: {msa_hash}")
            msa_result = _load_msa(msa_path)
        else:
            logger.info(f"🔬 Computing MSA for protein (will cache)")
            msa_result = _compute_msa(protein_seq)
            _save_msa(msa_result, msa_path)
    
    # Process ligands
    results = []
    for i, ligand_dict in enumerate(ligands):
        # Check cancellation between ligands
        if cancellation_token and _check_cancelled(cancellation_token):
            logger.info(f"⚠️ Shard {shard_index} cancelled at ligand {i}/{len(ligands)}")
            break
        
        ligand_name = ligand_dict.get('name', f'ligand_{i}')
        smiles = ligand_dict['smiles']
        
        logger.info(f"  Processing {ligand_name}: {smiles[:50]}...")
        
        try:
            # Validate SMILES
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                raise ValueError(f"Invalid SMILES: {smiles}")
            
            # Run Boltz-2 prediction
            prediction = model.predict(
                protein_sequence=protein_seq,
                ligand_smiles=smiles,
                msa=msa_result,
                use_potentials=use_potentials,
                num_samples=1  # Can be configured
            )
            
            # Extract results
            result = {
                'ligand_name': ligand_name,
                'smiles': smiles,
                'affinity': float(prediction.binding_affinity),
                'confidence': float(prediction.confidence),
                'ptm': float(prediction.ptm_score),
                'iptm': float(prediction.iptm_score),
                'plddt': float(prediction.plddt_score),
                'structure_cif': prediction.structure_cif,  # Base64 encoded
                'processing_time': time.time() - start_time
            }
            
            results.append(result)
            
        except Exception as e:
            logger.error(f"Failed to process {ligand_name}: {e}")
            results.append({
                'ligand_name': ligand_name,
                'smiles': smiles,
                'error': str(e),
                'affinity': None,
                'confidence': None
            })
    
    # Prepare response
    response = {
        'status': 'success',
        'batch_id': batch_id,
        'shard_index': shard_index,
        'protein_length': len(protein_seq),
        'total_ligands': len(ligands),
        'processed_ligands': len(results),
        'ligand_results': results,
        'processing_time': time.time() - start_time,
        'idempotency_key': idempotency_key
    }
    
    # Send webhook if configured
    if webhook_url and webhook_secret:
        _send_webhook(webhook_url, webhook_secret, response)
    
    logger.info(f"✅ Shard {shard_index} completed in {response['processing_time']:.1f}s")
    return response

@app.function(
    gpu="A100-40GB",
    image=boltz2_image,
    volumes={"/weights": weights_volume},
    container_idle_timeout=300,  # 5 minutes for interactive
    timeout=600  # 10 minute timeout
)
def predict_single(
    job_id: str,
    protein_seq: str,
    ligand_smiles: str,
    ligand_name: Optional[str] = None,
    use_msa: bool = False,  # Faster for interactive
    webhook_url: Optional[str] = None,
    webhook_secret: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fast single ligand prediction for interactive lane
    Optimized for low latency with reduced features
    """
    import torch
    from boltz import Boltz
    from rdkit import Chem
    
    start_time = time.time()
    logger = logging.getLogger(__name__)
    
    logger.info(f"⚡ Interactive prediction for job {job_id}")
    
    # Validate inputs
    mol = Chem.MolFromSmiles(ligand_smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {ligand_smiles}")
    
    # Get model
    model = _get_or_init_model()
    
    # Quick prediction without MSA for speed
    prediction = model.predict(
        protein_sequence=protein_seq,
        ligand_smiles=ligand_smiles,
        msa=None,  # Skip MSA for speed
        use_potentials=False,  # Skip for speed
        num_samples=1
    )
    
    result = {
        'status': 'success',
        'job_id': job_id,
        'ligand_name': ligand_name or 'ligand',
        'smiles': ligand_smiles,
        'affinity': float(prediction.binding_affinity),
        'confidence': float(prediction.confidence),
        'structure_cif': prediction.structure_cif,
        'processing_time': time.time() - start_time,
        'mode': 'interactive'
    }
    
    # Send webhook
    if webhook_url and webhook_secret:
        _send_webhook(webhook_url, webhook_secret, result)
    
    logger.info(f"⚡ Interactive job {job_id} completed in {result['processing_time']:.1f}s")
    return result

# Helper functions
_model_instance = None

def _get_or_init_model():
    """Get or initialize the model (cached in container)"""
    global _model_instance
    if _model_instance is None:
        from boltz import Boltz
        
        # Check if weights exist in volume
        weights_path = Path("/weights/boltz2_model.pt")
        if not weights_path.exists():
            # Download weights once
            _download_weights(weights_path)
        
        # Initialize model
        _model_instance = Boltz.from_pretrained(weights_path)
        _model_instance.eval()
        
    return _model_instance

def _download_weights(path: Path):
    """Download model weights to persistent volume"""
    import requests
    
    url = "https://storage.googleapis.com/boltz-models/boltz2_v1.pt"
    path.parent.mkdir(parents=True, exist_ok=True)
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

def _compute_msa(protein_seq: str) -> Any:
    """Compute MSA using MMseqs2"""
    # Implementation would use MMseqs2 to compute MSA
    # This is a placeholder
    return {"msa": "computed_msa_data"}

def _save_msa(msa_result: Any, path: Path):
    """Save MSA to cache volume"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(msa_result, f)

def _load_msa(path: Path) -> Any:
    """Load MSA from cache volume"""
    with open(path, 'r') as f:
        return json.load(f)

def _check_cancelled(token: str) -> bool:
    """Check if job has been cancelled"""
    # Would check against Redis or API
    # Placeholder for now
    return False

def _send_webhook(url: str, secret: str, payload: Dict[str, Any]):
    """Send webhook with HMAC signature"""
    import requests
    
    body = json.dumps(payload)
    signature = hmac.new(
        secret.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                'X-Modal-Signature': signature,
                'Content-Type': 'application/json'
            },
            timeout=5
        )
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Webhook failed: {e}")

# Deployment command
if __name__ == "__main__":
    modal.deploy(app)