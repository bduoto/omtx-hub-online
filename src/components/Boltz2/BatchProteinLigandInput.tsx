import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Upload, 
  X, 
  FileText, 
  Loader2, 
  Play,
  AlertCircle,
  CheckCircle,
  Database,
  Download
} from 'lucide-react';

interface LigandData {
  name: string;
  smiles: string;
}

interface BatchProteinLigandInputProps {
  onPredictionStart: () => void;
  onPredictionComplete: (result: any) => void;
  onPredictionError: (error: string) => void;
  isViewMode?: boolean;
}

// Generate random job name
const generateRandomJobName = () => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < 8; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
};

export const BatchProteinLigandInput: React.FC<BatchProteinLigandInputProps> = ({
  onPredictionStart,
  onPredictionComplete,
  onPredictionError,
  isViewMode = false
}) => {
  const [proteinName, setProteinName] = useState('');
  const [proteinSequence, setProteinSequence] = useState('');
  const [jobName, setJobName] = useState(generateRandomJobName());
  const [ligands, setLigands] = useState<LigandData[]>([]);
  const [useMSAServer, setUseMSAServer] = useState(true);
  const [usePotentials, setUsePotentials] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  // SMILES validation function
  const isValidSMILES = (smiles: string): boolean => {
    if (!smiles || smiles.trim().length === 0) return false;
    
    const trimmed = smiles.trim();
    
    // Basic SMILES validation
    const validChars = /^[A-Za-z0-9\[\]()=#@+\-\\.\\/:]*$/;
    if (!validChars.test(trimmed)) return false;
    
    // Check for balanced brackets and parentheses
    const brackets = trimmed.match(/\[|\]/g);
    const parentheses = trimmed.match(/\(|\)/g);
    
    if (brackets && brackets.length % 2 !== 0) return false;
    if (parentheses && parentheses.length % 2 !== 0) return false;
    
    // Must contain at least one letter
    if (!/[A-Za-z]/.test(trimmed)) return false;
    
    // Length check
    if (trimmed.length > 300) return false;
    
    return true;
  };

  // CSV parsing function
  const parseCSVFile = useCallback(async (file: File): Promise<LigandData[]> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = (e) => {
        try {
          const text = e.target?.result as string;
          const lines = text.split('\n').filter(line => line.trim());
          
          if (lines.length === 0) {
            reject(new Error('File is empty'));
            return;
          }

          const ligands: LigandData[] = [];
          const errors: string[] = [];
          
          // Check if first line is a header
          const firstLine = lines[0].toLowerCase();
          const hasHeader = firstLine.includes('smiles') || firstLine.includes('name') || firstLine.includes('compound');
          
          const dataLines = hasHeader ? lines.slice(1) : lines;
          
          dataLines.forEach((line, index) => {
            const lineNumber = hasHeader ? index + 2 : index + 1;
            const columns = line.split(',').map(col => col.trim().replace(/['"]/g, ''));
            
            if (columns.length === 0) return;
            
            let name = '';
            let smiles = '';
            
            if (columns.length === 1) {
              // Single column - assume it's SMILES
              smiles = columns[0];
              name = `Ligand_${lineNumber}`;
            } else if (columns.length >= 2) {
              // Multiple columns - first is name, second is SMILES
              name = columns[0] || `Ligand_${lineNumber}`;
              smiles = columns[1];
            }
            
            if (!isValidSMILES(smiles)) {
              errors.push(`Line ${lineNumber}: Invalid SMILES "${smiles}"`);
              return;
            }
            
            ligands.push({ name, smiles });
          });
          
          if (ligands.length === 0) {
            reject(new Error('No valid SMILES found in file'));
            return;
          }
          
          if (ligands.length > 1501) {
            reject(new Error(`File contains ${ligands.length} ligands. Maximum 1501 ligands per batch.`));
            return;
          }
          
          resolve(ligands);
        } catch (error) {
          reject(new Error(`Failed to parse file: ${error instanceof Error ? error.message : 'Unknown error'}`));
        }
      };
      
      reader.onerror = () => {
        reject(new Error('Failed to read file'));
      };
      
      reader.readAsText(file);
    });
  }, []);

  // File upload handler
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    // Validate file type
    const allowedTypes = ['.csv', '.txt'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!allowedTypes.includes(fileExtension)) {
      setUploadError('Please upload a CSV or TXT file');
      return;
    }
    
    setIsProcessing(true);
    setUploadError(null);
    setUploadedFile(file);
    
    try {
      const parsedLigands = await parseCSVFile(file);
      setLigands(parsedLigands);
      setUploadError(null);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Failed to process file');
      setUploadedFile(null);
      setLigands([]);
    } finally {
      setIsProcessing(false);
      event.target.value = '';
    }
  };

  // Clear uploaded data
  const clearUpload = () => {
    setLigands([]);
    setUploadedFile(null);
    setUploadError(null);
  };

  // Generate new random job name
  const regenerateJobName = () => {
    setJobName(generateRandomJobName());
  };

  // Start batch screening - Enhanced with Unified API v3
  const startBatchScreening = async () => {
    if (!proteinName.trim() || !proteinSequence.trim() || ligands.length === 0) {
      onPredictionError('Please provide protein name, sequence, and upload ligands');
      return;
    }

    setIsRunning(true);
    onPredictionStart();
    
    try {
      // Use the consolidated API v1
      const requestBody = {
        model: "boltz2",
        protein_sequence: proteinSequence.trim(),
        ligands: ligands.map(ligand => ({
          name: ligand.name || `Ligand ${ligands.indexOf(ligand) + 1}`,
          smiles: ligand.smiles
        })),
        batch_name: jobName,
        user_id: "current_user",
        max_concurrent: 5,
        priority: "normal",
        parameters: {
          use_msa: useMSAServer,
          use_potentials: usePotentials
        }
      };

      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBase}/api/v1/predict/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      
      // Unified API returns batch_id for polling
      if (result.batch_id) {
        pollUnifiedBatchStatus(result.batch_id);
      } else {
        onPredictionComplete(result);
      }
      
    } catch (error) {
      setIsRunning(false);
      onPredictionError(error instanceof Error ? error.message : 'Unknown error occurred');
    }
  };

  // Poll unified batch status - Enhanced with v3 API
  const pollUnifiedBatchStatus = async (batchId: string) => {
    const maxAttempts = 600; // 100 minutes max (10 second intervals)
    let attempts = 0;
    
    const pollInterval = setInterval(async () => {
      try {
        // Use the unified batch status endpoint
        const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${apiBase}/api/v1/batches/${batchId}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch batch status: ${response.status}`);
        }
        
        const batchStatus = await response.json();
        console.log('🔍 Unified batch status:', batchStatus);
        
        if (batchStatus.status === 'completed') {
          clearInterval(pollInterval);
          setIsRunning(false);
          
          // Fetch results and convert to legacy format for compatibility
          const resultsResponse = await fetch(`/api/v3/batches/${batchId}/results`);
          const results = resultsResponse.ok ? await resultsResponse.json() : null;
          
          // Return in format compatible with existing result handlers
          onPredictionComplete({
            batch_id: batchId,
            status: batchStatus.status,
            job_id: batchId, // For backward compatibility
            task_type: 'batch_protein_ligand_screening',
            batch_summary: {
              total_ligands: batchStatus.total_jobs,
              completed_jobs: batchStatus.progress.completed,
              failed_jobs: batchStatus.progress.failed
            },
            results: results?.results || [],
            progress: batchStatus.progress,
            insights: batchStatus.insights
          });
        } else if (batchStatus.status === 'failed' || batchStatus.status === 'cancelled') {
          clearInterval(pollInterval);
          setIsRunning(false);
          onPredictionError(`Batch ${batchStatus.status}: ${batchStatus.insights?.batch_health || 'Unknown error'}`);
        } else if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setIsRunning(false);
          onPredictionError('Batch polling timeout - jobs may still be running');
        } else {
          // Still running - show progress
          const progress = batchStatus.progress;
          console.log(`🔄 Batch progress: ${progress.completed}/${progress.total} (${Math.round(progress.progress_percentage)}%)`);
        }
        
        attempts++;
      } catch (error) {
        console.error('Unified batch polling error:', error);
        attempts++;
        
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setIsRunning(false);
          onPredictionError('Failed to check batch status');
        }
      }
    }, 10000); // Poll every 10 seconds
  };

  // Poll batch job status - Legacy method for backward compatibility
  const pollJobStatus = async (jobId: string) => {
    const maxAttempts = 600; // 100 minutes max (10 second intervals)
    let attempts = 0;
    
    const pollInterval = setInterval(async () => {
      try {
        // Use the batch status endpoint for batch jobs
        const response = await fetch(`/api/v2/jobs/${jobId}/batch-status`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch batch status: ${response.status}`);
        }
        
        const batchStatus = await response.json();
        console.log('🔍 Batch status:', batchStatus);
        
        if (batchStatus.status === 'completed' || batchStatus.status === 'partially_completed') {
          clearInterval(pollInterval);
          setIsRunning(false);
          
          // Return the full batch result
          onPredictionComplete({
            ...batchStatus,
            job_id: jobId,
            task_type: 'batch_protein_ligand_screening'
          });
        } else if (batchStatus.status === 'failed') {
          clearInterval(pollInterval);
          setIsRunning(false);
          onPredictionError(batchStatus.message || 'Batch job failed');
        } else if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setIsRunning(false);
          onPredictionError('Batch polling timeout - jobs may still be running');
        } else {
          // Still running - could show progress here
          console.log(`Batch progress: ${batchStatus.batch_summary.completed_jobs}/${batchStatus.batch_summary.total_ligands}`);
        }
        
        attempts++;
      } catch (error) {
        console.error('Error polling batch status:', error);
        attempts++;
        
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setIsRunning(false);
          onPredictionError('Batch polling failed');
        }
      }
    }, 10000); // Poll every 10 seconds
  };

  // Download sample CSV
  const downloadSampleCSV = () => {
    const sampleContent = `name,smiles
Aspirin,CC(=O)Oc1ccccc1C(=O)O
Caffeine,CN1C=NC2=C1C(=O)N(C(=O)N2C)C
Ibuprofen,CC(C)Cc1ccc(cc1)C(C)C(=O)O
Acetaminophen,CC(=O)Nc1ccc(cc1)O
Penicillin G,CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O`;

    const blob = new Blob([sampleContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sample_ligands.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const isReadyToRun = proteinName.trim().length > 0 && 
                       proteinSequence.trim().length > 0 && 
                       ligands.length > 0;

  return (
    <div className="space-y-6">
      {/* Run Button */}
      {!isViewMode && (
        <div className="flex items-center justify-center">
          <Button
            onClick={startBatchScreening}
            disabled={!isReadyToRun || isRunning}
            className="bg-blue-600 hover:bg-blue-700 text-white gap-2 px-8 py-3 text-lg font-semibold"
          >
            {isRunning ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Processing Batch...
              </>
            ) : (
              <>
                <Play className="h-5 w-5" />
                Start Batch Screening
              </>
            )}
          </Button>
        </div>
      )}

      {/* Job Name */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <Label htmlFor="batch-job-name" className="text-sm font-medium text-gray-300">
                Job Name
              </Label>
              <Input
                id="batch-job-name"
                placeholder="Auto-generated"
                value={jobName}
                onChange={(e) => !isViewMode && setJobName(e.target.value)}
                className="mt-1 bg-gray-800/50 border-gray-700 text-white"
                readOnly={isViewMode}
              />
            </div>
            {!isViewMode && (
              <Button
                variant="outline"
                size="sm"
                onClick={regenerateJobName}
                className="mt-6 border-gray-600 text-gray-300 hover:text-white"
              >
                Generate New
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Protein Information */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white text-sm">Target Protein</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Protein Name */}
          <div>
            <Label htmlFor="batch-protein-name" className="text-sm font-medium text-gray-300">
              Protein Name
            </Label>
            <Input
              id="batch-protein-name"
              placeholder="e.g., Carbonic Anhydrase II"
              value={proteinName}
              onChange={(e) => !isViewMode && setProteinName(e.target.value)}
              className="mt-1 bg-gray-800/50 border-gray-700 text-white"
              readOnly={isViewMode}
            />
          </div>

          {/* Protein Sequence */}
          <div>
            <Label htmlFor="batch-protein-sequence" className="text-sm font-medium text-gray-300">
              Protein Sequence
            </Label>
            <Textarea
              id="batch-protein-sequence"
              placeholder="Enter protein sequence in FASTA format"
              value={proteinSequence}
              onChange={(e) => !isViewMode && setProteinSequence(e.target.value.toUpperCase())}
              className="mt-1 bg-gray-800/50 border-gray-700 text-white min-h-[100px] font-mono text-sm"
              rows={4}
              readOnly={isViewMode}
            />
            {proteinSequence && (
              <div className="mt-1 text-xs text-gray-400">
                Length: {proteinSequence.length} residues
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Ligand Upload */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white text-sm flex items-center justify-between">
            <span>Ligand Library (CSV)</span>
            {ligands.length > 0 && (
              <span className="text-blue-400 text-xs">
                {ligands.length} ligand{ligands.length > 1 ? 's' : ''} loaded
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* File Upload */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm text-gray-300">Upload CSV File (max 1501 ligands)</Label>
              {uploadedFile && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearUpload}
                  className="text-gray-500 hover:text-red-400 h-6 w-6 p-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>

            <div className="border-2 border-dashed border-gray-600 rounded-lg p-6 text-center">
              <input
                type="file"
                id="batch-file-upload"
                accept=".csv,.txt"
                onChange={handleFileUpload}
                className="hidden"
                disabled={isProcessing || isViewMode}
              />
              
              {uploadedFile ? (
                <div className="space-y-2">
                  <CheckCircle className="h-8 w-8 text-green-400 mx-auto" />
                  <div className="text-sm text-green-400 font-medium">
                    {uploadedFile.name}
                  </div>
                  <div className="text-xs text-gray-400">
                    {ligands.length} ligands parsed successfully
                  </div>
                  {ligands.slice(0, 3).map((ligand, idx) => (
                    <div key={idx} className="text-xs text-gray-500">
                      {ligand.name}: {ligand.smiles}
                    </div>
                  ))}
                  {ligands.length > 3 && (
                    <div className="text-xs text-gray-500">
                      ... and {ligands.length - 3} more
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="h-8 w-8 text-gray-400 mx-auto" />
                  <div>
                    <label
                      htmlFor="batch-file-upload"
                      className="text-sm text-blue-400 hover:text-blue-300 cursor-pointer"
                    >
                      {isProcessing ? 'Processing...' : 'Click to upload CSV file'}
                    </label>
                    <div className="text-xs text-gray-500 mt-1">
                      Format: name,smiles (one ligand per line)
                    </div>
                  </div>
                </div>
              )}
            </div>

            {uploadError && (
              <Alert className="border-red-700 bg-red-900/20">
                <AlertCircle className="h-4 w-4 text-red-400" />
                <AlertDescription className="text-red-400">
                  {uploadError}
                </AlertDescription>
              </Alert>
            )}
          </div>

          {/* Sample Download */}
          <div className="flex justify-center">
            <Button
              variant="outline"
              size="sm"
              onClick={downloadSampleCSV}
              className="border-gray-600 text-gray-300 hover:text-white"
            >
              <Download className="h-4 w-4 mr-2" />
              Download Sample CSV
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Settings */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white text-sm">Advanced Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="batch-use-msa" className="text-sm font-medium text-gray-300">
                Use MSA Server
              </Label>
              <p className="text-xs text-gray-400 mt-1">
                Multiple sequence alignment for better accuracy
              </p>
            </div>
            <Switch
              id="batch-use-msa"
              checked={useMSAServer}
              onCheckedChange={setUseMSAServer}
              disabled={isViewMode}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="batch-use-potentials" className="text-sm font-medium text-gray-300">
                Use Potentials
              </Label>
              <p className="text-xs text-gray-400 mt-1">
                Additional potential functions (increases computation time)
              </p>
            </div>
            <Switch
              id="batch-use-potentials"
              checked={usePotentials}
              onCheckedChange={setUsePotentials}
              disabled={isViewMode}
            />
          </div>
        </CardContent>
      </Card>

      {/* Validation Notice */}
      {!isReadyToRun && !isViewMode && (
        <Alert className="border-yellow-700 bg-yellow-900/20">
          <AlertCircle className="h-4 w-4 text-yellow-400" />
          <AlertDescription className="text-yellow-400">
            Please provide protein name, sequence, and upload a ligand CSV file to start batch screening.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};