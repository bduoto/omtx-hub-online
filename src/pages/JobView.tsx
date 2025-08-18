import React, { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { 
  ArrowLeft, 
  Download, 
  Copy, 
  CheckIcon, 
  Eye, 
  EyeOff
} from 'lucide-react';

import Header, { PREDICTION_TASKS } from '@/components/Boltz2/Header';
import { InputSection } from '@/components/Boltz2/InputSection';
import { OutputSection } from '@/components/Boltz2/OutputSection';
import { jobService, Job } from '@/services/jobService';

const JobView = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  
  const [job, setJob] = useState<Job | null>(location.state?.job || null);
  const [loading, setLoading] = useState(!job);
  const [error, setError] = useState<string | null>(null);
  const [copySuccess, setCopySuccess] = useState<string | null>(null);
  const [isInputHidden, setIsInputHidden] = useState(false);
  const [isInputCollapsed, setIsInputCollapsed] = useState(false);

  // If no job data in location state, fetch from API
  useEffect(() => {
    if (!job && jobId) {
      const fetchJob = async () => {
        try {
          setLoading(true);
          const jobData = await jobService.getJob(jobId);
          setJob(jobData);
        } catch (err) {
          console.error('Failed to fetch job:', err);
          setError('Failed to load job details. Please try again.');
        } finally {
          setLoading(false);
        }
      };
      fetchJob();
    }
  }, [jobId, job]);

  // Determine task type from job data
  const getTaskType = () => {
    if (!job) return 'protein_ligand_binding';
    return job.input_data?.task_type || 'protein_ligand_binding';
  };

  const selectedTask = getTaskType();
  const currentTask = PREDICTION_TASKS.find(task => task.id === selectedTask) || PREDICTION_TASKS[0];

  // Mock input state (read-only display)
  const [sequenceInputs, setSequenceInputs] = useState<string[]>([]);
  const [ligands, setLigands] = useState([{ name: '', formula: '' }]);
  const [workflowName, setWorkflowName] = useState('');
  const [useMSAServer, setUseMSAServer] = useState(true);
  const [usePotentials, setUsePotentials] = useState(false);

  // Populate form data from job when loaded
  useEffect(() => {
    if (job?.input_data) {
      const inputData = job.input_data;
      
      // Extract protein sequences
      if (inputData.input_data?.sequences) {
        const proteinSeqs = inputData.input_data.sequences
          .filter((seq: any) => seq.protein)
          .map((seq: any) => seq.protein.sequence);
        setSequenceInputs(proteinSeqs);
      } else if (inputData.protein_sequences) {
        setSequenceInputs(inputData.protein_sequences);
      }

      // Extract ligands
      if (inputData.input_data?.sequences) {
        const ligandSeqs = inputData.input_data.sequences
          .filter((seq: any) => seq.ligand)
          .map((seq: any) => ({ name: seq.ligand.id || 'Ligand', formula: seq.ligand.smiles }));
        if (ligandSeqs.length > 0) {
          setLigands(ligandSeqs);
        }
      } else if (inputData.ligands) {
        const mappedLigands = inputData.ligands.map((ligand: string, index: number) => ({
          name: job.ligand_name || `Ligand ${index + 1}`,
          formula: ligand
        }));
        setLigands(mappedLigands);
      }

      // Set workflow name
      setWorkflowName(job.ligand_name || jobService.formatJobName(job));

      // Set options
      setUseMSAServer(inputData.use_msa || inputData.use_msa_server || true);
      setUsePotentials(inputData.use_potentials || false);
    }
  }, [job]);

  const handleCopyToClipboard = async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopySuccess(type);
      setTimeout(() => setCopySuccess(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleDownloadJob = async () => {
    if (!job) return;
    
    try {
      const blob = await jobService.exportJobData(job.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `job_${job.id}_export.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download job data:', err);
    }
  };

  const handleDownloadStructure = async (format: 'cif' | 'pdb' | 'mmcif' = 'cif') => {
    if (!job) return;
    
    try {
      const blob = await jobService.downloadStructure(job.id, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `structure_${job.id}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download structure:', err);
    }
  };

  // Mock handlers (inputs are read-only)
  const handlePredictionStart = () => {};
  const handlePredictionResult = () => {};
  const handlePredictionError = () => {};

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-lg">Loading job details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 text-lg mb-4">{error}</p>
          <Button onClick={() => navigate('/my-results')} className="bg-blue-600 hover:bg-blue-700">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Results
          </Button>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-400 text-lg mb-4">Job not found</p>
          <Button onClick={() => navigate('/my-results')} className="bg-blue-600 hover:bg-blue-700">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Results
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        {/* Header with navigation */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button 
              variant="ghost" 
              onClick={() => navigate('/my-results')}
              className="text-gray-400 hover:text-white"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Results
            </Button>
            <div className="h-6 w-px bg-gray-600"></div>
            <h1 className="text-2xl font-bold text-white">Job Details</h1>
          </div>
          <div className="flex items-center space-x-3">
            <Button 
              variant="ghost" 
              onClick={handleDownloadJob}
              className="text-gray-400 hover:text-white"
            >
              <Download className="h-4 w-4 mr-2" />
              Export Job
            </Button>
          </div>
        </div>

        {/* Job Metadata */}
        <Card className="mb-6 bg-gray-800/50 border-gray-700">
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-semibold text-white mb-3">Job Information</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Job ID:</span>
                    <div className="flex items-center gap-2">
                      <span className="text-white font-mono">{job.id}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopyToClipboard(job.id, 'id')}
                        className="h-6 w-6 p-0 text-gray-400 hover:text-white"
                      >
                        {copySuccess === 'id' ? <CheckIcon className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      </Button>
                    </div>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Job Name:</span>
                    <span className="text-white">{jobService.formatJobName(job)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Task Type:</span>
                    <Badge variant="secondary" className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                      {currentTask.name}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Status:</span>
                    <Badge 
                      variant="secondary" 
                      className={`${
                        job.status === 'completed' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                        job.status === 'failed' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                        'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                      }`}
                    >
                      {jobService.mapDisplayStatus(job.status)}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Created:</span>
                    <span className="text-white">{new Date(job.created_at).toLocaleString()}</span>
                  </div>
                  {job.completed_at && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">Completed:</span>
                      <span className="text-white">{new Date(job.completed_at).toLocaleString()}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Job Content */}
        <div className="h-[800px] border border-gray-700 rounded-lg overflow-hidden">
          <ResizablePanelGroup 
            direction="horizontal" 
            className="h-full"
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
                    <Badge variant="secondary" className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                      {currentTask.name}
                    </Badge>
                    <Badge variant="secondary" className="bg-gray-500/20 text-gray-400 border-gray-500/30">
                      Read-only
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
                    selectedTask={selectedTask}
                    sequenceInputs={sequenceInputs}
                    onSequenceInputsChange={() => {}}
                    ligands={ligands}
                    onLigandsChange={() => {}}
                    workflowName={workflowName}
                    onWorkflowNameChange={() => {}}
                    useMSAServer={useMSAServer}
                    onUseMSAServerChange={() => {}}
                    usePotentials={usePotentials}
                    onUsePotentialsChange={() => {}}
                    onPredictionStart={() => {}}
                    onPredictionComplete={() => {}}
                    onPredictionError={() => {}}
                    isViewMode={true}
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
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge 
                      variant="secondary" 
                      className={`${
                        job.status === 'completed' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                        job.status === 'failed' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                        'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                      }`}
                    >
                      {jobService.mapDisplayStatus(job.status)}
                    </Badge>
                  </div>
                </div>
                
                {/* Output Content */}
                <div className="flex-1 min-h-0 overflow-auto">
                  {job.status === 'failed' ? (
                    <div className="p-4">
                      <Alert className="bg-red-950 border-red-800">
                        <AlertDescription className="text-red-300">
                          {job.error_message || 'Job failed to complete'}
                        </AlertDescription>
                      </Alert>
                    </div>
                  ) : (
                    <OutputSection 
                      result={job.output_data ? { 
                        ...job, 
                        job_id: job.id,
                        status: job.status,
                        task_type: selectedTask,
                        message: job.error_message || '',
                        ...job.output_data 
                      } : null}
                      isLoading={false}
                      selectedTask={selectedTask}
                      isInputCollapsed={isInputCollapsed}
                      onInputCollapseChange={setIsInputCollapsed}
                    />
                  )}
                </div>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>
      </div>
    </div>
  );
};

export default JobView;