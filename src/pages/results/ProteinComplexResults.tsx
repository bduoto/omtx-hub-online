import React from 'react';
import BaseResultsPage from './BaseResultsPage';

const ProteinComplexResults: React.FC = () => {
  return (
    <BaseResultsPage
      taskType="protein_complex"
      pageTitle="Protein Complex Prediction Results"
      pageDescription="Multi-chain protein complex structure and interface analysis"
    />
  );
};

export default ProteinComplexResults;