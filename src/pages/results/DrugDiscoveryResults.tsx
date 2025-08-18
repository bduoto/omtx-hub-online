import React from 'react';
import BaseResultsPage from './BaseResultsPage';

const DrugDiscoveryResults: React.FC = () => {
  return (
    <BaseResultsPage
      taskType="drug_discovery"
      pageTitle="Drug Discovery Results"
      pageDescription="High-throughput compound screening and lead optimization analysis"
    />
  );
};

export default DrugDiscoveryResults;