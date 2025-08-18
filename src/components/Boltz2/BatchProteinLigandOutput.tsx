import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  CheckCircle,
  XCircle,
  Clock,
  Database,
  BarChart3,
  Eye,
  FileDown,
  AlertCircle,
  Atom,
  Loader2
} from 'lucide-react';
import { BatchResultsDataTable } from './BatchResultsDataTable';
import { BatchStructureViewer } from './BatchStructureViewer';
import { BatchIndividualResults } from './BatchIndividualResults';
import { BatchDashboard } from './BatchDashboard';

interface IndividualResult {
  job_id: string;
  job_name: string;
  ligand_name: string;
  ligand_smiles: string;
  status: string;
  result?: {
    affinity?: number;
    confidence?: number;
    execution_time?: number;
  };
  error?: string;
}

interface BatchResult {
  job_id: string;
  batch_id?: string;
  task_type: string;
  status: string;
  batch_summary?: {
    total_ligands: number;
    completed_jobs: number;
    failed_jobs: number;
    execution_time: number;
  };
  progress?: {
    total_jobs: number;
    completed_jobs: number;
    failed_jobs: number;
    pending_jobs: number;
    total?: number;
    completed?: number;
    failed?: number;
    running?: number;
  };
  individual_results?: IndividualResult[];
  individual_jobs?: any[];
  individual_job_ids?: string[];
  estimated_completion?: number;
  message?: string;
  results?: {
    individual_jobs?: any[];
  };
}

interface BatchProteinLigandOutputProps {
  result: BatchResult | null;
  isLoading: boolean;
}

