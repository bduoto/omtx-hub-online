
import React, { useState } from 'react';
import { Header } from '@/components/Header';
import { Navigation } from '@/components/Navigation';
import { DirectoryPanel } from '@/components/DirectoryPanel';
import { FileViewer } from '@/components/FileViewer';
import { OrganizationSelector } from '@/components/OrganizationSelector';
import { SearchBar } from '@/components/SearchBar';

const Gallery = () => {
  const [selectedOrganization, setSelectedOrganization] = useState('All Organizations');
  const [selectedPath, setSelectedPath] = useState('/');
  const [selectedFile, setSelectedFile] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      <Header />
      <Navigation />
      
      <main className="flex-1 flex flex-col max-w-7xl mx-auto w-full px-6 py-8 min-h-0">
        {/* Top Controls */}
        <div className="flex items-center justify-between mb-6 flex-shrink-0">
          <div className="flex flex-col space-y-4">
            <h1 className="text-3xl font-bold text-white">Gallery</h1>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-400 font-medium">Organization:</div>
              <OrganizationSelector 
                selected={selectedOrganization}
                onSelect={setSelectedOrganization}
              />
            </div>
          </div>
          <div className="w-96">
            <SearchBar 
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder="Search files and folders..."
            />
          </div>
        </div>

        {/* Main Content - Full Height with proper flex distribution */}
        <div className="flex gap-6 flex-1 min-h-0 overflow-hidden">
          {/* Directory Panel - Fixed width but responsive */}
          <div className="w-80 flex-shrink-0 min-h-0">
            <DirectoryPanel 
              selectedPath={selectedPath}
              onPathSelect={setSelectedPath}
              organization={selectedOrganization}
              searchQuery={searchQuery}
            />
          </div>

          {/* File Viewer - Takes remaining space */}
          <div className="flex-1 min-w-0 min-h-0">
            <FileViewer 
              path={selectedPath}
              organization={selectedOrganization}
              searchQuery={searchQuery}
              selectedFile={selectedFile}
              onFileSelect={setSelectedFile}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default Gallery;
