import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { StructureViewer } from './StructureViewer';
import { ExpandedViewer } from './ExpandedViewer';

import { 
  downloadCifFile, 
  extractCifContent,
  generateTimestampedFilename,
  validateStructureContent
} from '@/utils/fileConverters';

import { 
  FileText, 
  Download, 
  RotateCcw, 
  ZoomIn, 
  ZoomOut, 
  Loader2, 
  CheckCircle, 
  AlertCircle, 
  Info,
  Activity,
  BarChart3,
  TrendingUp,
  Target,
  Users,
  Dna,
  Microscope,
  FileDown,
  Calendar,
  Settings,
  Database,
  Eye,
  Star,
  ArrowDown,
  Terminal,
  Clock,
  Zap,
  Layers
} from 'lucide-react';

// Helper function to format execution time with clear units
const formatExecutionTime = (seconds: number): string => {
  if (!seconds || seconds <= 0) return 'N/A';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  
  const parts = [];
  
  if (hours > 0) {
    parts.push(`${hours}h`);
  }
  if (minutes > 0) {
    parts.push(`${minutes}m`);
  }
  if (remainingSeconds > 0 || parts.length === 0) {
    parts.push(`${remainingSeconds}s`);
  }
  
  return parts.join(' ');
};

interface PredictionResult {
  job_id: string;
  status: string;
  task_type?: string;
  message?: string;
  designs?: Array<{
    sequence: string;
    score: number;
    rank: number;
    framework?: string;
  }>;
  target_info?: {
    pdb_name: string;
    target_chain: string;
    hotspot_residues: string[];
  };
  design_parameters?: {
    num_designs: number;
    framework: string;
  };
  structure_file_content?: string;
  structure_file_base64?: string;
  structure_files?: {
    primary_structure?: {
      filename?: string;
      content?: string;
      base64?: string;
      type?: string;
    };
  };
  execution_time?: number;
  prediction_id?: string;
  parameters?: {
    model?: string;
    gpu_used?: string;
    use_msa_server?: boolean;
    use_potentials?: boolean;
    diffusion_samples?: number;
    recycling_steps?: number;
  };
  modal_logs?: Array<{
    timestamp: string;
    level: string;
    message: string;
    source: string;
  }>;
  error?: string;
}

interface OutputSectionProps {
  result: PredictionResult | null;
  isLoading: boolean;
  selectedTask?: string;
  isInputCollapsed?: boolean;
  onInputCollapseChange?: (collapsed: boolean) => void;
}

