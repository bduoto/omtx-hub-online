import React from 'react';
import BaseResultsPage from './BaseResultsPage';

const VariantComparisonResults: React.FC = () => {
  return (
    <BaseResultsPage
      taskType="variant_comparison"
      pageTitle="Variant Comparison Results"
      pageDescription="Structural and functional impact analysis of protein variants"
    />
  );
};

export default VariantComparisonResults;