"""
Task-specific input/output schemas for dynamic form generation
Defines the structure of inputs and outputs for each prediction task
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

class FieldType(str, Enum):
    """Input field types for form generation"""
    TEXT = "text"
    TEXTAREA = "textarea"
    EMAIL = "email"
    NUMBER = "number"
    SELECT = "select"
    CHECKBOX = "checkbox"
    FILE = "file"
    SEQUENCE = "sequence"  # Special type for protein sequences
    SMILES = "smiles"      # Special type for SMILES strings
    MULTI_SELECT = "multi_select"

class OutputType(str, Enum):
    """Output types for result processing"""
    STRUCTURE = "structure"
    AFFINITY = "affinity"
    CONFIDENCE = "confidence"
    BINDING_SITES = "binding_sites"
    COMPARISON = "comparison"
    SCREENING_RESULTS = "screening_results"
    METRICS = "metrics"
    VISUALIZATION = "visualization"
    FILES = "files"

@dataclass
class ValidationRule:
    """Validation rules for input fields"""
    rule_type: str  # 'required', 'min_length', 'max_length', 'pattern', 'custom'
    value: Union[str, int, bool]
    message: str

@dataclass
class InputField:
    """Input field definition"""
    id: str
    label: str
    field_type: FieldType
    description: Optional[str] = None
    placeholder: Optional[str] = None
    default_value: Optional[Union[str, int, bool]] = None
    options: Optional[List[Dict[str, str]]] = None  # For select fields
    validation: Optional[List[ValidationRule]] = None
    conditional: Optional[Dict[str, Any]] = None  # Show field based on other field values
    help_text: Optional[str] = None

@dataclass
class OutputField:
    """Output field definition"""
    id: str
    label: str
    output_type: OutputType
    description: Optional[str] = None
    format: Optional[str] = None  # Data format (json, cif, pdb, etc.)
    visualization: Optional[str] = None  # How to display (table, chart, 3d, etc.)
    required: bool = True
    conditional: Optional[Dict[str, Any]] = None  # Show based on input or other outputs

@dataclass
class TaskSchema:
    """Complete schema for a prediction task"""
    task_id: str
    task_name: str
    description: str
    input_fields: List[InputField]
    output_fields: List[OutputField]
    estimated_time: Optional[int] = None
    resource_requirements: Optional[Dict[str, Any]] = None
    examples: Optional[List[Dict[str, Any]]] = None

class TaskSchemaRegistry:
    """Registry for task-specific schemas"""
    
    def __init__(self):
        self.schemas: Dict[str, TaskSchema] = {}
        self._initialize_default_schemas()
    
    def _initialize_default_schemas(self):
        """Initialize schemas for all task types"""
        
        # Protein-Ligand Binding Task
        protein_ligand_schema = TaskSchema(
            task_id="protein_ligand_binding",
            task_name="Protein-Ligand Binding",
            description="Predict protein-ligand binding affinity and structure",
            input_fields=[
                InputField(
                    id="protein_sequence",
                    label="Protein Sequence",
                    field_type=FieldType.SEQUENCE,
                    description="Enter the protein sequence in FASTA format",
                    placeholder="MKTAYIAKQRQISFVKSHFSRQ...",
                    validation=[
                        ValidationRule("required", True, "Protein sequence is required"),
                        ValidationRule("min_length", 10, "Sequence must be at least 10 amino acids"),
                        ValidationRule("max_length", 2000, "Sequence cannot exceed 2000 amino acids")
                    ],
                    help_text="Use standard single-letter amino acid codes"
                ),
                InputField(
                    id="protein_name",
                    label="Protein Name",
                    field_type=FieldType.TEXT,
                    description="Name of the protein (e.g., TRIM25, p53, etc.)",
                    placeholder="TRIM25",
                    validation=[
                        ValidationRule("required", True, "Protein name is required"),
                        ValidationRule("min_length", 1, "Protein name cannot be empty"),
                        ValidationRule("max_length", 100, "Protein name cannot exceed 100 characters")
                    ],
                    help_text="Required for file naming and organization"
                ),
                InputField(
                    id="ligand_smiles",
                    label="Ligand SMILES",
                    field_type=FieldType.SMILES,
                    description="Enter the ligand structure in SMILES format",
                    placeholder="N[C@@H](Cc1ccc(O)cc1)C(=O)O",
                    validation=[
                        ValidationRule("required", True, "Ligand SMILES is required"),
                        ValidationRule("pattern", r"^[A-Za-z0-9\[\]()@#+\-=\\\/]+$", "Invalid SMILES format")
                    ],
                    help_text="Use standard SMILES notation"
                ),
                InputField(
                    id="job_name",
                    label="Job Name",
                    field_type=FieldType.TEXT,
                    description="Name for this prediction job",
                    placeholder="My Protein-Ligand Binding Prediction",
                    validation=[
                        ValidationRule("required", True, "Job name is required"),
                        ValidationRule("min_length", 1, "Job name cannot be empty"),
                        ValidationRule("max_length", 200, "Job name cannot exceed 200 characters")
                    ],
                    default_value="Protein-Ligand Binding Prediction"
                ),
                InputField(
                    id="use_msa",
                    label="Use MSA Server",
                    field_type=FieldType.CHECKBOX,
                    description="Use multiple sequence alignment for better accuracy",
                    default_value=True,
                    help_text="Recommended for better prediction accuracy"
                ),
                InputField(
                    id="use_potentials",
                    label="Use Potentials",
                    field_type=FieldType.CHECKBOX,
                    description="Use additional potential functions",
                    default_value=False,
                    help_text="May improve accuracy but increases computation time"
                )
            ],
            output_fields=[
                OutputField(
                    id="structure",
                    label="3D Structure",
                    output_type=OutputType.STRUCTURE,
                    description="Predicted protein-ligand complex structure",
                    format="cif",
                    visualization="3d"
                ),
                OutputField(
                    id="affinity",
                    label="Binding Affinity",
                    output_type=OutputType.AFFINITY,
                    description="Predicted binding affinity score",
                    format="float",
                    visualization="metric"
                ),
                OutputField(
                    id="confidence",
                    label="Confidence Score",
                    output_type=OutputType.CONFIDENCE,
                    description="Prediction confidence score",
                    format="float",
                    visualization="metric"
                ),
                OutputField(
                    id="binding_sites",
                    label="Binding Sites",
                    output_type=OutputType.BINDING_SITES,
                    description="Predicted binding site residues",
                    format="json",
                    visualization="table"
                ),
                OutputField(
                    id="execution_metrics",
                    label="Execution Metrics",
                    output_type=OutputType.METRICS,
                    description="Execution time and resource usage",
                    format="json",
                    visualization="table"
                )
            ],
            estimated_time=300,
            examples=[
                {
                    "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQ",
                    "ligand_smiles": "N[C@@H](Cc1ccc(O)cc1)C(=O)O",
                    "job_name": "Example Tyrosine Binding"
                }
            ]
        )
        
        # Protein Structure Prediction Task
        protein_structure_schema = TaskSchema(
            task_id="protein_structure",
            task_name="Protein Structure Prediction",
            description="Predict protein structure from sequence",
            input_fields=[
                InputField(
                    id="protein_sequence",
                    label="Protein Sequence",
                    field_type=FieldType.SEQUENCE,
                    description="Enter the protein sequence in FASTA format",
                    placeholder="MKTAYIAKQRQISFVKSHFSRQ...",
                    validation=[
                        ValidationRule("required", True, "Protein sequence is required"),
                        ValidationRule("min_length", 10, "Sequence must be at least 10 amino acids"),
                        ValidationRule("max_length", 2000, "Sequence cannot exceed 2000 amino acids")
                    ],
                    help_text="Use standard single-letter amino acid codes"
                ),
                InputField(
                    id="protein_name",
                    label="Protein Name",
                    field_type=FieldType.TEXT,
                    description="Name of the protein (e.g., TRIM25, p53, etc.)",
                    placeholder="TRIM25",
                    validation=[
                        ValidationRule("required", True, "Protein name is required"),
                        ValidationRule("min_length", 1, "Protein name cannot be empty"),
                        ValidationRule("max_length", 100, "Protein name cannot exceed 100 characters")
                    ],
                    help_text="Required for file naming and organization"
                ),
                InputField(
                    id="job_name",
                    label="Job Name",
                    field_type=FieldType.TEXT,
                    description="Name for this prediction job",
                    placeholder="My Protein Structure Prediction",
                    validation=[
                        ValidationRule("required", True, "Job name is required"),
                        ValidationRule("min_length", 1, "Job name cannot be empty"),
                        ValidationRule("max_length", 200, "Job name cannot exceed 200 characters")
                    ],
                    default_value="Protein Structure Prediction"
                ),
                InputField(
                    id="use_msa",
                    label="Use MSA Server",
                    field_type=FieldType.CHECKBOX,
                    description="Use multiple sequence alignment for better accuracy",
                    default_value=True,
                    help_text="Recommended for better prediction accuracy"
                ),
                InputField(
                    id="prediction_quality",
                    label="Prediction Quality",
                    field_type=FieldType.SELECT,
                    description="Choose prediction quality vs speed tradeoff",
                    options=[
                        {"value": "fast", "label": "Fast (Lower accuracy)"},
                        {"value": "balanced", "label": "Balanced (Recommended)"},
                        {"value": "high", "label": "High Quality (Slower)"}
                    ],
                    default_value="balanced"
                )
            ],
            output_fields=[
                OutputField(
                    id="structure",
                    label="3D Structure",
                    output_type=OutputType.STRUCTURE,
                    description="Predicted protein structure",
                    format="cif",
                    visualization="3d"
                ),
                OutputField(
                    id="confidence",
                    label="Confidence Score",
                    output_type=OutputType.CONFIDENCE,
                    description="Overall prediction confidence",
                    format="float",
                    visualization="metric"
                ),
                OutputField(
                    id="plddt_score",
                    label="pLDDT Score",
                    output_type=OutputType.METRICS,
                    description="Per-residue confidence score",
                    format="float",
                    visualization="metric"
                ),
                OutputField(
                    id="secondary_structure",
                    label="Secondary Structure",
                    output_type=OutputType.VISUALIZATION,
                    description="Predicted secondary structure elements",
                    format="json",
                    visualization="chart"
                ),
                OutputField(
                    id="execution_metrics",
                    label="Execution Metrics",
                    output_type=OutputType.METRICS,
                    description="Execution time and resource usage",
                    format="json",
                    visualization="table"
                )
            ],
            estimated_time=180,
            examples=[
                {
                    "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQ",
                    "job_name": "Example Protein Structure",
                    "prediction_quality": "balanced"
                }
            ]
        )
        
        # Protein Complex Prediction Task
        protein_complex_schema = TaskSchema(
            task_id="protein_complex",
            task_name="Protein Complex Prediction",
            description="Predict protein-protein complex structures",
            input_fields=[
                InputField(
                    id="chain_a_sequence",
                    label="Chain A Sequence",
                    field_type=FieldType.SEQUENCE,
                    description="Enter the first protein sequence",
                    placeholder="MKTAYIAKQRQISFVKSHFSRQ...",
                    validation=[
                        ValidationRule("required", True, "Chain A sequence is required"),
                        ValidationRule("min_length", 10, "Sequence must be at least 10 amino acids")
                    ]
                ),
                InputField(
                    id="chain_b_sequence",
                    label="Chain B Sequence",
                    field_type=FieldType.SEQUENCE,
                    description="Enter the second protein sequence",
                    placeholder="MKTAYIAKQRQISFVKSHFSRQ...",
                    validation=[
                        ValidationRule("required", True, "Chain B sequence is required"),
                        ValidationRule("min_length", 10, "Sequence must be at least 10 amino acids")
                    ]
                ),
                InputField(
                    id="job_name",
                    label="Job Name",
                    field_type=FieldType.TEXT,
                    description="Optional name for this prediction job",
                    placeholder="My Protein Complex Prediction",
                    default_value="Protein Complex Prediction"
                ),
                InputField(
                    id="use_msa",
                    label="Use MSA Server",
                    field_type=FieldType.CHECKBOX,
                    description="Use multiple sequence alignment for better accuracy",
                    default_value=True
                )
            ],
            output_fields=[
                OutputField(
                    id="structure",
                    label="Complex Structure",
                    output_type=OutputType.STRUCTURE,
                    description="Predicted protein complex structure",
                    format="cif",
                    visualization="3d"
                ),
                OutputField(
                    id="interface_confidence",
                    label="Interface Confidence",
                    output_type=OutputType.CONFIDENCE,
                    description="Confidence in protein-protein interface",
                    format="float",
                    visualization="metric"
                ),
                OutputField(
                    id="iptm_score",
                    label="ipTM Score",
                    output_type=OutputType.METRICS,
                    description="Interface predicted template modeling score",
                    format="float",
                    visualization="metric"
                ),
                OutputField(
                    id="interface_residues",
                    label="Interface Residues",
                    output_type=OutputType.BINDING_SITES,
                    description="Residues at the protein-protein interface",
                    format="json",
                    visualization="table"
                )
            ],
            estimated_time=450
        )
        
        # Drug Discovery Task
        drug_discovery_schema = TaskSchema(
            task_id="drug_discovery",
            task_name="Drug Discovery",
            description="Screen compounds for drug discovery",
            input_fields=[
                InputField(
                    id="protein_sequence",
                    label="Target Protein Sequence",
                    field_type=FieldType.SEQUENCE,
                    description="Enter the target protein sequence",
                    validation=[
                        ValidationRule("required", True, "Target protein sequence is required")
                    ]
                ),
                InputField(
                    id="compound_library",
                    label="Compound Library",
                    field_type=FieldType.TEXTAREA,
                    description="Enter SMILES strings (one per line)",
                    placeholder="N[C@@H](Cc1ccc(O)cc1)C(=O)O\nCCOC(=O)C(C)(C)C\n...",
                    validation=[
                        ValidationRule("required", True, "At least one compound is required")
                    ],
                    help_text="Enter one SMILES string per line"
                ),
                InputField(
                    id="max_compounds",
                    label="Maximum Compounds",
                    field_type=FieldType.NUMBER,
                    description="Maximum number of compounds to screen",
                    default_value=100,
                    validation=[
                        ValidationRule("min_value", 1, "Must screen at least 1 compound"),
                        ValidationRule("max_value", 1000, "Cannot screen more than 1000 compounds")
                    ]
                )
            ],
            output_fields=[
                OutputField(
                    id="screening_results",
                    label="Screening Results",
                    output_type=OutputType.SCREENING_RESULTS,
                    description="Results for all screened compounds",
                    format="json",
                    visualization="table"
                ),
                OutputField(
                    id="top_compounds",
                    label="Top Compounds",
                    output_type=OutputType.SCREENING_RESULTS,
                    description="Best performing compounds",
                    format="json",
                    visualization="chart"
                ),
                OutputField(
                    id="hit_rate",
                    label="Hit Rate",
                    output_type=OutputType.METRICS,
                    description="Percentage of compounds with good binding",
                    format="float",
                    visualization="metric"
                )
            ],
            estimated_time=3600
        )
        
        # Batch Protein-Ligand Screening Task
        batch_protein_ligand_schema = TaskSchema(
            task_id="batch_protein_ligand_screening",
            task_name="Batch Protein-Ligand Screening",
            description="Screen multiple ligands against a single protein target",
            input_fields=[
                InputField(
                    id="protein_name",
                    label="Protein Name",
                    field_type=FieldType.TEXT,
                    description="Name of the target protein",
                    placeholder="Carbonic Anhydrase II",
                    validation=[
                        ValidationRule("required", True, "Protein name is required")
                    ]
                ),
                InputField(
                    id="protein_sequence",
                    label="Protein Sequence",
                    field_type=FieldType.SEQUENCE,
                    description="Enter the protein sequence in FASTA format",
                    placeholder="MKTAYIAKQRQISFVKSHFSRQ...",
                    validation=[
                        ValidationRule("required", True, "Protein sequence is required"),
                        ValidationRule("min_length", 10, "Sequence must be at least 10 amino acids"),
                        ValidationRule("max_length", 2000, "Sequence cannot exceed 2000 amino acids")
                    ],
                    help_text="Use standard single-letter amino acid codes"
                ),
                InputField(
                    id="ligands",
                    label="Ligands Array",
                    field_type=FieldType.TEXTAREA,
                    description="Array of ligands with name and smiles properties (max 1501 ligands)",
                    validation=[
                        ValidationRule("required", True, "At least one ligand is required")
                    ],
                    help_text="Processed ligands from CSV upload"
                ),
                InputField(
                    id="job_name",
                    label="Job Name",
                    field_type=FieldType.TEXT,
                    description="Name for this batch screening job",
                    placeholder="My Batch Screening",
                    validation=[
                        ValidationRule("required", True, "Job name is required"),
                        ValidationRule("min_length", 1, "Job name cannot be empty"),
                        ValidationRule("max_length", 200, "Job name cannot exceed 200 characters")
                    ],
                    default_value="Batch Protein-Ligand Screening"
                ),
                InputField(
                    id="use_msa",
                    label="Use MSA Server",
                    field_type=FieldType.CHECKBOX,
                    description="Use multiple sequence alignment for better accuracy",
                    default_value=True,
                    help_text="Recommended for better prediction accuracy"
                ),
                InputField(
                    id="use_potentials",
                    label="Use Potentials",
                    field_type=FieldType.CHECKBOX,
                    description="Use additional potential functions",
                    default_value=False,
                    help_text="May improve accuracy but increases computation time"
                )
            ],
            output_fields=[
                OutputField(
                    id="batch_results",
                    label="Batch Results",
                    output_type=OutputType.SCREENING_RESULTS,
                    description="Results for all protein-ligand pairs",
                    format="json",
                    visualization="table"
                ),
                OutputField(
                    id="individual_jobs",
                    label="Individual Job Results",
                    output_type=OutputType.FILES,
                    description="Links to individual prediction results",
                    format="json",
                    visualization="list"
                ),
                OutputField(
                    id="summary_metrics",
                    label="Summary Metrics",
                    output_type=OutputType.METRICS,
                    description="Overall batch screening metrics",
                    format="json",
                    visualization="chart"
                ),
                OutputField(
                    id="execution_metrics",
                    label="Execution Metrics",
                    output_type=OutputType.METRICS,
                    description="Batch execution time and resource usage",
                    format="json",
                    visualization="table"
                )
            ],
            estimated_time=450300,  # Estimate 5 minutes per ligand * 1501 ligands
            examples=[
                {
                    "protein_name": "Carbonic Anhydrase II",
                    "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQ",
                    "ligand_csv": "ligands.csv",
                    "job_name": "CA2 Screening Batch"
                }
            ]
        )
        
        # RFAntibody Nanobody Design Task
        nanobody_design_schema = TaskSchema(
            task_id="nanobody_design",
            task_name="Nanobody Design",
            description="Design nanobodies targeting specific epitopes using RFAntibody",
            input_fields=[
                InputField(
                    id="target_name",
                    label="Target Name",
                    field_type=FieldType.TEXT,
                    description="Name of the target protein/antigen (e.g., EGFR, HER2, etc.)",
                    placeholder="EGFR",
                    validation=[
                        ValidationRule("required", True, "Target name is required"),
                        ValidationRule("min_length", 1, "Target name cannot be empty"),
                        ValidationRule("max_length", 100, "Target name cannot exceed 100 characters")
                    ],
                    help_text="Required for file naming and organization"
                ),
                InputField(
                    id="target_pdb_content",
                    label="Target PDB Content",
                    field_type=FieldType.TEXTAREA,
                    description="Enter the target PDB structure content",
                    placeholder="ATOM      1  CA  ALA A   1      10.000  10.000  10.000...",
                    validation=[
                        ValidationRule("required", True, "Target PDB content is required"),
                        ValidationRule("min_length", 50, "PDB content must be at least 50 characters")
                    ],
                    help_text="Paste PDB file content for the target antigen"
                ),
                InputField(
                    id="target_chain",
                    label="Target Chain",
                    field_type=FieldType.TEXT,
                    description="Chain identifier in the PDB structure",
                    placeholder="A",
                    default_value="A",
                    validation=[
                        ValidationRule("required", True, "Target chain is required"),
                        ValidationRule("max_length", 1, "Chain must be a single letter")
                    ]
                ),
                InputField(
                    id="hotspot_residues",
                    label="Hotspot Residues",
                    field_type=FieldType.TEXT,
                    description="Comma-separated list of hotspot residue numbers",
                    placeholder="1,2,3,10,15",
                    validation=[
                        ValidationRule("required", True, "At least one hotspot residue is required")
                    ],
                    help_text="Residues that should be targeted by the nanobody"
                ),
                InputField(
                    id="num_designs",
                    label="Number of Designs",
                    field_type=FieldType.NUMBER,
                    description="Number of nanobody designs to generate",
                    default_value=10,
                    validation=[
                        ValidationRule("min_value", 1, "Must generate at least 1 design"),
                        ValidationRule("max_value", 50, "Cannot generate more than 50 designs")
                    ]
                ),
                InputField(
                    id="framework",
                    label="Framework Type",
                    field_type=FieldType.SELECT,
                    description="Nanobody framework to use",
                    options=[
                        {"value": "vhh", "label": "VHH (Heavy chain only)"},
                        {"value": "vh", "label": "VH (Heavy chain)"},
                        {"value": "vl", "label": "VL (Light chain)"}
                    ],
                    default_value="vhh"
                ),
                InputField(
                    id="job_name",
                    label="Job Name",
                    field_type=FieldType.TEXT,
                    description="Name for this design job",
                    placeholder="My Nanobody Design",
                    validation=[
                        ValidationRule("required", True, "Job name is required"),
                        ValidationRule("min_length", 1, "Job name cannot be empty"),
                        ValidationRule("max_length", 200, "Job name cannot exceed 200 characters")
                    ],
                    default_value="Nanobody Design"
                )
            ],
            output_fields=[
                OutputField(
                    id="designs",
                    label="Nanobody Designs",
                    output_type=OutputType.SCREENING_RESULTS,
                    description="Generated nanobody designs with sequences and scores",
                    format="json",
                    visualization="table"
                ),
                OutputField(
                    id="structure",
                    label="Top Design Structure",
                    output_type=OutputType.STRUCTURE,
                    description="3D structure of the best nanobody design",
                    format="cif",
                    visualization="3d"
                ),
                OutputField(
                    id="design_metrics",
                    label="Design Metrics",
                    output_type=OutputType.METRICS,
                    description="Quality metrics for the designs",
                    format="json",
                    visualization="table"
                ),
                OutputField(
                    id="execution_metrics",
                    label="Execution Metrics",
                    output_type=OutputType.METRICS,
                    description="RFAntibody pipeline execution details",
                    format="json",
                    visualization="table"
                )
            ],
            estimated_time=1800,  # 30 minutes for RFAntibody pipeline
            examples=[
                {
                    "target_pdb_content": "ATOM      1  CA  ALA A   1      10.000  10.000  10.000  1.00 20.00           C  ",
                    "target_chain": "A",
                    "hotspot_residues": "1,2,3",
                    "num_designs": 10,
                    "framework": "vhh",
                    "job_name": "Example Nanobody Design"
                }
            ]
        )
        
        # Register all schemas
        self.schemas[protein_ligand_schema.task_id] = protein_ligand_schema
        self.schemas[protein_structure_schema.task_id] = protein_structure_schema
        self.schemas[protein_complex_schema.task_id] = protein_complex_schema
        self.schemas[drug_discovery_schema.task_id] = drug_discovery_schema
        self.schemas[batch_protein_ligand_schema.task_id] = batch_protein_ligand_schema
        self.schemas[nanobody_design_schema.task_id] = nanobody_design_schema
    
    def get_schema(self, task_id: str) -> Optional[TaskSchema]:
        """Get schema for a specific task"""
        return self.schemas.get(task_id)
    
    def get_all_schemas(self) -> Dict[str, TaskSchema]:
        """Get all registered schemas"""
        return self.schemas
    
    def get_input_fields(self, task_id: str) -> List[InputField]:
        """Get input fields for a specific task"""
        schema = self.get_schema(task_id)
        return schema.input_fields if schema else []
    
    def get_output_fields(self, task_id: str) -> List[OutputField]:
        """Get output fields for a specific task"""
        schema = self.get_schema(task_id)
        return schema.output_fields if schema else []
    
    def validate_input(self, task_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input data against task schema"""
        schema = self.get_schema(task_id)
        if not schema:
            return {"valid": False, "errors": [f"Unknown task: {task_id}"]}
        
        errors = []
        for field in schema.input_fields:
            field_value = input_data.get(field.id)
            
            if field.validation:
                for rule in field.validation:
                    if rule.rule_type == "required" and rule.value:
                        # Special handling for ligands field in batch screening
                        if field.id == "ligands" and task_id == "batch_protein_ligand_screening":
                            # Accept both list and string (JSON) formats
                            if field_value is None:
                                errors.append(f"{field.label}: {rule.message}")
                            elif isinstance(field_value, list) and len(field_value) == 0:
                                errors.append(f"{field.label}: {rule.message}")
                            elif isinstance(field_value, str):
                                try:
                                    # Try to parse as JSON if it's a string
                                    import json
                                    parsed = json.loads(field_value) if field_value else []
                                    if not isinstance(parsed, list) or len(parsed) == 0:
                                        errors.append(f"{field.label}: {rule.message}")
                                except:
                                    # If not valid JSON, check if empty string
                                    if not field_value.strip():
                                        errors.append(f"{field.label}: {rule.message}")
                        else:
                            # Handle different field types for required validation
                            if field_value is None or field_value == "":
                                errors.append(f"{field.label}: {rule.message}")
                            elif isinstance(field_value, list) and len(field_value) == 0:
                                errors.append(f"{field.label}: {rule.message}")
                    elif rule.rule_type == "min_length" and field_value and len(str(field_value)) < rule.value:
                        errors.append(f"{field.label}: {rule.message}")
                    elif rule.rule_type == "max_length" and field_value and len(str(field_value)) > rule.value:
                        errors.append(f"{field.label}: {rule.message}")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all schemas to dictionary format"""
        return {
            task_id: asdict(schema)
            for task_id, schema in self.schemas.items()
        }

# Global instance
task_schema_registry = TaskSchemaRegistry()