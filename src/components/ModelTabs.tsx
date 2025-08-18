
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';

interface ModelTabsProps {
  onRequestTool: () => void;
}

export const ModelTabs: React.FC<ModelTabsProps> = ({ onRequestTool }) => {
  const [activeTab, setActiveTab] = useState('my-models');

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between mb-8">
      <div className="text-center mb-4 sm:mb-0">
        <p className="text-gray-400 mb-4">Have a tool suggestion?</p>
        <Button 
          onClick={onRequestTool}
          className="bg-[#E2E756] hover:bg-[#C4C93A] text-gray-900 font-medium px-6 py-2"
        >
          Request a Tool
        </Button>
      </div>
      
      <div className="flex border border-gray-600 rounded-lg overflow-hidden">
        <button
          onClick={() => setActiveTab('my-models')}
          className={`px-6 py-3 text-sm font-medium transition-colors ${
            activeTab === 'my-models'
              ? 'bg-[#E2E756] text-gray-900'
              : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
        >
          My Models (0)
        </button>
        <button
          onClick={() => setActiveTab('organization-models')}
          className={`px-6 py-3 text-sm font-medium transition-colors ${
            activeTab === 'organization-models'
              ? 'bg-[#E2E756] text-gray-900'
              : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
        >
          Organization Models (0)
        </button>
      </div>
    </div>
  );
};
