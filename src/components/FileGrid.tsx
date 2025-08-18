import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { FileImage, Folder, FileText, File, Image, Camera, Monitor, Palette } from 'lucide-react';
import { jobService } from '@/services/jobService';

interface FileItem {
  id: string;
  name: string;
  type: 'folder' | 'image' | 'document' | 'file' | 'job';
  size?: string;
  modified: string;
  thumbnail?: string;
  path: string;
  jobId?: string;
  job?: any;
}

interface FileGridProps {
  path: string;
  organization: string;
  searchQuery: string;
  viewMode: 'grid' | 'list';
  selectedFile: FileItem | null;
  onFileSelect: (file: FileItem | null) => void;
}

// Enhanced file structure with all files organized by path
const staticFiles: { [key: string]: FileItem[] } = {
  '/': [
    // Recently opened files for root
    {
      id: 'recent1',
      name: 'protein-structure-1.png',
      type: 'image',
      size: '2.4 MB',
      modified: '2 hours ago',
      thumbnail: '/lovable-uploads/f5170632-c5f7-4903-bb3c-581d05ea59c5.png',
      path: '/protein-structure-1.png'
    },
    {
      id: 'recent2',
      name: 'molecular-complex-2.png',
      type: 'image',
      size: '1.8 MB',
      modified: '5 hours ago',
      thumbnail: '/lovable-uploads/3f9b94bc-09fc-4b4e-a377-91136ab61c92.png',
      path: '/molecular-complex-2.png'
    },
    {
      id: 'recent3',
      name: 'docking_site.jpeg',
      type: 'image',
      size: '1.2 MB',
      modified: '1 day ago',
      path: '/docking_site.jpeg'
    },
    {
      id: 'recent4',
      name: 'lab_logo.png',
      type: 'image',
      size: '800 KB',
      modified: '2 days ago',
      path: '/lab_logo.png'
    }
  ],
  '/projects': [
    // All files from GPCR Screens subfolder
    {
      id: 'p1',
      name: 'protein-structure-1.png',
      type: 'image',
      size: '2.4 MB',
      modified: '2 hours ago',
      thumbnail: '/lovable-uploads/f5170632-c5f7-4903-bb3c-581d05ea59c5.png',
      path: '/projects/gpcr-screens/protein-structure-1.png'
    },
    {
      id: 'p2',
      name: 'molecular-complex-2.png',
      type: 'image',
      size: '1.8 MB',
      modified: '5 hours ago',
      thumbnail: '/lovable-uploads/3f9b94bc-09fc-4b4e-a377-91136ab61c92.png',
      path: '/projects/gpcr-screens/molecular-complex-2.png'
    },
    // All files from ESMFold subfolder
    {
      id: 'p3',
      name: 'protein-domains.png',
      type: 'image',
      size: '3.2 MB',
      modified: '1 day ago',
      thumbnail: '/lovable-uploads/d22ca358-5cfd-441a-9bb8-3c4007b837cd.png',
      path: '/projects/esmfold/protein-domains.png'
    },
    {
      id: 'p4',
      name: 'multi-chain-complex.png',
      type: 'image',
      size: '2.1 MB',
      modified: '2 days ago',
      thumbnail: '/lovable-uploads/bcecac76-55c5-4e58-a625-686c61fe264a.png',
      path: '/projects/esmfold/multi-chain-complex.png'
    },
    {
      id: 'p5',
      name: 'enzyme-structure.png',
      type: 'image',
      size: '1.9 MB',
      modified: '3 days ago',
      thumbnail: '/lovable-uploads/cb1ec19f-a8a2-4eb2-aae8-cf632f24cf6c.png',
      path: '/projects/esmfold/enzyme-structure.png'
    },
    {
      id: 'p6',
      name: 'membrane-protein.png',
      type: 'image',
      size: '4.1 MB',
      modified: '4 days ago',
      thumbnail: '/lovable-uploads/f9bcef82-8130-41df-95f9-bdeeb8f1f0cc.png',
      path: '/projects/esmfold/membrane-protein.png'
    },
    {
      id: 'p7',
      name: 'protein-assembly.png',
      type: 'image',
      size: '2.8 MB',
      modified: '5 days ago',
      thumbnail: '/lovable-uploads/c912a164-6290-4c77-b77a-d331c5289766.png',
      path: '/projects/esmfold/protein-assembly.png'
    },
    {
      id: 'p8',
      name: 'transmembrane-complex.png',
      type: 'image',
      size: '1.6 MB',
      modified: '1 week ago',
      thumbnail: '/lovable-uploads/05f27fae-4674-48f4-a387-28b927fdc83a.png',
      path: '/projects/esmfold/transmembrane-complex.png'
    }
  ],
  '/assets': [
    {
      id: 'a1',
      name: 'docking_site.jpeg',
      type: 'image',
      size: '1.2 MB',
      modified: '3 hours ago',
      path: '/assets/docking_site.jpeg'
    },
    {
      id: 'a2',
      name: 'SMILES_catalog.csv',
      type: 'document',
      size: '500 KB',
      modified: '1 day ago',
      path: '/assets/SMILES_catalog.csv'
    },
    {
      id: 'a3',
      name: 'lab_logo.png',
      type: 'image',
      size: '800 KB',
      modified: '2 days ago',
      path: '/assets/lab_logo.png'
    },
    {
      id: 'a4',
      name: 'GPCR_superfamily_results.csv',
      type: 'document',
      size: '2.1 MB',
      modified: '3 days ago',
      path: '/assets/GPCR_superfamily_results.csv'
    }
  ],
  '/projects/gpcr-screens': [
    {
      id: 'g1',
      name: 'protein-structure-1.png',
      type: 'image',
      size: '2.4 MB',
      modified: '2 hours ago',
      thumbnail: '/lovable-uploads/f5170632-c5f7-4903-bb3c-581d05ea59c5.png',
      path: '/projects/gpcr-screens/protein-structure-1.png'
    },
    {
      id: 'g2',
      name: 'molecular-complex-2.png',
      type: 'image',
      size: '1.8 MB',
      modified: '5 hours ago',
      thumbnail: '/lovable-uploads/3f9b94bc-09fc-4b4e-a377-91136ab61c92.png',
      path: '/projects/gpcr-screens/molecular-complex-2.png'
    }
  ],
  '/projects/esmfold': [
    {
      id: 'e1',
      name: 'protein-domains.png',
      type: 'image',
      size: '3.2 MB',
      modified: '1 day ago',
      thumbnail: '/lovable-uploads/d22ca358-5cfd-441a-9bb8-3c4007b837cd.png',
      path: '/projects/esmfold/protein-domains.png'
    },
    {
      id: 'e2',
      name: 'multi-chain-complex.png',
      type: 'image',
      size: '2.1 MB',
      modified: '2 days ago',
      thumbnail: '/lovable-uploads/bcecac76-55c5-4e58-a625-686c61fe264a.png',
      path: '/projects/esmfold/multi-chain-complex.png'
    },
    {
      id: 'e3',
      name: 'enzyme-structure.png',
      type: 'image',
      size: '1.9 MB',
      modified: '3 days ago',
      thumbnail: '/lovable-uploads/cb1ec19f-a8a2-4eb2-aae8-cf632f24cf6c.png',
      path: '/projects/esmfold/enzyme-structure.png'
    },
    {
      id: 'e4',
      name: 'membrane-protein.png',
      type: 'image',
      size: '4.1 MB',
      modified: '4 days ago',
      thumbnail: '/lovable-uploads/f9bcef82-8130-41df-95f9-bdeeb8f1f0cc.png',
      path: '/projects/esmfold/membrane-protein.png'
    },
    {
      id: 'e5',
      name: 'protein-assembly.png',
      type: 'image',
      size: '2.8 MB',
      modified: '5 days ago',
      thumbnail: '/lovable-uploads/c912a164-6290-4c77-b77a-d331c5289766.png',
      path: '/projects/esmfold/protein-assembly.png'
    },
    {
      id: 'e6',
      name: 'transmembrane-complex.png',
      type: 'image',
      size: '1.6 MB',
      modified: '1 week ago',
      thumbnail: '/lovable-uploads/05f27fae-4674-48f4-a387-28b927fdc83a.png',
      path: '/projects/esmfold/transmembrane-complex.png'
    }
  ],
  '/recent': [], // Will be populated dynamically
  '/archive': [],
  '/archive/2023': [],
  '/archive/2024': []
};

