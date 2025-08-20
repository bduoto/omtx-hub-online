import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { 
  Upload, 
  X, 
  FileText, 
  Loader2, 
  Play,
  Download,
  AlertCircle,
  CheckCircle,
  Database
} from 'lucide-react';

interface LigandData {
  id: string;
  smiles: string;
  name?: string;
}

interface BatchScreeningInputProps {
  onBatchStart: (batchId: string) => void;
  onBatchComplete: (results: any) => void;
  onBatchError: (error: string) => void;
  isViewMode?: boolean;
}

interface BatchProgress {
  batchId: string;
  progressPercentage: number;
  completed: number;
  failed: number;
  inProgress: number;
  total: number;
  status: string;
  currentMessage: string;
}

export const BatchScreeningInput: React.FC<BatchScreeningInputProps> = ({
  onBatchStart,
  onBatchComplete,
  onBatchError,
  isViewMode = false
}) => {
  const [proteinSequence, setProteinSequence] = useState('');
  const [jobName, setJobName] = useState('batch_screening');
  const [ligands, setLigands] = useState<LigandData[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null);
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);

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
            let id = '';
            
            if (columns.length === 1) {
              // Single column - assume it's SMILES
              smiles = columns[0];
              name = `Compound_${lineNumber}`;
              id = `L${lineNumber.toString().padStart(3, '0')}`;
            } else if (columns.length >= 2) {
              // Multiple columns - try to detect SMILES vs name
              const col1 = columns[0];
              const col2 = columns[1];
              
              if (isValidSMILES(col1)) {
                smiles = col1;
                name = col2 || `Compound_${lineNumber}`;
                id = `L${lineNumber.toString().padStart(3, '0')}`;
              } else if (isValidSMILES(col2)) {
                name = col1 || `Compound_${lineNumber}`;
                smiles = col2;
                id = col1 ? col1.replace(/[^a-zA-Z0-9]/g, '_') : `L${lineNumber.toString().padStart(3, '0')}`;
              } else {
                name = col1 || `Compound_${lineNumber}`;
                smiles = col2;
                id = col1 ? col1.replace(/[^a-zA-Z0-9]/g, '_') : `L${lineNumber.toString().padStart(3, '0')}`;
              }
            }
            
            if (!isValidSMILES(smiles)) {
              errors.push(`Line ${lineNumber}: Invalid SMILES "${smiles}"`);
              return;
            }
            
            ligands.push({ 
              id: id || `L${lineNumber.toString().padStart(3, '0')}`, 
              smiles, 
              name: name || `Compound_${lineNumber}` 
            });
          });
          
          if (ligands.length === 0) {
            reject(new Error('No valid SMILES found in file'));
            return;
          }
          
          if (ligands.length > 100) {
            reject(new Error(`File contains ${ligands.length} ligands. Maximum 100 ligands per batch.`));
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

  // Start batch screening - Enhanced with Unified API v3
  const startBatchScreening = async () => {
    if (!proteinSequence.trim() || ligands.length === 0) {
      onBatchError('Please provide a protein sequence and upload ligands');
      return;
    }

    setIsRunning(true);
    
    try {
      // Use the consolidated API v1
      const requestBody = {
        model: "boltz2",
        protein_sequence: proteinSequence.trim(),
        ligands: ligands.map(ligand => ({
          name: ligand.name,
          smiles: ligand.smiles
        })),
        batch_name: jobName,
        user_id: "current_user",
        max_concurrent: 5,
        priority: "normal",
        parameters: {
          use_msa: true,
          use_potentials: false
        }
      };

      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://34.29.29.170';
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
        setCurrentBatchId(result.batch_id);
        onBatchStart(result.batch_id);
        pollUnifiedBatchStatus(result.batch_id);
      } else {
        onBatchComplete(result);
      }
      
    } catch (error) {
      setIsRunning(false);
      onBatchError(error instanceof Error ? error.message : 'Unknown error occurred');
    }
  };

  // Poll unified batch status - Enhanced with v3 API
  const pollUnifiedBatchStatus = async (batchId: string) => {
    const maxAttempts = 600; // 100 minutes max (10 second intervals)
    let attempts = 0;
    
    const pollInterval = setInterval(async () => {
      try {
        // Use the consolidated batch endpoint
        const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://34.29.29.170';
        const response = await fetch(`${apiBase}/api/v1/batches/${batchId}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch batch status: ${response.status}`);
        }
        
        const batchStatus = await response.json();
        console.log('🔍 Unified batch status:', batchStatus);
        
        // Update progress display
        setBatchProgress({
          batchId: batchId,
          progressPercentage: batchStatus.progress?.progress_percentage || 0,
          completed: batchStatus.progress?.completed || 0,
          failed: batchStatus.progress?.failed || 0,
          inProgress: batchStatus.progress?.running || 0,
          total: batchStatus.total_jobs || 0,
          status: batchStatus.status,
          currentMessage: batchStatus.insights?.batch_health || 'Processing batch...'
        });
        
        if (batchStatus.status === 'completed') {
          clearInterval(pollInterval);
          setIsRunning(false);
          
          // Fetch results and convert to legacy format for compatibility
          const resultsResponse = await fetch(`/api/v3/batches/${batchId}/results`);
          const results = resultsResponse.ok ? await resultsResponse.json() : null;
          
          // Return in format compatible with existing result handlers
          onBatchComplete({
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
          onBatchError(`Batch ${batchStatus.status}: ${batchStatus.insights?.batch_health || 'Unknown error'}`);
        } else if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setIsRunning(false);
          onBatchError('Batch polling timeout - jobs may still be running');
        }
        
        attempts++;
      } catch (error) {
        console.error('Unified batch polling error:', error);
        attempts++;
        
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setIsRunning(false);
          onBatchError('Failed to check batch status');
        }
      }
    }, 10000); // Poll every 10 seconds
  };
  
  // Legacy progress polling removed - now using pollUnifiedBatchStatus with v3 API

  // Download results - Enhanced with unified API
  const downloadResults = async () => {
    if (!currentBatchId) return;
    
    try {
      // Try unified API v3 first
      const v3Response = await fetch(`/api/v3/batches/${currentBatchId}/results`);
      if (v3Response.ok) {
        const results = await v3Response.json();
        
        // Check if results have download URLs
        if (results.download_urls && results.download_urls.length > 0) {
          // Download from first available URL
          const downloadUrl = results.download_urls[0];
          const response = await fetch(downloadUrl);
          if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `${currentBatchId}_results.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            return;
          }
        }
      }
      
      // Fallback to legacy API
      const response = await fetch(`/api/v2/batch/${currentBatchId}/download`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `${currentBatchId}_results.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Error downloading results:', error);
    }
  };

  const isReadyToRun = proteinSequence.trim().length > 0 && ligands.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white text-lg flex items-center gap-2">
            <Database className="h-5 w-5" />
            Batch Protein-Ligand Screening
          </CardTitle>
          <p className="text-gray-400 text-sm">
            Screen a protein against multiple ligands (up to 100) and get comprehensive binding predictions
          </p>
        </CardHeader>
      </Card>

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

      {/* Progress Display */}
      {batchProgress && (
        <Card className="bg-blue-900/30 border-blue-700">
          <CardContent className="pt-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-blue-400 font-medium">Batch Progress</span>
                <span className="text-blue-300 text-sm">
                  {batchProgress.completed + batchProgress.failed}/{batchProgress.total} processed
                </span>
              </div>
              
              <Progress 
                value={batchProgress.progressPercentage} 
                className="w-full"
              />
              
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="text-green-400 font-medium">{batchProgress.completed}</div>
                  <div className="text-gray-400">Completed</div>
                </div>
                <div className="text-center">
                  <div className="text-yellow-400 font-medium">{batchProgress.inProgress}</div>
                  <div className="text-gray-400">In Progress</div>
                </div>
                <div className="text-center">
                  <div className="text-red-400 font-medium">{batchProgress.failed}</div>
                  <div className="text-gray-400">Failed</div>
                </div>
              </div>
              
              <p className="text-blue-300 text-sm text-center">
                {batchProgress.currentMessage}
              </p>
              
              {(batchProgress.status === 'completed' || batchProgress.status === 'partially_completed') && (
                <div className="flex justify-center pt-2">
                  <Button
                    onClick={downloadResults}
                    className="bg-green-600 hover:bg-green-700 text-white gap-2"
                  >
                    <Download className="h-4 w-4" />
                    Download Results
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Input Parameters */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white text-sm">Input Parameters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Job Name */}
          <div>
            <Label htmlFor="batch-job-name" className="text-sm font-medium text-gray-300">
              Job Name
            </Label>
            <Input
              id="batch-job-name"
              placeholder="batch_screening"
              value={jobName}
              onChange={(e) => !isViewMode && setJobName(e.target.value)}
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
              placeholder="Enter protein sequence for screening..."
              value={proteinSequence}
              onChange={(e) => !isViewMode && setProteinSequence(e.target.value.toUpperCase())}
              className="mt-1 bg-gray-800/50 border-gray-700 text-white min-h-[100px] font-mono text-sm"
              rows={4}
              readOnly={isViewMode}
            />
            {proteinSequence && (
              <div className="mt-2 text-xs text-gray-400">
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
            <span>Ligand Library Upload</span>
            {ligands.length > 0 && (
              <span className="text-blue-400 text-xs">
                {ligands.length} compound{ligands.length > 1 ? 's' : ''} loaded
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* File Upload */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm text-gray-300">Upload CSV/TXT File</Label>
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
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="h-8 w-8 text-gray-400 mx-auto" />
                  <div>
                    <label
                      htmlFor="batch-file-upload"
                      className="text-sm text-blue-400 hover:text-blue-300 cursor-pointer"
                    >
                      {isProcessing ? 'Processing...' : 'Click to upload CSV/TXT file'}
                    </label>
                    <div className="text-xs text-gray-500 mt-1">
                      Format: Name,SMILES or just SMILES (max 100 compounds)
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

          {/* Sample Format */}
          <div className="bg-gray-800/30 border border-gray-700 rounded-md p-3">
            <div className="text-xs text-gray-400 space-y-1">
              <div className="font-medium">Sample CSV format:</div>
              <div className="font-mono bg-gray-900/50 p-2 rounded text-xs">
                Name,SMILES<br/>
                Aspirin,CC(=O)Oc1ccccc1C(=O)O<br/>
                Caffeine,CN1C=NC2=C1C(=O)N(C(=O)N2C)C
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Validation Notice */}
      {!isReadyToRun && !isViewMode && (
        <Alert className="border-yellow-700 bg-yellow-900/20">
          <AlertCircle className="h-4 w-4 text-yellow-400" />
          <AlertDescription className="text-yellow-400">
            Please provide a protein sequence and upload a ligand library to start batch screening.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};