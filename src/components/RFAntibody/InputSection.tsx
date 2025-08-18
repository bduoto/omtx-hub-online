import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { 
  Play, 
  Loader2, 
  Upload, 
  X, 
  Plus, 
  Minus, 
  Folder, 
  AlertCircle,
  FileText,
  Trash2,
  Copy,
  CheckCircle,
  RotateCcw
} from 'lucide-react';

// RFAntibody specific interfaces
interface PDBFile {
  name: string;
  content: string;
  chains?: string[];
}

interface HotspotResidue {
  chain: string;
  residueNumber: number;
}

interface NanobodyDesignParams {
  numDesigns: number;
  cdrLengthH1?: number;
  cdrLengthH2?: number;
  cdrLengthH3?: number;
  framework: 'vhh' | 'humanized' | 'camelid';
}

interface InputSectionProps {
  selectedTask: string;
  sequenceInputs: string[];
  onSequenceInputsChange: (inputs: string[]) => void;
  ligands: { name: string; formula: string }[];
  onLigandsChange: (ligands: { name: string; formula: string }[]) => void;
  workflowName: string;
  onWorkflowNameChange: (name: string) => void;
  useMSAServer: boolean;
  onUseMSAServerChange: (use: boolean) => void;
  usePotentials: boolean;
  onUsePotentialsChange: (use: boolean) => void;
  onPredictionStart: () => void;
  onPredictionComplete: (result: any) => void;
  onPredictionError: (error: string) => void;
  isViewMode?: boolean;
  isReadOnlyMode?: boolean;
  submittedValues?: {
    sequences: string[];
    ligands: { name: string; formula: string }[];
    settings: {
      useMSAServer: boolean;
      usePotentials: boolean;
      workflowName: string;
    };
  } | null;
  onNewPrediction?: () => void;
}

// Read-only input components
const ReadOnlyInput: React.FC<{ 
  label: string; 
  value: string; 
  multiline?: boolean;
  className?: string;
}> = React.memo(({ label, value, multiline = false, className = "" }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleSelectAll = (e: React.MouseEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    e.currentTarget.select();
  };

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center justify-between">
        <Label className="text-gray-300">{label}</Label>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-6 px-2 text-gray-400 hover:text-white"
        >
          {copied ? (
            <CheckCircle className="h-3 w-3" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
        </Button>
      </div>
      {multiline ? (
        <Textarea 
          value={value} 
          readOnly 
          className="bg-gray-800/50 border-gray-600 text-gray-200 cursor-text resize-none min-h-[80px]"
          onClick={handleSelectAll}
        />
      ) : (
        <Input 
          value={value} 
          readOnly 
          className="bg-gray-800/50 border-gray-600 text-gray-200 cursor-text"
          onClick={handleSelectAll}
        />
      )}
    </div>
  );
});

const SettingsDisplay: React.FC<{ 
  useMSAServer: boolean; 
  usePotentials: boolean; 
  taskType: string;
  workflowName: string;
}> = React.memo(({ useMSAServer, usePotentials, taskType, workflowName }) => (
  <Card className="bg-gray-800/50 border-gray-700">
    <CardHeader>
      <CardTitle className="text-sm text-gray-300 flex items-center gap-2">
        <FileText className="h-4 w-4" />
        Prediction Settings
      </CardTitle>
    </CardHeader>
    <CardContent className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-400">Job Name</span>
        <span className="text-sm text-gray-200 font-medium">{workflowName}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-400">MSA Server</span>
        <Badge variant={useMSAServer ? "default" : "secondary"} className="text-xs">
          {useMSAServer ? "Enabled" : "Disabled"}
        </Badge>
      </div>
      {taskType === 'protein_ligand_binding' && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Use Potentials</span>
          <Badge variant={usePotentials ? "default" : "secondary"} className="text-xs">
            {usePotentials ? "Enabled" : "Disabled"}
          </Badge>
        </div>
      )}
    </CardContent>
  </Card>
));

