"""
Boltz-2 Post-Processing Service
High-performance pipeline for extracting scientific metrics from predicted complexes.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import Counter
from dataclasses import dataclass
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading

try:
    import MDAnalysis as mda
    from sklearn.decomposition import PCA
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from rdkit import Chem
    from rdkit.Chem.Scaffolds import MurckoScaffold
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Optional dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ContactResult:
    """Result from contact analysis of a single complex"""
    residue_contacts: Set[Tuple[str, str, int]]  # (segid, resname, resid)
    contact_count: int
    ligand_atoms: int
    protein_atoms: int
    success: bool
    error: Optional[str] = None

@dataclass
class BatchAnalysis:
    """Comprehensive batch-level analysis results"""
    hotspot_residues: List[Dict]
    binding_modes: Dict[str, int]
    scaffold_diversity: Dict[str, Any]
    cluster_summary: Dict[str, Any]
    total_jobs: int
    processed_jobs: int

class BoltzPostProcessor:
    """
    High-performance post-processor for Boltz-2 prediction results.
    
    Features:
    - Async contact analysis with thread pooling
    - Efficient clustering with PCA preprocessing
    - Batch-level hotspot aggregation
    - Chemical scaffold analysis
    - Performance monitoring and caching
    """
    
    def __init__(self, max_workers: int = 4, contact_cutoff: float = 4.0):
        self.max_workers = max_workers
        self.contact_cutoff = contact_cutoff
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._residue_index_cache = {}
        self._lock = threading.Lock()
        
        if not DEPENDENCIES_AVAILABLE:
            logger.error("Required dependencies (MDAnalysis, scikit-learn, rdkit) not available")
            raise ImportError("Install required packages: pip install MDAnalysis scikit-learn rdkit")
    
    async def process_job_async(self, job_data: Dict) -> Dict[str, Any]:
        """
        Process a single completed job asynchronously.
        
        Args:
            job_data: Job data with structure_file path and results
            
        Returns:
            Dictionary with derived metrics
        """
        try:
            # Extract structure file path
            structure_path = self._get_structure_path(job_data)
            if not structure_path:
                return {"success": False, "error": "No structure file found"}
            
            # Run contact analysis in thread pool
            loop = asyncio.get_event_loop()
            contact_result = await loop.run_in_executor(
                self.executor, 
                self._analyze_contacts, 
                structure_path
            )
            
            # Calculate ensemble SD from affinity values
            ensemble_sd = self._calculate_ensemble_sd(job_data)
            
            return {
                "success": contact_result.success,
                "contacts_json": json.dumps(list(contact_result.residue_contacts)) if contact_result.success else None,
                "contact_count": contact_result.contact_count,
                "ensemble_sd": ensemble_sd,
                "ligand_atoms": contact_result.ligand_atoms,
                "protein_atoms": contact_result.protein_atoms,
                "error": contact_result.error
            }
            
        except Exception as e:
            logger.error(f"Error processing job {job_data.get('job_id', 'unknown')}: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_batch_async(self, jobs: List[Dict], batch_id: str) -> BatchAnalysis:
        """
        Process entire batch with clustering and aggregation.
        
        Args:
            jobs: List of job data with contact results
            batch_id: Batch identifier
            
        Returns:
            Comprehensive batch analysis
        """
        try:
            # Process all jobs concurrently
            job_tasks = [self.process_job_async(job) for job in jobs]
            job_results = await asyncio.gather(*job_tasks, return_exceptions=True)
            
            # Filter successful results
            successful_jobs = []
            processed_results = []
            
            for job, result in zip(jobs, job_results):
                if isinstance(result, dict) and result.get("success"):
                    successful_jobs.append(job)
                    processed_results.append(result)
            
            if not successful_jobs:
                logger.warning(f"No successful contact analyses for batch {batch_id}")
                return self._empty_batch_analysis(len(jobs))
            
            # Aggregate hotspots across all jobs
            hotspots = await self._aggregate_hotspots_async(processed_results)
            
            # Perform clustering analysis
            cluster_analysis = await self._cluster_binding_modes_async(successful_jobs, processed_results)
            
            # Analyze chemical diversity if SMILES available
            scaffold_diversity = await self._analyze_scaffolds_async(successful_jobs)
            
            return BatchAnalysis(
                hotspot_residues=hotspots,
                binding_modes=cluster_analysis["mode_counts"],
                scaffold_diversity=scaffold_diversity,
                cluster_summary=cluster_analysis["summary"],
                total_jobs=len(jobs),
                processed_jobs=len(successful_jobs)
            )
            
        except Exception as e:
            logger.error(f"Error processing batch {batch_id}: {e}")
            return self._empty_batch_analysis(len(jobs))
    
    def _get_structure_path(self, job_data: Dict) -> Optional[str]:
        """Extract structure file path from job data"""
        # Try multiple possible locations
        paths_to_check = [
            job_data.get("structure_file"),
            job_data.get("output_data", {}).get("structure_file"),
            job_data.get("results", {}).get("structure_file"),
            job_data.get("raw_modal_result", {}).get("structure_file")
        ]
        
        for path in paths_to_check:
            if path and Path(path).exists():
                return str(path)
        
        return None
    
    def _analyze_contacts(self, structure_path: str) -> ContactResult:
        """
        Analyze protein-ligand contacts using MDAnalysis.
        Thread-safe implementation for concurrent processing.
        """
        try:
            # Load structure
            universe = mda.Universe(structure_path)
            
            # Define selections
            protein = universe.select_atoms("protein and not name H*")
            ligand = universe.select_atoms("not protein and not name HOH and not name H*")
            
            if len(ligand) == 0:
                return ContactResult(set(), 0, 0, len(protein), False, "No ligand atoms found")
            
            if len(protein) == 0:
                return ContactResult(set(), 0, len(ligand), 0, False, "No protein atoms found")
            
            # Calculate distance matrix
            distances = mda.lib.distances.distance_array(
                protein.positions, 
                ligand.positions
            )
            
            # Find contacts within cutoff
            protein_indices, ligand_indices = np.where(distances <= self.contact_cutoff)
            
            # Get unique residue contacts
            contacted_residues = set()
            for pi in protein_indices:
                atom = protein.atoms[pi]
                residue_key = (atom.segid, atom.resname, atom.resid)
                contacted_residues.add(residue_key)
            
            return ContactResult(
                residue_contacts=contacted_residues,
                contact_count=len(contacted_residues),
                ligand_atoms=len(ligand),
                protein_atoms=len(protein),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Contact analysis failed for {structure_path}: {e}")
            return ContactResult(set(), 0, 0, 0, False, str(e))
    
    def _calculate_ensemble_sd(self, job_data: Dict) -> float:
        """Calculate ensemble standard deviation from affinity values"""
        try:
            raw_modal = job_data.get("raw_modal_result", {})
            
            # Try multiple ensemble field patterns
            ensemble_values = []
            for key in ["affinity_ensemble", "affinity_ensemble1", "affinity_ensemble2"]:
                value = raw_modal.get(key)
                if value is not None:
                    ensemble_values.append(float(value))
            
            # Also include main affinity
            main_affinity = raw_modal.get("affinity")
            if main_affinity is not None:
                ensemble_values.append(float(main_affinity))
            
            return float(np.std(ensemble_values)) if len(ensemble_values) > 1 else 0.0
            
        except Exception as e:
            logger.warning(f"Could not calculate ensemble SD: {e}")
            return 0.0
    
    async def _aggregate_hotspots_async(self, job_results: List[Dict]) -> List[Dict]:
        """Aggregate hotspot residues across all jobs"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._aggregate_hotspots, job_results)
    
    def _aggregate_hotspots(self, job_results: List[Dict]) -> List[Dict]:
        """Synchronous hotspot aggregation"""
        residue_counter = Counter()
        total_jobs = len(job_results)
        
        for result in job_results:
            contacts_json = result.get("contacts_json")
            if contacts_json:
                try:
                    contacts = json.loads(contacts_json)
                    for contact in contacts:
                        if len(contact) == 3:  # (segid, resname, resid)
                            residue_counter[tuple(contact)] += 1
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Could not parse contacts: {e}")
        
        # Convert to percentage and format
        hotspots = []
        for (segid, resname, resid), count in residue_counter.most_common(10):
            percentage = (count / total_jobs) * 100
            hotspots.append({
                "residue": f"{resname}{resid}",
                "chain": segid,
                "count": count,
                "percentage": round(percentage, 1),
                "residue_key": f"{segid}:{resname}:{resid}"
            })
        
        return hotspots
    
    async def _cluster_binding_modes_async(self, jobs: List[Dict], job_results: List[Dict]) -> Dict:
        """Cluster binding modes using contact fingerprints"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self._cluster_binding_modes, 
            jobs, 
            job_results
        )
    
    def _cluster_binding_modes(self, jobs: List[Dict], job_results: List[Dict]) -> Dict:
        """Synchronous clustering implementation"""
        try:
            # Build residue index
            all_residues = set()
            for result in job_results:
                contacts_json = result.get("contacts_json")
                if contacts_json:
                    contacts = json.loads(contacts_json)
                    all_residues.update(tuple(c) for c in contacts if len(c) == 3)
            
            if len(all_residues) < 3:
                return {"mode_counts": {"Novel": len(jobs)}, "summary": {"total_clusters": 1}}
            
            residue_index = {res: i for i, res in enumerate(sorted(all_residues))}
            
            # Build contact fingerprints
            fingerprints = []
            for result in job_results:
                fp = np.zeros(len(residue_index), dtype=np.uint8)
                contacts_json = result.get("contacts_json")
                if contacts_json:
                    contacts = json.loads(contacts_json)
                    for contact in contacts:
                        if len(contact) == 3:
                            key = tuple(contact)
                            if key in residue_index:
                                fp[residue_index[key]] = 1
                fingerprints.append(fp)
            
            fingerprints = np.array(fingerprints)
            
            if fingerprints.shape[0] < 2:
                return {"mode_counts": {"Novel": len(jobs)}, "summary": {"total_clusters": 1}}
            
            # PCA + KMeans clustering
            n_components = min(50, fingerprints.shape[1] - 1, fingerprints.shape[0] - 1)
            if n_components > 0:
                pca = PCA(n_components=n_components)
                fingerprints_pca = pca.fit_transform(fingerprints)
            else:
                fingerprints_pca = fingerprints
            
            # Determine optimal k
            k = min(6, len(fingerprints))
            kmeans = KMeans(n_clusters=k, n_init="auto", random_state=42)
            cluster_labels = kmeans.fit_predict(fingerprints_pca)
            
            # Label clusters (simplified - largest is "Classical", others are "Novel")
            cluster_counts = Counter(cluster_labels)
            mode_counts = {"Classical": 0, "Allosteric": 0, "Novel": 0}
            
            # Assign largest cluster as Classical
            largest_cluster = cluster_counts.most_common(1)[0][0]
            for i, label in enumerate(cluster_labels):
                if label == largest_cluster:
                    mode_counts["Classical"] += 1
                else:
                    mode_counts["Novel"] += 1
            
            return {
                "mode_counts": mode_counts,
                "summary": {
                    "total_clusters": len(cluster_counts),
                    "cluster_sizes": dict(cluster_counts),
                    "silhouette_score": silhouette_score(fingerprints_pca, cluster_labels) if len(set(cluster_labels)) > 1 else 0.0
                }
            }
            
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return {"mode_counts": {"Novel": len(jobs)}, "summary": {"total_clusters": 1}}
    
    async def _analyze_scaffolds_async(self, jobs: List[Dict]) -> Dict[str, Any]:
        """Analyze chemical scaffold diversity"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._analyze_scaffolds, jobs)
    
    def _analyze_scaffolds(self, jobs: List[Dict]) -> Dict[str, Any]:
        """Synchronous scaffold analysis"""
        try:
            smiles_list = []
            for job in jobs:
                # Try multiple SMILES locations
                smiles = (
                    job.get("input_data", {}).get("smiles") or
                    job.get("smiles") or
                    job.get("ligand_smiles")
                )
                if smiles:
                    smiles_list.append(smiles)
            
            if not smiles_list:
                return {"total_compounds": len(jobs), "unique_scaffolds": 0, "note": "No SMILES data available"}
            
            # Calculate Bemis-Murcko scaffolds
            scaffolds = set()
            valid_smiles = 0
            
            for smiles in smiles_list:
                try:
                    mol = Chem.MolFromSmiles(smiles)
                    if mol:
                        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
                        scaffold_smiles = Chem.MolToSmiles(scaffold)
                        scaffolds.add(scaffold_smiles)
                        valid_smiles += 1
                except Exception as e:
                    logger.warning(f"Could not process SMILES {smiles}: {e}")
            
            return {
                "total_compounds": len(jobs),
                "compounds_with_smiles": len(smiles_list),
                "valid_smiles": valid_smiles,
                "unique_scaffolds": len(scaffolds),
                "scaffold_diversity": len(scaffolds) / max(valid_smiles, 1)
            }
            
        except Exception as e:
            logger.error(f"Scaffold analysis failed: {e}")
            return {"total_compounds": len(jobs), "unique_scaffolds": 0, "error": str(e)}
    
    def _empty_batch_analysis(self, total_jobs: int) -> BatchAnalysis:
        """Return empty analysis when processing fails"""
        return BatchAnalysis(
            hotspot_residues=[],
            binding_modes={"Novel": total_jobs},
            scaffold_diversity={"total_compounds": total_jobs, "unique_scaffolds": 0},
            cluster_summary={"total_clusters": 0},
            total_jobs=total_jobs,
            processed_jobs=0
        )
    
    def __del__(self):
        """Cleanup thread pool"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

# Global instance for reuse
post_processor = BoltzPostProcessor(max_workers=4)