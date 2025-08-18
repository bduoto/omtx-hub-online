
import React from 'react';
import { ModelCard } from '@/components/ModelCard';

interface Model {
  title: string;
  description: string;
  author: string;
  category: string;
  bookmarked: boolean;
}

interface ModelGridProps {
  models: Model[];
}

export const ModelGrid: React.FC<ModelGridProps> = ({ models }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {models.map((model, index) => (
        <ModelCard key={index} {...model} />
      ))}
    </div>
  );
};