const ReadOnlyInputDisplay: React.FC<{
  taskType: string;
  values: {
    sequences: string[];
    ligands: { name: string; formula: string }[];
    settings: {
      useMSAServer: boolean;
      usePotentials: boolean;
      workflowName: string;
    };
  };
  onNewPrediction?: () => void;
}> = React.memo(({ taskType, values, onNewPrediction }) => {
  return (
    <div className="h-full overflow-auto p-6 space-y-6">
      {/* Header with New Prediction button */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Submitted Parameters</h3>
        {onNewPrediction && (
          <Button
            onClick={onNewPrediction}
            variant="outline"
            size="sm"
            className="border-gray-600 text-gray-300 hover:text-white"
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            New Prediction
          </Button>
        )}
      </div>

      {/* Protein Sequence(s) */}
      {values.sequences.map((sequence, index) => (
        <ReadOnlyInput
          key={`sequence-${index}`}
          label={values.sequences.length > 1 ? `Protein Sequence ${index + 1}` : "Protein Sequence"}
          value={sequence}
          multiline={true}
        />
      ))}

      {/* Ligands (for protein-ligand binding) */}
      {taskType === 'protein_ligand_binding' && values.ligands.length > 0 && (
        <div className="space-y-4">
          <Label className="text-gray-300">Ligand Information</Label>
          {values.ligands.map((ligand, index) => (
            <div key={`ligand-${index}`} className="space-y-2">
              {ligand.name && (
                <ReadOnlyInput
                  label={`Ligand ${index + 1} Name`}
                  value={ligand.name}
                />
              )}
              <ReadOnlyInput
                label={`Ligand ${index + 1} SMILES`}
                value={ligand.formula}
              />
            </div>
          ))}
        </div>
      )}

      {/* Settings */}
      <SettingsDisplay
        useMSAServer={values.settings.useMSAServer}
        usePotentials={values.settings.usePotentials}
        taskType={taskType}
        workflowName={values.settings.workflowName}
      />
    </div>
  );
});

// Task-specific input components for RFAntibody
const NanobodyDesignInputs: React.FC<{
  pdbFile: PDBFile | null;
  onPdbFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  targetChain: string;
  onTargetChainChange: (chain: string) => void;
  hotspotResidues: string;
  onHotspotResiduesChange: (residues: string) => void;
  numDesigns: number;
  onNumDesignsChange: (num: number) => void;
  framework: 'vhh' | 'humanized' | 'camelid';
  onFrameworkChange: (fw: 'vhh' | 'humanized' | 'camelid') => void;
  jobName: string;
  onJobNameChange: (name: string) => void;
  isViewMode?: boolean;
}> = ({ 
  pdbFile, 
  onPdbFileChange, 
  targetChain, 
  onTargetChainChange,
  hotspotResidues, 
  onHotspotResiduesChange,
  numDesigns,
  onNumDesignsChange,
  framework,
  onFrameworkChange,
  jobName, 
  onJobNameChange, 
  isViewMode 
}) => (
  <div className="space-y-4">
    <div>
      <Label htmlFor="job-name" className="text-sm font-medium text-gray-300">
        Job Name
      </Label>
      <Input
        id="job-name"
        placeholder="nanobody_design"
        value={jobName}
        onChange={(e) => !isViewMode && onJobNameChange(e.target.value)}
        className="mt-1 bg-gray-800/50 border-gray-700 text-white"
        readOnly={isViewMode}
      />
    </div>
    
    {/* PDB File Upload */}
    <div>
      <Label className="text-sm font-medium text-gray-300">
        Target Structure (PDB)
      </Label>
      <div className="mt-1">
        <div className="flex items-center gap-2">
          <input
            type="file"
            id="pdb-file-upload"
            accept=".pdb"
            onChange={onPdbFileChange}
            className="hidden"
            disabled={isViewMode}
          />
          <label
            htmlFor="pdb-file-upload"
            className={`flex items-center gap-2 px-3 py-2 bg-gray-700/50 border border-gray-600 rounded-md cursor-pointer hover:bg-gray-700 transition-colors text-sm ${
              isViewMode ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            <Upload className="h-4 w-4" />
            Upload PDB
          </label>
          {pdbFile && (
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="bg-gray-700">
                {pdbFile.name}
              </Badge>
              {!isViewMode && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onPdbFileChange(null)}
                  className="h-6 w-6 p-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          )}
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Upload target protein structure in PDB format
        </p>
      </div>
    </div>

    {/* Target Chain Selection */}
    {pdbFile && pdbFile.chains && (
      <div>
        <Label htmlFor="target-chain" className="text-sm font-medium text-gray-300">
          Target Chain
        </Label>
        <select
          id="target-chain"
          value={targetChain}
          onChange={(e) => !isViewMode && onTargetChainChange(e.target.value)}
          className="mt-1 w-full bg-gray-800/50 border-gray-700 text-white rounded-md px-3 py-2"
          disabled={isViewMode}
        >
          <option value="">Select chain...</option>
          {pdbFile.chains.map(chain => (
            <option key={chain} value={chain}>Chain {chain}</option>
          ))}
        </select>
      </div>
    )}

    {/* Hotspot Residues */}
    <div>
      <Label htmlFor="hotspot-residues" className="text-sm font-medium text-gray-300">
        Hotspot Residues
      </Label>
      <Input
        id="hotspot-residues"
        placeholder="e.g., A:123, A:125, B:45"
        value={hotspotResidues}
        onChange={(e) => !isViewMode && onHotspotResiduesChange(e.target.value)}
        className="mt-1 bg-gray-800/50 border-gray-700 text-white"
        readOnly={isViewMode}
      />
      <p className="text-xs text-gray-400 mt-2">
        Specify residues to target (format: Chain:ResidueNumber)
      </p>
    </div>

    {/* Design Parameters */}
    <div className="space-y-4 p-4 bg-gray-800/30 rounded-lg">
      <h4 className="text-sm font-medium text-gray-300">Design Parameters</h4>
      
      {/* Number of Designs */}
      <div>
        <Label htmlFor="num-designs" className="text-sm text-gray-400">
          Number of Designs: {numDesigns}
        </Label>
        <input
          type="range"
          id="num-designs"
          min="1"
          max="100"
          value={numDesigns}
          onChange={(e) => !isViewMode && onNumDesignsChange(parseInt(e.target.value))}
          className="mt-2 w-full"
          disabled={isViewMode}
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>1</span>
          <span>100</span>
        </div>
      </div>

      {/* Framework Selection */}
      <div>
        <Label htmlFor="framework" className="text-sm text-gray-400">
          Nanobody Framework
        </Label>
        <select
          id="framework"
          value={framework}
          onChange={(e) => !isViewMode && onFrameworkChange(e.target.value as any)}
          className="mt-1 w-full bg-gray-800/50 border-gray-700 text-white rounded-md px-3 py-2"
          disabled={isViewMode}
        >
          <option value="vhh">VHH (Camelid)</option>
          <option value="humanized">Humanized VHH</option>
          <option value="camelid">Generic Camelid</option>
        </select>
      </div>
    </div>
  </div>
);


export const InputSection: React.FC<InputSectionProps> = ({
  selectedTask,
  sequenceInputs,
  onSequenceInputsChange,
  ligands,
  onLigandsChange,
  workflowName,
  onWorkflowNameChange,
  useMSAServer,
  onUseMSAServerChange,
  usePotentials,
  onUsePotentialsChange,
  onPredictionStart,
  onPredictionComplete,
  onPredictionError,
  isViewMode,
  isReadOnlyMode = false,
  submittedValues,
  onNewPrediction
}) => {
  // Early return for read-only mode
  if (isReadOnlyMode && submittedValues) {
    return (
      <ReadOnlyInputDisplay 
        taskType={selectedTask}
        values={submittedValues}
        onNewPrediction={onNewPrediction}
      />
    );
  }

  const [isRunning, setIsRunning] = useState(false);
  const [fileUploadError, setFileUploadError] = useState<string | null>(null);
  const [isProcessingFile, setIsProcessingFile] = useState(false);
  
  // Task-specific state for RFAntibody
  const [taskInputs, setTaskInputs] = useState({
    // Nanobody Design
    pdbFile: null as PDBFile | null,
    targetChain: '',
    hotspotResidues: '',
    numDesigns: 10,
    framework: 'vhh' as 'vhh' | 'humanized' | 'camelid',
    jobName: '',
    
    // CDR Optimization (future)
    antibodyPdb: null as PDBFile | null,
    targetPdb: null as PDBFile | null,
    
    // Epitope Targeted Design (future)
    epitopeResidues: '',
    
    // Antibody De Novo Design (future)
    designConstraints: ''
  });

  // Sync task-specific inputs with parent state for proper read-only display
  useEffect(() => {
    switch (selectedTask) {
      case 'nanobody_design':
        // For RFAntibody, we'll store the PDB file name and hotspot residues
        if (taskInputs.jobName !== workflowName) {
          onWorkflowNameChange(taskInputs.jobName);
        }
        break;
      // Other task types will be implemented later
    }
  }, [taskInputs, selectedTask]);

  // Sync workflow name for all task types
  useEffect(() => {
    if (taskInputs.jobName && taskInputs.jobName !== workflowName) {
      onWorkflowNameChange(taskInputs.jobName);
    }
  }, [taskInputs.jobName]);

  const updateSequenceInput = (value: string) => {
    onSequenceInputsChange([value]);
  };



  const validateInputs = () => {
    switch (selectedTask) {
      case 'nanobody_design':
        if (!taskInputs.pdbFile) {
          return "Please upload a target PDB file";
        }
        if (!taskInputs.targetChain) {
          return "Please select a target chain";
        }
        if (!taskInputs.hotspotResidues.trim()) {
          return "Please specify hotspot residues";
        }
        return null;
        
      case 'cdr_optimization':
      case 'epitope_targeted_design':
      case 'antibody_de_novo_design':
        return "This task is not yet implemented";
        
      default:
        return "Please select a valid task";
    }
  };


  const pollJobStatus = async (jobId: string) => {
    console.log('pollJobStatus called with jobId:', jobId);
    const maxAttempts = 180; // 30 minutes max (10 second intervals)
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      try {
        console.log(`Polling attempt ${attempts + 1}/${maxAttempts} for job ${jobId}`);
        const response = await fetch(`/api/v2/models/rfantibody/status/${jobId}`);
        console.log('Poll response status:', response.status);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('Poll error response:', errorText);
          throw new Error(`Failed to fetch job status: ${response.status} - ${errorText}`);
        }
        
        const jobStatus = await response.json();
        console.log('Job status response:', jobStatus);
        
        if (jobStatus.status === 'completed') {
          // Job completed successfully
          if (jobStatus.results) {
            onPredictionComplete(jobStatus.results);
          } else {
            onPredictionError('Job completed but no result data available');
          }
          return;
        } else if (jobStatus.status === 'failed') {
          // Job failed
          const errorMsg = jobStatus.results?.error || jobStatus.message || 'Job failed';
          onPredictionError(errorMsg);
          return;
        } else if (jobStatus.status === 'running' || jobStatus.status === 'pending') {
          // Job still running, continue polling
          attempts++;
          await new Promise(resolve => setTimeout(resolve, 10000)); // Wait 10 seconds
        } else {
          // Unknown status
          onPredictionError(`Unknown job status: ${jobStatus.status}`);
          return;
        }
      } catch (error) {
        console.error('Error polling job status:', error);
        console.error('Poll error details:', error instanceof Error ? error.message : 'Unknown polling error');
        attempts++;
        
        if (attempts >= maxAttempts) {
          onPredictionError('Job polling timeout - please check job status manually');
          return;
        }
        
        await new Promise(resolve => setTimeout(resolve, 10000)); // Wait 10 seconds before retry
      }
    }
    
    // If we get here, polling timed out
    onPredictionError('Job polling timeout - job may still be running');
  };

  const updateTaskInput = (field: string, value: any) => {
    console.log('updateTaskInput called - field:', field, 'value:', value);
    setTaskInputs(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // PDB file upload handler
  const handlePdbFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdb')) {
      setFileUploadError('Please upload a PDB file (.pdb extension)');
      return;
    }
    
    setIsProcessingFile(true);
    setFileUploadError(null);
    
    try {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        
        // Simple chain detection - look for ATOM records and extract chain IDs
        const chains = new Set<string>();
        const lines = content.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('ATOM') || line.startsWith('HETATM')) {
            const chainId = line.substring(21, 22).trim();
            if (chainId && chainId !== ' ') {
              chains.add(chainId);
            }
          }
        }
        
        const pdbFile: PDBFile = {
          name: file.name,
          content: content,
          chains: Array.from(chains).sort()
        };
        
        updateTaskInput('pdbFile', pdbFile);
        
        // Auto-select first chain if available
        if (pdbFile.chains && pdbFile.chains.length > 0) {
          updateTaskInput('targetChain', pdbFile.chains[0]);
        }
        
        setIsProcessingFile(false);
      };
      
      reader.onerror = () => {
        setFileUploadError('Failed to read PDB file');
        setIsProcessingFile(false);
      };
      
      reader.readAsText(file);
      
    } catch (error) {
      setFileUploadError(error instanceof Error ? error.message : 'Failed to process PDB file');
      setIsProcessingFile(false);
    } finally {
      // Clear the input
      event.target.value = '';
    }
  };

  const getTaskInputs = () => {
    switch (selectedTask) {
      case 'nanobody_design':
        return (
          <NanobodyDesignInputs
            pdbFile={taskInputs.pdbFile}
            onPdbFileChange={handlePdbFileUpload}
            targetChain={taskInputs.targetChain}
            onTargetChainChange={(value) => !isViewMode && updateTaskInput('targetChain', value)}
            hotspotResidues={taskInputs.hotspotResidues}
            onHotspotResiduesChange={(value) => !isViewMode && updateTaskInput('hotspotResidues', value)}
            numDesigns={taskInputs.numDesigns}
            onNumDesignsChange={(value) => !isViewMode && updateTaskInput('numDesigns', value)}
            framework={taskInputs.framework}
            onFrameworkChange={(value) => !isViewMode && updateTaskInput('framework', value)}
            jobName={taskInputs.jobName || 'nanobody_design'}
            onJobNameChange={(value) => !isViewMode && updateTaskInput('jobName', value)}
            isViewMode={isViewMode}
          />
        );
        
      case 'cdr_optimization':
        // TODO: Implement CDR optimization inputs
        return (
          <div className="text-gray-400 text-center py-8">
            CDR Optimization - Coming Soon
          </div>
        );
        
      case 'epitope_targeted_design':
        // TODO: Implement epitope targeted design inputs
        return (
          <div className="text-gray-400 text-center py-8">
            Epitope Targeted Design - Coming Soon
          </div>
        );
        
      case 'antibody_de_novo_design':
        // TODO: Implement antibody de novo design inputs
        return (
          <div className="text-gray-400 text-center py-8">
            Antibody De Novo Design - Coming Soon
          </div>
        );
        
      default:
        return (
          <div className="text-gray-400 text-center py-8">
            Please select a task from the dropdown above
          </div>
        );
    }
  };

  const isReadyToRun = () => {
    switch (selectedTask) {
      case 'nanobody_design':
        return taskInputs.pdbFile !== null && 
               taskInputs.targetChain.length > 0 && 
               taskInputs.hotspotResidues.length > 0;
      case 'cdr_optimization':
      case 'epitope_targeted_design':
      case 'antibody_de_novo_design':
        return false; // Not implemented yet
      default:
        return false;
    }
  };

  const runPrediction = async () => {
    const validationError = validateInputs();
    if (validationError) {
      onPredictionError(validationError);
      return;
    }
    
    setIsRunning(true);
    onPredictionStart();
    
    try {
      let inputData: any = {};
      
      switch (selectedTask) {
        case 'nanobody_design':
          const pdbContent = taskInputs.pdbFile?.content || '';
          const hotspotList = taskInputs.hotspotResidues.split(',').map(h => h.trim()).filter(h => h);
          
          const requestBody = {
            pdb_content: pdbContent,
            hotspot_residues: hotspotList,
            num_designs: taskInputs.numDesigns,
            run_relax: false, // Could make this configurable later
            job_name: taskInputs.jobName || workflowName
          };
          
          console.log('🚀 Submitting RFAntibody prediction:', requestBody);
          
          const response = await fetch('/api/v2/models/rfantibody/predict', {
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
          console.log('🚀 RFAntibody prediction submitted:', result);
          
          // Check if we got a job ID for polling or a direct result
          if (result.job_id && result.status === 'running') {
            // Start polling for async job completion
            console.log('🔄 Starting to poll for job completion...');
            await pollJobStatus(result.job_id);
          } else if (result.job_id && result.status === 'completed') {
            // Job already completed (unlikely but possible)
            onPredictionComplete(result);
          } else {
            // Handle other response formats
            onPredictionComplete(result);
          }
          break;
          
        case 'cdr_optimization':
        case 'epitope_targeted_design':
        case 'antibody_de_novo_design':
          onPredictionError('This task is not yet implemented');
          return;
          
        default:
          onPredictionError('Unknown task type');
          return;
      }
    } catch (error) {
      onPredictionError(error instanceof Error ? error.message : 'Unknown error occurred');
    } finally {
      setIsRunning(false);
    }
  };


  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
        <div className="p-6 pb-16">
          {isViewMode ? (
            <div className="bg-gray-800/50 border border-gray-700 rounded-md p-3 mb-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-4 w-4 text-yellow-400" />
                <div>
                  <p className="text-yellow-400 text-sm font-medium">
                    Viewing Prediction Results
                  </p>
                  <p className="text-yellow-300 text-xs">
                    You can view the results but cannot modify parameters or run new predictions.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center mb-6">
              <Button
                onClick={runPrediction}
                disabled={!isReadyToRun() || isRunning}
                className="bg-blue-600 hover:bg-blue-700 text-white gap-2 px-8 py-3 text-lg font-semibold"
              >
                {isRunning ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="h-5 w-5" />
                    Run Prediction
                  </>
                )}
              </Button>
            </div>
          )}

          {/* Prediction Status */}
          {isRunning && (
            <div className="bg-blue-900/30 border border-blue-700 rounded-md p-3 mb-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                <div>
                  <p className="text-blue-400 text-sm font-medium">
                    Running {selectedTask.replace(/_/g, ' ').toLowerCase()} prediction...
                  </p>
                  <p className="text-blue-300 text-xs">
                    {selectedTask === 'nanobody_design' 
                      ? 'Nanobody design may take 10-20 minutes depending on complexity...'
                      : 'This may take several minutes depending on the task complexity...'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Task-specific inputs */}
          <Card className="bg-gray-800/50 border-gray-700 mb-6">
            <CardHeader className="pb-3">
              <CardTitle className="text-white text-lg">
                {selectedTask.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} Parameters
              </CardTitle>
              {selectedTask === 'nanobody_design' && (
                <p className="text-gray-400 text-sm mt-2">
                  Design nanobody sequences to bind specific epitopes on the target protein using RFAntibody.
                </p>
              )}
              {selectedTask === 'cdr_optimization' && (
                <p className="text-gray-400 text-sm mt-2">
                  Optimize CDR regions to improve binding affinity and specificity of existing antibodies.
                </p>
              )}
              {selectedTask === 'epitope_targeted_design' && (
                <p className="text-gray-400 text-sm mt-2">
                  Design antibodies to target specific epitope regions on the antigen surface.
                </p>
              )}
              {selectedTask === 'antibody_de_novo_design' && (
                <p className="text-gray-400 text-sm mt-2">
                  Generate complete antibody sequences from scratch using RFAntibody modeling.
                </p>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {getTaskInputs()}
            </CardContent>
          </Card>


          {/* Task-specific notices */}
          {!isViewMode && (
            <div className="bg-gray-800/30 border border-gray-700 rounded-md p-3 mb-6">
              <p className="text-gray-400 text-xs">
                {selectedTask === 'nanobody_design' && 
                  'Nanobody sequences will be designed to bind specific epitopes on the target protein using RFAntibody.'
                }
                {selectedTask === 'cdr_optimization' && 
                  'CDR optimization will improve binding affinity and specificity of existing antibody sequences.'
                }
                {selectedTask === 'epitope_targeted_design' && 
                  'Antibodies will be designed to target specific epitope regions on the antigen.'
                }
                {selectedTask === 'antibody_de_novo_design' && 
                  'Complete antibody sequences will be designed from scratch using RFAntibody.'
                }
                {!isReadyToRun() && (
                  <span className="block mt-1 text-yellow-500">
                    {selectedTask === 'nanobody_design' 
                      ? 'Please upload a target PDB file, select a chain, and specify hotspot residues to run prediction.'
                      : 'This prediction task is not yet implemented.'
                    }
                  </span>
                )}
              </p>
            </div>
          )}

          {/* Settings */}
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader className="pb-3">
              <CardTitle className="text-white text-sm">Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-gray-300">Folder</h3>
                  <div className="bg-gray-800/50 border border-gray-700 rounded-md p-2 flex items-center gap-2">
                    <Folder className="h-3 w-3 text-gray-500" />
                    <span className="text-gray-300 text-sm">Home</span>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-gray-300">Configuration Options</h3>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="use-msa"
                        checked={useMSAServer}
                        onCheckedChange={!isViewMode ? onUseMSAServerChange : undefined}
                        disabled={isViewMode}
                      />
                      <Label htmlFor="use-msa" className="text-xs text-gray-300">
                        Use MSA Server
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="use-potentials"
                        checked={usePotentials}
                        onCheckedChange={!isViewMode ? onUsePotentialsChange : undefined}
                        disabled={isViewMode}
                      />
                      <Label htmlFor="use-potentials" className="text-xs text-gray-300">
                        Use Potentials
                      </Label>
                    </div>
                    {selectedTask === 'protein_structure' && (
                      <div className="text-xs text-gray-500 mt-2">
                        MSA (Multiple Sequence Alignment) improves structure accuracy for evolutionarily conserved proteins.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};