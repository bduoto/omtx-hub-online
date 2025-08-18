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

import { BatchScreeningInput } from './BatchScreeningInput';
import { BatchProteinLigandInput } from './BatchProteinLigandInput';
import { JobNameSection } from '@/components/ui/JobNameSection';
import { TargetProtein } from '@/components/ui/TargetProtein';
import { generateRandomJobName } from '@/utils/jobNameGenerator';

interface Ligand {
  name: string;
  formula: string;
}

interface Variant {
  name: string;
  sequence: string;
}

interface InputSectionProps {
  selectedTask: string;
  sequenceInputs: string[];
  onSequenceInputsChange: (inputs: string[]) => void;
  ligands: Ligand[];
  onLigandsChange: (ligands: Ligand[]) => void;
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
    ligands: Ligand[];
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

// Task-specific input components
const ProteinStructureInputs: React.FC<{
  sequence: string;
  onSequenceChange: (sequence: string) => void;
  jobName: string;
  onJobNameChange: (name: string) => void;
  proteinName: string;
  onProteinNameChange: (name: string) => void;
  useMSAServer: boolean;
  onUseMSAServerChange: (use: boolean) => void;
  usePotentials: boolean;
  onUsePotentialsChange: (use: boolean) => void;
  isViewMode?: boolean;
}> = ({ sequence, onSequenceChange, jobName, onJobNameChange, proteinName, onProteinNameChange, useMSAServer, onUseMSAServerChange, usePotentials, onUsePotentialsChange, isViewMode }) => (
  <div className="space-y-4">
    <JobNameSection
      jobName={jobName}
      onJobNameChange={onJobNameChange}
      isViewMode={isViewMode}
    />
    
    <TargetProtein
      proteinName={proteinName}
      onProteinNameChange={onProteinNameChange}
      proteinSequence={sequence}
      onProteinSequenceChange={onSequenceChange}
      isViewMode={isViewMode}
    />
    
    <div className="grid grid-cols-2 gap-4">
      <div className="flex items-center space-x-2">
        <Switch
          id="use-msa-server"
          checked={useMSAServer}
          onCheckedChange={!isViewMode ? onUseMSAServerChange : undefined}
          disabled={isViewMode}
        />
        <Label htmlFor="use-msa-server" className="text-sm text-gray-300">
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
        <Label htmlFor="use-potentials" className="text-sm text-gray-300">
          Use Potentials
        </Label>
      </div>
    </div>
  </div>
);

const ProteinComplexInputs: React.FC<{
  chainASequence: string;
  onChainASequenceChange: (sequence: string) => void;
  chainBSequence: string;
  onChainBSequenceChange: (sequence: string) => void;
  chainAName: string;
  onChainANameChange: (name: string) => void;
  chainBName: string;
  onChainBNameChange: (name: string) => void;
  jobName: string;
  onJobNameChange: (name: string) => void;
  isViewMode?: boolean;
}> = ({ chainASequence, onChainASequenceChange, chainBSequence, onChainBSequenceChange, chainAName, onChainANameChange, chainBName, onChainBNameChange, jobName, onJobNameChange, isViewMode }) => (
  <div className="space-y-4">
    <JobNameSection
      jobName={jobName}
      onJobNameChange={onJobNameChange}
      isViewMode={isViewMode}
    />

    <TargetProtein
      proteinName={chainAName}
      onProteinNameChange={onChainANameChange}
      proteinSequence={chainASequence}
      onProteinSequenceChange={onChainASequenceChange}
      isViewMode={isViewMode}
    />

    <Card className="bg-gray-800/50 border-gray-700">
      <CardHeader>
        <CardTitle className="text-white text-sm">Chain B Protein</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label htmlFor="chain-b-name" className="text-sm font-medium text-gray-300">
            Chain B Name
          </Label>
          <Input
            id="chain-b-name"
            placeholder="e.g., Light Chain"
            value={chainBName}
            onChange={(e) => !isViewMode && onChainBNameChange(e.target.value)}
            className="mt-1 bg-gray-800/50 border-gray-700 text-white"
            readOnly={isViewMode}
          />
        </div>

        <div>
          <Label htmlFor="chain-b-sequence" className="text-sm font-medium text-gray-300">
            Chain B Sequence
          </Label>
          <Textarea
            id="chain-b-sequence"
            placeholder="Enter chain B sequence (e.g., FVNQHLCGSHLVEALYLVCGERGFFYTPKT)"
            value={chainBSequence}
            onChange={(e) => !isViewMode && onChainBSequenceChange(e.target.value.toUpperCase())}
            className="mt-1 bg-gray-800/50 border-gray-700 text-white min-h-[80px] font-mono text-sm"
            rows={3}
            readOnly={isViewMode}
          />
          {chainBSequence && (
            <div className="mt-1 text-xs text-gray-400">
              Chain B: {chainBSequence.length} residues
            </div>
          )}
        </div>
      </CardContent>
    </Card>

    {chainASequence && chainBSequence && (
      <div className="bg-gray-800/30 border border-gray-700 rounded-md p-3">
        <div className="text-sm text-gray-300">
          <strong>Complex Summary:</strong>
        </div>
        <div className="text-xs text-gray-400 mt-1">
          Total complex: {chainASequence.length + chainBSequence.length} residues
        </div>
      </div>
    )}
  </div>
);

const MutationAnalysisInputs: React.FC<{
  wildtypeSequence: string;
  onWildtypeSequenceChange: (sequence: string) => void;
  mutation: string;
  onMutationChange: (mutation: string) => void;
  jobName: string;
  onJobNameChange: (name: string) => void;
  isViewMode?: boolean;
}> = ({ wildtypeSequence, onWildtypeSequenceChange, mutation, onMutationChange, jobName, onJobNameChange, isViewMode }) => (
  <div className="space-y-4">
    <div>
      <Label htmlFor="wildtype-sequence" className="text-sm font-medium text-gray-300">
        Wild-type Sequence
      </Label>
      <Textarea
        id="wildtype-sequence"
        placeholder="Enter wild-type protein sequence"
        value={wildtypeSequence}
        onChange={(e) => !isViewMode && onWildtypeSequenceChange(e.target.value.toUpperCase())}
        className="mt-1 bg-gray-800/50 border-gray-700 text-white min-h-[100px] font-mono text-sm"
        rows={4}
        readOnly={isViewMode}
      />
      {wildtypeSequence && (
        <div className="mt-1 text-xs text-gray-400">
          Length: {wildtypeSequence.length} residues
        </div>
      )}
    </div>
    
    <div>
      <Label htmlFor="mutation" className="text-sm font-medium text-gray-300">
        Mutation <span className="text-gray-500">(format: K2A)</span>
      </Label>
      <Input
        id="mutation"
        placeholder="K2A"
        value={mutation}
        onChange={(e) => !isViewMode && onMutationChange(e.target.value.toUpperCase())}
        className="mt-1 bg-gray-800/50 border-gray-700 text-white font-mono"
        readOnly={isViewMode}
      />
      {mutation && (
        <div className="mt-1 text-xs text-gray-400">
          Mutation: {mutation.charAt(0)}→{mutation.slice(-1)} at position {mutation.slice(1, -1)}
        </div>
      )}
    </div>
    
    <div>
      <Label htmlFor="job-name" className="text-sm font-medium text-gray-300">
        Job Name
      </Label>
      <Input
        id="job-name"
        placeholder="mutation_analysis"
        value={jobName}
        onChange={(e) => !isViewMode && onJobNameChange(e.target.value)}
        className="mt-1 bg-gray-800/50 border-gray-700 text-white"
        readOnly={isViewMode}
      />
    </div>
  </div>
);

const VariantComparisonInputs: React.FC<{
  variants: Variant[];
  onVariantsChange: (variants: Variant[]) => void;
  jobName: string;
  onJobNameChange: (name: string) => void;
  isViewMode?: boolean;
}> = ({ variants, onVariantsChange, jobName, onJobNameChange, isViewMode }) => {
  const addVariant = () => {
    if (variants.length < 5 && !isViewMode) {
      onVariantsChange([...variants, { name: '', sequence: '' }]);
    }
  };
  
  const removeVariant = (index: number) => {
    if (variants.length > 2 && !isViewMode) {
      onVariantsChange(variants.filter((_, i) => i !== index));
    }
  };
  
  const updateVariant = (index: number, field: 'name' | 'sequence', value: string) => {
    if (!isViewMode) {
      const updated = [...variants];
      updated[index][field] = field === 'sequence' ? value.toUpperCase() : value;
      onVariantsChange(updated);
    }
  };
  
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium text-gray-300">
          Protein Variants ({variants.length}/5)
        </Label>
        <Button
          onClick={addVariant}
          disabled={variants.length >= 5 || isViewMode}
          size="sm"
          className="bg-blue-600 hover:bg-blue-700"
        >
          <Plus className="h-4 w-4 mr-1" />
          Add Variant
        </Button>
      </div>
      
      {variants.map((variant, index) => (
        <Card key={index} className="bg-gray-800/30 border-gray-700">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-gray-300">
                Variant {index + 1}
              </h4>
              {variants.length > 2 && !isViewMode && (
                <Button
                  onClick={() => removeVariant(index)}
                  size="sm"
                  variant="ghost"
                  className="text-red-400 hover:text-red-300"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
            
            <div className="space-y-3">
              <div>
                <Label className="text-xs text-gray-400">
                  Variant Name
                </Label>
                <Input
                  placeholder={index === 0 ? "Wild-type" : `Variant ${String.fromCharCode(65 + index - 1)}`}
                  value={variant.name}
                  onChange={(e) => updateVariant(index, 'name', e.target.value)}
                  className="mt-1 bg-gray-800/50 border-gray-700 text-white text-sm"
                  readOnly={isViewMode}
                />
              </div>
              
              <div>
                <Label className="text-xs text-gray-400">
                  Sequence
                </Label>
                <Textarea
                  placeholder="Enter protein sequence"
                  value={variant.sequence}
                  onChange={(e) => updateVariant(index, 'sequence', e.target.value)}
                  className="mt-1 bg-gray-800/50 border-gray-700 text-white min-h-[60px] font-mono text-xs"
                  rows={2}
                  readOnly={isViewMode}
                />
                {variant.sequence && (
                  <div className="mt-1 text-xs text-gray-500">
                    Length: {variant.sequence.length} residues
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
      
      <div>
        <Label htmlFor="job-name" className="text-sm font-medium text-gray-300">
          Job Name
        </Label>
        <Input
          id="job-name"
          placeholder="variant_comparison"
          value={jobName}
          onChange={(e) => !isViewMode && onJobNameChange(e.target.value)}
          className="mt-1 bg-gray-800/50 border-gray-700 text-white"
          readOnly={isViewMode}
        />
      </div>
    </div>
  );
};

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
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isProcessingFile, setIsProcessingFile] = useState(false);
  
  // Task-specific state
  const [taskInputs, setTaskInputs] = useState({
    // Protein Structure
    sequence: '',
    jobName: generateRandomJobName(),
    structureProteinName: '',
    
    // Protein Complex
    chainASequence: '',
    chainBSequence: '',
    chainAName: '',
    chainBName: '',
    complexJobName: generateRandomJobName(),
    
    // Mutation Analysis
    wildtypeSequence: '',
    mutation: '',
    mutationProteinName: '',
    mutationJobName: generateRandomJobName(),
    
    // Variant Comparison
    variants: [
      { name: 'Wild-type', sequence: '' },
      { name: 'Variant A', sequence: '' }
    ] as Variant[],
    variantProteinName: '',
    variantJobName: generateRandomJobName(),
    
    // Protein-Ligand Binding (existing)
    proteinSequence: sequenceInputs[0] || '',
    ligandSmiles: ligands[0]?.formula || '',
    bindingProteinName: '',
    bindingJobName: generateRandomJobName()
  });

  const updateSequenceInput = (value: string) => {
    onSequenceInputsChange([value]);
  };

  const updateLigand = (index: number, field: 'name' | 'formula', value: string) => {
    const newLigands = [...ligands];
    newLigands[index] = { ...newLigands[index], [field]: value };
    onLigandsChange(newLigands);
  };

  const addLigand = () => {
    onLigandsChange([...ligands, { name: '', formula: '' }]);
  };

  const removeLigand = (index: number) => {
    if (ligands.length > 1) {
      const newLigands = ligands.filter((_, i) => i !== index);
      onLigandsChange(newLigands);
    }
  };

  const clearAllLigands = () => {
    onLigandsChange([{ name: '', formula: '' }]);
    setUploadedFile(null);
    setFileUploadError(null);
  };

  // SMILES validation function
  const isValidSMILES = (smiles: string): boolean => {
    if (!smiles || smiles.trim().length === 0) return false;
    
    const trimmed = smiles.trim();
    
    // Reject common invalid patterns
    if (trimmed.includes(' ') && trimmed.split(' ').length > 2) {
      return false; // Likely descriptive text with multiple spaces
    }
    
    // Reject if it contains common English words that indicate it's not a SMILES
    const invalidWords = ['and', 'or', 'the', 'of', 'in', 'with', 'to', 'from', 'test', 'frontend', 'backend', 'example'];
    const lowerCase = trimmed.toLowerCase();
    for (const word of invalidWords) {
      if (lowerCase.includes(word)) {
        return false;
      }
    }
    
    // Basic SMILES validation - check for valid characters only
    const validChars = /^[A-Za-z0-9\[\]()=#@+\-\\.\\/:]*$/;
    if (!validChars.test(trimmed)) return false;
    
    // Check for balanced brackets and parentheses
    const brackets = trimmed.match(/\[|\]/g);
    const parentheses = trimmed.match(/\(|\)/g);
    
    if (brackets && brackets.length % 2 !== 0) return false;
    if (parentheses && parentheses.length % 2 !== 0) return false;
    
    // Must contain at least one letter (element symbol)
    if (!/[A-Za-z]/.test(trimmed)) return false;
    
    // Should not be too long (most SMILES are under 200 characters)
    if (trimmed.length > 300) return false;
    
    return true;
  };

  // CSV/XLS file parsing function
  const parseFile = (file: File): Promise<Ligand[]> => {
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

          const ligands: Ligand[] = [];
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
              name = `Compound ${lineNumber}`;
            } else if (columns.length >= 2) {
              // Multiple columns - try to detect SMILES vs name
              const col1 = columns[0];
              const col2 = columns[1];
              
              // Heuristic: longer strings with chemical characters are likely SMILES
              if (isValidSMILES(col1)) {
                smiles = col1;
                name = col2 || `Compound ${lineNumber}`;
              } else if (isValidSMILES(col2)) {
                name = col1 || `Compound ${lineNumber}`;
                smiles = col2;
              } else {
                // If neither looks like SMILES, use first as name, second as SMILES
                name = col1 || `Compound ${lineNumber}`;
                smiles = col2;
              }
            }
            
            if (!isValidSMILES(smiles)) {
              errors.push(`Line ${lineNumber}: Invalid SMILES "${smiles}"`);
              return;
            }
            
            ligands.push({ name: name || `Compound ${lineNumber}`, formula: smiles });
          });
          
          if (ligands.length === 0) {
            reject(new Error('No valid SMILES found in file'));
            return;
          }
          
          if (errors.length > 0 && errors.length === dataLines.length) {
            reject(new Error(`All entries failed validation: ${errors.slice(0, 3).join(', ')}${errors.length > 3 ? '...' : ''}`));
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
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    // Validate file type
    const allowedTypes = ['.csv', '.txt', '.xls', '.xlsx'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!allowedTypes.includes(fileExtension)) {
      setFileUploadError('Please upload a CSV, TXT, XLS, or XLSX file');
      return;
    }
    
    setIsProcessingFile(true);
    setFileUploadError(null);
    setUploadedFile(file);
    
    try {
      let parsedLigands: Ligand[];
      
      if (fileExtension === '.csv' || fileExtension === '.txt') {
        parsedLigands = await parseFile(file);
      } else {
        // For XLS/XLSX files, we'd need a library like xlsx
        // For now, show a message to convert to CSV
        throw new Error('XLS/XLSX files not yet supported. Please convert to CSV or TXT format.');
      }
      
      if (parsedLigands.length > 100) {
        setFileUploadError(`File contains ${parsedLigands.length} ligands. Maximum 100 ligands per batch.`);
        return;
      }
      
      // Replace current ligands with uploaded ones
      onLigandsChange(parsedLigands);
      setFileUploadError(null);
      
    } catch (error) {
      setFileUploadError(error instanceof Error ? error.message : 'Failed to process file');
      setUploadedFile(null);
    } finally {
      setIsProcessingFile(false);
      // Clear the input
      event.target.value = '';
    }
  };

  const validateInputs = () => {
    switch (selectedTask) {
      case 'protein_structure':
        const hasStructureSequence = taskInputs.sequence && taskInputs.sequence.trim().length > 0;
        if (!hasStructureSequence) {
          return "Please provide a protein sequence for structure prediction";
        }
        if (taskInputs.sequence.trim().length < 10) {
          return "Protein sequence must be at least 10 amino acids long";
        }
        // Validate amino acid sequence
        const validAminoAcids = /^[ACDEFGHIKLMNPQRSTVWY]+$/i;
        if (!validAminoAcids.test(taskInputs.sequence.trim())) {
          return "Protein sequence contains invalid amino acid codes. Please use standard single-letter codes (A-Z excluding B, J, O, U, X, Z)";
        }
        return null;
        
      case 'protein_ligand_binding':
      default:
        const hasSequence = sequenceInputs[0] && sequenceInputs[0].trim().length > 0;
        const hasLigands = ligands.some(ligand => ligand.formula.trim().length > 0);
        
        if (!hasSequence) {
          return "Please provide a protein sequence";
        }
        if (!hasLigands) {
          return "Please provide at least one ligand SMILES";
        }
        
        // Validate SMILES strings
        for (const ligand of ligands) {
          if (ligand.formula.trim().length > 0 && !isValidSMILES(ligand.formula)) {
            return `Invalid SMILES string: "${ligand.formula}". Please provide a valid molecular SMILES notation.`;
          }
        }
        
        return null;
    }
  };

  const convertToUnifiedFormat = (taskType: string, inputData: any, sequences: string[], ligands: Ligand[], taskInputs: any) => {
    // Convert UI format to unified API format
    switch (taskType) {
      case 'protein_ligand_binding':
        return {
          protein_sequence: sequences[0] || '',
          ligand_smiles: ligands[0]?.formula || '',
          protein_name: taskInputs.jobName || ligands[0]?.name || 'protein_ligand_complex'
        };
      
      case 'protein_structure':
        return {
          protein_sequence: taskInputs.sequence || '',
          protein_name: taskInputs.jobName || 'protein_structure'
        };
      
      case 'protein_complex':
        return {
          chain_a_sequence: taskInputs.chainASequence || '',
          chain_b_sequence: taskInputs.chainBSequence || ''
        };
      
      case 'binding_site_prediction':
        return {
          protein_sequence: taskInputs.wildtypeSequence || ''
        };
      
      case 'variant_comparison':
        return {
          wildtype_sequence: taskInputs.wildtypeSequence || '',
          variants: taskInputs.variants || []
        };
      
      case 'drug_discovery':
        return {
          protein_sequence: sequences[0] || '',
          compound_library: ligands.map(ligand => ({
            name: ligand.name,
            smiles: ligand.formula
          }))
        };
      
      default:
        return inputData;
    }
  };

  const pollJobStatus = async (jobId: string) => {
    console.log('🔄 pollJobStatus called with jobId:', jobId);
    const maxAttempts = 180; // 30 minutes max (10 second intervals)
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      try {
        console.log(`🔄 Polling attempt ${attempts + 1}/${maxAttempts} for job ${jobId}`);
        const response = await fetch(`/api/v2/jobs/${jobId}`);
        console.log('📡 Poll response status:', response.status);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('❌ Poll error response:', errorText);
          throw new Error(`Failed to fetch job status: ${response.status} - ${errorText}`);
        }
        
        const jobStatus = await response.json();
        console.log('📊 Job status response:', jobStatus);
        console.log('📊 Job status:', jobStatus.status);
        console.log('📊 Result data keys:', jobStatus.result_data ? Object.keys(jobStatus.result_data) : 'No result_data');
        
        if (jobStatus.status === 'completed') {
          // Job completed successfully
          console.log('✅ Job completed! Processing result data...');
          
          // Check for result data in different possible locations
          const resultData = jobStatus.result_data || jobStatus.results || jobStatus.output_data;
          
          if (resultData) {
            console.log('✅ Found result data with keys:', Object.keys(resultData));
            console.log('✅ Affinity:', resultData.affinity);
            console.log('✅ Confidence:', resultData.confidence);
            console.log('✅ PTM Score:', resultData.ptm_score);
            
            const completeResult = {
              ...resultData,
              job_id: jobId,
              status: 'completed',
              task_type: jobStatus.task_type || 'protein_ligand_binding'
            };
            
            console.log('🎯 Calling onPredictionComplete with:', completeResult);
            onPredictionComplete(completeResult);
            console.log('🎯 onPredictionComplete called successfully');
          } else {
            console.error('❌ No result data found in response:', jobStatus);
            console.error('❌ Available keys:', Object.keys(jobStatus));
            onPredictionError('Job completed but no result data available');
          }
          return;
        } else if (jobStatus.status === 'failed') {
          // Job failed
          console.log('❌ Job failed:', jobStatus.error_message);
          onPredictionError(jobStatus.error_message || 'Job failed');
          return;
        } else if (jobStatus.status === 'running' || jobStatus.status === 'pending') {
          // Job still running, continue polling
          console.log(`⏳ Job still ${jobStatus.status}, continuing to poll...`);
          attempts++;
          await new Promise(resolve => setTimeout(resolve, 10000)); // Wait 10 seconds
        } else {
          // Unknown status
          console.error('❓ Unknown job status:', jobStatus.status);
          onPredictionError(`Unknown job status: ${jobStatus.status}`);
          return;
        }
      } catch (error) {
        console.error('❌ Error polling job status:', error);
        console.error('❌ Poll error details:', error instanceof Error ? error.message : 'Unknown polling error');
        attempts++;
        
        if (attempts >= maxAttempts) {
          onPredictionError('Job polling timeout - please check job status manually');
          return;
        }
        
        await new Promise(resolve => setTimeout(resolve, 10000)); // Wait 10 seconds before retry
      }
    }
    
    // If we get here, polling timed out
    console.error('⏰ Job polling timeout - job may still be running');
    onPredictionError('Job polling timeout - job may still be running');
  };

  const updateTaskInput = (field: string, value: any) => {
    console.log('updateTaskInput called - field:', field, 'value:', value);
    setTaskInputs(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const getTaskInputs = () => {
    switch (selectedTask) {
      case 'protein_structure':
        return (
          <ProteinStructureInputs
            sequence={taskInputs.sequence}
            onSequenceChange={(value) => !isViewMode && updateTaskInput('sequence', value)}
            jobName={taskInputs.jobName || 'structure_prediction'}
            onJobNameChange={(value) => !isViewMode && updateTaskInput('jobName', value)}
            proteinName={taskInputs.structureProteinName}
            onProteinNameChange={(value) => !isViewMode && updateTaskInput('structureProteinName', value)}
            useMSAServer={useMSAServer}
            onUseMSAServerChange={!isViewMode ? onUseMSAServerChange : () => {}}
            usePotentials={usePotentials}
            onUsePotentialsChange={!isViewMode ? onUsePotentialsChange : () => {}}
            isViewMode={isViewMode}
          />
        );
        
      case 'protein_complex':
        return (
          <ProteinComplexInputs
            chainASequence={taskInputs.chainASequence}
            onChainASequenceChange={(value) => !isViewMode && updateTaskInput('chainASequence', value)}
            chainBSequence={taskInputs.chainBSequence}
            onChainBSequenceChange={(value) => !isViewMode && updateTaskInput('chainBSequence', value)}
            chainAName={taskInputs.chainAName}
            onChainANameChange={(value) => !isViewMode && updateTaskInput('chainAName', value)}
            chainBName={taskInputs.chainBName}
            onChainBNameChange={(value) => !isViewMode && updateTaskInput('chainBName', value)}
            jobName={taskInputs.complexJobName || 'protein_complex'}
            onJobNameChange={(value) => !isViewMode && updateTaskInput('complexJobName', value)}
            isViewMode={isViewMode}
          />
        );
        
      case 'binding_site_prediction':
        return (
          <MutationAnalysisInputs
            wildtypeSequence={taskInputs.wildtypeSequence}
            onWildtypeSequenceChange={(value) => !isViewMode && updateTaskInput('wildtypeSequence', value)}
            mutation={taskInputs.mutation}
            onMutationChange={(value) => !isViewMode && updateTaskInput('mutation', value)}
            jobName={taskInputs.jobName || 'mutation_analysis'}
            onJobNameChange={(value) => !isViewMode && updateTaskInput('jobName', value)}
            isViewMode={isViewMode}
          />
        );
        
      case 'variant_comparison':
        return (
          <VariantComparisonInputs
            variants={taskInputs.variants}
            onVariantsChange={(value) => !isViewMode && updateTaskInput('variants', value)}
            jobName={taskInputs.jobName || 'variant_comparison'}
            onJobNameChange={(value) => !isViewMode && updateTaskInput('jobName', value)}
            isViewMode={isViewMode}
          />
        );
        
      case 'batch_protein_ligand_screening':
        return (
          <BatchProteinLigandInput
            onPredictionStart={onPredictionStart}
            onPredictionComplete={onPredictionComplete}
            onPredictionError={onPredictionError}
            isViewMode={isViewMode}
          />
        );
        
      case 'protein_ligand_binding':
      default:
        return (
          <div className="space-y-4">
            {/* Use new JobNameSection component */}
            <JobNameSection
              jobName={taskInputs.bindingJobName}
              onJobNameChange={(name) => setTaskInputs(prev => ({ ...prev, bindingJobName: name }))}
              isViewMode={isViewMode}
              isReadOnly={isReadOnlyMode}
            />

            {/* Use new TargetProtein component */}
            <TargetProtein
              proteinName={taskInputs.bindingProteinName}
              onProteinNameChange={(name) => setTaskInputs(prev => ({ ...prev, bindingProteinName: name }))}
              proteinSequence={sequenceInputs[0] || ''}
              onProteinSequenceChange={(sequence) => onSequenceInputsChange([sequence])}
              isViewMode={isViewMode}
              isReadOnly={isReadOnlyMode}
            />

            {/* Protein-Ligand Binding Parameters */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white text-sm">Protein-Ligand Binding Parameters</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="ligand-name" className="text-sm font-medium text-gray-300">
                    Ligand Name
                  </Label>
                  <Input
                    id="ligand-name"
                    placeholder="e.g., Aspirin"
                    value={ligands[0]?.name || ''}
                    onChange={(e) => !isViewMode && !isReadOnlyMode && onLigandsChange([{ 
                      name: e.target.value, 
                      formula: ligands[0]?.formula || '' 
                    }])}
                    className="mt-1 bg-gray-800/50 border-gray-700 text-white"
                    readOnly={isViewMode || isReadOnlyMode}
                  />
                </div>

                <div>
                  <Label htmlFor="ligand-smiles" className="text-sm font-medium text-gray-300">
                    Ligand SMILES
                  </Label>
                  <Input
                    id="ligand-smiles"
                    placeholder="Enter ligand in SMILES format (e.g., CC(=O)OC1=CC=CC=C1C(=O)O)"
                    value={ligands[0]?.formula || ''}
                    onChange={(e) => !isViewMode && !isReadOnlyMode && onLigandsChange([{ 
                      name: ligands[0]?.name || '', 
                      formula: e.target.value 
                    }])}
                    className="mt-1 bg-gray-800/50 border-gray-700 text-white font-mono"
                    readOnly={isViewMode || isReadOnlyMode}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Ligands Section - For future batch/multiple ligand functionality */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="text-white text-sm">Ligands</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-gray-400">
                  Multiple ligand support coming soon. Currently supporting single ligand prediction.
                </div>
                {isViewMode && ligands.length > 1 && (
                  <div className="mt-2 text-xs text-gray-400">
                    {ligands.length} ligands uploaded
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        );
    }
  };

  const isReadyToRun = () => {
    switch (selectedTask) {
      case 'protein_structure':
        console.log('Debug protein_structure - sequence:', taskInputs.sequence, 'length:', taskInputs.sequence.length);
        return taskInputs.sequence.length > 0;
      case 'protein_complex':
        return taskInputs.chainASequence.length > 0 && taskInputs.chainBSequence.length > 0;
      case 'binding_site_prediction':
        return taskInputs.wildtypeSequence.length > 0 && taskInputs.mutation.length > 0;
      case 'variant_comparison':
        return taskInputs.variants.filter(v => v.name && v.sequence).length >= 2;
      case 'protein_ligand_binding':
      default:
        return (sequenceInputs[0] || '').length > 0 && (ligands[0]?.formula || '').length > 0;
    }
  };

  const runPrediction = async () => {
    console.log('runPrediction called - selectedTask:', selectedTask, 'isReady:', isReadyToRun());
    if (!isReadyToRun()) {
      console.log('Not ready to run - returning early');
      return;
    }
    
    console.log('Starting prediction...');
    setIsRunning(true);
    onPredictionStart();
    
    try {
      // Prepare input data based on task type
      let inputData: any = {};
      
      switch (selectedTask) {
        case 'protein_structure':
          inputData = {
            version: 1,
            sequences: [
              {
                protein: {
                  id: "A",
                  sequence: taskInputs.sequence
                }
              }
            ]
          };
          console.log('Prepared protein_structure inputData:', inputData);
          break;
          
        case 'protein_complex':
          inputData = {
            version: 1,
            sequences: [
              {
                protein: {
                  id: "A",
                  sequence: taskInputs.chainASequence
                }
              },
              {
                protein: {
                  id: "B",
                  sequence: taskInputs.chainBSequence
                }
              }
            ]
          };
          break;
          
        case 'binding_site_prediction':
          // For mutation analysis, we'll process both wild-type and mutant
          inputData = {
            version: 1,
            mutation_analysis: {
              wildtype_sequence: taskInputs.wildtypeSequence,
              mutation: taskInputs.mutation
            }
          };
          break;
          
        case 'variant_comparison':
          inputData = {
            version: 1,
            variants: taskInputs.variants
              .filter(v => v.name && v.sequence)
              .map((variant, index) => ({
                protein: {
                  id: String.fromCharCode(65 + index),
                  sequence: variant.sequence,
                  name: variant.name
                }
              }))
          };
          break;
          
        case 'protein_ligand_binding':
        default:
          inputData = {
            version: 1,
            sequences: [
              {
                protein: {
                  id: "A",
                  sequence: sequenceInputs[0] || ''
                }
              },
              {
                ligand: {
                  id: "B",
                  smiles: ligands[0]?.formula || ''
                }
              }
            ],
            properties: [
              {
                affinity: {
                  binder: "B"
                }
              }
            ]
          };
          break;
      }
      
      // Convert to unified API format
      const unifiedInputData = convertToUnifiedFormat(selectedTask, inputData, sequenceInputs, ligands, taskInputs);
      console.log('Unified input data:', unifiedInputData);
      
      const requestBody = {
        model_id: "boltz2",
        task_type: selectedTask,
        input_data: unifiedInputData,
        job_name: taskInputs.jobName || workflowName,
        use_msa: useMSAServer,
        use_potentials: usePotentials
      };
      console.log('API request body:', requestBody);
      
      const response = await fetch('/api/v2/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
      
      console.log('API response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }
      
      const result = await response.json();
      console.log('API response result:', result);
      
      // For the unified API, we need to poll for job completion
      if (result.job_id) {
        console.log('Starting polling for job_id:', result.job_id);
        await pollJobStatus(result.job_id);
      } else {
        console.log('No job_id found, calling onPredictionComplete directly');
        onPredictionComplete(result);
      }
      
    } catch (error) {
      console.error('Prediction error:', error);
      console.error('Error stack:', error instanceof Error ? error.stack : 'No stack trace');
      onPredictionError(error instanceof Error ? error.message : 'Unknown error occurred');
    } finally {
      console.log('Finally block - setting isRunning to false');
      setIsRunning(false);
    }
  };

  // Function to poll batch progress
  const startBatchProgressPolling = (batchId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/batches/${batchId}`);
        if (response.ok) {
          const batchData = await response.json();
          
          // Update the result with current batch progress
          const updatedResult = {
            job_id: batchId,
            status: batchData.status,
            batch_mode: true,
            total_jobs: batchData.total_jobs,
            completed_jobs: batchData.completed_jobs,
            failed_jobs: batchData.failed_jobs,
            message: `Batch progress: ${batchData.completed_jobs}/${batchData.total_jobs} completed`,
            affinity: null,
            confidence: null,
            structure_file_base64: null
          };
          
          onPredictionComplete(updatedResult);
          
          // Stop polling if batch is complete
          if (batchData.status === 'completed' || batchData.status === 'failed' || batchData.status === 'partially_completed') {
            clearInterval(pollInterval);
            setIsRunning(false);
            
            // Fetch individual job results for display
            fetchBatchResults(batchId);
          }
        }
      } catch (error) {
        console.error('Error polling batch progress:', error);
      }
    }, 5000); // Poll every 5 seconds
  };

  // Function to fetch batch results
  const fetchBatchResults = async (batchId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/batches/${batchId}/jobs`);
      if (response.ok) {
        const jobsData = await response.json();
        
        // Create a summary result with all job data
        const batchResult = {
          job_id: batchId,
          status: 'batch_completed',
          batch_mode: true,
          batch_jobs: jobsData.jobs,
          total_jobs: jobsData.jobs.length,
          completed_jobs: jobsData.jobs.filter((job: any) => job.status === 'completed').length,
          failed_jobs: jobsData.jobs.filter((job: any) => job.status === 'failed').length,
          message: 'Batch prediction completed',
          affinity: null,
          confidence: null,
          structure_file_base64: null
        };
        
        onPredictionComplete(batchResult);
      }
    } catch (error) {
      console.error('Error fetching batch results:', error);
    }
  };

  const validLigandCount = ligands.filter(ligand => ligand.formula.trim().length > 0).length;

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
            selectedTask !== 'batch_protein_ligand_screening' && (
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
            )
          )}

          {/* Prediction Status */}
          {isRunning && (
            <div className="bg-blue-900/30 border border-blue-700 rounded-md p-3 mb-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                <div>
                  <p className="text-blue-400 text-sm font-medium">
                    Running {selectedTask === 'protein_structure' ? 'protein structure' : 
                             selectedTask === 'protein_ligand_binding' ? 'protein-ligand binding' : 
                             selectedTask.replace(/_/g, ' ').toLowerCase()} prediction...
                  </p>
                  <p className="text-blue-300 text-xs">
                    {selectedTask === 'protein_structure' 
                      ? 'Structure prediction may take 5-15 minutes depending on sequence length...'
                      : 'This may take 3-5 minutes depending on complexity...'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Task-specific inputs */}
          <Card className="bg-gray-800/50 border-gray-700 mb-6">
            <CardHeader className="pb-3">
              <CardTitle className="text-white text-lg">
                {selectedTask === 'protein_ligand_binding' ? 'Protein-Ligand Binding' : 
                 selectedTask === 'protein_structure' ? 'Protein Structure Prediction' :
                 selectedTask.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} Parameters
              </CardTitle>
              {selectedTask === 'protein_structure' && (
                <p className="text-gray-400 text-sm mt-2">
                  Predict the 3D structure of a single protein from its amino acid sequence using Boltz-2 AI.
                </p>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {getTaskInputs()}
            </CardContent>
          </Card>

          {/* View Mode Ligand Display */}
          {isViewMode && selectedTask === 'protein_ligand_binding' && ligands.length > 0 && (
            <Card className="bg-gray-800/50 border-gray-700 mb-6">
              <CardHeader className="pb-3">
                <CardTitle className="text-white text-sm">Ligand Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {ligands.map((ligand, index) => (
                  <div key={index} className="bg-gray-900/50 border border-gray-700 rounded-md p-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Name</label>
                        <div className="text-white text-sm">{ligand.name || `Ligand ${index + 1}`}</div>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">SMILES</label>
                        <div className="text-white text-sm font-mono break-all">{ligand.formula}</div>
                      </div>
                    </div>
                  </div>
                ))}
                <div className="text-xs text-gray-400">
                  {ligands.length} ligand{ligands.length > 1 ? 's' : ''} used in this prediction
                </div>
              </CardContent>
            </Card>
          )}

          {/* Ligands - Only show for Protein-Ligand Binding and not in view mode */}
          {selectedTask === 'protein_ligand_binding' && !isViewMode && (
            <>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-300">
                    Ligands {validLigandCount > 0 && <span className="text-blue-400">({validLigandCount} compounds)</span>}
                  </h3>
                  {ligands.length > 1 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={clearAllLigands}
                      className="text-gray-500 hover:text-red-400 text-xs"
                    >
                      Clear All
                    </Button>
                  )}
                </div>

                {/* File Upload Section */}
                <div className="bg-gray-800/50 border border-gray-700 rounded-md p-3">
                  <div className="flex items-center justify-between mb-3">
                    <label className="block text-xs text-gray-500">Batch Upload (CSV/TXT)</label>
                    {uploadedFile && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setUploadedFile(null);
                          setFileUploadError(null);
                        }}
                        className="text-gray-500 hover:text-red-400 h-6 w-6 p-0"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <input
                        type="file"
                        id="ligand-file-upload"
                        accept=".csv,.txt,.xls,.xlsx"
                        onChange={handleFileUpload}
                        className="hidden"
                        disabled={isProcessingFile}
                      />
                      <label
                        htmlFor="ligand-file-upload"
                        className={`flex items-center gap-2 px-3 py-2 bg-gray-700/50 border border-gray-600 rounded-md cursor-pointer hover:bg-gray-700 transition-colors text-sm ${
                          isProcessingFile ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                      >
                        {isProcessingFile ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Upload className="h-4 w-4" />
                        )}
                        {isProcessingFile ? 'Processing...' : 'Upload File'}
                      </label>
                      
                      {uploadedFile && (
                        <div className="flex items-center gap-2 text-sm text-green-400">
                          <FileText className="h-4 w-4" />
                          <span>{uploadedFile.name}</span>
                        </div>
                      )}
                    </div>
                    
                    <p className="text-xs text-gray-500">
                      Upload CSV/TXT with SMILES sequences. Format: "Name,SMILES" or just SMILES (one per line)
                    </p>
                    
                    {fileUploadError && (
                      <div className="text-xs text-red-400 bg-red-900/20 border border-red-800 rounded px-2 py-1">
                        {fileUploadError}
                      </div>
                    )}
                  </div>
                </div>

                {/* Individual Ligand Inputs */}
                <div className="space-y-3">
                  {ligands.map((ligand, index) => (
                    <div key={index} className="bg-gray-800/50 border border-gray-700 rounded-md p-3">
                      <div className="grid grid-cols-2 gap-3 mb-3">
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Name</label>
                          <Input
                            placeholder="Ligand name"
                            value={ligand.name}
                            onChange={(e) => updateLigand(index, 'name', e.target.value)}
                            className="bg-transparent border-gray-700 text-white text-sm h-8"
                            readOnly={isViewMode}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">SMILES</label>
                          <Input
                            placeholder="Enter SMILES (e.g., CCO, N[C@@H](Cc1ccc(O)cc1)C(=O)O)"
                            value={ligand.formula}
                            onChange={(e) => updateLigand(index, 'formula', e.target.value)}
                            className={`bg-transparent border-gray-700 text-white text-sm h-8 ${
                              ligand.formula && !isValidSMILES(ligand.formula) ? 'border-red-500' : ''
                            }`}
                            readOnly={isViewMode}
                          />
                          {ligand.formula && !isValidSMILES(ligand.formula) && (
                            <p className="text-xs text-red-400 mt-1">Invalid SMILES format</p>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2 justify-end">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => removeLigand(index)}
                          disabled={ligands.length === 1}
                          className="text-gray-500 hover:text-red-400 h-8 w-8 p-0"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={addLigand}
                    className="bg-transparent border-gray-700 text-gray-400 hover:bg-gray-800 text-sm"
                    disabled={isViewMode}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add ligand
                  </Button>
                </div>
              </div>

              {/* Task-specific notices */}
              <div className="bg-gray-800/30 border border-gray-700 rounded-md p-3 mb-6">
                <p className="text-gray-400 text-xs">
                  {validLigandCount > 1 
                    ? `Binding affinity values will be predicted for ${validLigandCount} protein-ligand combinations using Boltz-2 model.`
                    : 'Binding affinity value(s) will be predicted using Boltz-2 model.'
                  }
                  {!isReadyToRun() && (
                    <span className="block mt-1 text-yellow-500">
                      Please add a protein sequence and at least one ligand SMILES to run prediction.
                    </span>
                  )}
                </p>
              </div>
            </>
          )}

          {/* Structure Prediction Notice */}
          {selectedTask === 'protein_structure' && !isViewMode && (
            <div className="bg-gray-800/30 border border-gray-700 rounded-md p-3 mb-6">
              <p className="text-gray-400 text-xs">
                3D protein structure will be predicted from the amino acid sequence using Boltz-2 model.
                {!isReadyToRun() && (
                  <span className="block mt-1 text-yellow-500">
                    Please provide a valid protein sequence (at least 10 amino acids) to run structure prediction.
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