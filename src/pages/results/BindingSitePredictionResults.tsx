import React from 'react';
import BaseResultsPage from './BaseResultsPage';

const BindingSitePredictionResults: React.FC = () => {
  return (
    <BaseResultsPage
      taskType="binding_site_prediction"
      pageTitle="Binding Site Prediction Results"
      pageDescription="Identification of potential binding sites and druggable cavities"
    />
  );
};

export default BindingSitePredictionResults;