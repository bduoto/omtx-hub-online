import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { StructureViewer } from './StructureViewer';
import { ExpandedViewer } from './ExpandedViewer';
import { BatchResultsOutput } from './BatchResultsOutput';
import { BatchProteinLigandOutput } from './BatchProteinLigandOutput';

import { 
  downloadCifFile, 
  extractCifContent,
  generateTimestampedFilename,
  validateStructureContent
} from '@/utils/fileConverters';

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

interface PredictionResult {
  job_id: string;
  status: string;
  task_type?: string;
  message?: string;
  affinity?: number;
  affinity_probability?: number;
  affinity_ensemble?: {
    affinity_pred_value?: number;
    affinity_probability_binary?: number;
    affinity_pred_value1?: number;
    affinity_probability_binary1?: number;
    affinity_pred_value2?: number;
    affinity_probability_binary2?: number;
  };
  confidence?: number;
  confidence_metrics?: {
    confidence_score?: number;
    ptm?: number;
    iptm?: number;
    ligand_iptm?: number;
    protein_iptm?: number;
    complex_plddt?: number;
    complex_iplddt?: number;
    complex_pde?: number;
    complex_ipde?: number;
    chains_ptm?: Record<string, number>;
    pair_chains_iptm?: Record<string, Record<string, number>>;
  };
  ptm_score?: number;
  iptm_score?: number;
  plddt_score?: number;
  ligand_iptm_score?: number;
  protein_iptm_score?: number;
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
  all_structures?: Array<{
    model_id: number;
    confidence?: number;
    content?: string;
    base64?: string;
    rank?: number;
  }>;
  structure_count?: number;
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
  boltz_output?: string;
  boltz_error?: string;
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
    const jobId = result.job_id || result.id;
    if (!jobId) {
      throw new Error('No job ID available for download');
    }
    const response = await fetch(`/api/v2/jobs/${jobId}/download/cif`);
    
    if (response.ok) {
      // Use the unified API download endpoint
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `boltz2_prediction_${jobId}.cif`;
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
    alert('No CIF structure data available for download');
    return;
  }
  
