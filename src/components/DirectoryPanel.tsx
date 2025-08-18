import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Folder, FolderOpen, ChevronRight, ChevronDown, HardDrive, FileText, Clock } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { jobService } from '@/services/jobService';

interface DirectoryItem {
  name: string;
  type: 'folder' | 'file';
  path: string;
  children?: DirectoryItem[];
  expanded?: boolean;
  isRoot?: boolean;
  files?: string[];
  jobId?: string;
  job?: any;
}

interface DirectoryPanelProps {
  selectedPath: string;
  onPathSelect: (path: string) => void;
  organization: string;
  searchQuery: string;
}

const mockDirectoryStructure: DirectoryItem[] = [
  {
    name: 'Recent',
    type: 'folder',
    path: '/recent',
    isRoot: true,
    children: []
  },
  {
    name: 'Projects',
    type: 'folder',
    path: '/projects',
    isRoot: true,
    children: [
      {
        name: 'GPCR Screens',
        type: 'folder',
        path: '/projects/gpcr-screens',
        files: ['protein-structure-1.png', 'molecular-complex-2.png']
      },
      {
        name: 'ESMFold',
        type: 'folder',
        path: '/projects/esmfold',
        files: [
          'protein-domains.png',
          'multi-chain-complex.png',
          'enzyme-structure.png',
          'membrane-protein.png',
          'protein-assembly.png',
          'transmembrane-complex.png'
        ]
      }
    ]
  },
  {
    name: 'Assets',
    type: 'folder',
    path: '/assets',
    isRoot: true,
    children: [
      {
        name: 'docking_site.jpeg',
        type: 'file',
        path: '/assets/docking_site.jpeg'
      },
      {
        name: 'SMILES_catalog.csv',
        type: 'file',
        path: '/assets/SMILES_catalog.csv'
      },
      {
        name: 'lab_logo.png',
        type: 'file',
        path: '/assets/lab_logo.png'
      },
      {
        name: 'GPCR_superfamily_results.csv',
        type: 'file',
        path: '/assets/GPCR_superfamily_results.csv'
      }
    ]
  },
  {
    name: 'Archive',
    type: 'folder',
    path: '/archive',
    isRoot: true,
    children: [
      { name: '2023', type: 'folder', path: '/archive/2023' },
      { name: '2024', type: 'folder', path: '/archive/2024' }
    ]
  }
];