// Enhanced utility functions for downloads
const downloadCIF = async (result: PredictionResult) => {
  try {
    // Try to download from unified API first
    const response = await fetch(`/api/v2/jobs/${result.job_id}/download/cif`);
    
    if (response.ok) {
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `rfantibody_prediction_${result.job_id}.cif`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      return;
    }
  } catch (error) {
    console.warn('Failed to download from unified API, falling back to direct content:', error);
  }
  
  // Fallback to direct content extraction
  const cifContent = result.structure_file_content || 
    (result.structure_file_base64 ? atob(result.structure_file_base64) : null) ||
    result.structure_files?.primary_structure?.content ||
    (result.structure_files?.primary_structure?.base64 ? atob(result.structure_files.primary_structure.base64) : null);
  
  if (!cifContent) {
    alert('No structure data available for download');
    return;
  }
  
  const blob = new Blob([cifContent], { type: 'chemical/x-cif' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `rfantibody_prediction_${result.job_id}.cif`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

// Responsive tile component
const MetricTile: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
  icon?: React.ReactNode;
}> = ({ title, value, subtitle, color = 'text-white', icon }) => (
  <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 flex-1 min-w-0">
    <div className="flex items-center justify-between mb-2">
      <div className="flex items-center space-x-2">
        {icon && <div className="text-blue-400">{icon}</div>}
        <h3 className="text-sm font-medium text-gray-400 truncate">{title}</h3>
      </div>
    </div>
    <div className={`text-2xl font-bold ${color} truncate`}>
      {typeof value === 'number' ? value.toFixed(3) : value}
    </div>
    {subtitle && (
      <p className="text-xs text-gray-500 mt-1 truncate">{subtitle}</p>
    )}
  </div>
);

// RFAntibody output component for nanobody design
const NanobodyDesignOutput: React.FC<{ result: PredictionResult }> = ({ result }) => {
  const [selectedTab, setSelectedTab] = useState('overview');
  
  // Structure viewer state
  const [expandedViewer, setExpandedViewer] = useState(false);
  const [cifContent, setCifContent] = useState<string | null>(null);
  
  // Extract CIF content when result changes
  useEffect(() => {
    if (result) {
      const extractedCif = extractCifContent(result);
      setCifContent(extractedCif);
    } else {
      setCifContent(null);
    }
  }, [result]);

  // Mock PDB content for testing (remove this in production)
  const mockPdbContent = `HEADER    NANOBODY DESIGN                         01-JAN-23   RFAB            
REMARK   1 REFERENCE                                                          
REMARK   1  AUTH   RFANTIBODY                                                 
REMARK   1  TITL   NANOBODY DESIGN PREDICTION                                 
ATOM      1  N   VAL A   1      -1.000   0.000   0.000  1.00 20.00           N  
ATOM      2  CA  VAL A   1       0.000   0.000   0.000  1.00 20.00           C  
ATOM      3  C   VAL A   1       1.000   0.000   0.000  1.00 20.00           C  
ATOM      4  O   VAL A   1      -1.500   1.000   0.000  1.00 20.00           O  
ATOM      5  CB  VAL A   1       0.000   0.000   1.000  1.00 20.00           C  
HELIX    1   1 VAL A    1  VAL A   10  1                                  10    
SHEET    1   A 2 GLY A  15  LEU A  20  0                                        
CONECT    1    2                                                              
CONECT    2    1    3                                                         
CONECT    3    2    4                                                         
CONECT    4    3                                                              
END                                                                           
`;

  // Use mock content if no real content is available (for testing)
  const effectiveCifContent = cifContent || mockPdbContent;
  
  // Determine viewer state
  const viewerState = (() => {
    if (result?.error) return 'error';
    if (!result) return 'pre-run';
    if (result.status === 'Running') return 'loading';
    if (cifContent) return 'loaded';
    if (effectiveCifContent) return 'loaded'; // Using mock content
    return 'empty';
  })();
  
  // Handle CIF download
  const handleDownloadCif = useCallback(() => {
    if (effectiveCifContent) {
      const filename = generateTimestampedFilename('nanobody_design', 'cif');
      downloadCifFile(effectiveCifContent, filename);
    }
  }, [effectiveCifContent]);

  return (
    <div className="h-full w-full flex flex-col">
      {/* Download Bar */}
      <div className="flex justify-between items-center gap-4 mb-6 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
        <div className="flex items-center gap-2">
          <CheckCircle className="h-5 w-5 text-green-400" />
          <span className="text-white font-medium">Nanobody Design Complete</span>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={async () => await downloadCIF(result)}
            className="bg-blue-600 hover:bg-blue-700 text-white"
            size="sm"
          >
            <Download className="h-4 w-4 mr-2" />
            Download Structure
          </Button>
        </div>
      </div>

      <Tabs value={selectedTab} onValueChange={setSelectedTab} className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-4 bg-gray-800/50 border border-gray-700 flex-shrink-0">
          <TabsTrigger value="overview" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Overview
          </TabsTrigger>
          <TabsTrigger value="designs" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Designs
          </TabsTrigger>
          <TabsTrigger value="structure" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Structure
          </TabsTrigger>
          <TabsTrigger value="logs" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Logs
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="flex-1 mt-6 overflow-auto">
          <div className="space-y-6 h-full overflow-y-auto pb-16">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <MetricTile
                title="Job ID"
                value={result.job_id.split('-')[0]}
                subtitle="Click to copy full ID"
                icon={<Database className="h-4 w-4" />}
              />
              <MetricTile
                title="Status"
                value={result.status}
                subtitle="Execution complete"
                color="text-green-400"
                icon={<CheckCircle className="h-4 w-4" />}
              />
              <MetricTile
                title="Execution Time"
                value={result.execution_time ? formatExecutionTime(result.execution_time) : 'N/A'}
                subtitle="Processing duration"
                icon={<Clock className="h-4 w-4" />}
              />
              <MetricTile
                title="Framework"
                value={result.design_parameters?.framework || 'VHH'}
                subtitle="Nanobody framework used"
                icon={<Dna className="h-4 w-4" />}
              />
            </div>

            {/* Target Information */}
            {result.target_info && (
              <Card className="bg-gray-800/50 border-gray-700">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-white">
                    <Target className="h-5 w-5 text-purple-400" />
                    Target Information
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <MetricTile
                      title="Target PDB"
                      value={result.target_info.pdb_name}
                      subtitle="Input structure"
                    />
                    <MetricTile
                      title="Target Chain"
                      value={result.target_info.target_chain}
                      subtitle="Selected chain"
                    />
                    <MetricTile
                      title="Hotspot Residues"
                      value={result.target_info.hotspot_residues?.length || 0}
                      subtitle="Targeted epitope sites"
                    />
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Message */}
            {result.message && (
              <Alert className="bg-blue-900/20 border-blue-700">
                <Info className="h-4 w-4" />
                <AlertDescription className="text-blue-200">
                  {result.message}
                </AlertDescription>
              </Alert>
            )}
          </div>
        </TabsContent>

        <TabsContent value="designs" className="flex-1 mt-6 overflow-auto">
          <div className="space-y-6 h-full overflow-y-auto pb-16">
            {/* Design Results */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Star className="h-5 w-5 text-yellow-400" />
                  Generated Nanobody Designs
                </CardTitle>
              </CardHeader>
              <CardContent>
                {result.designs && result.designs.length > 0 ? (
                  <div className="space-y-4">
                    {result.designs.map((design, index) => (
                      <div key={index} className="bg-gray-900/50 border border-gray-700 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="bg-blue-600">
                              Rank #{design.rank || index + 1}
                            </Badge>
                            <span className="text-white font-medium">
                              Design {index + 1}
                            </span>
                          </div>
                          <div className="text-sm text-yellow-400 font-medium">
                            Score: {design.score?.toFixed(3) || 'N/A'}
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div>
                            <label className="text-xs text-gray-400">Sequence</label>
                            <div className="bg-gray-800 rounded p-2 font-mono text-sm text-gray-200 break-all">
                              {design.sequence}
                            </div>
                          </div>
                          {design.framework && (
                            <div className="text-xs text-gray-400">
                              Framework: {design.framework}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    No design sequences available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="structure" className="flex-1 mt-6 overflow-auto">
          <div className="space-y-6 h-full overflow-y-auto pb-16">
            {/* Structure Information */}
            <Card className="bg-gray-800/50 border-gray-700 min-h-[700px] w-[108%] -mx-[4%]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Microscope className="h-5 w-5 text-purple-400" />
                  3D Structure Visualization
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Structure Stats */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <MetricTile
                      title="Design Count"
                      value={result.designs?.length || 0}
                      subtitle="Generated nanobodies"
                      icon={<Layers className="h-4 w-4" />}
                    />
                    {result.structure_file_content && (
                      <MetricTile
                        title="Structure File Size"
                        value={`${(result.structure_file_content.length / 1024).toFixed(1)}KB`}
                        subtitle="Coordinate data size"
                        icon={<FileText className="h-4 w-4" />}
                      />
                    )}
                    <MetricTile
                      title="Format"
                      value="CIF/PDB"
                      subtitle="Standard structure formats"
                      icon={<Database className="h-4 w-4" />}
                    />
                  </div>
                  
                  {/* Structure Viewer */}
                  <StructureViewer
                    cifContent={effectiveCifContent}
                    state={viewerState}
                    onDownloadCif={handleDownloadCif}
                    onExpand={() => setExpandedViewer(true)}
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="logs" className="flex-1 mt-6 overflow-auto">
          <div className="space-y-6 h-full overflow-y-auto pb-16">
            {/* Modal Logs */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Terminal className="h-5 w-5 text-orange-400" />
                  RFAntibody Execution Logs
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {result.modal_logs && result.modal_logs.length > 0 ? (
                    <div className="bg-gray-900 p-4 rounded-lg">
                      <h4 className="text-sm font-medium text-white mb-2">Modal Execution Logs</h4>
                      <div className="max-h-96 overflow-auto">
                        {result.modal_logs.map((log, index) => (
                          <div key={index} className="mb-2 text-sm">
                            <span className="text-gray-500">[{log.timestamp}]</span>
                            <span className={`ml-2 font-medium ${
                              log.level === 'ERROR' ? 'text-red-400' :
                              log.level === 'WARNING' ? 'text-yellow-400' :
                              log.level === 'INFO' ? 'text-blue-400' :
                              'text-gray-300'
                            }`}>
                              {log.level}:
                            </span>
                            <span className="ml-2 text-gray-300">{log.message}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gray-900 p-4 rounded-lg">
                      <h4 className="text-sm font-medium text-white mb-2">RFAntibody Output</h4>
                      <div className="max-h-96 overflow-auto">
                        <pre className="text-sm text-gray-300 whitespace-pre-wrap">
                          No execution logs available
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Expanded Viewer Modal */}
      {expandedViewer && (
        <ExpandedViewer
          cifContent={effectiveCifContent}
          state={viewerState}
          onClose={() => setExpandedViewer(false)}
          onDownloadCif={handleDownloadCif}
        />
      )}
    </div>
  );
};

export const OutputSection: React.FC<OutputSectionProps> = ({ 
  result, 
  isLoading, 
  selectedTask = 'nanobody_design' 
}) => {
  return (
    <div className="h-full w-full flex flex-col">
      {isLoading && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <Loader2 className="h-12 w-12 animate-spin text-blue-500 mx-auto mb-6" />
            <p className="text-lg font-medium text-gray-400 mb-2">
              Running {selectedTask.replace('_', ' ')} prediction...
            </p>
            <p className="text-sm text-gray-500 leading-relaxed">This may take 10-20 minutes</p>
          </div>
        </div>
      )}

      {!isLoading && !result && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <FileText className="h-20 w-20 text-gray-600 mx-auto mb-6" />
            <p className="text-lg font-medium text-gray-400 mb-2">No prediction results yet</p>
            <p className="text-sm text-gray-500 leading-relaxed">
              Submit a nanobody design prediction to see results here
            </p>
          </div>
        </div>
      )}

      {result && (
        <div className="flex-1 overflow-hidden flex flex-col">
          {result.error ? (
            <Card className="bg-red-950 border-red-800 flex-1 m-4">
              <CardContent className="p-6">
                <div className="flex items-center gap-2 mb-4">
                  <AlertCircle className="h-5 w-5 text-red-400" />
                  <h3 className="text-lg font-semibold text-red-400">Prediction Error</h3>
                </div>
                <p className="text-red-300">{result.error}</p>
              </CardContent>
            </Card>
          ) : (
            <div className="flex-1 overflow-hidden p-4">
              {selectedTask === 'nanobody_design' ? (
                <NanobodyDesignOutput result={result} />
              ) : (
                <div className="text-center py-8 text-gray-400">
                  Output view for {selectedTask.replace('_', ' ')} not implemented yet
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};