  const blob = new Blob([cifContent], { type: 'chemical/x-cif' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const jobId = result.job_id || result.id || 'unknown';
  a.download = `boltz2_prediction_${jobId}.cif`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const generatePDFReport = async (result: PredictionResult) => {
  try {
    // Import jsPDF dynamically
    const { jsPDF } = await import('jspdf');
    
    const doc = new jsPDF();
    let yPosition = 20;
    
    // Title Page
    doc.setFontSize(24);
    const reportTitle = result.task_type === 'protein_structure' 
      ? 'Boltz-2 Structure Prediction Report' 
      : 'Boltz-2 Prediction Report';
    doc.text(reportTitle, 20, yPosition);
    yPosition += 15;
    
    doc.setFontSize(12);
    doc.text(`Generated on ${new Date().toLocaleDateString()}`, 20, yPosition);
    yPosition += 10;
    doc.text(`Job ID: ${result.job_id || result.id || 'Unknown'}`, 20, yPosition);
    yPosition += 10;
    if (result.task_type) {
      doc.text(`Task Type: ${result.task_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}`, 20, yPosition);
      yPosition += 10;
    }
    yPosition += 10;
    
    // Overview Section
    doc.setFontSize(18);
    doc.text('1. Overview', 20, yPosition);
    yPosition += 15;
    
    doc.setFontSize(12);
    doc.text(`Status: ${result.status || 'Unknown'}`, 25, yPosition);
    yPosition += 8;
    if (result.execution_time) {
      doc.text(`Execution Time: ${formatExecutionTime(result.execution_time)}`, 25, yPosition);
      yPosition += 8;
    }
    if (result.message) {
      doc.text(`Message: ${result.message}`, 25, yPosition);
      yPosition += 8;
    }
    yPosition += 10;
    
    // Affinity Section (only for protein-ligand binding)
    if (result.affinity !== undefined && result.task_type === 'protein_ligand_binding') {
      doc.setFontSize(18);
      doc.text('2. Binding Affinity Analysis', 20, yPosition);
      yPosition += 15;
      
      doc.setFontSize(12);
      doc.text(`Primary Affinity Score: ${result.affinity.toFixed(4)}`, 25, yPosition);
      yPosition += 8;
      
      if (result.affinity_probability) {
        doc.text(`Binding Probability: ${(result.affinity_probability * 100).toFixed(1)}%`, 25, yPosition);
        yPosition += 8;
      }
      
      if (result.affinity_ensemble) {
        doc.text('Ensemble Results:', 25, yPosition);
        yPosition += 8;
        
        const ensemble = result.affinity_ensemble;
        if (ensemble.affinity_pred_value !== undefined) {
          doc.text(`  Ensemble Prediction: ${ensemble.affinity_pred_value.toFixed(4)}`, 30, yPosition);
          yPosition += 6;
        }
        if (ensemble.affinity_pred_value1 !== undefined) {
          doc.text(`  Model 1: ${ensemble.affinity_pred_value1.toFixed(4)}`, 30, yPosition);
          yPosition += 6;
        }
        if (ensemble.affinity_pred_value2 !== undefined) {
          doc.text(`  Model 2: ${ensemble.affinity_pred_value2.toFixed(4)}`, 30, yPosition);
          yPosition += 6;
        }
      }
      yPosition += 10;
    }
    
    // Confidence Section
    doc.setFontSize(18);
    const confidenceTitle = result.task_type === 'protein_structure' 
      ? `${result.affinity !== undefined ? '3' : '2'}. Structure Quality Metrics`
      : `${result.affinity !== undefined ? '3' : '2'}. Confidence Metrics`;
    doc.text(confidenceTitle, 20, yPosition);
    yPosition += 15;
    
    doc.setFontSize(12);
    const confidenceMetrics = [
      { label: 'Overall Confidence', value: result.confidence },
      { label: 'PTM Score', value: result.ptm_score },
      { label: 'pLDDT Score', value: result.plddt_score },
      { label: 'ipTM Score', value: result.iptm_score },
      { label: 'Ligand ipTM', value: result.ligand_iptm_score },
      { label: 'Protein ipTM', value: result.protein_iptm_score }
    ];
    
    confidenceMetrics.forEach(metric => {
      if (metric.value !== undefined) {
        doc.text(`${metric.label}: ${metric.value.toFixed(4)}`, 25, yPosition);
        yPosition += 8;
      }
    });
    yPosition += 10;
    
    // Structure Section
    doc.setFontSize(18);
    const structureTitle = result.task_type === 'protein_structure' 
      ? `${result.affinity !== undefined ? '4' : '3'}. 3D Structure Information`
      : `${result.affinity !== undefined ? '4' : '3'}. Structure Information`;
    doc.text(structureTitle, 20, yPosition);
    yPosition += 15;
    
    doc.setFontSize(12);
    if (result.structure_count) {
      doc.text(`Total Structures Generated: ${result.structure_count}`, 25, yPosition);
      yPosition += 8;
    }
    if (result.structure_file_content) {
      doc.text(`Primary Structure Size: ${result.structure_file_content.length.toLocaleString()} characters`, 25, yPosition);
      yPosition += 8;
    }
    yPosition += 10;
    
    // Parameters Section
    if (result.parameters) {
      doc.setFontSize(18);
      const parametersTitle = result.task_type === 'protein_structure' 
        ? `${result.affinity !== undefined ? '5' : '4'}. Structure Prediction Parameters`
        : `${result.affinity !== undefined ? '5' : '4'}. Prediction Parameters`;
      doc.text(parametersTitle, 20, yPosition);
      yPosition += 15;
      
      doc.setFontSize(12);
      Object.entries(result.parameters).forEach(([key, value]) => {
        const displayValue = typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value);
        doc.text(`${key.replace(/_/g, ' ')}: ${displayValue}`, 25, yPosition);
        yPosition += 8;
      });
      yPosition += 10;
    }
    
    // Add new page for logs if available
    if (result.modal_logs && result.modal_logs.length > 0) {
      doc.addPage();
      yPosition = 20;
      
      doc.setFontSize(18);
      const logsTitle = result.task_type === 'protein_structure' 
        ? `${result.affinity !== undefined ? '6' : '5'}. Structure Prediction Execution Logs`
        : `${result.affinity !== undefined ? '6' : '5'}. Execution Logs`;
      doc.text(logsTitle, 20, yPosition);
      yPosition += 15;
      
      doc.setFontSize(10);
      result.modal_logs.slice(0, 20).forEach(log => {
        const logLine = `[${log.timestamp}] ${log.level}: ${log.message}`;
        const lines = doc.splitTextToSize(logLine, 170);
        lines.forEach((line: string) => {
          if (yPosition > 280) {
            doc.addPage();
            yPosition = 20;
          }
          doc.text(line, 25, yPosition);
          yPosition += 6;
        });
      });
    }
    
    // Footer on all pages
    const pageCount = (doc as any).internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.text(`Page ${i} of ${pageCount}`, 20, 290);
      doc.text('Powered by Boltz-2 via OMTX Hub', 150, 290);
    }
    
    // Save the PDF
    const jobId = result.job_id || result.id || 'unknown';
    doc.save(`boltz2_prediction_report_${jobId}.pdf`);
    
  } catch (error) {
    console.error('Error generating PDF:', error);
    alert('Error generating PDF. Please try again.');
  }
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

// Enhanced tabbed output component for protein structure prediction
const ProteinStructureOutput: React.FC<{ 
  result: PredictionResult;
}> = ({ result }) => {
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
  const mockPdbContent = `HEADER    PROTEIN STRUCTURE                       01-JAN-23   TEST            
REMARK   1 REFERENCE                                                          
REMARK   1  AUTH   BOLTZ-2                                                    
REMARK   1  TITL   PROTEIN STRUCTURE PREDICTION                               
ATOM      1  N   MET A   1      -1.000   0.000   0.000  1.00 20.00           N  
ATOM      2  CA  MET A   1       0.000   0.000   0.000  1.00 20.00           C  
ATOM      3  C   MET A   1       1.000   0.000   0.000  1.00 20.00           C  
ATOM      4  O   MET A   1      -1.500   1.000   0.000  1.00 20.00           O  
ATOM      5  CB  MET A   1       0.000   0.000   1.000  1.00 20.00           C  
HELIX    1   1 MET A    1  MET A   10  1                                  10    
SHEET    1   A 2 VAL A  15  LEU A  20  0                                        
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
    if (result.status === 'Running' || result.status === 'running') return 'loading';
    if (cifContent) return 'loaded';
    if (effectiveCifContent) return 'loaded'; // Using mock content
    return 'empty';
  })();
  
  // Handle CIF download
  const handleDownloadCif = useCallback(() => {
    if (effectiveCifContent) {
      const filename = generateTimestampedFilename('structure', 'cif');
      downloadCifFile(effectiveCifContent, filename);
    }
  }, [effectiveCifContent]);
  
  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="h-full w-full flex flex-col">
      {/* Download Bar */}
      <div className="flex justify-between items-center gap-4 mb-6 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
        <div className="flex items-center gap-2">
          <CheckCircle className="h-5 w-5 text-green-400" />
          <span className="text-white font-medium">Structure Prediction Complete</span>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={async () => await downloadCIF(result)}
            className="bg-blue-600 hover:bg-blue-700 text-white"
            size="sm"
          >
            <Download className="h-4 w-4 mr-2" />
            Download CIF
          </Button>
          <Button
            onClick={() => generatePDFReport(result)}
            className="bg-purple-600 hover:bg-purple-700 text-white"
            size="sm"
          >
            <FileDown className="h-4 w-4 mr-2" />
            Download PDF Report
          </Button>
        </div>
      </div>

      <Tabs value={selectedTab} onValueChange={setSelectedTab} className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-5 bg-gray-800/50 border border-gray-700 flex-shrink-0">
          <TabsTrigger value="overview" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Overview
          </TabsTrigger>
          <TabsTrigger value="confidence" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Confidence
          </TabsTrigger>
          <TabsTrigger value="structure" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Structure
          </TabsTrigger>
          <TabsTrigger value="parameters" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Parameters
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
                value={result.job_id ? result.job_id.split('-')[0] : result.id ? result.id.split('-')[0] : 'N/A'}
                subtitle="Click to copy full ID"
                icon={<Database className="h-4 w-4" />}
              />
              <MetricTile
                title="Status"
                value={result.status || 'Unknown'}
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
                title="GPU Used"
                value={result.parameters?.gpu_used || 'A100-40GB'}
                subtitle="Hardware acceleration"
                icon={<Zap className="h-4 w-4" />}
              />
            </div>

            {/* Key Structure Metrics */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Dna className="h-5 w-5 text-green-400" />
                  Structure Quality Metrics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {result.ptm_score !== undefined && (
                    <MetricTile
                      title="PTM Score"
                      value={result.ptm_score}
                      subtitle="Overall structure confidence"
                      color={getScoreColor(result.ptm_score)}
                    />
                  )}
                  {result.plddt_score !== undefined && (
                    <MetricTile
                      title="pLDDT Score"
                      value={result.plddt_score}
                      subtitle="Per-residue confidence"
                      color={getScoreColor(result.plddt_score)}
                    />
                  )}
                  {result.confidence !== undefined && (
                    <MetricTile
                      title="Overall Confidence"
                      value={result.confidence}
                      subtitle="Combined structure score"
                      color={getScoreColor(result.confidence)}
                    />
                  )}
                </div>
              </CardContent>
            </Card>

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

        <TabsContent value="confidence" className="flex-1 mt-6 overflow-auto">
          <div className="space-y-6 h-full overflow-y-auto pb-16">
            {/* Confidence Metrics */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Star className="h-5 w-5 text-yellow-400" />
                  Structure Confidence Metrics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[
                    { label: 'Overall Confidence', value: result.confidence, description: 'Combined prediction confidence' },
                    { label: 'PTM Score', value: result.ptm_score, description: 'Predicted Template Modeling score' },
                    { label: 'pLDDT Score', value: result.plddt_score, description: 'Per-residue confidence estimate' },
                    { label: 'ipTM Score', value: result.iptm_score, description: 'Interface predicted TM-score' }
                  ].map((metric, index) => (
                    metric.value !== undefined && (
                      <div key={index} className="bg-gray-900/50 rounded-lg p-4">
                        <div className="text-center">
                          <div className={`text-3xl font-bold ${getScoreColor(metric.value)} mb-2`}>
                            {metric.value.toFixed(3)}
                          </div>
                          <div className="text-sm text-gray-400 mb-1">{metric.label}</div>
                          <div className="text-xs text-gray-500">{metric.description}</div>
                        </div>
                      </div>
                    )
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Confidence Interpretation Guide */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Info className="h-5 w-5 text-blue-400" />
                  Confidence Score Interpretation
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-green-900/20 border border-green-700 rounded-lg p-3">
                      <div className="text-green-400 font-semibold mb-1">High Confidence (&ge;0.80)</div>
                      <div className="text-green-300 text-sm">Very reliable structure prediction</div>
                    </div>
                    <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg p-3">
                      <div className="text-yellow-400 font-semibold mb-1">Medium Confidence (0.60-0.79)</div>
                      <div className="text-yellow-300 text-sm">Generally reliable with some uncertainty</div>
                    </div>
                    <div className="bg-red-900/20 border border-red-700 rounded-lg p-3">
                      <div className="text-red-400 font-semibold mb-1">Low Confidence (&lt;0.60)</div>
                      <div className="text-red-300 text-sm">Uncertain prediction, use with caution</div>
                    </div>
                  </div>
                </div>
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
                    {result.structure_count && (
                      <MetricTile
                        title="Structure Models"
                        value={result.structure_count}
                        subtitle="Generated conformations"
                        icon={<Layers className="h-4 w-4" />}
                      />
                    )}
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
                  
                  {/* Structure Quality Indicators */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {result.ptm_score !== undefined && (
                      <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-gray-400 text-sm">Structure Quality</span>
                          <span className={`text-sm font-medium ${getScoreColor(result.ptm_score)}`}>
                            {result.ptm_score >= 0.8 ? 'Excellent' : result.ptm_score >= 0.6 ? 'Good' : 'Fair'}
                          </span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full ${
                              result.ptm_score >= 0.8 ? 'bg-green-500' : 
                              result.ptm_score >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${result.ptm_score * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    )}
                    
                    {result.plddt_score !== undefined && (
                      <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-gray-400 text-sm">Local Accuracy</span>
                          <span className={`text-sm font-medium ${getScoreColor(result.plddt_score)}`}>
                            {result.plddt_score >= 0.8 ? 'High' : result.plddt_score >= 0.6 ? 'Medium' : 'Low'}
                          </span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full ${
                              result.plddt_score >= 0.8 ? 'bg-green-500' : 
                              result.plddt_score >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${result.plddt_score * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    )}
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

        <TabsContent value="parameters" className="flex-1 mt-6 overflow-auto">
          <div className="space-y-6 h-full overflow-y-auto pb-16">
            {/* Prediction Parameters */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Settings className="h-5 w-5 text-green-400" />
                  Structure Prediction Parameters
                </CardTitle>
              </CardHeader>
              <CardContent>
                {result.parameters ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(result.parameters).map(([key, value]) => (
                      <MetricTile
                        key={key}
                        title={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        value={typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                        subtitle="Configuration setting"
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    No parameter information available
                  </div>
                )}
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
                  Structure Prediction Execution Logs
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
                    <>
                      {/* Fallback to boltz output */}
                      <div className="bg-gray-900 p-4 rounded-lg">
                        <h4 className="text-sm font-medium text-white mb-2">Boltz-2 Structure Output</h4>
                        <div className="max-h-96 overflow-auto">
                          <pre className="text-sm text-gray-300 whitespace-pre-wrap">
                            {result.boltz_output || 'No output logs available'}
                          </pre>
                        </div>
                      </div>
                      
                      {result.boltz_error && (
                        <div className="bg-gray-900 p-4 rounded-lg border border-gray-600">
                          <h4 className="text-sm font-medium text-blue-400 mb-2">System Output (stderr)</h4>
                          <p className="text-xs text-gray-500 mb-2">
                            Progress bars, warnings, and system messages from structure prediction
                          </p>
                          <div className="max-h-96 overflow-auto">
                            <pre className="text-sm text-gray-300 whitespace-pre-wrap">
                              {result.boltz_error}
                            </pre>
                          </div>
                        </div>
                      )}
                    </>
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

// Enhanced tabbed output component for protein-ligand binding
const ProteinLigandBindingOutput: React.FC<{ 
  result: PredictionResult;
}> = ({ result }) => {
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
  const mockPdbContent = `HEADER    SMALL MOLECULE                          01-JAN-23   TEST            
REMARK   1 REFERENCE                                                          
REMARK   1  AUTH   TEST                                                       
REMARK   1  TITL   TEST STRUCTURE                                             
ATOM      1  C1  MOL A   1      -1.000   0.000   0.000  1.00 20.00           C  
ATOM      2  C2  MOL A   1       0.000   0.000   0.000  1.00 20.00           C  
ATOM      3  C3  MOL A   1       1.000   0.000   0.000  1.00 20.00           C  
ATOM      4  O1  MOL A   1      -1.500   1.000   0.000  1.00 20.00           O  
ATOM      5  N1  MOL A   1       0.000   0.000   1.000  1.00 20.00           N  
CONECT    1    2    4                                                         
CONECT    2    1    3                                                         
CONECT    3    2    5                                                         
CONECT    4    1                                                              
CONECT    5    3                                                              
END                                                                           
`;

  // Use mock content if no real content is available (for testing)
  const effectiveCifContent = cifContent || mockPdbContent;
  
  // Determine viewer state
  const viewerState = (() => {
    if (result?.error) return 'error';
    if (!result) return 'pre-run';
    if (result.status === 'Running' || result.status === 'running') return 'loading';
    if (cifContent) return 'loaded';
    if (effectiveCifContent) return 'loaded'; // Using mock content
    return 'empty';
  })();
  

  
  // Handle CIF download
  const handleDownloadCif = useCallback(() => {
    if (effectiveCifContent) {
      const filename = generateTimestampedFilename('structure', 'cif');
      downloadCifFile(effectiveCifContent, filename);
    }
  }, [effectiveCifContent]);
  

  
  // Handle screenshot

  
  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    return 'text-red-400';
  };
  
  const getScoreBadge = (score: number) => {
    if (score >= 0.8) return 'bg-green-500/20 text-green-400';
    if (score >= 0.6) return 'bg-yellow-500/20 text-yellow-400';
    return 'bg-red-500/20 text-red-400';
  };

  return (
    <div className="h-full w-full flex flex-col">
      {/* Download Bar */}
      <div className="flex justify-between items-center gap-4 mb-6 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
        <div className="flex items-center gap-2">
          <CheckCircle className="h-5 w-5 text-green-400" />
          <span className="text-white font-medium">Prediction Complete</span>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={async () => await downloadCIF(result)}
            className="bg-blue-600 hover:bg-blue-700 text-white"
            size="sm"
          >
            <Download className="h-4 w-4 mr-2" />
            Download CIF
          </Button>
          <Button
            onClick={() => generatePDFReport(result)}
            className="bg-purple-600 hover:bg-purple-700 text-white"
            size="sm"
          >
            <FileDown className="h-4 w-4 mr-2" />
            Download PDF Report
          </Button>
        </div>
      </div>

      <Tabs value={selectedTab} onValueChange={setSelectedTab} className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-6 bg-gray-800/50 border border-gray-700 flex-shrink-0">
          <TabsTrigger value="overview" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Overview
          </TabsTrigger>
          <TabsTrigger value="affinity" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Affinity
          </TabsTrigger>
          <TabsTrigger value="confidence" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Confidence
          </TabsTrigger>
          <TabsTrigger value="structure" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Structure
          </TabsTrigger>
          <TabsTrigger value="parameters" className="text-gray-300 data-[state=active]:bg-gray-700 data-[state=active]:text-white">
            Parameters
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
                value={result.job_id ? result.job_id.split('-')[0] : result.id ? result.id.split('-')[0] : 'N/A'}
                subtitle="Click to copy full ID"
                icon={<Database className="h-4 w-4" />}
              />
              <MetricTile
                title="Status"
                value={result.status || 'Unknown'}
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
                title="GPU Used"
                value={result.parameters?.gpu_used || 'A100-40GB'}
                subtitle="Hardware acceleration"
                icon={<Zap className="h-4 w-4" />}
              />
            </div>

            {/* Key Metrics */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <BarChart3 className="h-5 w-5 text-green-400" />
                  Key Metrics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {result.ptm_score !== undefined && (
                    <MetricTile
                      title="PTM Score"
                      value={result.ptm_score}
                      subtitle="Protein confidence"
                      color={getScoreColor(result.ptm_score)}
                    />
                  )}
                  {result.plddt_score !== undefined && (
                    <MetricTile
                      title="pLDDT Score"
                      value={result.plddt_score}
                      subtitle="Local structure confidence"
                      color={getScoreColor(result.plddt_score)}
                    />
                  )}
                  {result.confidence !== undefined && (
                    <MetricTile
                      title="Overall Confidence"
                      value={result.confidence}
                      subtitle="Combined score"
                      color={getScoreColor(result.confidence)}
                    />
                  )}
                </div>
              </CardContent>
            </Card>

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

        <TabsContent value="affinity" className="flex-1 mt-6 overflow-auto">
          <div className="space-y-6 h-full overflow-y-auto pb-16">
            {/* Affinity Analysis */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <TrendingUp className="h-5 w-5 text-blue-400" />
                  Binding Affinity Analysis
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Primary Metrics */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {result.affinity !== undefined && (
                      <div className="bg-gray-900/50 rounded-lg p-4">
                        <div className="text-center">
                          <div className="text-3xl font-bold text-white mb-2">
                            {result.affinity.toFixed(3)}
                          </div>
                          <div className="text-sm text-gray-400">Primary Affinity Score</div>
                        </div>
                      </div>
                    )}
                    
                    {result.affinity_probability !== undefined && (
                      <div className="bg-gray-900/50 rounded-lg p-4">
                        <div className="text-center">
                          <div className="text-3xl font-bold text-white mb-2">
                            {(result.affinity_probability * 100).toFixed(1)}%
                          </div>
                          <div className="text-sm text-gray-400">Binding Probability</div>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Ensemble Results */}
                  {result.affinity_ensemble && (
                    <div>
                      <h3 className="text-lg font-semibold text-white mb-4">Ensemble Analysis</h3>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {result.affinity_ensemble.affinity_pred_value !== undefined && (
                          <MetricTile
                            title="Ensemble Prediction"
                            value={result.affinity_ensemble.affinity_pred_value}
                            subtitle="Combined model result"
                          />
                        )}
                        {result.affinity_ensemble.affinity_pred_value1 !== undefined && (
                          <MetricTile
                            title="Model 1 Prediction"
                            value={result.affinity_ensemble.affinity_pred_value1}
                            subtitle="First model result"
                          />
                        )}
                        {result.affinity_ensemble.affinity_pred_value2 !== undefined && (
                          <MetricTile
                            title="Model 2 Prediction"
                            value={result.affinity_ensemble.affinity_pred_value2}
                            subtitle="Second model result"
                          />
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="confidence" className="flex-1 mt-6 overflow-auto">
          <div className="space-y-6 h-full overflow-y-auto pb-16">
            {/* Confidence Metrics */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Star className="h-5 w-5 text-yellow-400" />
                  Confidence Metrics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[
                    { label: 'Overall Confidence', value: result.confidence },
                    { label: 'PTM Score', value: result.ptm_score },
                    { label: 'pLDDT Score', value: result.plddt_score },
                    { label: 'ipTM Score', value: result.iptm_score },
                    { label: 'Ligand ipTM', value: result.ligand_iptm_score },
                    { label: 'Protein ipTM', value: result.protein_iptm_score }
                  ].map((metric, index) => (
                    metric.value !== undefined && (
                      <div key={index} className="bg-gray-900/50 rounded-lg p-4">
                        <div className="text-center">
                          <div className={`text-3xl font-bold ${getScoreColor(metric.value)} mb-2`}>
                            {metric.value.toFixed(3)}
                          </div>
                          <div className="text-sm text-gray-400">{metric.label}</div>
                        </div>
                      </div>
                    )
                  ))}
                </div>
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
                  <Target className="h-5 w-5 text-purple-400" />
                  Structure Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Structure Stats */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {result.structure_count && (
                      <MetricTile
                        title="Total Structures"
                        value={result.structure_count}
                        subtitle="Generated models"
                        icon={<Layers className="h-4 w-4" />}
                      />
                    )}
                    {result.structure_file_content && (
                      <MetricTile
                        title="Primary Structure"
                        value={`${(result.structure_file_content.length / 1024).toFixed(1)}KB`}
                        subtitle="Structure file size"
                        icon={<FileText className="h-4 w-4" />}
                      />
                    )}
                    <MetricTile
                      title="Format"
                      value="CIF"
                      subtitle="Structure format"
                      icon={<Database className="h-4 w-4" />}
                    />
                  </div>
                  
                  {/* Download Options */}
                  <div className="flex flex-wrap gap-2">
                    {result.all_structures && result.all_structures.length > 1 && (
                      <Badge variant="secondary" className="bg-gray-700 text-gray-300">
                        {result.all_structures.length} alternative structures available
                      </Badge>
                    )}
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

        <TabsContent value="parameters" className="flex-1 mt-6 overflow-auto">
          <div className="space-y-6 h-full overflow-y-auto pb-16">
            {/* Prediction Parameters */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Settings className="h-5 w-5 text-green-400" />
                  Prediction Parameters
                </CardTitle>
              </CardHeader>
              <CardContent>
                {result.parameters ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(result.parameters).map(([key, value]) => (
                      <MetricTile
                        key={key}
                        title={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        value={typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                        subtitle="Configuration setting"
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    No parameter information available
                  </div>
                )}
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
                  Execution Logs
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
                    <>
                      {/* Fallback to boltz output */}
                      <div className="bg-gray-900 p-4 rounded-lg">
                        <h4 className="text-sm font-medium text-white mb-2">Boltz-2 Output</h4>
                        <div className="max-h-96 overflow-auto">
                          <pre className="text-sm text-gray-300 whitespace-pre-wrap">
                            {result.boltz_output || 'No output logs available'}
                          </pre>
                        </div>
                      </div>
                      
                      {result.boltz_error && (
                        <div className="bg-gray-900 p-4 rounded-lg border border-gray-600">
                          <h4 className="text-sm font-medium text-blue-400 mb-2">System Output (stderr)</h4>
                          <p className="text-xs text-gray-500 mb-2">
                            Progress bars, warnings, and system messages from model execution
                          </p>
                          <div className="max-h-96 overflow-auto">
                            <pre className="text-sm text-gray-300 whitespace-pre-wrap">
                              {result.boltz_error}
                            </pre>
                          </div>
                        </div>
                      )}
                    </>
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
  selectedTask = 'protein_ligand_binding' 
}) => {
  // Debug logging
  console.log('🔍 OutputSection render - result:', result);
  console.log('🔍 OutputSection render - result keys:', result ? Object.keys(result) : 'No result');
  console.log('🔍 OutputSection render - isLoading:', isLoading);
  console.log('🔍 OutputSection render - selectedTask:', selectedTask);
  
  if (result) {
    console.log('🔍 OutputSection - result.affinity:', result.affinity);
    console.log('🔍 OutputSection - result.confidence:', result.confidence);
    console.log('🔍 OutputSection - result.status:', result.status);
    console.log('🔍 OutputSection - result.job_id:', result.job_id);
  }
  return (
    <div className="h-full w-full flex flex-col">
      {isLoading && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <Loader2 className="h-12 w-12 animate-spin text-blue-500 mx-auto mb-6" />
            <p className="text-lg font-medium text-gray-400 mb-2">
              Running {selectedTask.replace('_', ' ')} prediction...
            </p>
            <p className="text-sm text-gray-500 leading-relaxed">This may take 3-5 minutes</p>
          </div>
        </div>
      )}

      {!isLoading && !result && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <FileText className="h-20 w-20 text-gray-600 mx-auto mb-6" />
            <p className="text-lg font-medium text-gray-400 mb-2">No prediction results yet</p>
            <p className="text-sm text-gray-500 leading-relaxed">
              Submit a prediction to see results here
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
              {selectedTask === 'protein_ligand_binding' ? (
                <ProteinLigandBindingOutput 
                  result={result} 
                />
              ) : selectedTask === 'protein_structure' ? (
                <ProteinStructureOutput 
                  result={result}
                />
              ) : selectedTask === 'batch_protein_ligand_screening' ? (
                <BatchProteinLigandOutput 
                  result={result as any} 
                  isLoading={isLoading}
                />
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