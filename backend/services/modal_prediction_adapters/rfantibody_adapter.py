"""
RFAntibody Modal Prediction Adapter  
Handles RFAntibody specific parameter formatting and result processing
"""

from typing import Dict, Any, List
import logging

from .base_adapter import BaseModalAdapter

logger = logging.getLogger(__name__)

class RFAntibodyAdapter(BaseModalAdapter):
    """Adapter for RFAntibody nanobody design predictions"""
    
    def prepare_parameters(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare parameters for RFAntibody Modal function
        
        Expected input_data format:
        {
            "target_pdb_content": "PDB file content as string",
            "target_chain": "A",
            "hotspot_residues": ["A:123", "A:456"],
            "num_designs": 10,
            "framework": "vhh",
            "job_id": "unique_job_id"
        }
        """
        self.validate_input(input_data)
        
        # Extract and validate target PDB
        target_pdb_content = input_data.get('target_pdb_content', '')
        if not target_pdb_content or not isinstance(target_pdb_content, str):
            raise ValueError("target_pdb_content is required and must be a valid PDB string")
        
        # Validate PDB content has some basic structure
        if 'ATOM' not in target_pdb_content.upper():
            raise ValueError("target_pdb_content does not appear to be valid PDB format")
        
        # Extract target chain
        target_chain = input_data.get('target_chain', 'A')
        if not isinstance(target_chain, str) or len(target_chain) != 1:
            raise ValueError("target_chain must be a single character")
        
        # Extract and process hotspot residues
        hotspot_residues = input_data.get('hotspot_residues', [])
        if isinstance(hotspot_residues, str):
            # Convert "1,2,3" to ["1", "2", "3"] or "A:1,A:2" to ["A:1", "A:2"]
            hotspot_residues = [res.strip() for res in hotspot_residues.split(',') if res.strip()]
        
        if not isinstance(hotspot_residues, list):
            raise ValueError("hotspot_residues must be a list or comma-separated string")
        
        # Validate and normalize hotspot format
        normalized_hotspots = []
        for hotspot in hotspot_residues:
            if isinstance(hotspot, str):
                hotspot = hotspot.strip()
                if hotspot:
                    # Ensure proper chain:residue format
                    if ':' not in hotspot:
                        # Add target chain if not specified
                        hotspot = f"{target_chain}:{hotspot}"
                    normalized_hotspots.append(hotspot)
        
        if not normalized_hotspots:
            logger.warning("No valid hotspot residues provided for RFAntibody")
        
        # Extract number of designs
        num_designs = input_data.get('num_designs', 10)
        try:
            num_designs = int(num_designs)
            if num_designs < 1 or num_designs > 50:
                raise ValueError("num_designs must be between 1 and 50")
        except (ValueError, TypeError):
            raise ValueError("num_designs must be a valid integer")
        
        # Extract framework
        framework = input_data.get('framework', 'vhh')
        valid_frameworks = ['vhh', 'fab', 'scfv']
        if framework not in valid_frameworks:
            logger.warning(f"Framework '{framework}' not in standard list: {valid_frameworks}")
        
        # Extract job ID
        job_id = input_data.get('job_id')
        if job_id and not isinstance(job_id, str):
            job_id = str(job_id)
        
        parameters = {
            "target_pdb_content": target_pdb_content,
            "target_chain": target_chain,
            "hotspot_residues": normalized_hotspots,
            "num_designs": num_designs,
            "framework": framework,
            "job_id": job_id
        }
        
        logger.info(f"Prepared RFAntibody parameters: chain={target_chain}, hotspots={len(normalized_hotspots)}, designs={num_designs}")
        return parameters
    
    def process_result(self, modal_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process RFAntibody Modal function result
        
        Standardizes the result format and extracts design information
        """
        if not isinstance(modal_result, dict):
            raise ValueError("RFAntibody result must be a dictionary")
        
        # Extract core result data
        processed = {
            "status": modal_result.get("status", "unknown"),
            "task_type": "nanobody_design",
            "model_version": modal_result.get("model_version", "rfantibody_real_phase2"),
            "execution_time": self._extract_execution_time(modal_result),
            "designs": self._extract_designs(modal_result),
            "target_info": modal_result.get("target_info", {}),
            "design_parameters": modal_result.get("design_parameters", {})
        }
        
        # Add structure file content if available
        if "structure_file_content" in modal_result:
            processed["structure_file_content"] = modal_result["structure_file_content"]
        
        if "structure_file_base64" in modal_result:
            processed["structure_file_base64"] = modal_result["structure_file_base64"]
        
        # Add Modal logs if available
        if "modal_logs" in modal_result:
            processed["modal_logs"] = modal_result["modal_logs"]
        
        # Add GPU information
        if "gpu_used" in modal_result:
            processed["gpu_used"] = modal_result["gpu_used"]
        
        # Add phase information
        if "phase" in modal_result:
            processed["phase"] = modal_result["phase"]
        
        # Add any error information
        if "error" in modal_result:
            processed["error"] = modal_result["error"]
            processed["status"] = "failed"
        
        # Include raw result for debugging
        processed["raw_modal_result"] = modal_result
        
        design_count = len(processed["designs"]) if processed["designs"] else 0
        logger.info(f"Processed RFAntibody result: status={processed['status']}, designs={design_count}")
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
    
    def _extract_designs(self, modal_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract design information from result"""
        designs = modal_result.get("designs", [])
        
        if not isinstance(designs, list):
            return []
        
        # Normalize design format
        normalized_designs = []
        for i, design in enumerate(designs):
            if isinstance(design, dict):
                normalized_design = {
                    "rank": design.get("rank", i + 1),
                    "sequence": design.get("sequence", ""),
                    "confidence_score": design.get("confidence_score", design.get("rf2_score", 0.0)),
                    "binding_affinity": design.get("binding_affinity", None),
                    "framework": design.get("framework", "unknown"),
                    "target_chain": design.get("target_chain", "unknown"),
                    "design_strategy": design.get("design_strategy", "rfantibody_pipeline")
                }
                
                # Add any additional fields
                for key, value in design.items():
                    if key not in normalized_design:
                        normalized_design[key] = value
                
                normalized_designs.append(normalized_design)
        
        # Sort by confidence score if available
        try:
            normalized_designs.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)
            # Update ranks after sorting
            for i, design in enumerate(normalized_designs):
                design["rank"] = i + 1
        except (TypeError, KeyError):
            pass
        
        return normalized_designs
    
    def validate_input(self, input_data: Dict[str, Any]) -> None:
        """Validate RFAntibody specific input requirements"""
        super().validate_input(input_data)
        
        # RFAntibody specific validations
        required_fields = ["target_pdb_content", "target_chain"]
        for field in required_fields:
            if field not in input_data or not input_data[field]:
                raise ValueError(f"{field} is required for RFAntibody predictions")
        
        # Validate PDB content format
        pdb_content = input_data["target_pdb_content"]
        if not isinstance(pdb_content, str):
            raise ValueError("target_pdb_content must be a string")
        
        # Basic PDB format check
        pdb_upper = pdb_content.upper()
        if not any(keyword in pdb_upper for keyword in ['ATOM', 'HETATM', 'HEADER']):
            raise ValueError("target_pdb_content does not appear to be valid PDB format")
        
        # Check for reasonable PDB size
        if len(pdb_content) < 100:
            raise ValueError("target_pdb_content appears too short to be a valid PDB file")
        
        logger.debug("RFAntibody input validation passed")