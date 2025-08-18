
import React from 'react';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';

interface TableControlsProps {
  selectedJobsCount: number;
  canDownload: boolean;
  canDelete: boolean;
}

export const TableControls: React.FC<TableControlsProps> = ({
  selectedJobsCount,
  canDownload,
  canDelete,
}) => {
  return (
    <div className="flex gap-2">
      <Button className="bg-[#E2E756] hover:bg-[#d4d347] text-black font-medium border-0">
        <Download className="w-4 h-4 mr-2" />
        Export
      </Button>
      <Button 
        variant="ghost" 
        className={`transition-colors ${
          canDownload 
            ? 'text-[#E2E756] hover:text-[#d4d347] hover:bg-[#E2E756]/10 bg-[#E2E756]/5' 
            : 'text-gray-400 hover:text-white hover:bg-gray-700'
        }`}
      >
        Download Results
      </Button>
      <Button 
        variant="ghost" 
        className={`transition-colors ${
          canDelete 
            ? 'text-[#E2E756] hover:text-[#d4d347] hover:bg-[#E2E756]/10 bg-[#E2E756]/5' 
            : 'text-gray-400 hover:text-white hover:bg-gray-700'
        }`}
      >
        Delete Jobs
      </Button>
    </div>
  );
};
