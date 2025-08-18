
import React, { useState } from 'react';
import { SearchBar } from '@/components/SearchBar';
import { FilterPanel } from '@/components/FilterPanel';
import { ModelGrid } from '@/components/ModelGrid';
import { ModelList } from '@/components/ModelList';
import { ModelSearchControls } from '@/components/ModelSearchControls';

const models = [
  {
    title: 'Boltz-2',
    description: 'AlphaFold3 reproduction, predict protein/nucleic acid/small molecule complexes',
    author: 'Wohlwend et. al',
    category: 'Structure Prediction',
    bookmarked: true
  },
  {
    title: 'RFantibody', 
    description: 'De novo antibody design with RFdiffusion',
    author: 'Bennett et. al',
    category: 'Binder Design',
    bookmarked: true
  },
  {
    title: 'Chai-1',
    description: 'AlphaFold3 reproduction, predict protein/nucleic acid/small molecule complexes',
    author: 'Chai Discovery team',
    category: 'Structure Prediction', 
    bookmarked: true
  },
  {
    title: 'Protein Design',
    description: 'Design, diversify, and score your proteins with RFdiffusion pipeline',
    author: 'Watson et. al.',
    category: 'Protein Design',
    bookmarked: true
  },
  {
    title: 'Protein Scoring',
    description: 'Score protein designs for stability and function',
    author: 'Research Team',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'AlphaFold',
    description: 'Highly accurate protein structure prediction',
    author: 'DeepMind',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'Antibody Developability',
    description: 'Assess antibody developability and drug-like properties',
    author: 'Biopharma Team',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'ProteinMPNN',
    description: 'Design protein sequences for given structures',
    author: 'Dauparas et. al',
    category: 'Sequence Design',
    bookmarked: false
  },
  {
    title: 'All Atom Protein Design',
    description: 'Design ligand-binding proteins with RFdiffusion All Atom',
    author: 'Krishna et. al.',
    category: 'Protein Design',
    bookmarked: false
  },
  {
    title: 'RFpeptides',
    description: 'Design macrocyclic proteins',
    author: 'Rettie et. al',
    category: 'Protein Design',
    bookmarked: false
  },
  {
    title: 'Protenix',
    description: 'AlphaFold3 reproduction, predict protein/nucleic acid/small molecule complexes',
    author: 'ByteDance',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'NOS',
    description: 'Generate antibodies optimized for a given property',
    author: 'Gruver et. al',
    category: 'Finetuning and Active Learning',
    bookmarked: false
  },
  {
    title: 'ThermoMPNN',
    description: 'Protein mutation recommendation for increased thermostability',
    author: 'Dieckhaus et. al',
    category: 'Point Mutations',
    bookmarked: false
  },
  {
    title: 'BindCraft',
    description: 'Design de novo binders for your target',
    author: 'Pacesa et. al',
    category: 'Binder Design',
    bookmarked: false
  },
  {
    title: 'TAP (Therapeutic Antibody Profiling)',
    description: 'Developability profiler for antibodies',
    author: 'Raybould MJ et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'PLACER',
    description: 'Protein-ligand docking',
    author: 'Anishchenko et. al',
    category: 'Protein Ligand Docking',
    bookmarked: false
  },
  {
    title: 'IgDesign',
    description: 'In vitro validated antibody design against antigens',
    author: 'Shanehsazzadeh et. al',
    category: 'Antibody Design',
    bookmarked: false
  },
  {
    title: 'Autodock Vina',
    description: 'Protein-ligand docking',
    author: 'J. Eberhardt et. al',
    category: 'Protein Ligand Docking',
    bookmarked: false
  },
  {
    title: 'AntiFold',
    description: 'Design sequences for antibodies',
    author: 'Hummer et. al',
    category: 'Antibody Design',
    bookmarked: false
  },
  {
    title: 'DiffAb',
    description: 'Design CDR sequence and structure for antibodies',
    author: 'Luo et. al',
    category: 'Protein Design',
    bookmarked: false
  },
  {
    title: 'Antibody Diffusion Properties',
    description: 'Design property-aware CDR sequence/structure',
    author: 'Vilegas-Morcillo et. al',
    category: 'Protein Design',
    bookmarked: false
  },
  {
    title: 'DiffDock',
    description: 'Protein-ligand docking with diffusion models',
    author: 'Corso et. al',
    category: 'Protein Ligand Docking',
    bookmarked: false
  },
  {
    title: 'Antibody Evolution',
    description: 'Language models to recommend mutations for increased antibody binding affinity',
    author: 'Ho et. al',
    category: 'Protein Language Models',
    bookmarked: false
  },
  {
    title: 'Molstar Viewer',
    description: 'A web macromolecule viewer embedded into Tamarind (Visualize your PDB files and more!)',
    author: 'Sehnal et. al',
    category: 'Visualization',
    bookmarked: false
  },
  {
    title: 'GROMACS',
    description: 'Simulate protein only or protein-ligand interactions using GROMACS force field',
    author: 'H.J.C. Berendsen et. al',
    category: 'Molecular Dynamics',
    bookmarked: false
  },
  {
    title: 'OpenMM Protein MD',
    description: 'Simulate protein only or protein-ligand interactions using AMBER force field',
    author: 'Arantes P.R. et. al',
    category: 'Molecular Dynamics',
    bookmarked: false
  },
  {
    title: 'ImmuneBuilder',
    description: 'Antibody, Nanobody and TCR structure prediction',
    author: 'Abanades et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'FrameFlow',
    description: 'Motif scaffolding protein design',
    author: 'Yim et. al',
    category: 'Protein Design',
    bookmarked: false
  },
  {
    title: 'ProteinMPNN-ddG',
    description: 'Predict stability of point mutations',
    author: 'Dutton et. al',
    category: 'Point Mutations',
    bookmarked: false
  },
  {
    title: 'LigandMPNN',
    description: 'Inverse folding with modeling of small molecules and more',
    author: 'Dauparas et. al',
    category: 'Inverse Folding',
    bookmarked: false
  },
  {
    title: 'BoltzDesign1',
    description: 'Invert Boltz-1 to design protein binders',
    author: 'Cho et. al',
    category: 'Binder Design',
    bookmarked: false
  },
  {
    title: 'SuperWater',
    description: 'Add waters to protein',
    author: 'Kuang et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'CryoDRGN',
    description: 'Cryo-EM heterogeneity analysis',
    author: 'Zhong et. al',
    category: 'Experimental Data',
    bookmarked: false
  },
  {
    title: 'DeepEMhancer',
    description: 'Cryo-EM Postprocessing',
    author: 'Sanchez-Garcia et. al',
    category: 'Experimental Data',
    bookmarked: false
  },
  {
    title: 'Model Angelo',
    description: 'Given a density map and a protein sequence automatically build a model for it',
    author: 'Jamali et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'CryFold',
    description: 'Given a density map and a protein sequence automatically build a model for it',
    author: 'Su et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'ESMFold',
    description: 'Protein structure prediction using ESM language model',
    author: 'Research Team',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'PULCHRA',
    description: 'All-atom reconstruction and refinement of reduced protein models',
    author: 'Rotkiewicz P. et. al',
    category: 'Utilities',
    bookmarked: false
  },
  {
    title: 'AFSample2',
    description: 'Modified AlphaFold for higher accuracy multimer structure prediction',
    author: 'Kalakoti et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'ZymCTRL',
    description: 'Conditionally generate artificial enzymes',
    author: 'Illanes-Vicioso et. al',
    category: 'Protein Design',
    bookmarked: false
  },
  {
    title: 'ColabDock',
    description: 'Protein-protein docking using inverted AlphaFold',
    author: 'Feng et. al',
    category: 'Protein Protein Docking',
    bookmarked: false
  },
  {
    title: 'dyMEAN',
    description: 'Antibody structure prediction, design, and optimization',
    author: 'Kong et. al',
    category: 'Antibody Design',
    bookmarked: false
  },
  {
    title: 'ABodyBuilder3',
    description: 'Antibody structure prediction',
    author: 'Kenlay et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'EvoNB',
    description: 'Mutate nanobody sequences',
    author: 'Xiong et. al',
    category: 'Protein Language Models',
    bookmarked: false
  },
  {
    title: 'UniFold',
    description: 'Fine-tunable protein structure prediction',
    author: 'Li et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'Thompson Sampling',
    description: 'Screen billions of ligands against target receptors',
    author: 'Kathryn Klarich et. al',
    category: 'Generate Small Molecules',
    bookmarked: false
  },
  {
    title: 'Free Wilson SAR',
    description: 'SAR Analysis',
    author: 'Spencer M. Free and James W. Wilson et. al',
    category: 'Generate Small Molecules',
    bookmarked: false
  },
  {
    title: 'Highfold',
    description: 'Cyclic peptide structure prediction',
    author: 'Rettie et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'BioEmu',
    description: 'Approximate equilibrium distribution',
    author: 'Lewis et. al',
    category: 'Molecular Dynamics',
    bookmarked: false
  },
  {
    title: 'AbGPT',
    description: 'Generate antibody sequences',
    author: 'Kuan et. al',
    category: 'Protein Language Models',
    bookmarked: false
  },
  {
    title: 'Smina',
    description: 'Modified AutoDock, (unconventional) small molecule docking',
    author: 'Koes et. al',
    category: 'Protein Ligand Docking',
    bookmarked: false
  },
  {
    title: 'GNINA',
    description: 'Molecular docking with deep learning',
    author: 'McNutt et. al',
    category: 'Protein Ligand Docking',
    bookmarked: false
  },
  {
    title: 'Unimol DockingV2',
    description: 'State of the art protein-ligand docking',
    author: 'Alcaide et. al',
    category: 'Protein Ligand Docking',
    bookmarked: false
  },
  {
    title: 'DrugFlow',
    description: 'Generate small molecules',
    author: 'Schneuing et. al',
    category: 'Generate Small Molecules',
    bookmarked: false
  },
  {
    title: 'DiffSBDD',
    description: 'Generate small molecules',
    author: 'Sneuing et. al',
    category: 'Generate Small Molecules',
    bookmarked: false
  },
  {
    title: 'Virtual Screening',
    description: 'Screen billions of ligands against target receptors',
    author: 'Research Team',
    category: 'High Throughput',
    bookmarked: false
  },
  {
    title: 'AlphaFlow',
    description: 'AlphaFold fine tuned with a flow matching objective',
    author: 'Jing et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'EquiDock',
    description: 'Rigid body protein-protein docking',
    author: 'Ganea et. al',
    category: 'Protein Protein Docking',
    bookmarked: false
  },
  {
    title: 'AlphaLink',
    description: 'Rigid body protein-protein docking',
    author: 'Stahl et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'Reinvent Finetune',
    description: 'Finetune Reinvent4 on your SMILES dataset and generate small molecules',
    author: 'Loeffler et. al',
    category: 'Generate Small Molecules',
    bookmarked: false
  },
  {
    title: 'CombFold',
    description: 'Predict structures of large protein assemblies',
    author: 'Shor et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'MM/GB(PB)SA',
    description: 'Calculating protein-ligand binding free energy using Molecular mechanics/Generalized-Born (Poisson-Boltzmann) surface area',
    author: 'Research Team',
    category: 'Molecular Dynamics',
    bookmarked: false
  },
  {
    title: 'LibInvent',
    description: 'Given a scaffold, decorate it to generate molecules',
    author: 'Fialkova V et. al',
    category: 'Generate Small Molecules',
    bookmarked: false
  },
  {
    title: 'TCRModel2',
    description: 'Predict T Cell Receptor structures',
    author: 'Yin R et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'DLKcat',
    description: 'Deep learning-based kcat prediction',
    author: 'Li et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'FlowDock',
    description: 'Protein ligand docking and affinity prediction',
    author: 'Morehead et. al',
    category: 'Protein Ligand Docking',
    bookmarked: false
  },
  {
    title: 'CatPred',
    description: 'ESM-2 based kcat, Km, and Ki prediction',
    author: 'Boorla et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'ParaSurf',
    description: 'Predict paratope residues',
    author: 'Papadopoulos et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'Binding ddG',
    description: 'Binding ddG prediction of protein complexes',
    author: 'Shan et. al',
    category: 'Protein Protein Docking',
    bookmarked: false
  },
  {
    title: 'FoldMason',
    description: 'Multiple Protein Structure Alignment at Scale',
    author: 'Gilchrist et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'Foldseek',
    description: 'Ultra-fast protein structure search and alignment',
    author: 'van Kempen et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'Progen2',
    description: 'Generate novel protein sequences',
    author: 'Nijkamp et. al',
    category: 'Protein Language Models',
    bookmarked: false
  },
  {
    title: 'Progen2 Finetune',
    description: 'Finetune ProGen2 on your custom sequences',
    author: 'Nijkamp et. al',
    category: 'Protein Language Models',
    bookmarked: false
  },
  {
    title: 'COMPSS Protein Metrics',
    description: 'Score sequences using language model metrics',
    author: 'Johnson et. al',
    category: 'Protein Language Models',
    bookmarked: false
  },
  {
    title: 'SaProt',
    description: 'Language models for protein property prediction',
    author: 'Su et. al',
    category: 'Protein Language Models',
    bookmarked: false
  },
  {
    title: 'FREEDA',
    description: 'A computational pipeline to guide experimental testing of protein innovation by detecting positive selection.',
    author: 'Dudka et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'PEP-Patch',
    description: 'Quantify surface electrostatic potentials',
    author: 'Valentin J. Hoerschinger et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'MoFlow',
    description: 'Generate small molecules',
    author: 'Zang et. al',
    category: 'Generate Small Molecules',
    bookmarked: false
  },
  {
    title: 'AF Cluster',
    description: 'Predicting multiple conformations via sequence clustering',
    author: 'Wayment-Steele et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'DeepImmuno',
    description: 'Prediction of immunogenic epitopes for T cell immunity (Class 1)',
    author: 'Guangyuan Li et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'TLimmuno',
    description: 'Class II Immunogenicity Prediction',
    author: 'Guangshuai Wang et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'NetSolP',
    description: 'Solubility and usability based on protein language models',
    author: 'Thumuluri V et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'TEMPRO',
    description: 'Nanobody melting temperature prediction',
    author: 'Alvarez et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'TemStaPro',
    description: 'Protein thermostability prediction',
    author: 'Pudziuvelytė et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'ThermoMPNN-D',
    description: 'Double protein point mutation recommendation for increased thermostability',
    author: 'Dieckhaus et. al',
    category: 'Point Mutations',
    bookmarked: false
  },
  {
    title: 'EvoProtGrad',
    description: 'Generate mutations with directed evolution',
    author: 'Emami et. al',
    category: 'Protein Design',
    bookmarked: false
  },
  {
    title: 'ADMET',
    description: 'Quickly predict drug properties',
    author: 'Swanson K et. al',
    category: 'Generate Small Molecules',
    bookmarked: false
  },
  {
    title: 'AF2Bind',
    description: 'Predict ligand binding sites',
    author: 'Gazizov et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'AfCycDesign',
    description: 'Design cyclic peptides',
    author: 'Rettie et. al',
    category: 'Binder Design',
    bookmarked: false
  },
  {
    title: 'Structural Evolution',
    description: 'Mutate protein complexes with structure-informed language model',
    author: 'Varun R. Shanker et. al. et. al',
    category: 'Protein Language Models',
    bookmarked: false
  },
  {
    title: 'PRODIGY',
    description: 'Protein-protein binding affinity prediction',
    author: 'Xue L et. al',
    category: 'Protein Protein Docking',
    bookmarked: false
  },
  {
    title: 'Protein Redesign',
    description: 'Deep Learning-based model for Ligand-Binding Protein Redesign',
    author: 'Nguyen et. al',
    category: 'Protein Design',
    bookmarked: false
  },
  {
    title: 'BioPhi',
    description: 'Antibody humanization evaluation and mutation recommendation',
    author: 'Prihoda D et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'EvoPro',
    description: 'Genetic algorithm-based protein binder optimization pipeline',
    author: 'Goudy OJ et. al',
    category: 'Binder Design',
    bookmarked: false
  },
  {
    title: 'Humatch',
    description: 'Antibody humanization evaluation and mutation recommendation',
    author: 'Chinery et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'Aggrescan3D',
    description: 'Predict aggregation propensity in protein structures and rationally design protein solubility',
    author: 'Aleksander Kuriata et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'Deep Viscosity',
    description: 'Viscosity prediction for antibodies',
    author: 'Kalajaye et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'DeepSP',
    description: 'Viscosity, spatial charge map (SCM) and spatial aggregation propensity (SAP) predictions for antibodies',
    author: 'Lateefat Kalajaye et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'Relative Binding Free Energy',
    description: 'Relative energy of protein-ligand complexes',
    author: 'Scheen J et. al',
    category: 'Molecular Dynamics',
    bookmarked: false
  },
  {
    title: 'PepFuNN Peptide Sequence Analysis',
    description: 'Predict properties for peptides',
    author: 'Ochoa R et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'SPACE2',
    description: 'Cluster antibodies by structural similarity and accurately group those bind the same epitope',
    author: 'Spoendlin et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'AF Unmasked',
    description: 'Structure prediction with multimeric templates',
    author: 'Mirabello et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'DockQ',
    description: 'Evaluate your docking interface',
    author: 'Basu et. al',
    category: 'Protein Protein Docking',
    bookmarked: false
  },
  {
    title: 'AF-Traj',
    description: 'Predict protein conformations with subsampled AlphaFold2',
    author: 'Monteiro da Silva et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'Multiple Sequence Alignment',
    description: 'Multiple sequence alignment (MSA)',
    author: 'Steinegger et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'MSA Clustering',
    description: 'Clustering by MSA',
    author: 'Steinegger et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'SaProt Finetuning',
    description: 'SaProt finetuning',
    author: 'Su et. al',
    category: 'Protein Language Models',
    bookmarked: false
  },
  {
    title: 'Finetune Protein Language Model',
    description: 'Protein sequence property prediction finetuning',
    author: 'Schirmer et. al',
    category: 'Finetuning and Active Learning',
    bookmarked: false
  },
  {
    title: 'RSO Binder Design',
    description: 'Efficient binder design',
    author: 'Frank et. al',
    category: 'Binder Design',
    bookmarked: false
  },
  {
    title: 'Spatial PPI v2',
    description: 'Predict PPI of structures or sequences',
    author: 'Hu et. al',
    category: 'Protein Protein Docking',
    bookmarked: false
  },
  {
    title: 'PocketGen',
    description: '(Re)Generate a binding pocket for a given small molecule',
    author: 'Zhang et. al',
    category: 'Generate Small Molecules',
    bookmarked: false
  },
  {
    title: 'AFDesign',
    description: 'Redesign a protein binder to a sequence AlphaFold thinks will bind to the target structure',
    author: 'Ueki et. al',
    category: 'Antibody Design',
    bookmarked: false
  },
  {
    title: 'Protein Solubilization',
    description: 'Solubilize membrane proteins',
    author: 'Frank et. al',
    category: 'Protein Design',
    bookmarked: false
  },
  {
    title: 'RFdiffusion with Chai verification',
    description: 'Protein design with Chai verification',
    author: 'Watson et. al',
    category: 'Protein Design',
    bookmarked: false
  },
  {
    title: 'ColabDesign Fixed Backbone',
    description: 'Generate sequences given structure via reversing AlphaFold',
    author: 'Frank et. al',
    category: 'Protein Design',
    bookmarked: false
  },
  {
    title: 'DeepFRI',
    description: 'Predict protein function',
    author: 'Gligorijevic et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'AbLang2',
    description: 'Antibody language model',
    author: 'Olsen et. al',
    category: 'Antibody Design',
    bookmarked: false
  },
  {
    title: 'AbLang-MPNN',
    description: 'Hybrid antibody design using AbLang + ProteinMPNN ensemble',
    author: 'del Alamo et. al',
    category: 'Antibody Design',
    bookmarked: false
  },
  {
    title: 'AbMAP',
    description: 'Antibody language model',
    author: 'Singh et. al',
    category: 'Protein Language Models',
    bookmarked: false
  },
  {
    title: 'AntiBERTy',
    description: 'Optimize antibody/nanobody sequence affinity',
    author: 'Ruffolo et. al',
    category: 'Antibody Design',
    bookmarked: false
  },
  {
    title: 'deepSTABp',
    description: 'Predict protein melting temperature',
    author: 'Jung et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'HyperMPNN',
    description: 'Design thermostable proteins',
    author: 'Errett et. al',
    category: 'Inverse Folding',
    bookmarked: false
  },
  {
    title: 'AbMPNN',
    description: 'Antibody sequence design',
    author: 'Dreyer et. al',
    category: 'Antibody Design',
    bookmarked: false
  },
  {
    title: 'ANARCI',
    description: 'Annotate immune proteins',
    author: 'Dunbar et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'Antibody Annotation',
    description: 'Annotate immune proteins',
    author: 'Prihoda D et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'ESM2 Embeddings',
    description: 'Generate ESM2 Embeddings',
    author: 'Lin et. al',
    category: 'Finetuning and Active Learning',
    bookmarked: false
  },
  {
    title: 'ESM-IF1',
    description: 'Inverse folding with ESM-IF1 language model',
    author: 'Hsu et. al',
    category: 'Inverse Folding',
    bookmarked: false
  },
  {
    title: 'Prot T5 XL Embeddings',
    description: 'Generate Prot T5 Embeddings',
    author: 'Elnaggar et. al',
    category: 'Finetuning and Active Learning',
    bookmarked: false
  },
  {
    title: 'IPC 2.0',
    description: 'Predict protein isoelectric point and pKa',
    author: 'Kozlowski et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'N-Linked Glycosylation Prediction',
    description: 'Predict N-Linked Glycosylation sites',
    author: 'Pakhrin et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'MaSIF',
    description: 'Molecular surface interaction fingerprints',
    author: 'Gainza et. al',
    category: 'Finetuning and Active Learning',
    bookmarked: false
  },
  {
    title: 'ESM2',
    description: 'Score point mutations or mask residues using ESM-2 language model',
    author: 'Lin et. al',
    category: 'Point Mutations',
    bookmarked: false
  },
  {
    title: 'AMPLIFY',
    description: 'Score using AMPLIFY language model',
    author: 'Fournier et. al',
    category: 'Point Mutations',
    bookmarked: false
  },
  {
    title: 'BALM Paired',
    description: 'Score point mutations using BALM-paired language model',
    author: 'Burbach et. al',
    category: 'Point Mutations',
    bookmarked: false
  },
  {
    title: 'ESM-Scan',
    description: 'Score point mutations using ESM1b language model',
    author: 'Lin et. al',
    category: 'Point Mutations',
    bookmarked: false
  },
  {
    title: 'PDockQ',
    description: 'Predict DockQ score of a predicted protein structure',
    author: 'Bryant et. al',
    category: 'Protein Protein Docking',
    bookmarked: false
  },
  {
    title: 'IPSAE',
    description: 'Scoring function for interprotein interactions in AlphaFold',
    author: 'Dunbrack et. al',
    category: 'Protein Protein Docking',
    bookmarked: false
  },
  {
    title: 'PROPKA',
    description: 'Predict the pKa values of ionizable groups in proteins',
    author: 'Olsson et. al',
    category: 'Developability',
    bookmarked: false
  },
  {
    title: 'MDGen',
    description: 'Generative modeling of molecular dynamics trajectories',
    author: 'Jing et. al',
    category: 'Molecular Dynamics',
    bookmarked: false
  },
  {
    title: 'RosettaFold All-Atom',
    description: 'Use RosettaFold to predict complexes of proteins, nucleic acids, and small molecules',
    author: 'Krishna R et. al',
    category: 'Structure Prediction',
    bookmarked: false
  },
  {
    title: 'PLAbDab',
    description: 'Search antibody sequences from patents and literature',
    author: 'Abanades B et. al',
    category: 'Antibody Design',
    bookmarked: false
  },
  {
    title: 'Protein Properties',
    description: 'Calculate properties on input sequence/structure',
    author: 'Almeida DS et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'RMSD Calculator',
    description: 'Calculate RMSD between two protein structures',
    author: 'Delano et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'USalign',
    description: 'Structurally align proteins and nucleic acids',
    author: 'Chengxin Zhang et. al',
    category: 'Utilities',
    bookmarked: false
  },
  {
    title: 'AtomSurf',
    description: 'Atomic surface analysis',
    author: 'Mallet et. al',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'DNAWorks',
    description: 'Automatic oligonucleotide design for PCR-based gene synthesis',
    author: 'Research Team',
    category: 'Utilities',
    bookmarked: false
  },
  {
    title: 'Legolas',
    description: 'Predict protein chemical shifts from PDB structures',
    author: 'Research Team',
    category: 'Analysis',
    bookmarked: false
  },
  {
    title: 'OpenFE',
    description: 'Run different free energy protocols',
    author: 'Research Team',
    category: 'Molecular Dynamics',
    bookmarked: false
  },
  {
    title: 'RiffDiff-ProtFlow',
    description: 'Generate backbone fragments from a theozyme to build a motif library',
    author: 'Braun et. al',
    category: 'Protein Design',
    bookmarked: false
  }
];

export const SearchSection = () => {
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('grid');

  const toggleTag = (tag: string) => {
    setSelectedTags(prev => 
      prev.includes(tag) 
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

  const resetFilters = () => {
    setSelectedTags([]);
  };

  const filteredModels = models.filter(model => {
    const matchesSearch = model.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      model.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      model.author.toLowerCase().includes(searchQuery.toLowerCase()) ||
      model.category.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesTags = selectedTags.length === 0 || 
      selectedTags.some(selectedTag => 
        model.category.includes(selectedTag) || 
        model.description.includes(selectedTag)
      );
    
    return matchesSearch && matchesTags;
  });

  return (
    <div className="space-y-6">
      <ModelSearchControls
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onFilterToggle={() => setIsFilterOpen(!isFilterOpen)}
      />
      
      <FilterPanel
        isOpen={isFilterOpen}
        onClose={() => setIsFilterOpen(false)}
        selectedTags={selectedTags}
        onTagToggle={toggleTag}
        onResetFilters={resetFilters}
      />
      
      {viewMode === 'grid' ? (
        <ModelGrid models={filteredModels} />
      ) : (
        <ModelList models={filteredModels} />
      )}
    </div>
  );
};