export const BatchProteinLigandOutput: React.FC<BatchProteinLigandOutputProps> = ({
  result,
  isLoading
}) => {
  // Debug logging
  console.log('🔄 BatchProteinLigandOutput - result:', result);
  if (result) {
    console.log('🔄 BatchProteinLigandOutput - result keys:', Object.keys(result));
    console.log('🔄 BatchProteinLigandOutput - progress:', result.progress);
    console.log('🔄 BatchProteinLigandOutput - batch_summary:', result.batch_summary);
    console.log('🔄 BatchProteinLigandOutput - individual_jobs:', result.individual_jobs);
    console.log('🔄 BatchProteinLigandOutput - individual_results:', result.individual_results);
  }
  const navigate = useNavigate();
  const [currentJobIndex, setCurrentJobIndex] = useState(0);
  const [sortBy, setSortBy] = useState<'name' | 'affinity' | 'status' | 'index'>('index');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [enhancedResults, setEnhancedResults] = useState(null);
  const [fetchingEnhanced, setFetchingEnhanced] = useState(false);
  const [cifDownloadProgress, setCifDownloadProgress] = useState(0);
  const [isDownloadingCIF, setIsDownloadingCIF] = useState(false);
  const [cifDownloadStatus, setCifDownloadStatus] = useState('');

  // Auto-fetch enhanced results when batch completes
  useEffect(() => {
    const fetchEnhancedResults = async () => {
      if (result?.status === 'completed' && result?.batch_id && !enhancedResults && !fetchingEnhanced) {
        setFetchingEnhanced(true);
        try {
          console.log('🔍 Fetching enhanced results for batch:', result.batch_id);
          const response = await fetch(`/api/v3/batches/${result.batch_id}/enhanced-results?page=1&page_size=1501&include_raw_modal=true`);
          if (response.ok) {
            const data = await response.json();
            console.log('✅ Enhanced results loaded:', data);
            setEnhancedResults(data);
          } else {
            console.log('⚠️ Enhanced results not available yet');
          }
        } catch (error) {
          console.error('❌ Error fetching enhanced results:', error);
        } finally {
          setFetchingEnhanced(false);
        }
      }
    };

    fetchEnhancedResults();
  }, [result?.status, result?.batch_id, enhancedResults, fetchingEnhanced]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-3">
          <Clock className="h-12 w-12 text-blue-400 animate-pulse mx-auto" />
          <p className="text-gray-400">Processing batch screening...</p>
          <p className="text-sm text-gray-500">This may take several minutes</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-3">
          <Database className="h-12 w-12 text-gray-600 mx-auto" />
          <p className="text-gray-400">No batch results yet</p>
          <p className="text-sm text-gray-500">Submit a batch screening job to see results</p>
        </div>
      </div>
    );
  }
  
  // Handle different batch states
  const hasIndividualResults = (result.individual_results?.length || 0) > 0 || (result.individual_jobs?.length || 0) > 0;
  const hasTotalJobs = (result.progress?.total || 0) > 0;
  const isRunning = result.status === 'running' || result.status === 'processing' || result.status === 'pending';
  
  // Show loading state for running batch with no results yet
  if (isRunning && !hasIndividualResults) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-4">
          <div className="relative">
            <Clock className="h-16 w-16 text-blue-400 animate-pulse mx-auto" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="h-20 w-20 border-4 border-blue-400/20 border-t-blue-400 rounded-full animate-spin"></div>
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-lg text-gray-300 font-medium">Batch predictions submitted to Modal.com</p>
            <p className="text-sm text-gray-500">Processing {result.progress?.total || 'multiple'} protein-ligand predictions...</p>
            {result.progress?.running > 0 && (
              <p className="text-sm text-blue-400">
                {result.progress.running} job{result.progress.running > 1 ? 's' : ''} currently running
              </p>
            )}
          </div>
          <div className="mt-4">
            <Badge variant="secondary" className="bg-blue-900/20 text-blue-400 border-blue-500/30">
              <Clock className="h-3 w-3 mr-1 animate-pulse" />
              {result.status}
            </Badge>
          </div>
        </div>
      </div>
    );
  }
  
  // SKIP THE INTERMEDIATE SCREEN - Handle completed batch with enhanced results data
  if (result.status === 'completed' && enhancedResults && enhancedResults.individual_results) {
    // Use the enhanced results data to populate individual_results with comprehensive raw modal data
    const enhancedIndividualResults = enhancedResults.individual_results.map((item: any, index: number) => ({
      id: item.job_id || `enhanced_${index}`,
      job_id: item.job_id,
      ligand_name: item.ligand_name || `${index + 1}`,
      ligand_smiles: item.ligand_smiles || '',
      status: item.status || 'completed',
      affinity: item.affinity || 0,
      confidence: item.confidence || 0,
      input_data: {
        ligand_name: item.ligand_name || `${index + 1}`,
        ligand_smiles: item.ligand_smiles || '',
        batch_index: index
      },
      results: {
        affinity: item.affinity || 0,
        confidence: item.confidence || 0,
        binding_score: item.affinity || 0
      },
      // Include all raw modal data for comprehensive metrics
      raw_modal_result: item.raw_modal_result || {},
      affinity_ensemble: item.affinity_ensemble || {},
      confidence_metrics: item.confidence_metrics || {},
      prediction_confidence: item.prediction_confidence || {},
      binding_affinity: item.binding_affinity || {}
    }));

    // Update the result object with enhanced data
    const enhancedResult = {
      ...result,
      individual_results: enhancedIndividualResults,
      individual_jobs: enhancedIndividualResults,
      batch_summary: {
        total_ligands: enhancedResults.total_ligands_screened || enhancedIndividualResults.length,
        completed_jobs: enhancedResults.successful_predictions || enhancedIndividualResults.length,
        failed_jobs: enhancedResults.failed_predictions || 0,
        execution_time: 0
      },
      progress: {
        total_jobs: enhancedResults.total_ligands_screened || enhancedIndividualResults.length,
        completed_jobs: enhancedResults.successful_predictions || enhancedIndividualResults.length,
        failed_jobs: enhancedResults.failed_predictions || 0,
        pending_jobs: 0
      }
    };

    // Continue with the normal rendering flow using enhanced data
    result = enhancedResult;
  }
  
  // Show loading for completed batches without enhanced results yet
  if (result.status === 'completed' && (!hasIndividualResults || !hasTotalJobs) && fetchingEnhanced) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-3">
          <Loader2 className="h-12 w-12 text-blue-400 animate-spin mx-auto" />
          <p className="text-gray-400">Loading enhanced batch results...</p>
          <p className="text-sm text-gray-500">Processing complete results data...</p>
        </div>
      </div>
    );
  }

  // Handle both old and new batch result structures
  const batch_summary = result.batch_summary || {
    total_ligands: result.progress?.total_jobs || result.progress?.total || 0,
    completed_jobs: result.progress?.completed || 0,
    failed_jobs: result.progress?.failed || 0,
    execution_time: result.estimated_completion || 0
  };
  
  console.log('🔧 Computed batch_summary:', batch_summary);
  
  const individual_results = result.individual_results || 
                          result.individual_jobs || 
                          result.results?.individual_jobs || 
                          [];
  
  console.log('🔧 Individual results data:', individual_results);
  console.log('🔧 First result structure:', individual_results[0]);
  
  const successRate = batch_summary.total_ligands > 0 
    ? (batch_summary.completed_jobs / batch_summary.total_ligands * 100).toFixed(1)
    : 0;

  // Sort results - handle empty results gracefully
  const sortedResults = individual_results.length > 0 ? [...individual_results].sort((a, b) => {
    let aVal, bVal;
    
    switch (sortBy) {
      case 'name':
        // Handle different data structures for ligand name
        const aName = a.ligand_name || a.name || a.input_data?.ligand_name || '';
        const bName = b.ligand_name || b.name || b.input_data?.ligand_name || '';
        aVal = aName.toLowerCase();
        bVal = bName.toLowerCase();
        break;
      case 'affinity':
        aVal = a.result?.affinity || a.affinity || 0;
        bVal = b.result?.affinity || b.affinity || 0;
        break;
      case 'status':
        aVal = a.status;
        bVal = b.status;
        break;
      case 'index':
        // Sort by batch_index numerically (fix 1,10,2,3 issue)
        const aBatchIndex = Number(a.input_data?.batch_index ?? 999);
        const bBatchIndex = Number(b.input_data?.batch_index ?? 999);
        return aBatchIndex - bBatchIndex;
      default:
        // Default: sort by batch_index numerically (fix 1,10,2,3 issue)
        const aBatchIndexDefault = Number(a.input_data?.batch_index ?? 999);
        const bBatchIndexDefault = Number(b.input_data?.batch_index ?? 999);
        return aBatchIndexDefault - bBatchIndexDefault;
    }
    
    if (sortOrder === 'asc') {
      return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    } else {
      return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
    }
  }) : [];

  // Get top performers - handle empty results and check for any completed status
  const topPerformers = individual_results.length > 0 ? individual_results
    .filter(r => {
      // Accept completed, completed_reconstructed, or any status that isn't failed/pending
      const isCompleted = ['completed', 'completed_reconstructed'].includes(r.status) || 
                         (r.status !== 'failed' && r.status !== 'pending' && r.status !== 'running');
      // Check for affinity value (including 0)
      const hasAffinity = (r.result?.affinity !== undefined && r.result?.affinity !== null) || 
                         (r.affinity !== undefined && r.affinity !== null);
      return isCompleted && hasAffinity;
    })
    .sort((a, b) => (b.result?.affinity || b.affinity || 0) - (a.result?.affinity || a.affinity || 0))
    .slice(0, 5) : [];

  const currentJob = sortedResults.length > 0 ? sortedResults[currentJobIndex] : null;


  const downloadBatchResults = async () => {
    try {
      // Sort results by batch_index numerically before creating CSV
      const csvSortedResults = [...sortedResults].sort((a, b) => {
        const indexA = Number(a.input_data?.batch_index || 0);
        const indexB = Number(b.input_data?.batch_index || 0);
        return indexA - indexB;
      });
      
      // Create comprehensive CSV header matching Table View columns
      const csvHeader = [
        'Index',
        'Ligand Name', 
        'SMILES',
        'Status',
        // Direct Binding Outputs
        'Affinity',
        'Affinity Probability',
        // Ensemble Support
        'Ensemble Affinity',
        'Ensemble Probability',
        'Ensemble Affinity 2',
        'Ensemble Probability 2', 
        'Ensemble Affinity 1',
        'Ensemble Probability 1',
        // Model-Level Reliability
        'Confidence',
        // Interface-Specific Structure Confidence
        'iPTM Score',
        'Ligand iPTM Score',
        'Complex ipLDDT',
        'Complex iPDE',
        // Global/Monomer Structure Confidence
        'Complex pLDDT',
        'PTM Score',
        'Execution Time (s)'
      ].join(',') + '\n';
      
      const csvRows = csvSortedResults.map(r => {
        const input_data = r.input_data || {};
        const results = r.result || r.results || r.output_data || {};
        const raw_modal = r.raw_modal_result || {};
        const confidence_metrics = raw_modal.confidence_metrics || {};
        const affinity_ensemble = raw_modal.affinity_ensemble || {};
        
        // Extract values with comprehensive fallbacks (matching BatchResultsDataTable.tsx logic)
        const batchIndex = Number(input_data.batch_index || 0) + 1;
        const ligandName = input_data.ligand_name || r.ligand_name || r.name || 'Unknown';
        const ligandSmiles = input_data.ligand_smiles || r.ligand_smiles || '';
        const status = r.status || 'unknown';
        
        // Direct binding outputs
        const affinity = raw_modal.affinity || results?.affinity || r.affinity;
        const affinityProbability = raw_modal.affinity_probability;
        
        // Ensemble support
        const ensembleAffinity = affinity_ensemble.affinity_pred_value;
        const ensembleProbability = affinity_ensemble.affinity_probability_binary;
        const ensembleAffinity2 = affinity_ensemble.affinity_pred_value2;
        const ensembleProbability2 = affinity_ensemble.affinity_probability_binary2;
        const ensembleAffinity1 = affinity_ensemble.affinity_pred_value1;
        const ensembleProbability1 = affinity_ensemble.affinity_probability_binary1;
        
        // Model-level reliability
        const confidence = raw_modal.confidence || confidence_metrics.confidence_score || results?.confidence || r.confidence;
        
        // Interface-specific structure confidence
        const iptmScore = confidence_metrics.iptm || raw_modal.iptm_score;
        const ligandIptmScore = confidence_metrics.ligand_iptm;
        const complexIplddt = confidence_metrics.complex_iplddt;
        const complexIpde = confidence_metrics.complex_ipde;
        
        // Global/monomer structure confidence
        const complexPlddt = confidence_metrics.complex_plddt || raw_modal.plddt_score;
        const ptmScore = confidence_metrics.ptm || raw_modal.ptm_score;
        const executionTime = results.execution_time;
        
        // Format all values consistently
        const formatNumber = (val: any) => val !== undefined && val !== null ? Number(val).toFixed(4) : 'N/A';
        const formatTime = (val: any) => val !== undefined && val !== null ? Number(val).toFixed(1) : 'N/A';
        
        return [
          batchIndex,
          `"${ligandName}"`,
          `"${ligandSmiles}"`,
          `"${status}"`,
          // Direct Binding Outputs
          formatNumber(affinity),
          formatNumber(affinityProbability),
          // Ensemble Support
          formatNumber(ensembleAffinity),
          formatNumber(ensembleProbability),
          formatNumber(ensembleAffinity2),
          formatNumber(ensembleProbability2),
          formatNumber(ensembleAffinity1),
          formatNumber(ensembleProbability1),
          // Model-Level Reliability
          formatNumber(confidence),
          // Interface-Specific Structure Confidence
          formatNumber(iptmScore),
          formatNumber(ligandIptmScore),
          formatNumber(complexIplddt),
          formatNumber(complexIpde),
          // Global/Monomer Structure Confidence
          formatNumber(complexPlddt),
          formatNumber(ptmScore),
          formatTime(executionTime)
        ].join(',');
      }).join('\n');
      
      const csvContent = csvHeader + csvRows;
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `comprehensive_batch_results_${result.job_id}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading results:', error);
    }
  };

  const downloadStructureFile = async (jobId: string) => {
    try {
      // Try batch-specific endpoint first, fallback to legacy endpoint
      const batchId = result?.batch_id || result?.job_id;
      let response;
      
      if (batchId) {
        response = await fetch(`/api/v3/batches/${batchId}/jobs/${jobId}/download/cif`);
        if (!response.ok) {
          console.log('Batch endpoint failed, trying legacy endpoint...');
          response = await fetch(`/api/v2/jobs/${jobId}/download/cif`);
        }
      } else {
        response = await fetch(`/api/v2/jobs/${jobId}/download/cif`);
      }
      
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `structure_${jobId}.cif`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading structure:', error);
    }
  };

  const downloadBatchCIFFiles = async () => {
    try {
      setIsDownloadingCIF(true);
      setCifDownloadProgress(0);
      setCifDownloadStatus('Initializing download...');
      
      // Import JSZip dynamically
      const JSZip = (await import('jszip')).default;
      const zip = new JSZip();
      
      const batchId = result?.batch_id || result?.job_id;
      const completedJobs = sortedResults.filter(job => job.status === 'completed');
      
      if (completedJobs.length === 0) {
        console.error('No completed jobs to download CIF files for');
        setIsDownloadingCIF(false);
        return;
      }
      
      setCifDownloadStatus(`Downloading ${completedJobs.length} CIF files...`);
      console.log(`Downloading CIF files for ${completedJobs.length} completed jobs...`);
      
      let completedDownloads = 0;
      
      // Download all CIF files with progress tracking
      const downloadPromises = completedJobs.map(async (job, index) => {
        try {
          const jobId = job.job_id || job.id;
          let response;
          
          // Try batch-specific endpoint first, fallback to legacy endpoint
          if (batchId) {
            response = await fetch(`/api/v3/batches/${batchId}/jobs/${jobId}/download/cif`);
            if (!response.ok) {
              console.log(`Batch endpoint failed for job ${jobId}, trying legacy...`);
              response = await fetch(`/api/v2/jobs/${jobId}/download/cif`);
            }
          } else {
            response = await fetch(`/api/v2/jobs/${jobId}/download/cif`);
          }
          
          if (response.ok) {
            const blob = await response.blob();
            const ligandName = job.input_data?.ligand_name || job.ligand_name || `${index + 1}`;
            const fileName = `${ligandName}_${jobId.slice(0, 8)}.cif`;
            zip.file(fileName, blob);
            console.log(`✅ Added ${fileName} to zip`);
          } else {
            console.error(`Failed to download CIF for job ${jobId}`);
          }
          
          // Update progress
          completedDownloads++;
          const progress = (completedDownloads / completedJobs.length) * 80; // Use 80% for downloads, 20% for compression
          setCifDownloadProgress(progress);
          setCifDownloadStatus(`Downloaded ${completedDownloads}/${completedJobs.length} files...`);
          
        } catch (error) {
          console.error(`Error downloading CIF for job ${job.job_id}:`, error);
          completedDownloads++;
          const progress = (completedDownloads / completedJobs.length) * 80;
          setCifDownloadProgress(progress);
        }
      });
      
      await Promise.all(downloadPromises);
      
      // Generate and download the zip file
      setCifDownloadStatus('Compressing files...');
      setCifDownloadProgress(85);
      console.log('Generating zip file...');
      
      const zipBlob = await zip.generateAsync({ 
        type: 'blob',
        compression: 'DEFLATE',
        compressionOptions: { level: 6 }
      });
      
      setCifDownloadProgress(95);
      setCifDownloadStatus('Preparing download...');
      
      const url = window.URL.createObjectURL(zipBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `batch_structures_${batchId?.slice(0, 8)}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      setCifDownloadProgress(100);
      setCifDownloadStatus('Download complete!');
      console.log('✅ Batch CIF download complete!');
      
      // Reset after a brief delay
      setTimeout(() => {
        setIsDownloadingCIF(false);
        setCifDownloadProgress(0);
        setCifDownloadStatus('');
      }, 2000);
      
    } catch (error) {
      console.error('Error downloading batch CIF files:', error);
      setCifDownloadStatus('Download failed');
      setTimeout(() => {
        setIsDownloadingCIF(false);
        setCifDownloadProgress(0);
        setCifDownloadStatus('');
      }, 3000);
    }
  };

  const viewStructure = (jobId: string) => {
    // Structure viewing is handled by the download/display functionality
    // in the Structures tab and CIF download buttons
    console.log('Structure view requested for job:', jobId);
  };

  return (
    <div className="space-y-6">
      {/* Summary Card */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Batch Screening Summary
            </div>
            <Badge variant={result.status === 'completed' ? 'default' : 'secondary'}>
              {result.status}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-gray-900/50 rounded-lg p-3">
              <div className="text-2xl font-bold text-white">{batch_summary.total_ligands}</div>
              <div className="text-xs text-gray-400">Total Ligands</div>
            </div>
            <div className="bg-gray-900/50 rounded-lg p-3">
              <div className="text-2xl font-bold text-green-400">{batch_summary.completed_jobs}</div>
              <div className="text-xs text-gray-400">Completed</div>
            </div>
            {result.progress?.running > 0 && (
              <div className="bg-gray-900/50 rounded-lg p-3">
                <div className="text-2xl font-bold text-blue-400 animate-pulse">{result.progress.running}</div>
                <div className="text-xs text-gray-400">Running</div>
              </div>
            )}
            <div className="bg-gray-900/50 rounded-lg p-3">
              <div className="text-2xl font-bold text-red-400">{batch_summary.failed_jobs}</div>
              <div className="text-xs text-gray-400">Failed</div>
            </div>
            <div className="bg-gray-900/50 rounded-lg p-3">
              <div className="text-2xl font-bold text-blue-400">{successRate}%</div>
              <div className="text-xs text-gray-400">Success Rate</div>
            </div>
          </div>
          
          <div className="mt-4">
            <Progress value={parseFloat(successRate.toString())} className="h-2" />
          </div>
          
          <div className="mt-4 flex justify-between items-center">
            <div className="text-sm text-gray-400">
              Execution time: {(batch_summary.execution_time / 60).toFixed(1)} minutes
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={downloadBatchResults}
                className="bg-green-600 hover:bg-green-700"
              >
                <Download className="h-4 w-4 mr-2" />
                Download Comprehensive CSV
              </Button>
              <Button
                size="sm"
                onClick={downloadBatchCIFFiles}
                className="bg-blue-600 hover:bg-blue-700"
                disabled={sortedResults.filter(job => job.status === 'completed').length === 0 || isDownloadingCIF}
              >
                {isDownloadingCIF ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Downloading...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Download Batch CIF
                  </>
                )}
              </Button>
            </div>
          </div>
          
          {/* CIF Download Progress Bar */}
          {isDownloadingCIF && (
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">{cifDownloadStatus}</span>
                <span className="text-gray-400">{Math.round(cifDownloadProgress)}%</span>
              </div>
              <Progress value={cifDownloadProgress} className="h-2" />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results Tabs */}
      <Tabs defaultValue="dashboard" className="w-full">
        <TabsList className="grid w-full grid-cols-5 bg-gray-800">
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="table">Table View</TabsTrigger>
          <TabsTrigger value="navigation">Individual Results</TabsTrigger>
          <TabsTrigger value="top">Top Performers</TabsTrigger>
          <TabsTrigger value="structures">Structures</TabsTrigger>
        </TabsList>

        {/* Dashboard - Comprehensive Analytics */}
        <TabsContent value="dashboard" className="space-y-4">
          <BatchDashboard 
            data={individual_results} 
            batchId={result?.batch_id || result?.job_id}
          />
        </TabsContent>

        {/* Table View - Excel-like Data Table */}
        <TabsContent value="table" className="space-y-4">
          <BatchResultsDataTable
            data={individual_results}
            onViewStructure={viewStructure}
            onDownloadStructure={downloadStructureFile}
            onDownloadAll={downloadBatchResults}
          />
        </TabsContent>

        {/* Individual Results Navigation */}
        <TabsContent value="navigation" className="space-y-4">
          <BatchIndividualResults
            jobs={sortedResults}
            currentJobIndex={currentJobIndex}
            onJobIndexChange={setCurrentJobIndex}
            onDownloadStructure={downloadStructureFile}
          />
        </TabsContent>

        {/* Top Performers */}
        <TabsContent value="top" className="space-y-4">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Top 5 Binding Compounds
              </CardTitle>
            </CardHeader>
            <CardContent>
              {topPerformers.length > 0 ? (
                <div className="space-y-3">
                  {topPerformers.map((job, index) => (
                    <div key={job.job_id} className="bg-gray-900/50 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="text-2xl font-bold text-yellow-400">
                            #{index + 1}
                          </div>
                          <div>
                            <h4 className="text-white font-semibold">{job.ligand_name || job.input_data?.ligand_name || job.name || 'Unknown'}</h4>
                            <p className="text-xs text-gray-400 font-mono">{job.ligand_smiles || job.input_data?.ligand_smiles || ''}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-green-400">
                            {(job.result?.affinity || job.affinity || 0).toFixed(3)}
                          </div>
                          <div className="text-xs text-gray-400">
                            {(job.result?.confidence || job.confidence) ? `${((job.result?.confidence || job.confidence) * 100).toFixed(1)}% conf` : ''}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <Alert className="border-yellow-700 bg-yellow-900/20">
                  <AlertCircle className="h-4 w-4 text-yellow-400" />
                  <AlertDescription className="text-yellow-400">
                    No completed results to show top performers
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Structures Tab */}
        <TabsContent value="structures" className="space-y-4">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Atom className="h-5 w-5" />
                Individual Structures
              </CardTitle>
            </CardHeader>
            <CardContent>
              <BatchStructureViewer
                completedJobs={sortedResults.filter(job => job.status === 'completed')}
                currentJobIndex={Math.max(0, Math.min(currentJobIndex, sortedResults.filter(job => job.status === 'completed').length - 1))}
                onJobIndexChange={(index) => {
                  // Map back to the original sorted results index
                  const completedJobs = sortedResults.filter(job => job.status === 'completed');
                  const selectedJob = completedJobs[index];
                  const originalIndex = sortedResults.findIndex(job => job === selectedJob);
                  if (originalIndex !== -1) {
                    setCurrentJobIndex(originalIndex);
                  }
                }}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};