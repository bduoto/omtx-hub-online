import React from 'react';
import BaseResultsPage from './BaseResultsPage';

const ProteinStructureResults: React.FC = () => {
  return (
    <BaseResultsPage
      taskType="protein_structure"
      pageTitle="Protein Structure Prediction Results"
      pageDescription="3D structure prediction from amino acid sequence using state-of-the-art folding models"
    />
  );
};

export default ProteinStructureResults;