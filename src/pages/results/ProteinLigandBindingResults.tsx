import React from 'react';
import BaseResultsPage from './BaseResultsPage';

const ProteinLigandBindingResults: React.FC = () => {
  return (
    <BaseResultsPage
      taskType="protein_ligand_binding"
      pageTitle="Protein-Ligand Binding Results"
      pageDescription="Binding affinity prediction and 3D complex structure analysis"
    />
  );
};

export default ProteinLigandBindingResults;