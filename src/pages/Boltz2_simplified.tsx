/**
 * Simplified Boltz-2 Page for Cloud Run Native API
 * 
 * No authentication required - integrates with company API gateway.
 * Clean, streamlined interface for Boltz-2 predictions.
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { 
  Activity, 
  Zap, 
  Database,
  CheckCircle,
  AlertCircle,
  Loader2,
  Server,
  Cpu,
  HardDrive
} from 'lucide-react';

import { apiClient } from '../services/apiClient_simplified';
import { jobStore } from '../stores/jobStore_simplified';
import BatchProteinLigandInputSimplified from '../components/Boltz2/BatchProteinLigandInput_simplified';

// System status interface
interface SystemStatus {
  status: string;
  timestamp: string;
  architecture: string;
  gpu_status: string;
  gpu_memory_gb: number;
  models: string[];
  ready_for_predictions: boolean;
}

export const Boltz2Simplified: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState<'batch' | 'individual'>('batch');
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Check system health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const status = await apiClient.getHealthStatus();
        setSystemStatus(status);
        setIsHealthy(status.ready_for_predictions);
        console.log('🏥 System status:', status);
      } catch (error) {
        console.error('🚨 Health check failed:', error);
        setIsHealthy(false);
        setError('Unable to connect to prediction service');
      }
    };
    
    checkHealth();
    
    // Check health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);
  
  const handlePredictionStart = () => {
    setError(null);
    setResults(null);
    console.log('🚀 Prediction started');
  };
  
  const handlePredictionComplete = (result: any) => {
    setResults(result);
    setError(null);
    console.log('✅ Prediction completed:', result);
  };
  
  const handlePredictionError = (errorMessage: string) => {
    setError(errorMessage);
    setResults(null);
    console.error('🚨 Prediction error:', errorMessage);
  };
  
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy': return 'bg-green-500';
      case 'available': return 'bg-green-500';
      case 'not_available': return 'bg-yellow-500';
      default: return 'bg-red-500';
    }
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-gray-800 flex items-center justify-center gap-3">
            <Zap className="w-8 h-8 text-blue-600" />
            Boltz-2 Protein Predictions
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Advanced protein-ligand binding predictions using Boltz-2 with L4 GPU acceleration.
            No authentication required - integrated with company API gateway.
          </p>
        </div>
        
        {/* System Status Card */}
        {systemStatus && (
          <Card className="w-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5" />
                System Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${getStatusColor(systemStatus.status)}`}></div>
                  <span className="text-sm font-medium">API: {systemStatus.status}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4" />
                  <span className="text-sm">GPU: {systemStatus.gpu_status}</span>
                  {systemStatus.gpu_memory_gb > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {systemStatus.gpu_memory_gb}GB
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4" />
                  <span className="text-sm">Arch: {systemStatus.architecture}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  <span className="text-sm">Models: {systemStatus.models.join(', ')}</span>
                </div>
              </div>
              
              {systemStatus.ready_for_predictions ? (
                <Alert className="mt-4 border-green-200 bg-green-50">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <AlertDescription className="text-green-800">
                    System ready for predictions. GPU acceleration available.
                  </AlertDescription>
                </Alert>
              ) : (
                <Alert className="mt-4 border-yellow-200 bg-yellow-50">
                  <AlertCircle className="h-4 w-4 text-yellow-600" />
                  <AlertDescription className="text-yellow-800">
                    System initializing or GPU not available. Predictions may use CPU fallback.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        )}
        
        {/* Error Display */}
        {error && (
          <Alert className="border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              {error}
            </AlertDescription>
          </Alert>
        )}
        
        {/* Connection Status */}
        {isHealthy === null ? (
          <Alert className="border-blue-200 bg-blue-50">
            <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
            <AlertDescription className="text-blue-800">
              Connecting to prediction service...
            </AlertDescription>
          </Alert>
        ) : !isHealthy ? (
          <Alert className="border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              Unable to connect to prediction service. Please check your connection or contact support.
              <div className="text-xs mt-1 font-mono">
                API URL: {apiClient.getApiUrl()}
              </div>
            </AlertDescription>
          </Alert>
        ) : null}
        
        {/* Tab Navigation */}
        <div className="flex justify-center space-x-1 p-1 bg-white rounded-lg shadow-sm border">
          <Button
            onClick={() => setActiveTab('batch')}
            variant={activeTab === 'batch' ? 'default' : 'ghost'}
            className="flex-1 max-w-xs"
          >
            <Database className="w-4 h-4 mr-2" />
            Batch Predictions
          </Button>
          <Button
            onClick={() => setActiveTab('individual')}
            variant={activeTab === 'individual' ? 'default' : 'ghost'}
            className="flex-1 max-w-xs"
            disabled={true} // Individual predictions coming soon
          >
            <Zap className="w-4 h-4 mr-2" />
            Individual (Coming Soon)
          </Button>
        </div>
        
        {/* Main Content */}
        <div className="space-y-6">
          {activeTab === 'batch' && isHealthy && (
            <BatchProteinLigandInputSimplified
              onPredictionStart={handlePredictionStart}
              onPredictionComplete={handlePredictionComplete}
              onPredictionError={handlePredictionError}
            />
          )}
          
          {activeTab === 'individual' && (
            <Card>
              <CardContent className="p-8 text-center">
                <div className="space-y-4">
                  <Zap className="w-12 h-12 text-gray-400 mx-auto" />
                  <h3 className="text-lg font-medium text-gray-600">
                    Individual Predictions Coming Soon
                  </h3>
                  <p className="text-sm text-gray-500">
                    Individual protein-ligand predictions will be available in the next update.
                    Use batch predictions for now with a single ligand.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
        
        {/* Results Display */}
        {results && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                Prediction Results
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm text-gray-600">Batch ID:</span>
                    <div className="font-mono text-sm">{results.batch_id}</div>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Status:</span>
                    <Badge variant={results.status === 'completed' ? 'default' : 'secondary'}>
                      {results.status}
                    </Badge>
                  </div>
                </div>
                
                {results.results && (
                  <div className="space-y-2">
                    <h4 className="font-medium">Results Summary:</h4>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      {results.results.best_affinity && (
                        <div>
                          <span className="text-gray-600">Best Affinity:</span>
                          <div className="font-mono">{results.results.best_affinity}</div>
                        </div>
                      )}
                      {results.results.average_affinity && (
                        <div>
                          <span className="text-gray-600">Average Affinity:</span>
                          <div className="font-mono">{results.results.average_affinity}</div>
                        </div>
                      )}
                      <div>
                        <span className="text-gray-600">Jobs:</span>
                        <div>{results.completed_jobs}/{results.total_jobs}</div>
                      </div>
                    </div>
                  </div>
                )}
                
                <Alert className="border-blue-200 bg-blue-50">
                  <AlertDescription className="text-blue-800">
                    Results are ready! Individual job details and structure files are available 
                    in the batch results dashboard.
                  </AlertDescription>
                </Alert>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* Footer Info */}
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
          <CardContent className="p-4">
            <div className="text-center space-y-2">
              <p className="text-sm text-gray-600">
                🔥 Powered by Cloud Run Native Architecture with L4 GPU acceleration
              </p>
              <p className="text-xs text-gray-500">
                Authentication handled by company API gateway • 84% cost savings vs A100 GPUs
              </p>
              <div className="flex justify-center gap-4 text-xs text-gray-500">
                <span>API Docs: <a href={apiClient.getApiDocsUrl()} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">View Documentation</a></span>
                <span>User ID: {apiClient.getUserId()}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Boltz2Simplified;