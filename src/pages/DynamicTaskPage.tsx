/**
 * Dynamic Task Page
 * Universal page for any prediction task using dynamic forms and outputs
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import { DynamicTaskForm } from '@/components/DynamicTaskForm';
import { DynamicTaskOutput } from '@/components/DynamicTaskOutput';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { jobService } from '@/services/jobService';
import { taskSchemaService } from '@/services/taskSchemaService';

interface DynamicTaskPageProps {
  taskId: string;
  modelId?: string;
}

export const DynamicTaskPage: React.FC<DynamicTaskPageProps> = ({ 
  taskId, 
  modelId = 'boltz2' 
}) => {
  const { jobId } = useParams<{ jobId?: string }>();
  const navigate = useNavigate();
  
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [initialValues, setInitialValues] = useState<Record<string, any>>({});

  useEffect(() => {
    if (jobId) {
      loadJobResults();
    }
  }, [jobId]);

  const loadJobResults = async () => {
    if (!jobId) return;
    
    try {
      setLoading(true);
      const jobResult = await jobService.getJob(jobId);
      setResult(jobResult);
      
      // If viewing a job, populate the form with the original inputs
      if (jobResult.input_data) {
        setInitialValues(jobResult.input_data);
      }
    } catch (error) {
      console.error('Error loading job results:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitPrediction = async (formData: Record<string, any>) => {
    try {
      setSubmitting(true);
      
      // Validate input data first
      const validation = await taskSchemaService.validateTaskInput(taskId, formData);
      if (!validation.valid) {
        throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
      }
      
      // Submit prediction using the unified API
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBase}/api/v1/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: modelId,
          protein_sequence: formData.protein_sequence || '',
          ligand_smiles: formData.ligand_smiles || '',
          job_name: formData.job_name || `${taskId} Prediction`,
          user_id: "omtx_deployment_user",
          parameters: {
            task_type: taskId,
            ...formData
          }
        }),
      });

      if (!response.ok) {
        throw new Error(`Prediction failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Navigate to job view
      navigate(`/tasks/${taskId}/job/${result.job_id}`);
      
    } catch (error) {
      console.error('Error submitting prediction:', error);
      // You might want to show an error toast here
    } finally {
      setSubmitting(false);
    }
  };

  const getTaskDisplayName = (taskId: string): string => {
    const names: Record<string, string> = {
      'protein_ligand_binding': 'Protein-Ligand Binding',
      'protein_structure': 'Protein Structure Prediction',
      'protein_complex': 'Protein Complex Prediction',
      'binding_site_prediction': 'Binding Site Prediction',
      'variant_comparison': 'Variant Comparison',
      'drug_discovery': 'Drug Discovery',
    };
    return names[taskId] || taskId.replace('_', ' ');
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Navigation */}
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="text-gray-400 hover:text-white mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Models
          </Button>
          
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 bg-clip-text text-transparent">
              {getTaskDisplayName(taskId)}
            </h1>
            {jobId && (
              <span className="text-sm text-gray-400">
                Job: {jobId}
              </span>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="h-[calc(100vh-200px)]">
          <ResizablePanelGroup direction="horizontal">
            <ResizablePanel defaultSize={50} minSize={30}>
              <div className="h-full pr-3">
                <DynamicTaskForm
                  taskId={taskId}
                  onSubmit={handleSubmitPrediction}
                  loading={submitting}
                  initialValues={initialValues}
                />
              </div>
            </ResizablePanel>
            
            <ResizableHandle withHandle />
            
            <ResizablePanel defaultSize={50} minSize={30}>
              <div className="h-full pl-3">
                <DynamicTaskOutput
                  taskId={taskId}
                  result={result}
                  jobId={jobId}
                  loading={loading}
                />
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>
      </div>
    </div>
  );
};

// Specific task page components
export const ProteinLigandBindingPage: React.FC = () => (
  <DynamicTaskPage taskId="protein_ligand_binding" />
);

export const ProteinStructurePage: React.FC = () => (
  <DynamicTaskPage taskId="protein_structure" />
);

export const ProteinComplexPage: React.FC = () => (
  <DynamicTaskPage taskId="protein_complex" />
);

export const BindingSitePredictionPage: React.FC = () => (
  <DynamicTaskPage taskId="binding_site_prediction" />
);

export const VariantComparisonPage: React.FC = () => (
  <DynamicTaskPage taskId="variant_comparison" />
);

export const DrugDiscoveryPage: React.FC = () => (
  <DynamicTaskPage taskId="drug_discovery" />
);

export default DynamicTaskPage;