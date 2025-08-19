import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  ChevronLeft,
  ChevronRight,
  BarChart3,
  TrendingUp,
  Star,
  Settings,
  FileText,
  Info,
  Activity,
  Target,
  Zap,
  Atom,
  Download,
  Eye,
  Database,
  CheckCircle,
  Clock
} from 'lucide-react';
import { 
  getAffinityColor as getAffinityColorUtil, 
  getProbabilityColor,
  getConfidenceColor,
  getPLDDTColor,
  getMetricDescription 
} from '@/utils/boltz2Metrics';

// MetricTile component copied from OutputSection.tsx
const MetricTile: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
  icon?: React.ReactNode;
}> = ({ title, value, subtitle, color = 'text-white', icon }) => (
  <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 flex-1 min-w-0">
    <div className="flex items-center justify-between mb-2">
      <div className="flex items-center space-x-2">
        {icon && <div className="text-blue-400">{icon}</div>}
        <h3 className="text-sm font-medium text-gray-400 truncate">{title}</h3>
      </div>
    </div>
    <div className={`text-2xl font-bold ${color} truncate`}>
      {typeof value === 'number' ? value.toFixed(3) : value}
    </div>
    {subtitle && (
      <p className="text-xs text-gray-500 mt-1 truncate">{subtitle}</p>
    )}
  </div>
);

// Use the correct color functions from utils
const getScoreColor = getConfidenceColor;
const getAffinityColor = getAffinityColorUtil;

interface BatchIndividualResultsProps {
  jobs: any[];
  currentJobIndex: number;
  onJobIndexChange: (index: number) => void;
  onDownloadStructure?: (jobId: string) => void;
}

