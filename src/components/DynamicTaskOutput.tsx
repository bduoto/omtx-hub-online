/**
 * Dynamic Task Output Component
 * Renders results based on task schema output fields
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { StructureViewer } from '@/components/Boltz2/StructureViewer';
import { taskSchemaService, OutputField, TaskSchema } from '@/services/taskSchemaService';
import { 
  Download, 
  Eye, 
  BarChart3, 
  Atom, // Replace Molecule with Atom since Molecule doesn't exist
  Target, 
  TrendingUp, 
  Clock, 
  CheckCircle,
  AlertCircle
} from 'lucide-react';

interface DynamicTaskOutputProps {
  taskId: string;
  result: any;
  jobId?: string;
  loading?: boolean;
}

interface OutputTabConfig {
  id: string;
  label: string;
  icon: React.ReactNode;
  fields: OutputField[];
  visible: boolean;
}

export const DynamicTaskOutput: React.FC<DynamicTaskOutputProps> = ({
  taskId,
  result,
  jobId,
  loading = false,
}) => {
  const [schema, setSchema] = useState<TaskSchema | null>(null);
  const [outputTabs, setOutputTabs] = useState<OutputTabConfig[]>([]);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [schemaLoading, setSchemaLoading] = useState(true);

  useEffect(() => {
    loadOutputConfig();
  }, [taskId]);

  const loadOutputConfig = async () => {
    try {
      setSchemaLoading(true);
      const taskSchema = await taskSchemaService.getTaskSchema(taskId);
      setSchema(taskSchema);
      
      const config = await taskSchemaService.getOutputConfig(taskId);
      const tabs = generateOutputTabs(config.fields, config);
      setOutputTabs(tabs);
      
      // Set default active tab
      const firstVisibleTab = tabs.find(tab => tab.visible);
      if (firstVisibleTab) {
        setActiveTab(firstVisibleTab.id);
      }
      
    } catch (error) {
      console.error('Error loading output config:', error);
    } finally {
      setSchemaLoading(false);
    }
  };

  const generateOutputTabs = (fields: OutputField[], config: any): OutputTabConfig[] => {
    const tabs: OutputTabConfig[] = [
      {
        id: 'overview',
        label: 'Overview',
        icon: <Eye className="h-4 w-4" />,
        fields: fields.filter(f => f.output_type === 'metrics' || f.output_type === 'confidence'),
        visible: true,
      },
    ];

    // Add structure tab if task produces structures
    if (config.hasStructure) {
      tabs.push({
        id: 'structure',
        label: 'Structure',
        icon: <Atom className="h-4 w-4" />,
        fields: fields.filter(f => f.output_type === 'structure'),
        visible: true,
      });
    }

    // Add affinity tab if task produces affinity scores
    if (config.hasAffinity) {
      tabs.push({
        id: 'affinity',
        label: 'Affinity',
        icon: <Target className="h-4 w-4" />,
        fields: fields.filter(f => f.output_type === 'affinity'),
        visible: true,
      });
    }

    // Add confidence tab if task produces confidence scores
    if (config.hasConfidence) {
      tabs.push({
        id: 'confidence',
        label: 'Confidence',
        icon: <TrendingUp className="h-4 w-4" />,
        fields: fields.filter(f => f.output_type === 'confidence'),
        visible: true,
      });
    }

    // Add binding sites tab if task predicts binding sites
    if (config.hasBindingSites) {
      tabs.push({
        id: 'binding_sites',
        label: 'Binding Sites',
        icon: <Target className="h-4 w-4" />,
        fields: fields.filter(f => f.output_type === 'binding_sites'),
        visible: true,
      });
    }

    // Add screening results tab for drug discovery
    if (config.hasScreeningResults) {
      tabs.push({
        id: 'screening',
        label: 'Screening Results',
        icon: <BarChart3 className="h-4 w-4" />,
        fields: fields.filter(f => f.output_type === 'screening_results'),
        visible: true,
      });
    }

    // Add parameters tab
    tabs.push({
      id: 'parameters',
      label: 'Parameters',
      icon: <Clock className="h-4 w-4" />,
      fields: fields.filter(f => f.output_type === 'metrics'),
      visible: true,
    });

    return tabs;
  };

  const renderOverviewTab = () => {
    if (!result) return <div className="text-center py-8 text-gray-400">No results available</div>;

    const status = result.status || 'unknown';
    const confidence = result.confidence || result.overall_confidence;
    const executionTime = result.execution_time;

    return (
      <div className="space-y-6">
        {/* Status */}
        <Card className="bg-gray-900 border-gray-700">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              {status === 'completed' ? (
                <CheckCircle className="h-5 w-5 text-green-400" />
              ) : status === 'failed' ? (
                <AlertCircle className="h-5 w-5 text-red-400" />
              ) : (
                <Clock className="h-5 w-5 text-yellow-400" />
              )}
              Prediction Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Badge variant={status === 'completed' ? 'default' : 'secondary'}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </Badge>
              {executionTime && (
                <span className="text-sm text-gray-400">
                  Completed in {Math.round(executionTime)}s
                </span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Confidence Score */}
        {confidence && (
          <Card className="bg-gray-900 border-gray-700">
            <CardHeader>
              <CardTitle className="text-lg text-white">Confidence Score</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-300">Overall Confidence</span>
                  <span className="font-mono text-lg text-white">
                    {(confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <Progress value={confidence * 100} className="h-2" />
                <p className="text-xs text-gray-400">
                  {confidence > 0.8 ? 'High confidence' : 
                   confidence > 0.6 ? 'Medium confidence' : 'Low confidence'}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {result.affinity && (
            <Card className="bg-gray-900 border-gray-700">
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">
                    {result.affinity.toFixed(3)}
                  </div>
                  <div className="text-sm text-gray-400">Binding Affinity</div>
                </div>
              </CardContent>
            </Card>
          )}
          
          {result.plddt_score && (
            <Card className="bg-gray-900 border-gray-700">
              <CardContent className="pt-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">
                    {(result.plddt_score * 100).toFixed(1)}
                  </div>
                  <div className="text-sm text-gray-400">pLDDT Score</div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    );
  };

  const renderStructureTab = () => {
    if (!result || !result.structure_file_content) {
      return (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No structure data available for this prediction.
          </AlertDescription>
        </Alert>
      );
    }

    return (
      <div className="space-y-6">
        <StructureViewer
          cifContent={result.structure_file_content}
          state="loaded"
          onDownloadCif={() => {
            if (result.structure_file_content) {
              const blob = new Blob([result.structure_file_content], { type: 'text/plain' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `${jobId || 'structure'}.cif`;
              a.click();
              URL.revokeObjectURL(url);
            }
          }}
        />
      </div>
    );
  };

  const renderAffinityTab = () => {
    if (!result || !result.affinity) {
      return (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No affinity data available for this prediction.
          </AlertDescription>
        </Alert>
      );
    }

    return (
      <div className="space-y-6">
        <Card className="bg-gray-900 border-gray-700">
          <CardHeader>
            <CardTitle className="text-lg text-white">Binding Affinity Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-800 p-4 rounded">
                  <div className="text-sm text-gray-400">Affinity Score</div>
                  <div className="text-2xl font-bold text-white">
                    {result.affinity.toFixed(3)}
                  </div>
                </div>
                
                {result.affinity_probability && (
                  <div className="bg-gray-800 p-4 rounded">
                    <div className="text-sm text-gray-400">Affinity Probability</div>
                    <div className="text-2xl font-bold text-white">
                      {(result.affinity_probability * 100).toFixed(1)}%
                    </div>
                  </div>
                )}
              </div>
              
              <div className="text-sm text-gray-400">
                {result.affinity > 0 ? 
                  'Positive values indicate favorable binding' : 
                  'Negative values indicate unfavorable binding'
                }
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  const renderParametersTab = () => {
    if (!result) return <div className="text-center py-8 text-gray-400">No parameters available</div>;

    const parameters = result.parameters || {};
    const executionTime = result.execution_time;
    const gpuType = result.gpu_type;

    return (
      <div className="space-y-6">
        <Card className="bg-gray-900 border-gray-700">
          <CardHeader>
            <CardTitle className="text-lg text-white">Execution Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {executionTime && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Execution Time</span>
                  <span className="text-white">{Math.round(executionTime)}s</span>
                </div>
              )}
              
              {gpuType && (
                <div className="flex justify-between">
                  <span className="text-gray-400">GPU Type</span>
                  <span className="text-white">{gpuType}</span>
                </div>
              )}
              
              {Object.entries(parameters).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-gray-400">{key.replace('_', ' ')}</span>
                  <span className="text-white">{String(value)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  const renderTabContent = (tabId: string) => {
    switch (tabId) {
      case 'overview':
        return renderOverviewTab();
      case 'structure':
        return renderStructureTab();
      case 'affinity':
        return renderAffinityTab();
      case 'parameters':
        return renderParametersTab();
      default:
        return (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              This output type is not yet implemented.
            </AlertDescription>
          </Alert>
        );
    }
  };

  if (schemaLoading) {
    return (
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card className="bg-gray-800/50 border-gray-700">
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto mb-4"></div>
            <p className="text-gray-400">Processing prediction...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const visibleTabs = outputTabs.filter(tab => tab.visible);

  return (
    <Card className="bg-gray-800/50 border-gray-700">
      <CardHeader>
        <CardTitle className="text-xl font-bold bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 bg-clip-text text-transparent tracking-wide">
          Results
        </CardTitle>
        {schema && (
          <CardDescription className="text-gray-400">
            {schema.task_name} results
          </CardDescription>
        )}
      </CardHeader>
      
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2 md:grid-cols-3 lg:grid-cols-4 mb-6">
            {visibleTabs.map(tab => (
              <TabsTrigger 
                key={tab.id} 
                value={tab.id}
                className="flex items-center gap-2 text-xs"
              >
                {tab.icon}
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
          
          {visibleTabs.map(tab => (
            <TabsContent key={tab.id} value={tab.id}>
              {renderTabContent(tab.id)}
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
};