import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { 
  InfoIcon, 
  ArrowLeft,
  Eye,
  EyeOff,
  Download,
  FileDown
} from 'lucide-react';

import Header, { PREDICTION_TASKS } from '@/components/Boltz2/Header';
import { InputSection } from '@/components/Boltz2/InputSection';
import { OutputSection } from '@/components/Boltz2/OutputSection';

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

interface SavedJob {
  id: string;
  job_id: string;
  task_type: string;
  job_name: string;
  status: string;
  created_at: string;
  input_data: any;
  results: any;
  user_id: string;
}

interface BaseResultsPageProps {
  taskType: string;
  pageTitle: string;
  pageDescription: string;
}

const BaseResultsPage: React.FC<BaseResultsPageProps> = ({
  taskType,
  pageTitle,
  pageDescription
}) => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  
  const [savedJob, setSavedJob] = useState<SavedJob | null>(null);
  const [predictionResult, setPredictionResult] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInputHidden, setIsInputHidden] = useState(false);
  const [isInputCollapsed, setIsInputCollapsed] = useState(true);
  
  // State for InputSection compatibility
  const [sequenceInputs, setSequenceInputs] = useState(['']);
  const [ligands, setLigands] = useState([{ name: '', formula: '' }]);
  const [workflowName, setWorkflowName] = useState('(unnamed)');
  const [useMSAServer, setUseMSAServer] = useState(true);
  const [usePotentials, setUsePotentials] = useState(false);

  const currentTask = PREDICTION_TASKS.find(task => task.id === taskType) || PREDICTION_TASKS[0];

  // Infer task type from job data (for legacy jobs)
  const inferTaskType = (jobData: any): string => {
    console.log('BaseResults inferTaskType - jobData:', jobData);
    console.log('BaseResults inferTaskType - input_data:', jobData.input_data);
    console.log('BaseResults inferTaskType - inputs:', jobData.inputs);
    console.log('BaseResults inferTaskType - all keys:', Object.keys(jobData));
    
    // If task_type is already specific, use it
    if (jobData.task_type && jobData.task_type !== 'boltz2') {
      console.log('BaseResults inferTaskType - using existing task_type:', jobData.task_type);
      return jobData.task_type;
    }
    
    // Infer from input data structure - check multiple possible locations
    const inputData = jobData.input_data || jobData.inputs || {};
    
    if (inputData.chain_a_sequence && inputData.chain_b_sequence) {
      console.log('BaseResults inferTaskType - detected protein_complex');
      return 'protein_complex';
    }
    
    if (inputData.ligand_smiles || inputData.ligands?.length > 0) {
      console.log('BaseResults inferTaskType - detected protein_ligand_binding');
      return 'protein_ligand_binding';
    }
    
    if (inputData.variants?.length > 0) {
      console.log('BaseResults inferTaskType - detected variant_comparison');
      return 'variant_comparison';
    }
    
    if (inputData.compound_library?.length > 0) {
      console.log('BaseResults inferTaskType - detected drug_discovery');
      return 'drug_discovery';
    }
    
    if (inputData.pocket_constraints) {
      console.log('BaseResults inferTaskType - detected binding_site_prediction');
      return 'binding_site_prediction';
    }
    
    if (inputData.protein_sequence) {
      console.log('BaseResults inferTaskType - detected protein_structure');
      return 'protein_structure';
    }
    
    // Default fallback
    console.log('BaseResults inferTaskType - using fallback protein_ligand_binding');
    return 'protein_ligand_binding';
  };

  // Load job data
  useEffect(() => {
    const loadJobData = async () => {
      if (!jobId) {
        setError('No job ID provided');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await fetch(`/api/v2/jobs/${jobId}`);
        
        if (!response.ok) {
          throw new Error(`Failed to load job: ${response.statusText}`);
        }

        const jobData = await response.json();
        
        // Infer task type for legacy jobs or verify current jobs
        const actualTaskType = inferTaskType(jobData);
        if (actualTaskType !== taskType) {
          // For legacy "boltz2" jobs, redirect to correct page
          if (jobData.task_type === 'boltz2' || jobData.task_type === 'protein_ligand_binding') {
            console.warn(`Legacy job type "${jobData.task_type}" found, inferred as "${actualTaskType}"`);
            console.log(`Redirecting from ${taskType} to ${actualTaskType} page`);
            
            // Get correct URL and redirect
            const taskRoutes: { [key: string]: string } = {
              'protein_structure': `/results/protein-structure/${jobId}`,
              'protein_complex': `/results/protein-complex/${jobId}`,
              'protein_ligand_binding': `/results/protein-ligand-binding/${jobId}`,
              'binding_site_prediction': `/results/binding-site-prediction/${jobId}`,
              'variant_comparison': `/results/variant-comparison/${jobId}`,
              'drug_discovery': `/results/drug-discovery/${jobId}`,
            };
            
            const correctUrl = taskRoutes[actualTaskType] || `/boltz2/job/${jobId}`;
            window.location.href = correctUrl;
            return;
          } else {
            setError(`Job is of type "${jobData.task_type}" but expected "${taskType}"`);
            setLoading(false);
            return;
          }
        }

        setSavedJob(jobData);
        setPredictionResult(jobData.results || jobData.result_data);
        
        // Populate input data
        populateInputData(jobData.input_data || jobData.inputs);
        
      } catch (err) {
        console.error('Error loading job:', err);
        setError(err instanceof Error ? err.message : 'Failed to load job');
      } finally {
        setLoading(false);
      }
    };

    loadJobData();
  }, [jobId, taskType]);

  // Populate input form data based on task type and input data
  const populateInputData = (inputData: any) => {
    console.log('populateInputData received:', inputData);
    if (!inputData) {
      console.log('No input data to populate');
      return;
    }

    // Common fields
    setWorkflowName(inputData.job_name || '(unnamed)');
    setUseMSAServer(inputData.use_msa_server ?? inputData.use_msa ?? true);
    setUsePotentials(inputData.use_potentials ?? false);

    // Task-specific input handling
    switch (taskType) {
      case 'protein_ligand_binding':
        if (inputData.protein_sequence) {
          setSequenceInputs([inputData.protein_sequence]);
        }
        if (inputData.ligand_smiles) {
          setLigands([{ name: inputData.ligand_name || 'Ligand', formula: inputData.ligand_smiles }]);
        }
        break;

      case 'protein_structure':
        if (inputData.protein_sequence) {
          setSequenceInputs([inputData.protein_sequence]);
        }
        break;

      case 'protein_complex':
        if (inputData.chain_a_sequence && inputData.chain_b_sequence) {
          setSequenceInputs([inputData.chain_a_sequence, inputData.chain_b_sequence]);
        }
        break;

      case 'binding_site_prediction':
        if (inputData.protein_sequence) {
          setSequenceInputs([inputData.protein_sequence]);
        }
        break;

      case 'variant_comparison':
        if (inputData.wildtype_sequence) {
          setSequenceInputs([inputData.wildtype_sequence]);
        }
        // Note: variants would need special handling
        break;

      case 'drug_discovery':
        if (inputData.protein_sequence) {
          setSequenceInputs([inputData.protein_sequence]);
        }
        if (inputData.compound_library) {
          const ligandList = inputData.compound_library.map((compound: any) => ({
            name: compound.name || 'Compound',
            formula: compound.smiles || compound.formula || ''
          }));
          setLigands(ligandList);
        }
        break;
    }
  };

  const handleBackToResults = () => {
    navigate('/my-results');
  };

  const downloadJobReport = async () => {
    if (!savedJob) return;
    
    try {
      const response = await fetch(`/api/v2/jobs/${savedJob.job_id}/download/pdf`);
      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${savedJob.job_name || savedJob.job_id}_report.pdf`;
        link.click();
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Error downloading report:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-lg">Loading job results...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="max-w-md mx-auto text-center">
          <InfoIcon className="h-16 w-16 text-red-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Error Loading Job</h1>
          <p className="text-gray-400 mb-6">{error}</p>
          <Button onClick={handleBackToResults} className="bg-blue-600 hover:bg-blue-700">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to My Results
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      {/* Custom Header for Results Page */}
      <div className="border-b border-gray-700 bg-gray-800/50">
        <div className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost" 
                onClick={handleBackToResults}
                className="text-gray-400 hover:text-white"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to My Results
              </Button>
              <div>
                <h1 className="text-xl font-semibold text-white">{pageTitle}</h1>
                <p className="text-sm text-gray-400">{pageDescription}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant="secondary" className="bg-green-500/20 text-green-400 border-green-500/30">
                {savedJob?.status || 'Completed'}
              </Badge>
              <Badge variant="secondary" className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                {currentTask.name}
              </Badge>
              <Button
                onClick={downloadJobReport}
                variant="outline"
                size="sm"
                className="border-gray-600 text-gray-300 hover:bg-gray-700"
              >
                <FileDown className="h-4 w-4 mr-2" />
                Download Report
              </Button>
            </div>
          </div>
        </div>
      </div>
      
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
                    <h2 className="text-lg font-semibold text-white">Input Parameters</h2>
                    <Badge variant="secondary" className="bg-gray-500/20 text-gray-400 border-gray-500/30">
                      View Only
                    </Badge>
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
                    selectedTask={taskType}
                    sequenceInputs={sequenceInputs}
                    onSequenceInputsChange={() => {}} // Disabled
                    ligands={ligands}
                    onLigandsChange={() => {}} // Disabled
                    workflowName={workflowName}
                    onWorkflowNameChange={() => {}} // Disabled
                    useMSAServer={useMSAServer}
                    onUseMSAServerChange={() => {}} // Disabled
                    usePotentials={usePotentials}
                    onUsePotentialsChange={() => {}} // Disabled
                    onPredictionStart={() => {}} // Disabled
                    onPredictionComplete={() => {}} // Disabled
                    onPredictionError={() => {}} // Disabled
                    isViewMode={true} // This will disable all inputs and hide run button
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
                    <h2 className="text-lg font-semibold text-white">Results</h2>
                    {savedJob?.job_name && (
                      <Badge variant="secondary" className="bg-purple-500/20 text-purple-400 border-purple-500/30">
                        {savedJob.job_name}
                      </Badge>
                    )}
                  </div>
                  {savedJob?.created_at && (
                    <div className="text-sm text-gray-400">
                      Created: {new Date(savedJob.created_at).toLocaleDateString()}
                    </div>
                  )}
                </div>

                {/* Output Content */}
                <div className="flex-1 min-h-0 overflow-auto">
                  <OutputSection 
                    result={predictionResult}
                    isLoading={false}
                    selectedTask={taskType}
                    isInputCollapsed={isInputCollapsed}
                    onInputCollapseChange={setIsInputCollapsed}
                  />
                </div>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>

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
                Job ID: {savedJob?.job_id?.split('-')[0] || 'Unknown'}
              </Badge>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BaseResultsPage;