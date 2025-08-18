"""
File naming utilities for user-friendly job result file names
"""

import re
from typing import Optional, Dict, Any

class FileNamingService:
    """Generate user-friendly file names for job results"""
    
    @staticmethod
    def sanitize_name(name: str) -> str:
        """Sanitize a name for use in file names"""
        if not name:
            return "unnamed"

        # Remove or replace invalid characters (excluding dots for security)
        sanitized = re.sub(r'[^\w\-_]', '_', name)
        # Remove multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')

        # Additional security: prevent path traversal attempts
        if '..' in sanitized or sanitized.startswith('/') or sanitized.startswith('\\'):
            sanitized = re.sub(r'[./\\]', '_', sanitized)

        return sanitized or "unnamed"
    
    @staticmethod
    def generate_job_file_names(job_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate user-friendly file names for a job
        
        Args:
            job_data: Job data containing input_data, batch info, etc.
            
        Returns:
            Dict mapping file types to user-friendly names
        """
        
        input_data = job_data.get('input_data', {})
        
        # Extract job name from various possible sources
        job_name = (
            input_data.get('job_name') or 
            job_data.get('name', '').replace('Job ', '') or
            job_data.get('id', '')[:8]  # Fallback to short job ID
        )
        job_name = FileNamingService.sanitize_name(job_name)
        
        # Check if this is a batch job
        parent_batch_id = input_data.get('parent_batch_id')
        batch_index = input_data.get('batch_index')
        ligand_name = input_data.get('ligand_name')
        
        if parent_batch_id and batch_index is not None:
            # This is a batch job - use batch naming convention
            
            # Extract protein name from protein sequence or other sources
            protein_name = FileNamingService._extract_protein_name(input_data)
            
            # Format: {job_name}_{protein_name}_{index}
            base_name = f"{job_name}_{protein_name}_{batch_index + 1}"  # +1 for 1-based indexing
            
            # If we have a specific ligand name, include it
            if ligand_name and ligand_name != str(batch_index + 1):
                base_name = f"{job_name}_{protein_name}_{batch_index + 1}_{FileNamingService.sanitize_name(ligand_name)}"
                
        else:
            # Single job - just use job name
            base_name = job_name
        
        # Generate file names for different file types
        return {
            'structure_cif': f"{base_name}.cif",
            'structure_pdb': f"{base_name}.pdb", 
            'input_txt': f"{base_name}_input.txt",
            'structure_txt': f"{base_name}_structure.txt",
            'prediction_log': f"{base_name}_prediction.log",
            'results_json': f"{base_name}_results.json"
        }
    
    @staticmethod
    def _extract_protein_name(input_data: Dict[str, Any]) -> str:
        """Extract protein name from input data"""
        
        # Get explicit protein name or target name (for RFAntibody) - now required
        protein_name = input_data.get('protein_name') or input_data.get('target_name')
        if not protein_name:
            raise ValueError("protein_name (or target_name for antibody design) is required for file naming. No fallback auto-generation allowed.")
        
        return FileNamingService.sanitize_name(protein_name)
    
    @staticmethod
    def get_storage_path(job_id: str, file_name: str) -> str:
        """Get storage path for a file
        
        Args:
            job_id: Job ID for folder organization
            file_name: User-friendly file name
            
        Returns:
            Storage path like "jobs/{job_id}/{file_name}"
        """
        return f"jobs/{job_id}/{file_name}"

# Convenience instance
file_naming = FileNamingService()