import React from 'react';
import { Button } from '@/components/ui/button';
import { DirectoryPanel } from '@/components/DirectoryPanel';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface DirectorySidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
  selectedPath: string;
  onPathSelect: (path: string) => void;
  searchQuery: string;
}

export const DirectorySidebar = ({
  isCollapsed,
  onToggle,
  selectedPath,
  onPathSelect,
  searchQuery
}: DirectorySidebarProps) => {
  return (
    <div className={`h-full bg-gray-800 border-r border-gray-700 transition-all duration-300 ease-in-out ${
      isCollapsed ? 'w-12' : 'w-80'
    } ${isCollapsed ? 'shadow-lg' : 'shadow-xl'}`}>
      {isCollapsed ? (
        <div className="p-3">
          <Button
            variant="ghost"
            onClick={onToggle}
            className="text-gray-400 hover:text-white w-8 h-8 p-0"
          >
            <ChevronRight className="h-5 w-5" />
          </Button>
        </div>
      ) : (
        <div className="h-full flex flex-col">
          <div className="p-4 border-b border-gray-700 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Directory</h3>
            <Button
              variant="ghost"
              onClick={onToggle}
              className="text-gray-400 hover:text-white w-8 h-8 p-0"
            >
              <ChevronLeft className="h-5 w-5" />
            </Button>
          </div>
          <div className="flex-1 p-4">
            <DirectoryPanel 
              selectedPath={selectedPath}
              onPathSelect={onPathSelect}
              organization="All Organizations"
              searchQuery={searchQuery}
            />
          </div>
        </div>
      )}
    </div>
  );
};