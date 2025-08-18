import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { 
  InfoIcon, 
  ChevronDown, 
  ChevronUp, 
  Eye,
  EyeOff
} from 'lucide-react';

import Header, { PREDICTION_TASKS } from '@/components/RFAntibody/Header';
import { InputSection } from '@/components/RFAntibody/InputSection';
import { OutputSection } from '@/components/RFAntibody/OutputSection';

interface PredictionResult {
  job_id: string;
  status: string;
  task_type: string;
  message: string;
  output_data?: any;
  affinity?: number;
  affinity_probability?: number;
  confidence?: number;
  ptm_score?: number;
  plddt_score?: number;
  structure_file_base64?: string;
  execution_time?: number;
  parameters?: any;
  modal_logs?: any[];
  error?: string;
}

const RFAntibody = () => {
  const location = useLocation();
  const [selectedTask, setSelectedTask] = useState('nanobody_design');
  const [predictionResult, setPredictionResult] = useState<PredictionResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isInputHidden, setIsInputHidden] = useState(false);
  const [isInputCollapsed, setIsInputCollapsed] = useState(false);
  const [isViewMode, setIsViewMode] = useState(false);
  const [isReadOnlyMode, setIsReadOnlyMode] = useState(false);
  const [submittedValues, setSubmittedValues] = useState<{
    sequences: string[];
    ligands: { name: string; formula: string }[];
    settings: {
      useMSAServer: boolean;
      usePotentials: boolean;
      workflowName: string;
    };
  } | null>(null);
  
  // State for InputSection compatibility
  const [sequenceInputs, setSequenceInputs] = useState(['']);
  const [ligands, setLigands] = useState([{ name: '', formula: '' }]);
  const [workflowName, setWorkflowName] = useState('(unnamed)');
  const [useMSAServer, setUseMSAServer] = useState(true);
  const [usePotentials, setUsePotentials] = useState(false);

  const currentTask = PREDICTION_TASKS.find(task => task.id === selectedTask) || PREDICTION_TASKS[0];

  // Handle saved job data from navigation
  useEffect(() => {
    const state = location.state as any;
    if (state?.savedJob && state?.viewMode) {
      const savedJob = state.savedJob;
      const results = state.predictionResult || savedJob.results;
      
      // Set view mode
      setIsViewMode(true);
      setIsInputCollapsed(true);
      
      // Populate form with saved job data
      if (savedJob.input_data || savedJob.inputs) {
        // Set task type from saved job - check multiple possible locations
        const inputData = savedJob.input_data || savedJob.inputs || {};
        const taskType = inputData.task_type || savedJob.task_type || inputData.input_data?.task_type || 'protein_ligand_binding';
        
        console.log('🔍 Saved job data:', savedJob);
        console.log('🔍 Input data:', inputData);
        console.log('🔍 Detected task type:', taskType);
        
        setSelectedTask(taskType);
        
        // Restore input data based on task type
        // inputData is already defined above
        
        // Protein-ligand binding inputs
        const proteinSequence = inputData.protein_sequence || inputData.input_data?.protein_sequence;
        if (proteinSequence) {
          setSequenceInputs([proteinSequence]);
        }
        
        const ligandSmiles = inputData.ligand_smiles || inputData.input_data?.ligand_smiles;
        const ligandName = inputData.ligand_name || inputData.input_data?.ligand_name;
        if (ligandSmiles) {
          setLigands([{ name: ligandName || 'Ligand', formula: ligandSmiles }]);
        }
        if (inputData.compound_library) {
          // Handle batch upload case
          const ligandList = inputData.compound_library.map((compound: any) => ({
            name: compound.name || 'Compound',
            formula: compound.smiles || compound.formula || ''
          }));
          setLigands(ligandList);
        }
        
        // Common settings
        setWorkflowName(savedJob.job_name || inputData.job_name || '(unnamed)');
        setUseMSAServer(inputData.use_msa_server ?? inputData.use_msa ?? true);
        setUsePotentials(inputData.use_potentials ?? false);
      }
      
      // Set prediction results
      setPredictionResult(results);
    }
  }, [location.state]);

  // Auto-collapse input section when results are available
  useEffect(() => {
    if (predictionResult && !isLoading && !error) {
      setIsInputCollapsed(true);
    }
  }, [predictionResult, isLoading, error]);

  const handleTaskChange = (taskId: string) => {
    // Don't allow task changes in view mode or read-only mode
    if (isViewMode || isReadOnlyMode) return;
    
    setSelectedTask(taskId);
    // Clear previous results when changing tasks
    setPredictionResult(null);
    setError(null);
    setIsInputCollapsed(false);
    setIsReadOnlyMode(false);
    setSubmittedValues(null);
  };

  const handlePredictionStart = () => {
    setIsLoading(true);
    setError(null);
    setPredictionResult(null);
    setIsInputCollapsed(false);
    
    // Capture submitted values for read-only display
    setSubmittedValues({
      sequences: [...sequenceInputs],
      ligands: [...ligands],
      settings: {
        useMSAServer,
        usePotentials,
        workflowName
      }
    });
    
    // Enable read-only mode
    setIsReadOnlyMode(true);
  };

  const handlePredictionResult = async (result: any) => {
    // Enhance result with Modal logs
    const enhancedResult = await enhanceResultWithModalLogs(result);
    setPredictionResult(enhancedResult);
    setIsLoading(false);
  };

  const handlePredictionError = (errorMessage: string) => {
    setError(errorMessage);
    setIsLoading(false);
    setIsInputCollapsed(false);
  };

  const handleNewPrediction = () => {
    // Reset to editable mode for new prediction
    setIsReadOnlyMode(false);
    setSubmittedValues(null);
    setPredictionResult(null);
    setError(null);
    setIsInputCollapsed(false);
  };

  const enhanceResultWithModalLogs = async (result: any): Promise<PredictionResult> => {
    try {
      // Try to fetch Modal logs for this job
      const response = await fetch(`/api/v2/jobs/${result.job_id}/logs`);
      if (response.ok) {
        const logData = await response.json();
        return {
          ...result,
          modal_logs: logData.logs || [],
        };
      }
    } catch (error) {
      console.warn('Could not fetch Modal logs:', error);
    }
    return result;
  };


  const getTaskInstructions = (taskId: string) => {
    const instructions = {
      'protein_ligand_binding': 'Enter a protein sequence and ligand SMILES to predict binding affinity and generate the 3D complex structure.',
      'protein_structure': 'Enter a protein sequence to predict its 3D structure using state-of-the-art folding models.',
      'protein_complex': 'Enter multiple protein sequences to predict how they interact and form complexes.',
      'binding_site_prediction': 'Upload a protein structure to identify potential binding sites and druggable cavities.',
      'variant_comparison': 'Compare a reference protein sequence with variants to assess structural and functional changes.',
      'drug_discovery': 'Screen compound libraries against target proteins to identify potential drug candidates.'
    };
    return instructions[taskId as keyof typeof instructions] || instructions['protein_ligand_binding'];
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      <Header 
        selectedTask={selectedTask}
        onTaskChange={handleTaskChange}
        readonly={isViewMode}
      />
      
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex-1 min-h-0 p-4">
          <ResizablePanelGroup 
            direction="horizontal" 
            className="h-full border border-gray-700 rounded-lg overflow-hidden"
          >
            {/* Input Section Panel */}
            <ResizablePanel 
              defaultSize={isInputCollapsed ? 25 : 50}
              minSize={20}
              maxSize={70}
              className="bg-gray-800/30 overflow-hidden"
            >
              <div className="h-full flex flex-col">
                {/* Input Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800/50 min-h-[80px]">
                  <div className="flex items-center space-x-3">
                    <h2 className="text-lg font-semibold text-white">Input</h2>
                    <Badge variant="secondary" className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                      {currentTask.name}
                    </Badge>
                    {isViewMode && (
                      <Badge variant="secondary" className="bg-gray-500/20 text-gray-400 border-gray-500/30">
                        View Mode
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsInputHidden(!isInputHidden)}
                      className="text-gray-400 hover:text-white"
                    >
                      {isInputHidden ? (
                        <>
                          <EyeOff className="h-4 w-4 mr-2" />
                          Show
                        </>
                      ) : (
                        <>
                          <Eye className="h-4 w-4 mr-2" />
                          Hide
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                {/* Input Content */}
                <div className={`flex-1 min-h-0 ${isInputHidden ? 'hidden' : ''}`}>
                  <InputSection
                    selectedTask={selectedTask}
                    sequenceInputs={sequenceInputs}
                    onSequenceInputsChange={setSequenceInputs}
                    ligands={ligands}
                    onLigandsChange={setLigands}
                    workflowName={workflowName}
                    onWorkflowNameChange={setWorkflowName}
                    useMSAServer={useMSAServer}
                    onUseMSAServerChange={setUseMSAServer}
                    usePotentials={usePotentials}
                    onUsePotentialsChange={setUsePotentials}
                    onPredictionStart={handlePredictionStart}
                    onPredictionComplete={handlePredictionResult}
                    onPredictionError={handlePredictionError}
                    isViewMode={isViewMode}
                    isReadOnlyMode={isReadOnlyMode}
                    submittedValues={submittedValues}
                    onNewPrediction={handleNewPrediction}
                  />
                </div>
              </div>
            </ResizablePanel>

            <ResizableHandle className="w-1 bg-gray-700 hover:bg-gray-600 transition-colors" />

            {/* Output Section Panel */}
            <ResizablePanel 
              defaultSize={isInputCollapsed ? 75 : 50}
              minSize={30}
              className="bg-gray-900 overflow-hidden"
            >
              <div className="h-full flex flex-col">
                {/* Output Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800/50 min-h-[80px]">
                  <div className="flex items-center space-x-3">
                    <h2 className="text-lg font-semibold text-white">Output</h2>
                  </div>
                  <div className="flex items-center space-x-2">
                    {isViewMode && (
                      <Badge variant="secondary" className="bg-green-500/20 text-green-400 border-green-500/30">
                        Already Saved
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Output Content */}
                <div className="flex-1 min-h-0 overflow-auto">
                  <OutputSection 
                    result={predictionResult}
                    isLoading={isLoading}
                    selectedTask={selectedTask}
                    isInputCollapsed={isInputCollapsed}
                    onInputCollapseChange={setIsInputCollapsed}
                  />
                </div>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>

        {/* Error Display */}
        {error && (
          <Alert className="mt-6 bg-red-900/50 border-red-700">
            <InfoIcon className="h-4 w-4" />
            <AlertDescription className="text-red-200">
              {error}
            </AlertDescription>
          </Alert>
        )}

        {/* Footer */}
        <div className="mt-12 pt-8 border-t border-gray-700">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div>
              <p className="text-gray-400 text-sm">
                Powered by OMTX-Hub • Production-ready molecular modeling platform
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant="secondary" className="bg-gray-700 text-gray-300">
                Version 1.0.0
              </Badge>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RFAntibody;