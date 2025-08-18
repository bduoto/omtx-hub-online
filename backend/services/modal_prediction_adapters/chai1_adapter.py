"""
Chai-1 Modal Prediction Adapter
Handles Chai-1 specific parameter formatting and result processing
"""

from typing import Dict, Any, List
import logging

from .base_adapter import BaseModalAdapter

logger = logging.getLogger(__name__)

class Chai1Adapter(BaseModalAdapter):
    """Adapter for Chai-1 multi-modal molecular predictions"""
    
    def prepare_parameters(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare parameters for Chai-1 Modal function
        
        Expected input_data format:
        {
            "protein_sequences": ["SEQUENCE1", "SEQUENCE2"],
            "ligands": ["SMILES1", "SMILES2"],
            "use_msa_server": bool,
            "num_steps": int
        }
        """
        self.validate_input(input_data)
        
        # Extract and validate protein sequences
        protein_sequences = input_data.get('protein_sequences', [])
        if not protein_sequences:
            raise ValueError("At least one protein sequence is required")
        
        if not isinstance(protein_sequences, list):
            protein_sequences = [protein_sequences]
        
        # Validate sequences
        for i, seq in enumerate(protein_sequences):
            if not isinstance(seq, str) or not seq.strip():
                raise ValueError(f"Protein sequence {i+1} is invalid")
        
        # Extract and validate ligands
        ligands = input_data.get('ligands', [])
        if not isinstance(ligands, list):
            ligands = [ligands] if ligands else []
        
        # Validate ligands (SMILES strings)
        for i, ligand in enumerate(ligands):
            if not isinstance(ligand, str) or not ligand.strip():
                raise ValueError(f"Ligand {i+1} SMILES string is invalid")
        
        # Extract boolean parameters
        use_msa_server = input_data.get('use_msa_server', True)
        
        # Extract num_steps (Chai-1 specific)
        num_steps = input_data.get('num_steps', 200)
        try:
            num_steps = int(num_steps)
            if num_steps < 50 or num_steps > 1000:
                raise ValueError("num_steps must be between 50 and 1000")
        except (ValueError, TypeError):
            raise ValueError("num_steps must be a valid integer")
        
        parameters = {
            "protein_sequences": protein_sequences,
            "ligands": ligands,
            "use_msa_server": bool(use_msa_server),
            "num_steps": num_steps
        }
        
        logger.info(f"Prepared Chai-1 parameters: {len(protein_sequences)} proteins, {len(ligands)} ligands, {num_steps} steps")
        return parameters
    
    def process_result(self, modal_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Chai-1 Modal function result
        
        Standardizes the result format and extracts key information
        """
        if not isinstance(modal_result, dict):
            raise ValueError("Chai-1 result must be a dictionary")
        
        # Extract core result data
        processed = {
            "status": modal_result.get("status", "unknown"),
            "task_type": "multi_modal_prediction",
            "model_version": modal_result.get("model_version", "chai1_default"),
            "execution_time": self._extract_execution_time(modal_result),
            "structure_data": self._extract_structure_data(modal_result),
            "prediction_confidence": modal_result.get("confidence", None),
            "binding_affinity": modal_result.get("binding_affinity", None),
            "diffusion_steps": modal_result.get("num_steps", modal_result.get("diffusion_steps", None))
        }
        
        # Add structure file content if available
        if "structure_file_content" in modal_result:
            processed["structure_file_content"] = modal_result["structure_file_content"]
        
        if "structure_file_base64" in modal_result:
            processed["structure_file_base64"] = modal_result["structure_file_base64"]
        
        # Add Chai-1 specific results
        if "diffusion_trajectory" in modal_result:
            processed["diffusion_trajectory"] = modal_result["diffusion_trajectory"]
        
        if "attention_weights" in modal_result:
            processed["attention_weights"] = modal_result["attention_weights"]
        
        # Add Modal logs if available
        if "modal_logs" in modal_result:
            processed["modal_logs"] = modal_result["modal_logs"]
        
        # Add GPU information
        if "gpu_used" in modal_result:
            processed["gpu_used"] = modal_result["gpu_used"]
        
        # Add any error information
        if "error" in modal_result:
            processed["error"] = modal_result["error"]
            processed["status"] = "failed"
        
        # Include raw result for debugging
        processed["raw_modal_result"] = modal_result
        
        logger.info(f"Processed Chai-1 result: status={processed['status']}")
        return processed
    
    def _extract_execution_time(self, modal_result: Dict[str, Any]) -> float:
        """Extract execution time from various possible locations"""
        # Try direct field
        if "execution_time" in modal_result:
            return float(modal_result["execution_time"])
        
        # Try metadata
        metadata = modal_result.get("_execution_metadata", {})
        if "execution_time" in metadata:
            return float(metadata["execution_time"])
        
        return 0.0
    
    def _extract_structure_data(self, modal_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structure-related data from result"""
        structure_data = {}
        
        # Extract coordinate information
        if "coordinates" in modal_result:
            structure_data["coordinates"] = modal_result["coordinates"]
        
        # Extract atom information
        if "atoms" in modal_result:
            structure_data["atoms"] = modal_result["atoms"]
        
        # Extract bonds information
        if "bonds" in modal_result:
            structure_data["bonds"] = modal_result["bonds"]
        
        # Extract any PDB/CIF information
        if "pdb_content" in modal_result:
            structure_data["pdb_content"] = modal_result["pdb_content"]
        
        if "cif_content" in modal_result:
            structure_data["cif_content"] = modal_result["cif_content"]
        
        # Chai-1 specific structure data
        if "multi_modal_features" in modal_result:
            structure_data["multi_modal_features"] = modal_result["multi_modal_features"]
        
        return structure_data
    
    def validate_input(self, input_data: Dict[str, Any]) -> None:
        """Validate Chai-1 specific input requirements"""
        super().validate_input(input_data)
        
        # Chai-1 specific validations
        if "protein_sequences" not in input_data:
            raise ValueError("protein_sequences is required for Chai-1 predictions")
        
        protein_sequences = input_data["protein_sequences"]
        if not protein_sequences:
            raise ValueError("At least one protein sequence is required")
        
        # Validate sequence format (basic amino acid check)
        valid_amino_acids = set('ACDEFGHIKLMNPQRSTVWY')
        for i, seq in enumerate(protein_sequences if isinstance(protein_sequences, list) else [protein_sequences]):
            if not isinstance(seq, str):
                raise ValueError(f"Protein sequence {i+1} must be a string")
            
            # Check for valid amino acid characters
            invalid_chars = set(seq.upper()) - valid_amino_acids
            if invalid_chars and len(invalid_chars) > 2:  # Allow some flexibility
                logger.warning(f"Protein sequence {i+1} contains potentially invalid characters: {invalid_chars}")
        
        # Validate num_steps if provided
        if "num_steps" in input_data:
            try:
                num_steps = int(input_data["num_steps"])
                if num_steps < 50 or num_steps > 1000:
                    logger.warning(f"num_steps {num_steps} is outside recommended range (50-1000)")
            except (ValueError, TypeError):
                raise ValueError("num_steps must be a valid integer")
        
        logger.debug("Chai-1 input validation passed")