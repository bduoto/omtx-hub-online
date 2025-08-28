import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
  Download, 
  Activity, 
  Beaker, 
  FileText, 
  Eye,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  ExternalLink
} from 'lucide-react';
import { StructureViewer } from '@/components/Boltz2/StructureViewer';

interface Boltz2ResultsViewerProps {
  jobId: string;
  jobData?: any;
  onClose?: () => void;
}

interface JobResults {
  job_id: string;
  status: string;
  model: string;
  created_at: string;
  completed_at?: string;
  results?: {
    affinity: number;
    confidence: number;
    rmsd: number;
    model_version: string;
    processing_time: number;
    structure_file?: string;
    results_file?: string;
    input_file?: string;
    additional_metrics?: {
      ptm?: number;
      iptm?: number;
      plddt?: number;
      clash_score?: number;
      interface_area?: number;
      predicted_tm_score?: number;
      interface_predicted_tm_score?: number;
      model_confidence?: number;
    };
  };
  input_data?: {
    protein_sequence?: string;
    ligand_smiles?: string;
    ligand_name?: string;
    parameters?: any;
  };
}

export const Boltz2ResultsViewer: React.FC<Boltz2ResultsViewerProps> = ({ 
  jobId, 
  jobData,
  onClose 
}) => {
  const [job, setJob] = useState<JobResults | null>(jobData);
  const [loading, setLoading] = useState(!jobData);
  const [error, setError] = useState<string | null>(null);
  const [structureUrl, setStructureUrl] = useState<string | null>(null);
  const [downloadingStructure, setDownloadingStructure] = useState(false);

  // Fetch job data if not provided
  useEffect(() => {
    if (!jobData && jobId) {
      fetchJobData();
    } else if (jobData) {
      // If job data is provided, set it directly
      setJob(jobData);
      setLoading(false);
    }
  }, [jobId, jobData]);

  const fetchJobData = async () => {
    try {
      setLoading(true);
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBase}/api/v1/jobs/${jobId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch job: ${response.status}`);
      }
      
      const data = await response.json();
      setJob(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching job:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch job data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      'completed': { label: 'Completed', variant: 'default' as const, icon: CheckCircle },
      'running': { label: 'Running', variant: 'secondary' as const, icon: Loader2 },
      'queued': { label: 'Queued', variant: 'outline' as const, icon: Clock },
      'pending': { label: 'Pending', variant: 'outline' as const, icon: Clock },
      'failed': { label: 'Failed', variant: 'destructive' as const, icon: AlertCircle }
    };

    const config = statusConfig[status] || statusConfig['pending'];
    const Icon = config.icon;

    return (
      <Badge variant={config.variant} className="flex items-center gap-1">
        <Icon className="w-3 h-3" />
        {config.label}
      </Badge>
    );
  };

  const formatProcessingTime = (seconds?: number) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  };

  const getAffinityColor = (affinity: number) => {
    if (affinity < -10) return 'text-green-600 dark:text-green-400';
    if (affinity < -8) return 'text-blue-600 dark:text-blue-400';
    if (affinity < -6) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.8) return 'text-green-600 dark:text-green-400';
    if (confidence > 0.6) return 'text-blue-600 dark:text-blue-400';
    if (confidence > 0.4) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const downloadFile = async (fileType: string, filename: string) => {
    try {
      setDownloadingStructure(true);
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      
      // Use the correct files endpoint
      const response = await fetch(`${apiBase}/api/v1/jobs/${jobId}/files/${fileType}?user_id=omtx_deployment_user`);
      
      if (!response.ok) {
        throw new Error('Failed to download file');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download error:', err);
      setError('Failed to download file');
    } finally {
      setDownloadingStructure(false);
    }
  };

  const viewStructure = async () => {
    if (!job?.results?.structure_file) return;
    
    try {
      setDownloadingStructure(true);
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      
      // Fetch structure file content using the correct endpoint
      const response = await fetch(`${apiBase}/api/v1/jobs/${jobId}/files/cif?user_id=omtx_deployment_user`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch structure');
      }
      
      const structureData = await response.text();
      setStructureUrl(structureData);
    } catch (err) {
      console.error('Structure viewing error:', err);
      setError('Failed to load structure');
    } finally {
      setDownloadingStructure(false);
    }
  };

  if (loading) {
    return (
      <Card className="w-full">
        <CardContent className="flex items-center justify-center p-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">Loading job results...</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!job) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>No Data</AlertTitle>
        <AlertDescription>No job data available</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <CardTitle className="text-2xl">Boltz-2 Prediction Results</CardTitle>
              {getStatusBadge(job.status)}
            </div>
            {onClose && (
              <Button variant="outline" size="sm" onClick={onClose}>
                Close
              </Button>
            )}
          </div>
          <div className="text-sm text-muted-foreground mt-2">
            Job ID: {job.job_id} • Model: {job.results?.model_version || 'Boltz-2'}
          </div>
        </CardHeader>
      </Card>

      {/* Main Results */}
      {job && job.status === 'completed' && job.results && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Binding Affinity */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">Binding Affinity</CardTitle>
                <Activity className="w-4 h-4 text-muted-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${getAffinityColor(job.results?.affinity || 0)}`}>
                {job.results?.affinity?.toFixed(2) || 'N/A'} kcal/mol
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {(job.results?.affinity || 0) < -8 ? 'Strong binding' : 
                 (job.results?.affinity || 0) < -6 ? 'Moderate binding' : 'Weak binding'}
              </p>
            </CardContent>
          </Card>

          {/* Confidence Score */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">Confidence Score</CardTitle>
                <Beaker className="w-4 h-4 text-muted-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${getConfidenceColor(job.results?.confidence || 0)}`}>
                {((job.results?.confidence || 0) * 100).toFixed(1)}%
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {(job.results?.confidence || 0) > 0.7 ? 'High confidence' : 
                 (job.results?.confidence || 0) > 0.5 ? 'Moderate confidence' : 'Low confidence'}
              </p>
            </CardContent>
          </Card>

          {/* Processing Time */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">Processing Time</CardTitle>
                <Clock className="w-4 h-4 text-muted-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatProcessingTime(job.results?.processing_time)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                GPU: L4 • {job.created_at && new Date(job.created_at).toLocaleString()}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Detailed Results Tabs */}
      {job && job.status === 'completed' && job.results && (
        <Tabs defaultValue="metrics" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="metrics">Metrics</TabsTrigger>
            <TabsTrigger value="structure">Structure</TabsTrigger>
            <TabsTrigger value="input">Input Data</TabsTrigger>
            <TabsTrigger value="files">Files</TabsTrigger>
          </TabsList>

          {/* Additional Metrics */}
          <TabsContent value="metrics">
            <Card>
              <CardHeader>
                <CardTitle>Additional Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {job.results?.additional_metrics?.ptm !== undefined && (
                    <div>
                      <p className="text-sm font-medium">pTM Score</p>
                      <p className="text-lg">{job.results.additional_metrics.ptm.toFixed(3)}</p>
                    </div>
                  )}
                  {job.results?.additional_metrics?.iptm !== undefined && (
                    <div>
                      <p className="text-sm font-medium">ipTM Score</p>
                      <p className="text-lg">{job.results?.additional_metrics?.iptm?.toFixed(3)}</p>
                    </div>
                  )}
                  {job.results?.additional_metrics?.plddt !== undefined && (
                    <div>
                      <p className="text-sm font-medium">pLDDT</p>
                      <p className="text-lg">{job.results?.additional_metrics?.plddt?.toFixed(1)}</p>
                    </div>
                  )}
                  {job.results?.rmsd !== undefined && (
                    <div>
                      <p className="text-sm font-medium">RMSD</p>
                      <p className="text-lg">{job.results?.rmsd?.toFixed(2)} Å</p>
                    </div>
                  )}
                  {job.results?.additional_metrics?.clash_score !== undefined && (
                    <div>
                      <p className="text-sm font-medium">Clash Score</p>
                      <p className="text-lg">{job.results?.additional_metrics?.clash_score?.toFixed(1)}</p>
                    </div>
                  )}
                  {job.results?.additional_metrics?.interface_area !== undefined && (
                    <div>
                      <p className="text-sm font-medium">Interface Area</p>
                      <p className="text-lg">{job.results?.additional_metrics?.interface_area?.toFixed(1)} Ų</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Structure Viewer */}
          <TabsContent value="structure">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>3D Structure</CardTitle>
                  <div className="space-x-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={viewStructure}
                      disabled={!job.results?.structure_file || downloadingStructure}
                    >
                      {downloadingStructure ? (
                        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                      ) : (
                        <Eye className="w-4 h-4 mr-1" />
                      )}
                      View
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => downloadFile('cif', `${jobId}_structure.cif`)}
                      disabled={!job.results?.structure_file}
                    >
                      <Download className="w-4 h-4 mr-1" />
                      Download CIF
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {structureUrl ? (
                  <StructureViewer 
                    structureData={structureUrl}
                    format="cif"
                    height={500}
                  />
                ) : (
                  <div className="flex items-center justify-center h-[500px] bg-muted/20 rounded-lg">
                    <p className="text-muted-foreground">
                      Click "View" to load the 3D structure
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Input Data */}
          <TabsContent value="input">
            <Card>
              <CardHeader>
                <CardTitle>Input Data</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {job.input_data?.protein_sequence && (
                  <div>
                    <p className="text-sm font-medium mb-1">Protein Sequence ({job.input_data.protein_sequence.length} residues)</p>
                    <div className="p-3 bg-muted/50 rounded-md font-mono text-xs break-all">
                      {job.input_data.protein_sequence}
                    </div>
                  </div>
                )}
                {job.input_data?.ligand_smiles && (
                  <div>
                    <p className="text-sm font-medium mb-1">Ligand SMILES {job.input_data?.ligand_name && `(${job.input_data.ligand_name})`}</p>
                    <div className="p-3 bg-muted/50 rounded-md font-mono text-sm">
                      {job.input_data.ligand_smiles}
                    </div>
                  </div>
                )}
                {job.input_data?.parameters && (
                  <div>
                    <p className="text-sm font-medium mb-1">Parameters</p>
                    <div className="p-3 bg-muted/50 rounded-md">
                      <pre className="text-xs">
                        {JSON.stringify(job.input_data.parameters, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Files */}
          <TabsContent value="files">
            <Card>
              <CardHeader>
                <CardTitle>Generated Files</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {job.results?.structure_file && (
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <FileText className="w-5 h-5 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">Structure File (CIF)</p>
                          <p className="text-xs text-muted-foreground">{job.results?.structure_file}</p>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => downloadFile('cif', `${jobId}_structure.cif`)}
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                  {job.results?.results_file && (
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <FileText className="w-5 h-5 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">Results File (JSON)</p>
                          <p className="text-xs text-muted-foreground">{job.results?.results_file}</p>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => downloadFile('json', `${jobId}_results.json`)}
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                  {job.results?.input_file && (
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <FileText className="w-5 h-5 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">Input File (JSON)</p>
                          <p className="text-xs text-muted-foreground">{job.results?.input_file}</p>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => downloadFile('json', `${jobId}_input.json`)}
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}

      {/* Error State */}
      {job.status === 'failed' && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Prediction Failed</AlertTitle>
          <AlertDescription>
            {job.results?.error || 'The prediction failed to complete. Please try again.'}
          </AlertDescription>
        </Alert>
      )}

      {/* Running State */}
      {(job.status === 'running' || job.status === 'queued' || job.status === 'pending') && (
        <Alert>
          <Loader2 className="h-4 w-4 animate-spin" />
          <AlertTitle>Prediction In Progress</AlertTitle>
          <AlertDescription>
            Your Boltz-2 prediction is currently being processed on GPU. This typically takes 30-60 seconds.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};