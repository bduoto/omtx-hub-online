/**
 * Base Model Page Component
 * Reusable component for all model prediction interfaces
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { modelService, ModelDefinition } from '@/services/modelService';
import { jobService } from '@/services/jobService';
import { Header } from '@/components/Header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, ExternalLink, Info, Clock, Cpu, HardDrive } from 'lucide-react';

interface BaseModelPageProps {
  modelId: string;
  children?: React.ReactNode;
  customHeader?: React.ReactNode;
  customInputSection?: React.ReactNode;
  customOutputSection?: React.ReactNode;
}

interface ModelPageState {
  model: ModelDefinition | null;
  loading: boolean;
  error: string | null;
  jobId: string | null;
  results: any | null;
  submitting: boolean;
}

export const BaseModelPage: React.FC<BaseModelPageProps> = ({
  modelId,
  children,
  customHeader,
  customInputSection,
  customOutputSection,
}) => {
  const { jobId } = useParams<{ jobId?: string }>();
  const navigate = useNavigate();
  
  const [state, setState] = useState<ModelPageState>({
    model: null,
    loading: true,
    error: null,
    jobId: jobId || null,
    results: null,
    submitting: false,
  });

  useEffect(() => {
    loadModel();
  }, [modelId]);

  useEffect(() => {
    if (jobId) {
      loadJobResults();
    }
  }, [jobId]);

  const loadModel = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      const model = await modelService.getModel(modelId);
      setState(prev => ({ ...prev, model, loading: false }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to load model',
        loading: false,
      }));
    }
  };

  const loadJobResults = async () => {
    if (!jobId) return;
    
    try {
      const results = await jobService.getJob(jobId);
      setState(prev => ({ ...prev, results }));
    } catch (error) {
      console.error('Error loading job results:', error);
    }
  };

  const handleSubmitPrediction = async (inputData: any) => {
    if (!state.model) return;

    try {
      setState(prev => ({ ...prev, submitting: true }));
      
      // Submit prediction using the unified API
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBase}/api/v1/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: modelId,
          protein_sequence: inputData.protein_sequence || '',
          ligand_smiles: inputData.ligand_smiles || '',
          job_name: inputData.job_name || `${state.model.name} Prediction`,
          user_id: "omtx_deployment_user",
          parameters: {
            task_type: inputData.task_type,
            ...inputData
          }
        }),
      });

      if (!response.ok) {
        throw new Error(`Prediction failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Navigate to job view
      navigate(`/${modelId}/job/${result.job_id}`);
      
    } catch (error) {
      console.error('Error submitting prediction:', error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to submit prediction',
        submitting: false,
      }));
    }
  };

  const formatEstimatedTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `~${hours}h ${minutes % 60}m`;
    }
    return `~${minutes}m`;
  };

  const renderModelInfo = () => {
    if (!state.model) return null;

    return (
      <Card className="bg-gray-800/50 border-gray-700 mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <CardTitle className="text-xl text-white">
                  {state.model.name}
                </CardTitle>
                <p className="text-gray-400 mt-1">
                  {state.model.description}
                </p>
              </div>
              <Badge variant="secondary">
                v{state.model.version}
              </Badge>
            </div>
            
            <div className="flex gap-2">
              {state.model.documentation_url && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(state.model.documentation_url, '_blank')}
                  className="bg-gray-800 border-gray-600 text-white hover:bg-gray-700"
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Docs
                </Button>
              )}
              {state.model.paper_url && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(state.model.paper_url, '_blank')}
                  className="bg-gray-800 border-gray-600 text-white hover:bg-gray-700"
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Paper
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="pt-0">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Clock className="w-4 h-4" />
              <span>
                {state.model.resources.estimated_time_seconds
                  ? formatEstimatedTime(state.model.resources.estimated_time_seconds)
                  : 'Variable'
                }
              </span>
            </div>
            
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Cpu className="w-4 h-4" />
              <span>
                {state.model.resources.gpu_required
                  ? `${state.model.resources.gpu_memory_gb || 'Unknown'}GB GPU`
                  : 'CPU'
                }
              </span>
            </div>
            
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <HardDrive className="w-4 h-4" />
              <span>
                {state.model.resources.memory_gb || 'Unknown'}GB RAM
              </span>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-2">
            {state.model.tags.map((tag, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  };

  const renderDefaultInputSection = () => {
    if (!state.model) return null;

    return (
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Input Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Supported Tasks
              </label>
              <div className="flex flex-wrap gap-2">
                {state.model.capabilities.supported_tasks.map((task, index) => (
                  <Badge key={index} variant="secondary">
                    {task.replace('_', ' ')}
                  </Badge>
                ))}
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Input Formats
              </label>
              <div className="flex flex-wrap gap-2">
                {state.model.capabilities.input_formats.map((format, index) => (
                  <Badge key={index} variant="outline">
                    {format.toUpperCase()}
                  </Badge>
                ))}
              </div>
            </div>

            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                This model supports {state.model.capabilities.supported_tasks.length} task types.
                Please use the model-specific interface for predictions.
              </AlertDescription>
            </Alert>
          </div>
        </CardContent>
      </Card>
    );
  };

  const renderDefaultOutputSection = () => {
    if (!state.results) return null;

    return (
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Results</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="bg-gray-900 p-4 rounded text-sm text-gray-300 overflow-auto">
            {JSON.stringify(state.results, null, 2)}
          </pre>
        </CardContent>
      </Card>
    );
  };

  if (state.loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white">
        <Header />
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="mb-6">
            <Button
              variant="ghost"
              onClick={() => navigate('/')}
              className="text-gray-400 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Models
            </Button>
          </div>
          
          <div className="space-y-6">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white">
        <Header />
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="mb-6">
            <Button
              variant="ghost"
              onClick={() => navigate('/')}
              className="text-gray-400 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Models
            </Button>
          </div>
          
          <Alert variant="destructive">
            <AlertDescription>{state.error}</AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header />
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Navigation */}
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="text-gray-400 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Models
          </Button>
        </div>

        {/* Custom Header or Model Info */}
        {customHeader || renderModelInfo()}

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Input Section */}
          <div>
            {customInputSection || renderDefaultInputSection()}
          </div>

          {/* Output Section */}
          <div>
            {customOutputSection || renderDefaultOutputSection()}
          </div>
        </div>

        {/* Custom Children */}
        {children}
      </div>
    </div>
  );
};

export default BaseModelPage;