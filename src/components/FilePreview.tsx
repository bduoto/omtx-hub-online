
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, Share, Eye, X } from 'lucide-react';

interface FilePreviewProps {
  file: {
    id: string;
    name: string;
    type: string;
    size?: string;
    modified: string;
    thumbnail?: string;
    path: string;
  };
  onClose: () => void;
}

export const FilePreview: React.FC<FilePreviewProps> = ({ file, onClose }) => {
  return (
    <Card className="bg-gray-800 border-gray-700 h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-white text-lg truncate" title={file.name}>
            {file.name}
          </CardTitle>
          <div className="flex items-center space-x-2">
            <Button variant="ghost" size="sm" className="text-white">
              <Eye className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" className="text-white">
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" className="text-white">
              <Share className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" className="text-white hover:text-red-400" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Preview Area */}
        <div className="mb-6">
          {file.thumbnail && file.type === 'image' ? (
            <div className="aspect-video rounded-lg overflow-hidden bg-gray-900">
              <img
                src={file.thumbnail}
                alt={file.name}
                className="w-full h-full object-contain"
              />
            </div>
          ) : (
            <div className="aspect-video rounded-lg bg-gray-700 flex items-center justify-center">
              <p className="text-gray-400">Preview not available</p>
            </div>
          )}
        </div>

        {/* File Details */}
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-gray-400 text-sm">Type</label>
              <p className="text-white capitalize">{file.type}</p>
            </div>
            <div>
              <label className="text-gray-400 text-sm">Size</label>
              <p className="text-white">{file.size || 'Unknown'}</p>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-gray-400 text-sm">Modified</label>
              <p className="text-white">{file.modified}</p>
            </div>
            <div>
              <label className="text-gray-400 text-sm">Path</label>
              <p className="text-white font-mono text-sm truncate" title={file.path}>
                {file.path}
              </p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 pt-4 border-t border-gray-700">
          <div className="flex space-x-2">
            <Button className="flex-1 bg-[#E2E756] hover:bg-[#E2E756]/90 text-black">
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
            <Button className="flex-1 bg-[#E2E756] hover:bg-[#E2E756]/90 text-black">
              <Share className="h-4 w-4 mr-2" />
              Share
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
