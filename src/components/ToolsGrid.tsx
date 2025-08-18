
import React from 'react';
import { ToolCard } from '@/components/ToolCard';

const tools = [
  {
    title: 'Batch Workflows',
    description: 'Use any of our tools at massive scales',
    icon: '',
    color: 'from-blue-500 to-[#E2E756]',
    backgroundImage: '/lovable-uploads/aa36e027-f615-4f42-96d4-c83a04ba3804.png'
  },
  {
    title: 'Pipelines', 
    description: 'Chain together tools to create a custom pipeline',
    icon: '',
    color: 'from-[#E2E756] to-teal-500',
    backgroundImage: '/lovable-uploads/f721da29-81dd-4604-a708-fdf04f3d64c0.png'
  },
  {
    title: 'Playground',
    description: 'Experiment with tools in a project environment',
    icon: '',
    color: 'from-teal-500 to-[#E2E756]',
    backgroundImage: '/lovable-uploads/6dd967b5-7505-4a4a-b64a-bc3ba17e732f.png'
  },
  {
    title: 'Database',
    description: 'Store and manage all your proteins',
    icon: '',
    color: 'from-green-500 to-[#E2E756]',
    backgroundImage: '/lovable-uploads/b6c48d6e-bf7c-4e2b-a288-f4d4d8a7bf94.png'
  }
];

export const ToolsGrid = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
      {tools.map((tool, index) => (
        <ToolCard key={index} {...tool} />
      ))}
    </div>
  );
};