export const BatchIndividualResults: React.FC<BatchIndividualResultsProps> = ({
  jobs,
  currentJobIndex,
  onJobIndexChange,
  onDownloadStructure
}) => {
  const currentJob = jobs[currentJobIndex];
  const totalJobs = jobs.length;

  if (!currentJob) {
    return (
      <Alert className="border-red-700 bg-red-900/20">
        <Info className="h-4 w-4 text-red-400" />
        <AlertDescription className="text-red-400">
          No job data available
        </AlertDescription>
      </Alert>
    );
  }

  // Extract job data with fallbacks
  const jobData = {
    id: currentJob.id || currentJob.job_id,
    name: currentJob.job_name || currentJob.name || `Job ${currentJobIndex + 1}`,
    status: currentJob.status,
    ligand_name: currentJob.ligand_name || currentJob.input_data?.ligand_name || 'Unknown Ligand',
    ligand_smiles: currentJob.ligand_smiles || currentJob.input_data?.ligand_smiles || 'N/A',
    protein_name: currentJob.protein_name || currentJob.input_data?.protein_name || 'Unknown Protein',
    batch_index: currentJob.input_data?.batch_index || currentJobIndex,
    
    // Results data with multiple fallback paths
    results: currentJob.results || currentJob.result || currentJob.output_data || {},
    
    // Input parameters
    input_data: currentJob.input_data || {},
    
    // Logs
    logs: currentJob.logs || []
  };

  const results = jobData.results;
  
  // Extract comprehensive metrics from raw_modal_result
  const raw_modal = currentJob.raw_modal_result || {};
  const confidence_metrics = raw_modal.confidence_metrics || {};
  const affinity_ensemble = raw_modal.affinity_ensemble || {};
  
  const metrics = {
    // Direct binding outputs (highest priority)
    affinity: raw_modal.affinity || results.affinity || results.binding_score || results.affinity_pred_value,
    affinity_probability: raw_modal.affinity_probability,
    
    // Ensemble support
    ensemble_affinity: affinity_ensemble.affinity_pred_value,
    ensemble_affinity_probability: affinity_ensemble.affinity_probability_binary,
    ensemble_affinity2: affinity_ensemble.affinity_pred_value2,
    ensemble_affinity_probability2: affinity_ensemble.affinity_probability_binary2,
    ensemble_affinity1: affinity_ensemble.affinity_pred_value1,
    ensemble_affinity_probability1: affinity_ensemble.affinity_probability_binary1,
    
    // Model-level reliability
    confidence: raw_modal.confidence || confidence_metrics.confidence_score || results.confidence || results.confidence_score,
    
    // Interface-specific structure confidence
    iptm_score: confidence_metrics.iptm || raw_modal.iptm_score || results.iptm_score || results.iptm,
    ligand_iptm_score: confidence_metrics.ligand_iptm,
    complex_iplddt: confidence_metrics.complex_iplddt,
    pair_chains_iptm_1_0: raw_modal.pair_chains_iptm?.["1"]?.["0"],
    pair_chains_iptm_0_1: raw_modal.pair_chains_iptm?.["0"]?.["1"],
    complex_ipde: confidence_metrics.complex_ipde,
    
    // Global/monomer structure confidence
    complex_plddt: confidence_metrics.complex_plddt || raw_modal.plddt_score || results.plddt_score || results.plddt,
    ptm_score: confidence_metrics.ptm || raw_modal.ptm_score || results.ptm_score || results.ptm,
    chains_ptm_1: raw_modal.chains_ptm?.["1"],
    chains_ptm_0: raw_modal.chains_ptm?.["0"],
    complex_pde: confidence_metrics.complex_pde,
    protein_iptm_score: results.protein_iptm_score,
    
    // Execution metadata
    execution_time: results.execution_time
  };

  const navigatePrevious = () => {
    if (currentJobIndex > 0) {
      onJobIndexChange(currentJobIndex - 1);
    }
  };

  const navigateNext = () => {
    if (currentJobIndex < totalJobs - 1) {
      onJobIndexChange(currentJobIndex + 1);
    }
  };

  return (
    <div className="space-y-6">
      {/* Navigation Header */}
      <div className="flex items-center justify-between bg-gray-900/50 rounded-lg p-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-blue-400" />
            <h3 className="text-lg font-semibold text-white">
              Individual Result {currentJobIndex + 1} of {totalJobs}
            </h3>
          </div>
          <Badge variant="secondary" className="bg-gray-700 text-gray-200">
            {jobData.ligand_name}
          </Badge>
          <Badge 
            variant={jobData.status === 'completed' ? 'default' : 'secondary'}
            className={jobData.status === 'completed' ? 'bg-green-600' : 'bg-yellow-600'}
          >
            {jobData.status}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={navigatePrevious}
            disabled={currentJobIndex === 0}
            className="bg-gradient-to-r from-cyan-400 to-blue-500 to-purple-600 hover:from-cyan-500 hover:to-blue-600 hover:to-purple-700 text-white border-0 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          
          <span className="text-sm text-gray-400 px-2">
            {currentJobIndex + 1} / {totalJobs}
          </span>
          
          <Button
            size="sm"
            onClick={navigateNext}
            disabled={currentJobIndex === totalJobs - 1}
            className="bg-gradient-to-r from-cyan-400 to-blue-500 to-purple-600 hover:from-cyan-500 hover:to-blue-600 hover:to-purple-700 text-white border-0 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>

        </div>
      </div>

      {/* Overview Section */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <Info className="h-5 w-5 text-blue-400" />
            Overview
          </CardTitle>
        </CardHeader>
                <CardContent>
          <div className="space-y-6">
            {/* Summary Cards - matching original structure */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <MetricTile
                title="Job ID"
                value={jobData.id ? jobData.id.split('-')[0] : 'N/A'}
                subtitle="Click to copy full ID"
                icon={<Database className="h-4 w-4" />}
              />
              <MetricTile
                title="Status"
                value={jobData.status}
                subtitle={jobData.status === 'completed' ? 'Execution complete' : 'Processing status'}
                color={jobData.status === 'completed' ? 'text-green-400' : 'text-yellow-400'}
                icon={jobData.status === 'completed' ? <CheckCircle className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
              />
              <MetricTile
                title="Execution Time"
                value={metrics.execution_time ? `${metrics.execution_time.toFixed(1)}s` : 'N/A'}
                subtitle="Processing duration"
                icon={<Clock className="h-4 w-4" />}
              />
              <MetricTile
                title="Batch Position"
                value={Number(jobData.batch_index) + 1}
                subtitle="Position in batch"
                icon={<BarChart3 className="h-4 w-4" />}
              />
            </div>

            {/* Ligand and Protein Information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <MetricTile
                title="Ligand Name"
                value={jobData.ligand_name}
                subtitle="Target ligand"
                icon={<Atom className="h-4 w-4" />}
              />
              <MetricTile
                title="Protein"
                value={jobData.protein_name}
                subtitle="Target protein"
                icon={<Activity className="h-4 w-4" />}
              />
            </div>

            {/* SMILES */}
            <div className="bg-gray-900/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-400 mb-2">SMILES String</h4>
              <code className="text-white font-mono text-sm break-all">{jobData.ligand_smiles}</code>
            </div>

            {/* Message */}
            {results.message && (
              <Alert className="bg-blue-900/20 border-blue-700">
                <Info className="h-4 w-4" />
                <AlertDescription className="text-blue-200">
                  {results.message}
                </AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>

      {/* === DIRECT BINDING OUTPUTS (Most Important) === */}
      {jobData.status === 'completed' && (metrics.affinity !== undefined || metrics.affinity_probability !== undefined) && (
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <TrendingUp className="h-5 w-5 text-red-400" />
              Direct Binding Outputs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {metrics.affinity !== undefined && (
                <MetricTile
                  title="Affinity"
                  value={metrics.affinity.toFixed(4)}
                  subtitle={`Log scale, 1 µM ref. ${metrics.affinity <= -1 ? '(<0.1 µM)' : metrics.affinity <= 0 ? '(0.1-1 µM)' : metrics.affinity <= 1 ? '(1-10 µM)' : '(>10 µM)'}`}
                  color={getAffinityColor(metrics.affinity)}
                  icon={<TrendingUp className="h-4 w-4" />}
                />
              )}
              {metrics.affinity_probability !== undefined && (
                <MetricTile
                  title="Affinity Probability"
                  value={metrics.affinity_probability.toFixed(4)}
                  subtitle="Binding probability score"
                  color={metrics.affinity_probability > 0.7 ? 'text-green-400' : metrics.affinity_probability > 0.4 ? 'text-yellow-400' : 'text-red-400'}
                  icon={<Target className="h-4 w-4" />}
                />
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* === ENSEMBLE SUPPORT (Consensus to Members) === */}
      {jobData.status === 'completed' && (metrics.ensemble_affinity !== undefined || metrics.ensemble_affinity1 !== undefined) && (
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <BarChart3 className="h-5 w-5 text-blue-400" />
              Ensemble Support
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Consensus Metrics */}
              {(metrics.ensemble_affinity !== undefined || metrics.ensemble_affinity_probability !== undefined) && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-3">Consensus</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {metrics.ensemble_affinity !== undefined && (
                      <MetricTile
                        title="Ensemble Affinity"
                        value={metrics.ensemble_affinity.toFixed(4)}
                        subtitle="Consensus affinity prediction"
                        color="text-blue-400"
                        icon={<BarChart3 className="h-4 w-4" />}
                      />
                    )}
                    {metrics.ensemble_affinity_probability !== undefined && (
                      <MetricTile
                        title="Ensemble Probability"
                        value={metrics.ensemble_affinity_probability.toFixed(4)}
                        subtitle="Consensus probability"
                        color="text-blue-400"
                        icon={<Target className="h-4 w-4" />}
                      />
                    )}
                  </div>
                </div>
              )}

              {/* Member 2 Metrics */}
              {(metrics.ensemble_affinity2 !== undefined || metrics.ensemble_affinity_probability2 !== undefined) && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-3">Ensemble Member 2</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {metrics.ensemble_affinity2 !== undefined && (
                      <MetricTile
                        title="Affinity 2"
                        value={metrics.ensemble_affinity2.toFixed(4)}
                        subtitle="Secondary ensemble prediction"
                        color={getAffinityColor(metrics.ensemble_affinity2)}
                        icon={<BarChart3 className="h-4 w-4" />}
                      />
                    )}
                    {metrics.ensemble_affinity_probability2 !== undefined && (
                      <MetricTile
                        title="Probability 2"
                        value={metrics.ensemble_affinity_probability2.toFixed(4)}
                        subtitle="Secondary probability"
                        color="text-purple-400"
                        icon={<Target className="h-4 w-4" />}
                      />
                    )}
                  </div>
                </div>
              )}

              {/* Member 1 Metrics */}
              {(metrics.ensemble_affinity1 !== undefined || metrics.ensemble_affinity_probability1 !== undefined) && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-3">Ensemble Member 1</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {metrics.ensemble_affinity1 !== undefined && (
                      <MetricTile
                        title="Affinity 1"
                        value={metrics.ensemble_affinity1.toFixed(4)}
                        subtitle="Primary ensemble prediction"
                        color="text-cyan-400"
                        icon={<BarChart3 className="h-4 w-4" />}
                      />
                    )}
                    {metrics.ensemble_affinity_probability1 !== undefined && (
                      <MetricTile
                        title="Probability 1"
                        value={metrics.ensemble_affinity_probability1.toFixed(4)}
                        subtitle="Primary probability"
                        color="text-cyan-400"
                        icon={<Target className="h-4 w-4" />}
                      />
                    )}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* === MODEL-LEVEL RELIABILITY === */}
      {jobData.status === 'completed' && metrics.confidence !== undefined && (
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Star className="h-5 w-5 text-yellow-400" />
              Model-Level Reliability
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4">
              <MetricTile
                title="Overall Confidence"
                value={metrics.confidence.toFixed(4)}
                subtitle="Model confidence score"
                color={getScoreColor(metrics.confidence)}
                icon={<Star className="h-4 w-4" />}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* === INTERFACE-SPECIFIC STRUCTURE CONFIDENCE === */}
      {jobData.status === 'completed' && (
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Zap className="h-5 w-5 text-indigo-400" />
              Interface-Specific Structure Confidence
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Primary Interface Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {metrics.iptm_score !== undefined && (
                  <MetricTile
                    title="iPTM Score"
                    value={metrics.iptm_score.toFixed(4)}
                    subtitle="Interface confidence"
                    color="text-indigo-400"
                    icon={<Zap className="h-4 w-4" />}
                  />
                )}
                {metrics.ligand_iptm_score !== undefined && (
                  <MetricTile
                    title="Ligand iPTM"
                    value={metrics.ligand_iptm_score.toFixed(4)}
                    subtitle="Ligand interface confidence"
                    color="text-indigo-400"
                    icon={<Atom className="h-4 w-4" />}
                  />
                )}
                {metrics.complex_iplddt !== undefined && (
                  <MetricTile
                    title="Complex ipLDDT"
                    value={metrics.complex_iplddt.toFixed(4)}
                    subtitle="Interface local distance confidence"
                    color="text-teal-400"
                    icon={<Activity className="h-4 w-4" />}
                  />
                )}
              </div>

              {/* Cross-chain Interface Metrics */}
              {(metrics.pair_chains_iptm_1_0 !== undefined || metrics.pair_chains_iptm_0_1 !== undefined) && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-3">Cross-chain Interface (Higher = Better)</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {metrics.pair_chains_iptm_1_0 !== undefined && (
                      <MetricTile
                        title="Chain [1][0] iPTM"
                        value={metrics.pair_chains_iptm_1_0.toFixed(4)}
                        subtitle="Chain 1 to 0 interface"
                        color="text-indigo-400"
                        icon={<Database className="h-4 w-4" />}
                      />
                    )}
                    {metrics.pair_chains_iptm_0_1 !== undefined && (
                      <MetricTile
                        title="Chain [0][1] iPTM"
                        value={metrics.pair_chains_iptm_0_1.toFixed(4)}
                        subtitle="Chain 0 to 1 interface"
                        color="text-indigo-400"
                        icon={<Database className="h-4 w-4" />}
                      />
                    )}
                  </div>
                </div>
              )}

              {/* Interface Error Metric */}
              {metrics.complex_ipde !== undefined && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-3">Interface Error (Lower = Better)</h4>
                  <div className="grid grid-cols-1 gap-4">
                    <MetricTile
                      title="Complex iPDE"
                      value={metrics.complex_ipde.toFixed(4)}
                      subtitle="Interface predicted distance error"
                      color={metrics.complex_ipde < 5 ? 'text-green-400' : metrics.complex_ipde < 10 ? 'text-yellow-400' : 'text-red-400'}
                      icon={<Settings className="h-4 w-4" />}
                    />
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* === GLOBAL/MONOMER STRUCTURE CONFIDENCE === */}
      {jobData.status === 'completed' && (
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Atom className="h-5 w-5 text-amber-400" />
              Global/Monomer Structure Confidence
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Primary Global Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {metrics.complex_plddt !== undefined && (
                  <MetricTile
                    title="Complex pLDDT"
                    value={metrics.complex_plddt.toFixed(4)}
                    subtitle="Overall structure quality"
                    color={getScoreColor(metrics.complex_plddt)}
                    icon={<Atom className="h-4 w-4" />}
                  />
                )}
                {metrics.ptm_score !== undefined && (
                  <MetricTile
                    title="PTM Score"
                    value={metrics.ptm_score.toFixed(4)}
                    subtitle="Predicted template modeling"
                    color={getScoreColor(metrics.ptm_score)}
                    icon={<Activity className="h-4 w-4" />}
                  />
                )}
              </div>

              {/* Per-chain PTM Scores */}
              {(metrics.chains_ptm_1 !== undefined || metrics.chains_ptm_0 !== undefined) && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-3">Per-chain PTM Scores</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {metrics.chains_ptm_1 !== undefined && (
                      <MetricTile
                        title="Chain 1 PTM"
                        value={metrics.chains_ptm_1.toFixed(4)}
                        subtitle="Protein chain confidence"
                        color={getScoreColor(metrics.chains_ptm_1)}
                        icon={<Activity className="h-4 w-4" />}
                      />
                    )}
                    {metrics.chains_ptm_0 !== undefined && (
                      <MetricTile
                        title="Chain 0 PTM"
                        value={metrics.chains_ptm_0.toFixed(4)}
                        subtitle="Ligand chain confidence"
                        color={getScoreColor(metrics.chains_ptm_0)}
                        icon={<Atom className="h-4 w-4" />}
                      />
                    )}
                  </div>
                </div>
              )}

              {/* Global Error Metric */}
              {metrics.complex_pde !== undefined && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-3">Global Error (Lower = Better)</h4>
                  <div className="grid grid-cols-1 gap-4">
                    <MetricTile
                      title="Complex PDE"
                      value={metrics.complex_pde.toFixed(4)}
                      subtitle="Complex predicted distance error"
                      color={metrics.complex_pde < 3 ? 'text-green-400' : metrics.complex_pde < 5 ? 'text-yellow-400' : 'text-red-400'}
                      icon={<Settings className="h-4 w-4" />}
                    />
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Parameters Section */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <Settings className="h-5 w-5 text-gray-400" />
            Input Parameters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              {Object.entries(jobData.input_data).map(([key, value]) => (
                <div key={key} className="bg-gray-900/50 rounded-lg p-3">
                  <span className="text-gray-400 capitalize">{key.replace(/_/g, ' ')}:</span>
                  <p className="text-white mt-1 break-all">
                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Section */}
      {jobData.logs && jobData.logs.length > 0 && (
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <FileText className="h-5 w-5 text-gray-400" />
              Execution Logs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="bg-gray-900/50 rounded-lg p-4 max-h-64 overflow-y-auto">
              <pre className="text-xs text-gray-300 whitespace-pre-wrap">
                {jobData.logs.join('\n')}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error State */}
      {jobData.status === 'failed' && (
        <Alert className="border-red-700 bg-red-900/20">
          <Info className="h-4 w-4 text-red-400" />
          <AlertDescription className="text-red-400">
            This job failed to complete. Check the logs above for more details.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}; 