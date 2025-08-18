
import React from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, X, Grid3X3, List } from 'lucide-react';

interface ModelSearchControlsProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  viewMode: 'list' | 'grid';
  onViewModeChange: (mode: 'list' | 'grid') => void;
  onFilterToggle: () => void;
  showNewButton?: boolean;
  onRequestTool?: () => void;
}

export const ModelSearchControls: React.FC<ModelSearchControlsProps> = ({
  searchQuery,
  onSearchChange,
  viewMode,
  onViewModeChange,
  onFilterToggle,
  showNewButton = false,
  onRequestTool,
}) => {
  const handleReset = () => {
    onSearchChange('');
  };

  return (
    <div className="flex items-center gap-4 mb-6">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
        <Input
          type="text"
          placeholder="Search models..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-10 pr-10 bg-gray-800 border-gray-700 text-white placeholder-gray-400 focus:border-[#E2E756]"
        />
        {searchQuery && (
          <button
            onClick={handleReset}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      
      <div className="flex items-center gap-2">
        <div className="flex bg-gray-800 rounded-lg p-1">
          <Button
            variant={viewMode === 'grid' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => onViewModeChange('grid')}
            className={`p-2 ${
              viewMode === 'grid'
                ? 'bg-[#E2E756] text-gray-900 hover:bg-[#d4d347]'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            <Grid3X3 className="w-4 h-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => onViewModeChange('list')}
            className={`p-2 ${
              viewMode === 'list'
                ? 'bg-[#E2E756] text-gray-900 hover:bg-[#d4d347]'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            <List className="w-4 h-4" />
          </Button>
        </div>
        
        <Button
          variant="outline"
          onClick={onFilterToggle}
          className="bg-gray-800 border-gray-700 text-white hover:bg-gray-700 hover:border-[#E2E756]"
        >
          Filters
        </Button>
        
        {showNewButton && onRequestTool && (
          <Button
            onClick={onRequestTool}
            className="bg-[#E2E756] hover:bg-[#d4d347] text-black font-medium"
          >
            New
          </Button>
        )}
      </div>
    </div>
  );
};
