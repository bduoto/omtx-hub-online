
import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileGrid } from '@/components/FileGrid';
import { FilePreview } from '@/components/FilePreview';
import { Grid, List, Download, Share } from 'lucide-react';

interface FileViewerProps {
  path: string;
  organization: string;
  searchQuery: string;
  selectedFile: any;
  onFileSelect: (file: any) => void;
}

export const FileViewer: React.FC<FileViewerProps> = ({
  path,
  organization,
  searchQuery,
  selectedFile,
  onFileSelect
}) => {
  const [viewMode, setViewMode] = React.useState<'grid' | 'list'>('grid');

  const handleClosePreview = () => {
    onFileSelect(null);
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Toolbar */}
      <Card className="bg-gray-800 border-gray-700 mb-4 flex-shrink-0">
        <div className="p-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-white font-medium">Path:</span>
            <span className="text-gray-400 font-mono">{path}</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('grid')}
              className="text-white"
            >
              <Grid className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('list')}
              className="text-white"
            >
              <List className="h-4 w-4" />
            </Button>
            <div className="w-px h-6 bg-gray-600 mx-2" />
            <Button variant="ghost" size="sm" className="text-white">
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
            <Button variant="ghost" size="sm" className="text-white">
              <Share className="h-4 w-4 mr-2" />
              Share
            </Button>
          </div>
        </div>
      </Card>

      {/* Content Area - Responsive with proper overflow handling */}
      <div className="flex-1 flex gap-4 min-h-0 overflow-hidden">
        {/* File Grid - Takes available space */}
        <div className={`${selectedFile ? 'flex-1' : 'w-full'} min-w-0`}>
          <FileGrid 
            path={path}
            organization={organization}
            searchQuery={searchQuery}
            viewMode={viewMode}
            selectedFile={selectedFile}
            onFileSelect={onFileSelect}
          />
        </div>

        {/* File Preview - Fixed width when visible */}
        {selectedFile && (
          <div className="w-96 flex-shrink-0 min-h-0">
            <FilePreview file={selectedFile} onClose={handleClosePreview} />
          </div>
        )}
      </div>
    </div>
  );
};
