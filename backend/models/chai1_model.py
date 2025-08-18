"""
Chai-1 Model Deployment for OMTX-Hub
Real GPU predictions using Modal.com for Chai-1 protein structure prediction
"""

import modal
import base64
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import tempfile
import subprocess
from datetime import datetime

# Define Modal app with dedicated name for Chai-1
app = modal.App("omtx-hub-chai1")

# Create Modal image with Chai-1 dependencies
chai1_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install(["git", "wget", "build-essential"])
    .pip_install([
        "chai_lab",  # Official Chai-1 package
        "torch>=2.0.0",  # PyTorch with CUDA support
        "numpy",
        "pandas",
        "pyarrow",  # For MSA files
        "matplotlib",
        "biopython",
    ])
)

# Create persistent volume for model weights
chai1_volume = modal.Volume.from_name("chai1-weights", create_if_missing=True)

@app.function(
    image=chai1_image,
    gpu="A100-80GB",  # Chai-1 needs 80GB for optimal performance
    volumes={
        "/weights": chai1_volume,
    },
    timeout=3600,  # 60 minutes for complex predictions
    memory=32768,  # 32GB RAM
)
def chai1_predict_modal(
    fasta_content: str,
    num_samples: int = 5,
    use_msa_server: bool = False,
    use_templates_server: bool = False,
    num_trunk_recycles: int = 3,
    num_diffn_timesteps: int = 200,
    use_esm_embeddings: bool = True,
    seed: int = 42,
    job_id: str = "",
) -> Dict[str, Any]:
    """
    Run Chai-1 prediction on Modal GPU infrastructure.
    
    Args:
        fasta_content: FASTA formatted sequences with entity|name=identifier headers
        num_samples: Number of structure samples to generate (num_diffn_samples)
        use_msa_server: Whether to use MSA server for improved accuracy
        use_templates_server: Whether to use template server for improved accuracy  
        num_trunk_recycles: Number of trunk recycling iterations (default 3)
        num_diffn_timesteps: Number of diffusion timesteps (default 200)
        use_esm_embeddings: Use ESM embeddings (default True)
        seed: Random seed for reproducibility (default 42)
        job_id: Job ID for tracking
        
    Returns:
        Dictionary with prediction results including structures and scores
    """
    import tempfile
    from pathlib import Path
    import subprocess
    import json
    from datetime import datetime
    
    start_time = datetime.now()
    
    try:
        print(f"🚀 Starting Chai-1 prediction for job {job_id}")
        
        # Set environment for model weights
        os.environ["CHAI1_WEIGHTS_DIR"] = "/weights"
        
        # Create working directory
        work_dir = Path(tempfile.mkdtemp())
        
        # Write FASTA file
        fasta_path = work_dir / "input.fasta"
        with open(fasta_path, "w") as f:
            f.write(fasta_content)
        print(f"✅ Wrote FASTA file: {len(fasta_content)} chars")
        
        # Build Chai-1 CLI command with proper parameters
        cmd = [
            "chai-lab", "fold",
            str(fasta_path),
            "--output-dir", str(work_dir / "output"),
            "--num-samples", str(num_samples),
            "--num-trunk-recycles", str(num_trunk_recycles),
            "--num-diffn-timesteps", str(num_diffn_timesteps),
            "--seed", str(seed),
        ]
        
        # Add server flags
        if use_msa_server:
            cmd.append("--use-msa-server")
        if use_templates_server:
            cmd.append("--use-templates-server")
            
        # Add embedding flag
        if not use_esm_embeddings:
            cmd.append("--no-esm-embeddings")
        
        # Run Chai-1
        print(f"🔧 Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3000  # 50 minute timeout for subprocess
        )
        
        if result.returncode != 0:
            raise Exception(f"Chai-1 failed: {result.stderr}")
            
        print("✅ Chai-1 prediction completed successfully")
        
        # Parse outputs
        output_dir = work_dir / "output"
        structures = []
        
        # Chai-1 outputs numbered PDB files (0.pdb, 1.pdb, etc.)
        for i in range(num_samples):
            pdb_path = output_dir / f"{i}.pdb"
            if pdb_path.exists():
                with open(pdb_path, "r") as f:
                    pdb_content = f.read()
                
                # Extract confidence scores from PDB B-factor column if available
                # This is a simplified extraction - real implementation would parse properly
                confidence_scores = []
                for line in pdb_content.split("\n"):
                    if line.startswith("ATOM"):
                        try:
                            b_factor = float(line[60:66].strip())
                            confidence_scores.append(b_factor)
                        except:
                            pass
                
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
                
                structures.append({
                    "pdb_content": base64.b64encode(pdb_content.encode()).decode(),
                    "confidence_score": avg_confidence,
                    "sample_index": i
                })
        
        # Read any additional metadata files
        metadata = {}
        summary_path = output_dir / "summary.json"
        if summary_path.exists():
            with open(summary_path, "r") as f:
                metadata = json.load(f)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        return {
            "success": True,
            "job_id": job_id,
            "structures": structures,
            "num_structures": len(structures),
            "metadata": metadata,
            "execution_time": execution_time,
            "parameters": {
                "num_samples": num_samples,
                "use_msa": use_msa,
                "use_templates": use_templates,
                "had_custom_msa": bool(msa_content),
                "had_custom_template": bool(template_content)
            }
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "job_id": job_id,
            "error": "Prediction timed out after 50 minutes",
            "execution_time": 3000
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "job_id": job_id,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "execution_time": (datetime.now() - start_time).total_seconds()
        }

# Health check function
@app.function()
def health_check():
    """Simple health check for Chai-1 deployment."""
    return {
        "status": "healthy",
        "model": "chai1",
        "timestamp": datetime.now().isoformat()
    }