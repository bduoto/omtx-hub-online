/**
 * BatchStructureViewer Component
 * 
 * Displays individual protein-ligand structures from batch screening results with navigation.
 * Features:
 * - Navigate between completed structures using arrow buttons or keyboard (← →)
 * - Automatically loads CIF content from job results or downloads from API
 * - Shows job information (ligand name, SMILES, affinity, confidence)
 * - Integrates with existing StructureViewer for 3D molecular visualization
 * - Provides download functionality for individual structures
 * 
 * Used in the "Structures" tab of batch protein-ligand screening results.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Atom,
  Loader2,
  AlertCircle,
  Eye,
  Keyboard
} from 'lucide-react';
import { StructureViewer } from './StructureViewer';

interface BatchStructureViewerProps {
  completedJobs: any[];
  currentJobIndex: number;
  onJobIndexChange: (index: number) => void;
}

export const BatchStructureViewer: React.FC<BatchStructureViewerProps> = ({
  completedJobs,
  currentJobIndex,
  onJobIndexChange
}) => {
  const [cifContent, setCifContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewerState, setViewerState] = useState<'pre-run' | 'loading' | 'loaded' | 'error' | 'empty'>('pre-run');

  const currentJob = completedJobs[currentJobIndex];
  const totalJobs = completedJobs.length;

  // Load CIF content for current job
  const loadStructureForCurrentJob = useCallback(async () => {
    if (!currentJob || currentJob.status !== 'completed') {
      setCifContent(null);
      setViewerState('empty');
      return;
    }

    setIsLoading(true);
    setError(null);
    setViewerState('loading');

    try {
      // Try to get structure content from job results first - check multiple paths
      const jobResults = currentJob.results || currentJob.result || currentJob.output_data || {};
      
      console.log('🔍 BatchStructureViewer loading structure for job:', {
        currentJob: currentJob,
        jobResults: jobResults,
        structure_file_content: jobResults.structure_file_content,
        structure_file_base64: jobResults.structure_file_base64
      });
      
      // Check for structure content in multiple formats
      if (jobResults.structure_file_content) {
        console.log('✅ Found structure_file_content');
        setCifContent(jobResults.structure_file_content);
        setViewerState('loaded');
        setIsLoading(false);
        return;
      }
      
      // Check for base64 encoded structure
      if (jobResults.structure_file_base64) {
        console.log('✅ Found structure_file_base64, decoding...');
        try {
          const decodedContent = atob(jobResults.structure_file_base64);
          setCifContent(decodedContent);
          setViewerState('loaded');
          setIsLoading(false);
          return;
        } catch (decodeErr) {
          console.error('Error decoding base64 structure:', decodeErr);
        }
      }

      // Fallback to downloading from API - try multiple endpoints
      const jobId = currentJob.id || currentJob.job_id;
      console.log(`⚠️ No structure content found in results, trying API download for job: ${jobId}`);
      
      if (jobId) {
        // Try batch-specific endpoints first
        const batchId = window.location.pathname.split('/batch-results/')[1];
        const downloadEndpoints = [
          `/api/v3/batches/${batchId}/jobs/${jobId}/download/cif`,  // New unified batch API endpoint
          `/api/v2/batches/${batchId}/jobs/${jobId}/download/cif`,  // Legacy batch endpoint
          `/api/v2/jobs/${jobId}/download/cif`,                    // Individual job endpoint
          `/api/v2/batches/${batchId}/jobs/${jobId}/structure.cif`, // Direct file path
          `/api/v2/batches/${batchId}/download/${jobId}.cif`       // Alternative path
        ];
        
        let downloadSuccess = false;
        for (const endpoint of downloadEndpoints) {
          try {
            console.log(`🔍 Trying structure download from: ${endpoint}`);
            const response = await fetch(endpoint);
            if (response.ok) {
              const cifText = await response.text();
              console.log(`✅ Successfully downloaded CIF from: ${endpoint}`);
              setCifContent(cifText);
              setViewerState('loaded');
              downloadSuccess = true;
              break;
            } else {
              console.log(`❌ Failed to download from ${endpoint}: ${response.status}`);
            }
          } catch (endpointError) {
            console.log(`❌ Error with endpoint ${endpoint}:`, endpointError);
          }
        }
        
        if (!downloadSuccess) {
          throw new Error(`Failed to download structure from any endpoint. Job ID: ${jobId}, Batch ID: ${batchId}`);
        }
      } else {
        throw new Error('No job ID available');
      }
    } catch (err) {
      console.error('Error loading structure:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setViewerState('error');
      setCifContent(null);
    } finally {
      setIsLoading(false);
    }
  }, [currentJob]);

  // Load structure when current job changes
  useEffect(() => {
    loadStructureForCurrentJob();
  }, [loadStructureForCurrentJob]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return; // Don't interfere with form inputs
      }

      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault();
          navigatePrevious();
          break;
        case 'ArrowRight':
          event.preventDefault();
          navigateNext();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [currentJobIndex, totalJobs]);

  const navigatePrevious = useCallback(() => {
    if (currentJobIndex > 0) {
      onJobIndexChange(currentJobIndex - 1);
    }
  }, [currentJobIndex, onJobIndexChange]);

  const navigateNext = useCallback(() => {
    if (currentJobIndex < totalJobs - 1) {
      onJobIndexChange(currentJobIndex + 1);
    }
  }, [currentJobIndex, totalJobs, onJobIndexChange]);

  const downloadCurrentStructure = useCallback(async () => {
    if (!currentJob || !cifContent) return;

    try {
      const blob = new Blob([cifContent], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      const ligandName = currentJob.input_data?.ligand_name || currentJob.ligand_name || 'ligand';
      const batchIndex = (currentJob.input_data?.batch_index || currentJobIndex) + 1;
      a.download = `structure_${batchIndex}_${ligandName}.cif`;
      
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading structure:', error);
    }
  }, [currentJob, cifContent, currentJobIndex]);

  if (completedJobs.length === 0) {
    return (
      <Alert className="border-yellow-700 bg-yellow-900/20">
        <AlertCircle className="h-4 w-4 text-yellow-400" />
        <AlertDescription className="text-yellow-400">
          No completed structures available to display
        </AlertDescription>
      </Alert>
    );
  }

  if (!currentJob) {
    return (
      <Alert className="border-red-700 bg-red-900/20">
        <AlertCircle className="h-4 w-4 text-red-400" />
        <AlertDescription className="text-red-400">
          Invalid job index
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      {/* Navigation Header */}
      <div className="flex items-center justify-between bg-gray-900/50 rounded-lg p-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Atom className="h-5 w-5 text-blue-400" />
            <h3 className="text-lg font-semibold text-white">
              Structure {currentJobIndex + 1} of {totalJobs}
            </h3>
          </div>
          <Badge variant="secondary" className="bg-gray-700 text-gray-200">
            {currentJob.input_data?.ligand_name || currentJob.ligand_name || 'Unknown Ligand'}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={navigatePrevious}
            disabled={currentJobIndex === 0}
            className="bg-gradient-to-r from-cyan-400 to-blue-500 to-purple-600 hover:from-cyan-500 hover:to-blue-600 hover:to-purple-700 text-white border-0 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          
          <span className="text-sm text-gray-400 px-2">
            {currentJobIndex + 1} / {totalJobs}
          </span>
          
          <Button
            size="sm"
            onClick={navigateNext}
            disabled={currentJobIndex === totalJobs - 1}
            className="bg-gradient-to-r from-cyan-400 to-blue-500 to-purple-600 hover:from-cyan-500 hover:to-blue-600 hover:to-purple-700 text-white border-0 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>

          {cifContent && (
            <Button
              size="sm"
              onClick={downloadCurrentStructure}
              className="bg-gradient-to-r from-cyan-400 to-blue-500 to-purple-600 hover:from-cyan-500 hover:to-blue-600 hover:to-purple-700 text-white border-0"
            >
              <Download className="h-4 w-4" />
              Download
            </Button>
          )}
        </div>
      </div>

      {/* Keyboard Navigation Hint */}
      <div className="flex items-center justify-center">
        <Badge variant="secondary" className="bg-gray-800 text-gray-400 text-xs">
          <Keyboard className="h-3 w-3 mr-1" />
          Use ← → arrow keys to navigate
        </Badge>
      </div>

      {/* Job Information */}
      <div className="bg-gray-900/50 rounded-lg p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Ligand:</span>
            <p className="text-white font-medium">
              {currentJob.input_data?.ligand_name || currentJob.ligand_name || currentJob.metadata?.ligand_name || 'Unknown'}
            </p>
          </div>
          <div>
            <span className="text-gray-400">SMILES:</span>
            <p className="text-white font-mono text-xs break-all">
              {currentJob.input_data?.ligand_smiles || currentJob.ligand_smiles || currentJob.metadata?.ligand_smiles || 'N/A'}
            </p>
          </div>
          <div>
            <span className="text-gray-400">Affinity:</span>
            <p className="text-white">
              {(() => {
                const results = currentJob.results || currentJob.result || currentJob.output_data || {};
                const affinity = results.affinity || results.binding_score || results.affinity_pred_value || currentJob.affinity;
                return affinity !== undefined ? affinity.toFixed(3) : 'N/A';
              })()}
            </p>
          </div>
          <div>
            <span className="text-gray-400">Confidence:</span>
            <p className="text-white">
              {(() => {
                const results = currentJob.results || currentJob.result || currentJob.output_data || {};
                const confidence = results.confidence || results.confidence_score || currentJob.confidence;
                return confidence !== undefined ? `${(confidence * 100).toFixed(1)}%` : 'N/A';
              })()}
            </p>
          </div>
        </div>
      </div>

      {/* Structure Viewer */}
      {error ? (
        <Alert className="border-red-700 bg-red-900/20">
          <AlertCircle className="h-4 w-4 text-red-400" />
          <AlertDescription className="text-red-400">
            Error loading structure: {error}
          </AlertDescription>
        </Alert>
      ) : (
        <StructureViewer
          cifContent={cifContent || undefined}
          state={viewerState}
          title={`Structure: ${currentJob.input_data?.ligand_name || currentJob.ligand_name || 'Unknown Ligand'}`}
          onDownloadCif={downloadCurrentStructure}
          className="min-h-[800px]"
        />
      )}
    </div>
  );
}; 