export const DirectoryPanel: React.FC<DirectoryPanelProps> = ({
  selectedPath,
  onPathSelect,
  organization,
  searchQuery
}) => {
  const navigate = useNavigate();
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['/']));
  const [directoryStructure, setDirectoryStructure] = useState<DirectoryItem[]>(mockDirectoryStructure);
  const [recentJobsLoading, setRecentJobsLoading] = useState(false);

  // Fetch recent jobs to populate Recent folder
  useEffect(() => {
    const fetchRecentJobs = async () => {
      try {
        setRecentJobsLoading(true);
        const response = await jobService.getJobs(1, 10); // Get last 10 jobs
        const recentJobs = response.jobs
          .filter(job => job.status === 'completed')
          .slice(0, 5) // Limit to 5 most recent
          .map(job => ({
            name: jobService.formatJobName(job),
            type: 'file' as const,
            path: `/recent/${job.id}`,
            jobId: job.id,
            job: job
          }));

        setDirectoryStructure(prev => 
          prev.map(item => 
            item.path === '/recent' 
              ? { ...item, children: recentJobs }
              : item
          )
        );
      } catch (error) {
        console.error('Failed to fetch recent jobs:', error);
      } finally {
        setRecentJobsLoading(false);
      }
    };

    fetchRecentJobs();
  }, []);

  const toggleFolder = (path: string) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedFolders(newExpanded);
  };

  const isLeafFolder = (item: DirectoryItem) => {
    return (!item.children || item.children.length === 0) && item.files && item.files.length > 0;
  };

  const handleItemClick = (item: DirectoryItem) => {
    // Handle recent job navigation
    if (item.jobId && item.job) {
      navigate(`/boltz2/job/${item.jobId}`, { state: { job: item.job } });
      return;
    }
    
    // Always select the path for file viewing
    onPathSelect(item.path);
    
    // For folders (not individual files), also handle expansion
    if (item.type === 'folder' && item.children && !isLeafFolder(item)) {
      toggleFolder(item.path);
    }
  };

  const getFolderIcon = (item: DirectoryItem, isExpanded: boolean) => {
    // Special case for Recent folder
    if (item.path === '/recent' && item.type === 'folder') {
      return isExpanded ? (
        <FolderOpen className="h-4 w-4 drop-shadow-sm" style={{ color: '#56E7A4' }} />
      ) : (
        <Clock className="h-4 w-4 drop-shadow-sm" style={{ color: '#56E7A4' }} />
      );
    }
    
    // Special case for recent job items
    if (item.jobId && item.job) {
      return <FileText className="h-4 w-4 drop-shadow-sm" style={{ color: '#FFA500' }} />;
    }
    
    // Special case for lab_logo.png - show the uploaded image
    if (item.type === 'file' && item.name === 'lab_logo.png') {
      return (
        <img 
          src="/lovable-uploads/37d64e18-5b50-49bc-8903-4b1c894d4613.png" 
          alt="Lab Logo" 
          className="h-4 w-4 drop-shadow-sm rounded-sm object-contain"
        />
      );
    }
    
    // Files get document icon
    if (item.type === 'file') {
      return <FileText className="h-4 w-4 drop-shadow-sm" style={{ color: '#56E7A4' }} />;
    }
    
    // Leaf folders (no children but has files) are displayed as documents
    if (isLeafFolder(item)) {
      return <FileText className="h-4 w-4 drop-shadow-sm" style={{ color: '#56E7A4' }} />;
    }
    
    // Regular folders use folder/folder-open icons
    return isExpanded ? (
      <FolderOpen className="h-4 w-4 drop-shadow-sm" style={{ color: '#56E7A4' }} />
    ) : (
      <Folder className="h-4 w-4 drop-shadow-sm" style={{ color: '#56E7A4' }} />
    );
  };

  const renderDirectoryItem = (item: DirectoryItem, depth: number = 0) => {
    const isExpanded = expandedFolders.has(item.path);
    const isSelected = selectedPath === item.path;
    const hasChildren = item.children && item.children.length > 0;
    const isLeaf = isLeafFolder(item);
    const isFile = item.type === 'file';

    // Filter based on search query
    if (searchQuery && !item.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return null;
    }

    return (
      <div key={item.path}>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div
                className={`flex items-center py-1.5 px-3 cursor-pointer hover:bg-gray-700/50 rounded-md transition-all duration-200 hover:scale-[1.02] relative ${
                  isSelected ? 'bg-[#E2E756]/20 text-[#E2E756] shadow-md' : 'text-gray-300'
                } ${item.isRoot ? 'font-semibold' : ''}`}
                style={{ paddingLeft: `${depth * 20 + 12}px` }}
                onClick={() => handleItemClick(item)}
              >
                {/* Folded corner effect for selected leaf folders and files */}
                {(isLeaf || isFile) && isSelected && (
                  <div className="absolute top-0 right-0 w-0 h-0 border-l-[12px] border-l-transparent border-t-[12px] border-t-[#E2E756] rounded-tr-md"></div>
                )}
                
                {hasChildren && !isLeaf && !isFile && (
                  <div className="mr-2 transition-transform duration-200">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-gray-400" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-gray-400" />
                    )}
                  </div>
                )}
                <div className="mr-3 transition-transform duration-200 hover:scale-110">
                  {getFolderIcon(item, isExpanded)}
                </div>
                <span className={`text-sm ${item.isRoot ? 'font-bold' : 'font-medium'} truncate`}>
                  {item.name}
                </span>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>{item.name}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
        
        {isExpanded && hasChildren && !isLeaf && !isFile && (
          <div className="animate-accordion-down">
            {item.children?.map(child => renderDirectoryItem(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <Card className="bg-gray-800 border-gray-700 h-full flex flex-col shadow-xl">
      <div className="p-4 flex-shrink-0 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-3">Directory</h3>
        
        {/* Root */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div
                className={`flex items-center py-2 px-3 cursor-pointer hover:bg-gray-700/50 rounded-md transition-all duration-200 hover:scale-[1.02] ${
                  selectedPath === '/' ? 'bg-[#E2E756]/20 text-[#E2E756] shadow-md' : 'text-gray-300'
                }`}
                onClick={() => onPathSelect('/')}
              >
                <div className="mr-3 transition-transform duration-200 hover:scale-110">
                  <HardDrive className="h-5 w-5 drop-shadow-sm" style={{ color: '#56E7A4' }} />
                </div>
                <span className="text-sm font-bold">Root</span>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>Root</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Scrollable Directory Tree */}
      <div className="flex-1 px-4 pb-4 min-h-0">
        <ScrollArea className="h-full">
          <div className="space-y-0.5 pr-3 py-1">
            {directoryStructure.map(item => renderDirectoryItem(item))}
          </div>
        </ScrollArea>
      </div>
    </Card>
  );
};