const getFileIcon = (type: string, fileName?: string, isSelected: boolean = false) => {
  const baseClasses = "h-8 w-8 drop-shadow-sm transition-all duration-200";
  const iconColor = '#56E7A4';
  const jobIconColor = '#FFA500';
  
  switch (type) {
    case 'folder':
      return <Folder className={`${baseClasses}`} style={{ color: iconColor }} />;
    case 'job':
      return <FileText className={`${baseClasses} ${isSelected ? 'transform rotate-1' : ''}`} style={{ color: jobIconColor }} />;
    case 'image':
      // All files now look like documents
      return <FileText className={`${baseClasses} ${isSelected ? 'transform rotate-1' : ''}`} style={{ color: iconColor }} />;
    case 'document':
      return <FileText className={`${baseClasses} ${isSelected ? 'transform rotate-1' : ''}`} style={{ color: iconColor }} />;
    default:
      return <FileText className={`${baseClasses} hover:text-white transition-colors ${isSelected ? 'transform rotate-1' : ''}`} style={{ color: iconColor }} />;
  }
};

export const FileGrid: React.FC<FileGridProps> = ({
  path,
  organization,
  searchQuery,
  viewMode,
  selectedFile,
  onFileSelect
}) => {
  const navigate = useNavigate();
  const [allFiles, setAllFiles] = useState<{ [key: string]: FileItem[] }>(staticFiles);
  const [loading, setLoading] = useState(false);

  // Fetch recent jobs when path is /recent
  useEffect(() => {
    if (path === '/recent') {
      const fetchRecentJobs = async () => {
        try {
          setLoading(true);
          const response = await jobService.getJobs(1, 10);
          const recentJobs = response.jobs
            .filter(job => job.status === 'completed')
            .slice(0, 8) // Limit to 8 most recent for grid display
            .map(job => ({
              id: job.id,
              name: jobService.formatJobName(job),
              type: 'job' as const,
              size: 'Job Result',
              modified: new Date(job.completed_at || job.created_at).toLocaleDateString(),
              path: `/recent/${job.id}`,
              jobId: job.id,
              job: job
            }));

          setAllFiles(prev => ({
            ...prev,
            '/recent': recentJobs
          }));
        } catch (error) {
          console.error('Failed to fetch recent jobs:', error);
        } finally {
          setLoading(false);
        }
      };

      fetchRecentJobs();
    }
  }, [path]);

  // Get files for the current path
  const currentFiles = allFiles[path] || [];
  
  const filteredFiles = currentFiles.filter(file =>
    file.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleFileClick = (file: FileItem) => {
    // Handle recent job navigation
    if (file.jobId && file.job) {
      navigate(`/boltz2/job/${file.jobId}`, { state: { job: file.job } });
      return;
    }

    // If clicking the same file that's already selected, deselect it
    if (selectedFile?.id === file.id) {
      onFileSelect(null);
    } else {
      onFileSelect(file);
    }
  };

  if (loading && path === '/recent') {
    return (
      <Card className="bg-gray-800 border-gray-700 h-full flex flex-col shadow-xl">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading recent jobs...</p>
          </div>
        </div>
      </Card>
    );
  }

  if (viewMode === 'grid') {
    return (
      <Card className="bg-gray-800 border-gray-700 h-full flex flex-col shadow-xl">
        <ScrollArea className="flex-1">
          <div className="p-4">
            {filteredFiles.length === 0 && path === '/recent' ? (
              <div className="text-center text-gray-400 py-8">
                <p>No recent completed jobs found.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredFiles.map((file) => {
                const isSelected = selectedFile?.id === file.id;
                return (
                  <TooltipProvider key={file.id}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div
                          className={`cursor-pointer rounded-lg border-2 transition-all duration-200 hover:border-[#E2E756]/50 hover:scale-[1.02] hover:shadow-lg relative ${
                            isSelected
                              ? 'border-[#E2E756] bg-[#E2E756]/10 shadow-lg scale-[1.02]'
                              : 'border-gray-700 bg-gray-900 hover:bg-gray-800'
                          }`}
                          onClick={() => handleFileClick(file)}
                        >
                          {/* Folded corner effect for selected files */}
                          {isSelected && (
                            <div className="absolute top-0 right-0 w-0 h-0 border-l-[20px] border-l-transparent border-t-[20px] border-t-[#E2E756] rounded-tr-lg"></div>
                          )}
                          
                          <div className="p-3">
                            {file.thumbnail ? (
                              <div className="aspect-square rounded-md overflow-hidden mb-3 group relative">
                                <img
                                  src={file.thumbnail}
                                  alt={file.name}
                                  className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-110"
                                />
                              </div>
                            ) : (
                              <div className="aspect-square rounded-md bg-gray-700 flex items-center justify-center mb-3 transition-all duration-200 hover:bg-gray-600">
                                <div className="transition-transform duration-200 hover:scale-110">
                                  {getFileIcon(file.type, file.name, isSelected)}
                                </div>
                              </div>
                            )}
                            <div>
                              <p className="text-white text-sm font-medium truncate transition-colors hover:text-[#E2E756]" title={file.name}>
                                {file.name}
                              </p>
                              <p className="text-gray-400 text-xs mt-1">
                                {file.size} • {file.modified}
                              </p>
                            </div>
                          </div>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{file.name}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                );
              })}
              </div>
            )}
          </div>
        </ScrollArea>
      </Card>
    );
  }

  return (
    <Card className="bg-gray-800 border-gray-700 h-full flex flex-col shadow-xl">
      <ScrollArea className="flex-1">
        <div className="p-4">
          <div className="space-y-2">
            {filteredFiles.map((file) => {
              const isSelected = selectedFile?.id === file.id;
              return (
                <TooltipProvider key={file.id}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        className={`flex items-center p-3 rounded-lg cursor-pointer transition-all duration-200 hover:bg-gray-700/50 hover:scale-[1.01] relative ${
                          isSelected ? 'bg-[#E2E756]/20 shadow-md' : 'hover:shadow-sm'
                        }`}
                        onClick={() => handleFileClick(file)}
                      >
                        {/* Folded corner effect for selected files */}
                        {isSelected && (
                          <div className="absolute top-0 right-0 w-0 h-0 border-l-[15px] border-l-transparent border-t-[15px] border-t-[#E2E756] rounded-tr-lg"></div>
                        )}
                        
                        <div className="mr-3 transition-transform duration-200 hover:scale-110">
                          {file.thumbnail ? (
                            <img
                              src={file.thumbnail}
                              alt={file.name}
                              className="w-12 h-12 rounded object-cover shadow-sm"
                            />
                          ) : (
                            getFileIcon(file.type, file.name, isSelected)
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-white font-medium truncate transition-colors hover:text-[#E2E756]">{file.name}</p>
                          <p className="text-gray-400 text-sm">{file.modified}</p>
                        </div>
                        <div className="text-gray-400 text-sm font-mono">
                          {file.size}
                        </div>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{file.name}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              );
            })}
          </div>
        </div>
      </ScrollArea>
    </Card>
  );
};
