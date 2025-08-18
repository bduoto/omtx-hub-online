
import React from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, RotateCcw } from 'lucide-react';

interface SearchControlsProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  onReset?: () => void;
}

export const SearchControls: React.FC<SearchControlsProps> = ({
  searchQuery,
  onSearchChange,
  onReset,
}) => {
  return (
    <div className="flex items-center gap-4 mb-4">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
        <Input
          placeholder="Search Jobs..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-10 bg-gray-800 border-gray-600 text-white placeholder-gray-500 focus:border-[#E2E756] focus:ring-[#E2E756]"
        />
      </div>
      <Button 
        variant="outline" 
        size="icon" 
        className="text-gray-400 border-gray-600 hover:bg-gray-700"
        onClick={onReset}
      >
        <RotateCcw className="w-4 h-4" />
      </Button>
    </div>
  );
};
