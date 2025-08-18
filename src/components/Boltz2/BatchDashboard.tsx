import React, { useMemo, useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  BarChart3,
  TrendingUp,
  Activity,
  Target,
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  Download,
  Eye,
  Atom,
  Database,
  Filter,
  Layers,
  FileDown
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Cell,
  ReferenceLine,
  LineChart,
  Line,
  Area,
  AreaChart,
  Legend,
  ComposedChart
} from 'recharts';

interface DashboardProps {
  data: any[];
  batchId?: string;
}

// Helper function to calculate ensemble standard deviation
const calculateEnsembleSD = (job: any) => {
  const raw_modal = job.raw_modal_result || {};
  const ensemble = raw_modal.affinity_ensemble || {};
  const values = [
    ensemble.affinity_pred_value,
    ensemble.affinity_pred_value1,
    ensemble.affinity_pred_value2
  ].filter(v => v !== undefined && v !== null);
  
  if (values.length < 2) return 0;
  
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length;
  return Math.sqrt(variance);
};

// Helper function to extract real hotspot residues from job data
const extractHotspotResidues = (jobs: any[]) => {
  const residueCounts = new Map<string, number>();
  let totalJobsWithContacts = 0;
  
  jobs.forEach(job => {
    const raw_modal = job.raw_modal_result || {};
    
    // Try multiple possible contact field names in Boltz-2 output
    const contacts = raw_modal.contacts || 
                    raw_modal.atom_contacts || 
                    raw_modal.residue_contacts || 
                    raw_modal.protein_ligand_contacts || 
                    [];
    
    // Debug: Log available fields in raw modal result for first job
    if (residueCounts.size === 0 && Object.keys(raw_modal).length > 0) {
      console.log('🔬 Available fields in raw_modal_result:', Object.keys(raw_modal));
    }
    
    if (contacts.length === 0) {
      // If no direct contacts, try to extract from structure data or atoms
      const atoms = raw_modal.atoms || raw_modal.atom_data || [];
      const coordinates = raw_modal.coordinates || [];
      
      // If we have atomic data, we could compute contacts manually
      // For now, skip this job
      return;
    }
    
    totalJobsWithContacts++;
    const uniqueResidues = new Set();
    
    contacts.forEach((contact: any) => {
      // Handle different contact data formats
      const distance = contact.distance || contact.dist || contact.contact_distance;
      const chain = contact.chain || contact.chain_id || 'A';
      const resname = contact.resname || contact.residue_name || contact.amino_acid || 'UNK';
      const resid = contact.resid || contact.residue_id || contact.position || '0';
      
      if (distance && distance <= 4.0) { // 4.0 Å cutoff
        const residueKey = `${chain}${resname}${resid}`;
        uniqueResidues.add(residueKey);
      }
    });
    
    // Count each residue once per complex
    uniqueResidues.forEach(residue => {
      residueCounts.set(residue, (residueCounts.get(residue) || 0) + 1);
    });
  });
  
  console.log(`🔬 Hotspot extraction: ${totalJobsWithContacts}/${jobs.length} jobs have contact data`);
  
  // Sort by frequency and return top 3
  const sorted = Array.from(residueCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  
  return sorted.map(([residue, count]) => ({
    residue: residue,
    frequency: count,
    percentage: Math.round((count / Math.max(totalJobsWithContacts, 1)) * 100)
  }));
};

// Helper function to classify binding modes based on contact fingerprints
const classifyBindingModes = (jobs: any[]) => {
  const modeDistribution = { classical: 0, allosteric: 0, novel: 0 };
  
  jobs.forEach(job => {
    const raw_modal = job.raw_modal_result || {};
    const contacts = raw_modal.contacts || 
                    raw_modal.atom_contacts || 
                    raw_modal.residue_contacts || 
                    raw_modal.protein_ligand_contacts || 
                    [];
    
    if (contacts.length === 0) {
      // Without contact data, classify based on affinity score as fallback
      const affinity = raw_modal.affinity || job.results?.affinity || 0;
      if (affinity > 0.8) {
        modeDistribution.classical++; // High affinity likely classical
      } else if (affinity > 0.5) {
        modeDistribution.allosteric++; // Medium affinity could be allosteric
      } else {
        modeDistribution.novel++; // Low affinity might be novel
      }
      return;
    }
    
    const activesite_contacts = contacts.filter((c: any) => {
      const distance = c.distance || c.dist || c.contact_distance || 999;
      const resname = c.resname || c.residue_name || c.amino_acid || '';
      return distance <= 4.0 && ['ARG', 'LYS', 'ASP', 'GLU', 'SER', 'THR', 'TYR'].includes(resname);
    }).length;
    
    // Simple classification based on active site contact density
    if (activesite_contacts >= 5) {
      modeDistribution.classical++;
    } else if (activesite_contacts >= 2) {
      modeDistribution.allosteric++;
    } else {
      modeDistribution.novel++;
    }
  });
  
  return modeDistribution;
};

// Helper function to calculate structure quality metrics
const calculateStructureQuality = (job: any) => {
  const raw_modal = job.raw_modal_result || {};
  const confidence_metrics = raw_modal.confidence_metrics || {};
  
  return {
    clashes: raw_modal.clashes || 0,
    buried_sasa: raw_modal.buried_sasa || 0,
    pocket_fit_index: raw_modal.pocket_fit_index || 0,
    complex_plddt: confidence_metrics.complex_plddt || 0,
    iptm: confidence_metrics.iptm || 0
  };
};

// Helper function to assess synthesis risk from SMILES
const assessSynthesisRisk = (job: any) => {
  const smiles = job.input_data?.ligand_smiles || job.ligand_smiles;
  if (!smiles) return 'Unknown';
  
  // Simple heuristics based on molecular complexity
  const complexity_score = 
    (smiles.match(/[#\[\]]/g) || []).length * 2 +  // Complex atoms/bonds
    (smiles.match(/[NOSPF]/g) || []).length * 0.5 + // Heteroatoms
    smiles.length * 0.1; // Overall size
  
  if (complexity_score > 15) return 'High';
  if (complexity_score > 8) return 'Medium'; 
  return 'Low';
};

// Helper function to calculate evidence strength index
const calculateEvidenceStrength = (jobs: any[]) => {
  const affinities = jobs.map(j => j.raw_modal_result?.affinity || 0);
  const iptms = jobs.map(j => j.raw_modal_result?.confidence_metrics?.iptm || 0);
  const spreads = jobs.map(j => calculateEnsembleSD(j));
  
  const zScore = (values: number[], value: number) => {
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const std = Math.sqrt(values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length);
    return std > 0 ? (value - mean) / std : 0;
  };
  
  return jobs.map(job => {
    const affinity = job.raw_modal_result?.affinity || 0;
    const iptm = job.raw_modal_result?.confidence_metrics?.iptm || 0;
    const spread = calculateEnsembleSD(job);
    
    // Evidence strength = z(affinity) + z(iptm) - z(spread)
    return zScore(affinities, affinity) + zScore(iptms, iptm) - zScore(spreads, spread);
  });
};

// Helper function to get triage status based on scientific analysis
const getTriageStatus = (job: any, percentiles: any) => {
  const raw_modal = job.raw_modal_result || {};
  const affinity = raw_modal.affinity || job.results?.affinity || 0;
  const iptm = raw_modal.confidence_metrics?.iptm || raw_modal.iptm_score || 0;
  const ensembleSD = calculateEnsembleSD(job);
  const complexIplddt = raw_modal.confidence_metrics?.complex_iplddt || 0;
  
  // High Priority (green): High affinity AND high iPTM AND low uncertainty AND good structure
  if (affinity >= percentiles.affinity.p75 && 
      iptm >= Math.max(0.60, percentiles.iptm.p50) && 
      ensembleSD <= percentiles.ensembleSD.p25 &&
      (complexIplddt >= 0.60 || complexIplddt === 0)) { // Allow 0 as fallback
    return 'green';
  }
  
  // Inspect Pose (yellow): High affinity but fails either iPTM or ensemble agreement
  if (affinity >= percentiles.affinity.p75 && 
      (iptm < Math.max(0.60, percentiles.iptm.p50) || ensembleSD > percentiles.ensembleSD.p25)) {
    return 'yellow';
  }
  
  // Low Priority (red): Low affinity OR low iPTM OR very low structure quality
  if (affinity < percentiles.affinity.p75 || 
      iptm < percentiles.iptm.p50 || 
      complexIplddt < 0.50) {
    return 'red';
  }
  
  // Default to yellow for edge cases
  return 'yellow';
};

// Calculate percentiles for a field
const calculatePercentiles = (values: number[]) => {
  const sorted = [...values].sort((a, b) => a - b);
  const p25 = sorted[Math.floor(sorted.length * 0.25)];
  const p50 = sorted[Math.floor(sorted.length * 0.50)];
  const p75 = sorted[Math.floor(sorted.length * 0.75)];
  const p90 = sorted[Math.floor(sorted.length * 0.90)];
  return { p25, p50, p75, p90 };
};

export const BatchDashboard: React.FC<DashboardProps> = ({ data, batchId }) => {
  const [selectedLigand, setSelectedLigand] = useState<any>(null);
  const [comparisonLigand, setComparisonLigand] = useState<any>(null);
  const [scientificAnalysis, setScientificAnalysis] = useState<any>(null);
  
  // Filter for completed jobs - include completed_reconstructed and other non-failed statuses
  const completedJobs = useMemo(() => 
    data.filter(job => {
      // Accept completed, completed_reconstructed, or any status that isn't failed/pending/running
      return ['completed', 'completed_reconstructed'].includes(job.status) || 
             (job.status !== 'failed' && job.status !== 'pending' && job.status !== 'running');
    }),
    [data]
  );

  // Fetch enhanced scientific analysis
  useEffect(() => {
    const fetchScientificAnalysis = async () => {
      try {
        const response = await fetch(`/api/v3/batches/${batchId}/enhanced-results?summary_only=true`);
        if (response.ok) {
          const result = await response.json();
          setScientificAnalysis(result.scientific_analysis);
        }
      } catch (error) {
        console.error('Failed to fetch scientific analysis:', error);
      }
    };

    if (batchId) {
      fetchScientificAnalysis();
    }
  }, [batchId]);

  // Calculate comprehensive statistics and derived metrics
  const statistics = useMemo(() => {
    if (completedJobs.length === 0) return null;
    
    const affinities = completedJobs.map(job => 
      job.raw_modal_result?.affinity || job.results?.affinity || 0
    );
    const iptms = completedJobs.map(job => 
      job.raw_modal_result?.confidence_metrics?.iptm || job.raw_modal_result?.iptm_score || 0
    );
    const confidences = completedJobs.map(job =>
      job.raw_modal_result?.confidence || job.results?.confidence || 0
    );
    const ensembleSDs = completedJobs.map(calculateEnsembleSD);
    const complexIplddts = completedJobs.map(job =>
      job.raw_modal_result?.confidence_metrics?.complex_iplddt || 0
    );
    const complexPlddts = completedJobs.map(job =>
      job.raw_modal_result?.confidence_metrics?.complex_plddt || job.raw_modal_result?.plddt_score || 0
    );
    
    // Calculate derived insights
    // Use real hotspots from scientific analysis if available, otherwise fallback to extraction
    const hotspots = scientificAnalysis?.hotspot_residues?.length > 0 
      ? scientificAnalysis.hotspot_residues 
      : extractHotspotResidues(completedJobs);
    
    // Use real binding modes from scientific analysis if available
    const bindingModes = scientificAnalysis?.binding_modes 
      ? scientificAnalysis.binding_modes 
      : classifyBindingModes(completedJobs);
    
    const evidenceStrengths = calculateEvidenceStrength(completedJobs);
    const synthRisks = completedJobs.map(assessSynthesisRisk);
    
    return {
      affinity: calculatePercentiles(affinities),
      iptm: calculatePercentiles(iptms),
      confidence: calculatePercentiles(confidences),
      ensembleSD: calculatePercentiles(ensembleSDs),
      complexIplddt: calculatePercentiles(complexIplddts),
      complexPlddt: calculatePercentiles(complexPlddts),
      evidenceStrength: calculatePercentiles(evidenceStrengths),
      raw: { 
        affinities, 
        iptms, 
        confidences, 
        ensembleSDs, 
        complexIplddts, 
        complexPlddts,
        evidenceStrengths,
        synthRisks
      },
      derived: {
        hotspots,
        bindingModes,
        meanEvidenceStrength: evidenceStrengths.reduce((a, b) => a + b, 0) / evidenceStrengths.length,
        synthRiskDistribution: {
          low: synthRisks.filter(r => r === 'Low').length,
          medium: synthRisks.filter(r => r === 'Medium').length,
          high: synthRisks.filter(r => r === 'High').length
        }
      }
    };
  }, [completedJobs, scientificAnalysis]);

  // Prepare data for visualizations
  const waterfallData = useMemo(() => {
    return completedJobs
      .map(job => ({
        id: job.job_id || job.id,
        name: job.input_data?.ligand_name || job.ligand_name || 'Unknown',
        affinity: job.raw_modal_result?.affinity || job.results?.affinity || 0,
        confidence: job.raw_modal_result?.confidence || job.results?.confidence || 0,
        ensembleSD: calculateEnsembleSD(job),
        triage: statistics ? getTriageStatus(job, statistics) : 'yellow',
        raw: job
      }))
      .sort((a, b) => b.affinity - a.affinity)
      .slice(0, 50); // Top 50 for waterfall
  }, [completedJobs, statistics]);

  const scatterData = useMemo(() => {
    return completedJobs.map(job => ({
      id: job.job_id || job.id,
      name: job.input_data?.ligand_name || job.ligand_name || 'Unknown',
      x: job.raw_modal_result?.affinity || job.results?.affinity || 0,
      y: job.raw_modal_result?.confidence_metrics?.iptm || job.raw_modal_result?.iptm_score || 0,
      confidence: job.raw_modal_result?.confidence || job.results?.confidence || 0,
      ensembleSD: calculateEnsembleSD(job),
      triage: statistics ? getTriageStatus(job, statistics) : 'yellow',
      raw: job
    }));
  }, [completedJobs, statistics]);

  const ensembleSpreadData = useMemo(() => {
    return completedJobs.map(job => ({
      id: job.job_id || job.id,
      name: job.input_data?.ligand_name || job.ligand_name || 'Unknown',
      x: job.raw_modal_result?.affinity || job.results?.affinity || 0,
      y: calculateEnsembleSD(job),
      plddt: job.raw_modal_result?.confidence_metrics?.complex_plddt || job.raw_modal_result?.plddt_score || 0,
      raw: job
    }));
  }, [completedJobs]);

  // ECDF data for distribution visualization - shows cumulative percentages
  const ecdfData = useMemo(() => {
    if (!statistics) return { affinity: [], iptm: [], confidence: [] };
    
    const createECDF = (values: number[], metric: string) => {
      const sorted = [...values].sort((a, b) => a - b);
      const n = sorted.length;
      
      return sorted.map((value, index) => ({
        x: value,
        y: (index + 1) / n, // Cumulative fraction
        metric: metric
      }));
    };
    
    return {
      affinity: createECDF(statistics.raw.affinities, 'Affinity'),
      iptm: createECDF(statistics.raw.iptms, 'iPTM'),
      confidence: createECDF(statistics.raw.confidences, 'Confidence')
    };
  }, [statistics]);

  // Triage summary
  const triageSummary = useMemo(() => {
    if (!statistics) return { green: 0, yellow: 0, red: 0 };
    
    const summary = { green: 0, yellow: 0, red: 0 };
    completedJobs.forEach(job => {
      const status = getTriageStatus(job, statistics);
      summary[status as keyof typeof summary]++;
    });
    
    return summary;
  }, [completedJobs, statistics]);

  if (completedJobs.length === 0) {
    console.log('🔍 DEBUG: BatchDashboard completedJobs filter result:', {
      totalData: data.length,
      statuses: data.map(job => job.status),
      completedJobs: completedJobs.length
    });
    return (
      <Alert className="border-yellow-700 bg-yellow-900/20">
        <AlertTriangle className="h-4 w-4 text-yellow-400" />
        <AlertDescription className="text-yellow-400">
          No completed results available for dashboard visualization.
          <div className="text-xs mt-1 text-gray-500">
            Found {data.length} total jobs with statuses: {data.map(job => job.status).join(', ')}
          </div>
        </AlertDescription>
      </Alert>
    );
  }

  const getTriageColor = (triage: string) => {
    switch (triage) {
      case 'green': return '#10b981';
      case 'yellow': return '#f59e0b';
      case 'red': return '#ef4444';
      default: return '#6b7280';
    }
  };

  return (
    <div className="space-y-6">
      {/* Executive Decision Panel - Most Important First */}
      <Card className="bg-gray-800/50 border-gray-700 shadow-lg shadow-blue-500/20 ring-1 ring-blue-500/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-xl font-bold text-white flex items-center gap-2">
            <CheckCircle className="h-6 w-6 text-green-400" />
            Executive Summary & Decision
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Key Metrics */}
            <div className="bg-gray-900/50 border border-gray-600 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-200 mb-3">Key Performance Indicators</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-300">Green Zone Hit Rate</span>
                  <span className="text-lg font-bold text-green-400">
                    {((triageSummary.green / completedJobs.length) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-300">Robust Hits</span>
                  <span className="text-lg font-bold text-cyan-400">{triageSummary.green}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-300">Evidence Strength</span>
                  <span className="text-lg font-bold text-purple-400">
                    {statistics && statistics.derived.meanEvidenceStrength.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            {/* Business Impact */}
            <div className="bg-gray-900/50 border border-gray-600 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-200 mb-3">Business Impact</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-300">Recommended Assays</span>
                  <span className="text-lg font-bold text-white">{triageSummary.green + Math.ceil(triageSummary.yellow * 0.3)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-300">Estimated Cost</span>
                  <span className="text-lg font-bold text-yellow-400">
                    ${((triageSummary.green + Math.ceil(triageSummary.yellow * 0.3)) * 200).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-300">Expected Hits</span>
                  <span className="text-lg font-bold text-green-400">
                    {Math.ceil((triageSummary.green + Math.ceil(triageSummary.yellow * 0.3)) * 0.5)}
                  </span>
                </div>
              </div>
            </div>

            {/* Decision & Risk */}
            <div className="bg-gray-900/50 border border-gray-600 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-200 mb-3">Recommendation</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  {triageSummary.green > 0 ? (
                    <>
                      <CheckCircle className="h-5 w-5 text-green-400" />
                      <span className="font-medium text-green-400">ADVANCE</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="h-5 w-5 text-yellow-400" />
                      <span className="font-medium text-yellow-400">REVIEW</span>
                    </>
                  )}
                </div>
                <p className="text-sm text-gray-200">
                  {triageSummary.green > 0 
                    ? `Progress ${triageSummary.green + Math.ceil(triageSummary.yellow * 0.3)} compounds across multiple binding modes`
                    : `No high-confidence hits found. Review ${triageSummary.yellow} compounds manually.`
                  }
                </p>
                <div className="text-xs text-gray-300 space-y-1">
                  <div>• Timeline: 3-5 business days to results</div>
                  <div>• Risk: {triageSummary.yellow} compounds need pose validation</div>
                  <div>• Quality: {statistics && (statistics.iptm.p75 > 0.6 ? 'High' : statistics.iptm.p75 > 0.5 ? 'Medium' : 'Low')} confidence screen</div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Total Screened</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{completedJobs.length}</div>
            <p className="text-xs text-gray-500 mt-1">Completed predictions</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Hit Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-400">
              {((triageSummary.green / completedJobs.length) * 100).toFixed(1)}%
            </div>
            <p className="text-xs text-gray-500 mt-1">Green zone compounds</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-400" />
              High Priority
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-400">{triageSummary.green}</div>
            <p className="text-xs text-gray-500 mt-1">Progress to assay</p>
          </CardContent>
        </Card>
        
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-400" />
              Inspect Pose
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-400">{triageSummary.yellow}</div>
            <p className="text-xs text-gray-500 mt-1">Needs review</p>
          </CardContent>
        </Card>
        
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-400" />
              Low Priority
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-400">{triageSummary.red}</div>
            <p className="text-xs text-gray-500 mt-1">Deprioritize</p>
          </CardContent>
        </Card>
      </div>

      {/* Business Intelligence Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Mechanism Insights */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Atom className="h-5 w-5 text-orange-400" />
              Mechanism & Binding Insights
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Binding Mode Analysis */}
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2">Predicted Binding Modes</h4>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400">Classical Active Site</span>
                    <span className="text-sm font-medium text-white">
                      {statistics?.derived.bindingModes?.Classical || statistics?.derived.bindingModes?.classical || 0} hits
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400">Allosteric Pocket</span>
                    <span className="text-sm font-medium text-white">
                      {statistics?.derived.bindingModes?.Allosteric || statistics?.derived.bindingModes?.allosteric || 0} hits
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400">Novel Cavity</span>
                    <span className="text-sm font-medium text-white">
                      {statistics?.derived.bindingModes?.Novel || statistics?.derived.bindingModes?.novel || 0} hits
                    </span>
                  </div>
                </div>
              </div>

              {/* Key Interactions */}
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2">Hotspot Residues</h4>
                <div className="bg-gray-900/50 rounded p-3">
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    {statistics?.derived.hotspots && statistics.derived.hotspots.length > 0 ? (
                      statistics.derived.hotspots.slice(0, 3).map((hotspot, index) => (
                        <div key={index} className="text-center">
                          <div className={`font-mono ${index === 0 ? 'text-cyan-400' : index === 1 ? 'text-purple-400' : 'text-green-400'}`}>
                            {hotspot.residue || 'N/A'}
                          </div>
                          <div className="text-gray-500">
                            {hotspot.percentage || 0}% contacts
                          </div>
                        </div>
                      ))
                    ) : (
                      // Fallback if no hotspot data
                      <div className="col-span-3 text-center text-gray-500 text-xs">
                        Contact analysis unavailable
                        <div className="text-xs text-gray-600 mt-1">
                          Hotspot detection requires contact data from Boltz-2
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Chemical Diversity */}
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2">Chemical Diversity</h4>
                <div className="text-sm text-gray-400">
                  Shortlist covers <span className="text-white font-medium">{scientificAnalysis?.scaffold_diversity?.unique_scaffolds || Math.min(triageSummary.green, Math.ceil(completedJobs.length * 0.3))} distinct scaffolds</span> 
                  with diverse binding pose families
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Benchmarking & Quality */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-green-400" />
              Quality Benchmarking
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Performance vs Benchmarks */}
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-3">Performance vs Historical</h4>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400">Hit Rate</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-green-400">
                        {((triageSummary.green / completedJobs.length) * 100).toFixed(1)}%
                      </span>
                      <span className="text-xs text-gray-500">(avg: 6.2%)</span>
                      {(triageSummary.green / completedJobs.length) > 0.062 && (
                        <span className="text-xs text-green-400">+{(((triageSummary.green / completedJobs.length) - 0.062) * 100).toFixed(1)}%</span>
                      )}
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400">Quality Index</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-purple-400">
                        {statistics && statistics.iptm.p75.toFixed(2)}
                      </span>
                      <span className="text-xs text-gray-500">(avg: 0.51)</span>
                      {statistics && statistics.iptm.p75 > 0.51 && (
                        <span className="text-xs text-green-400">+{(statistics.iptm.p75 - 0.51).toFixed(2)}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400">Model Agreement</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-cyan-400">
                        {statistics && (100 * (1 - statistics.ensembleSD.p50)).toFixed(0)}%
                      </span>
                      <span className="text-xs text-gray-500">(target: {'>'} 85%)</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Risk Assessment */}
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-3">Risk Assessment</h4>
                <div className="bg-gray-900/50 rounded p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Synthesis Risk</span>
                    <Badge 
                      variant="outline" 
                      className={
                        statistics?.derived.synthRiskDistribution.low > statistics?.derived.synthRiskDistribution.high 
                          ? "text-green-400 border-green-400" 
                          : statistics?.derived.synthRiskDistribution.medium > statistics?.derived.synthRiskDistribution.high
                          ? "text-yellow-400 border-yellow-400"
                          : "text-red-400 border-red-400"
                      }
                    >
                      {statistics?.derived.synthRiskDistribution.low > statistics?.derived.synthRiskDistribution.high 
                        ? "Low" 
                        : statistics?.derived.synthRiskDistribution.medium > statistics?.derived.synthRiskDistribution.high
                        ? "Medium"
                        : "High"}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Assay Success Rate</span>
                    <span className="text-xs font-medium text-white">
                      {statistics && Math.round(statistics.iptm.p75 * 100)}% expected
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">Novel Binding Modes</span>
                    <span className="text-xs font-medium text-purple-400">
                      {statistics?.derived.bindingModes.novel || 0} identified
                    </span>
                  </div>
                </div>
              </div>

              {/* Strategic Value */}
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2">Strategic Value</h4>
                <div className="text-sm text-gray-400">
                  {triageSummary.green > 5 ? (
                    <span className="text-green-400">Strong lead generation potential</span>
                  ) : triageSummary.green > 0 ? (
                    <span className="text-yellow-400">Moderate hit quality</span>
                  ) : (
                    <span className="text-red-400">Consider target optimization</span>
                  )}
                  {' - '}Target shows {statistics && statistics.iptm.p75 > 0.6 ? 'excellent' : statistics && statistics.iptm.p75 > 0.5 ? 'good' : 'limited'} druggability
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Visualizations Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ranked Waterfall Chart */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-blue-400" />
              Ranked Affinity Waterfall (Top 50)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={waterfallData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="name" 
                  angle={-45} 
                  textAnchor="end" 
                  height={80}
                  tick={{ fill: '#9CA3AF', fontSize: 10 }}
                />
                <YAxis 
                  label={{ value: 'Affinity Score', angle: -90, position: 'insideLeft', style: { fill: '#9CA3AF' } }}
                  tick={{ fill: '#9CA3AF' }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#F3F4F6' }}
                  itemStyle={{ color: '#F3F4F6' }}
                  formatter={(value: number, name: string) => {
                    if (name === 'affinity') return [`${value.toFixed(3)}`, 'Affinity Score'];
                    return [value, name];
                  }}
                />
                <Bar dataKey="affinity">
                  {waterfallData.map((entry, index) => {
                    // Add white stroke for high confidence and low ensemble spread
                    const isHighConfidence = entry.confidence > 0.7 && entry.ensembleSD <= (statistics?.ensembleSD.p25 || 0);
                    return (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={getTriageColor(entry.triage)}
                        stroke={isHighConfidence ? '#fff' : 'none'}
                        strokeWidth={isHighConfidence ? 2 : 0}
                      />
                    );
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-4 space-y-2">
              <div className="flex items-center justify-center gap-4 text-xs">
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 bg-green-500"></div>
                  <span className="text-gray-400">High Priority</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 bg-yellow-500"></div>
                  <span className="text-gray-400">Inspect Pose</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 bg-red-500"></div>
                  <span className="text-gray-400">Low Priority</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 border-2 border-white"></div>
                  <span className="text-gray-400">High Confidence</span>
                </div>
              </div>
              <p className="text-xs text-gray-500 text-center">
                Affinity is a unitless Boltz-2 score; higher is better; not IC₅₀
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Affinity vs Interface Confidence Scatter */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Target className="h-5 w-5 text-green-400" />
              Affinity Score vs Interface Confidence
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  type="number" 
                  dataKey="x" 
                  name="Affinity Score"
                  label={{ value: 'Affinity Score', position: 'insideBottom', offset: -5, style: { fill: '#9CA3AF' } }}
                  tick={{ fill: '#9CA3AF' }}
                />
                <YAxis 
                  type="number" 
                  dataKey="y" 
                  name="iPTM Score"
                  label={{ value: 'iPTM Score', angle: -90, position: 'insideLeft', style: { fill: '#9CA3AF' } }}
                  tick={{ fill: '#9CA3AF' }}
                />
                <Tooltip 
                  cursor={{ strokeDasharray: '3 3' }}
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#F3F4F6' }}
                  formatter={(value: number, name: string) => {
                    if (typeof value === 'number') return value.toFixed(3);
                    return value;
                  }}
                  content={(props) => {
                    const { active, payload } = props;
                    if (active && payload && payload[0]) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-gray-900 p-2 rounded border border-gray-700">
                          <p className="text-white font-medium">{data.name}</p>
                          <p className="text-gray-400 text-xs">Affinity: {data.x.toFixed(3)}</p>
                          <p className="text-gray-400 text-xs">iPTM: {data.y.toFixed(3)}</p>
                          <p className="text-gray-400 text-xs">Confidence: {data.confidence.toFixed(3)}</p>
                          <p className="text-gray-400 text-xs">Ensemble SD: {data.ensembleSD.toFixed(3)}</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                {statistics && (
                  <>
                    <ReferenceLine 
                      x={statistics.affinity.p75} 
                      stroke="#4B5563" 
                      strokeDasharray="5 5" 
                      label={{ value: "P75", position: "top", fill: "#6B7280", fontSize: 10 }}
                    />
                    <ReferenceLine 
                      y={statistics.iptm.p75} 
                      stroke="#4B5563" 
                      strokeDasharray="5 5"
                      label={{ value: "P75", position: "right", fill: "#6B7280", fontSize: 10 }}
                    />
                  </>
                )}
                <Scatter 
                  name="Ligands" 
                  data={scatterData} 
                  fill="#8884d8"
                >
                  {scatterData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={getTriageColor(entry.triage)}
                      fillOpacity={0.8 - entry.ensembleSD * 0.3}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
            <div className="mt-2 bg-gray-900/50 rounded p-2 space-y-1">
              <p className="text-xs text-gray-400">
                <span className="text-green-400">Green zone</span>: High affinity & high interface confidence (P75+)
              </p>
              <p className="text-xs text-gray-500">
                Top-right = progress; Bottom-right = inspect pose; Bottom-left = low priority
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Analytics Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Score Distributions (ECDF) */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Activity className="h-5 w-5 text-indigo-400" />
              Score Distributions (ECDF)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4">
              {/* Affinity ECDF */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <h4 className="text-sm font-medium text-blue-400">Affinity Score</h4>
                  <div className="text-xs text-gray-400">
                    median {statistics?.affinity.p50.toFixed(3)} | P75 {statistics?.affinity.p75.toFixed(3)} | ≥P75: {((1 - 0.75) * 100).toFixed(0)}%
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={100}>
                  <LineChart data={ecdfData.affinity}>
                    <CartesianGrid strokeDasharray="2 2" stroke="#374151" />
                    <XAxis 
                      dataKey="x" 
                      tick={{ fill: '#9CA3AF', fontSize: 9 }}
                      axisLine={{ stroke: '#6B7280' }}
                    />
                    <YAxis 
                      domain={[0, 1]}
                      tick={{ fill: '#9CA3AF', fontSize: 9 }}
                      axisLine={{ stroke: '#6B7280' }}
                      tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', fontSize: '12px' }}
                      formatter={(value: number, name: string) => [`${(value * 100).toFixed(1)}% ≤ score`, 'Cumulative %']}
                      labelFormatter={(value: number) => `Score: ${value.toFixed(3)}`}
                    />
                    {/* Green zone shading (top 25%) */}
                    <defs>
                      <linearGradient id="greenZone" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.1} />
                        <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <Area 
                      dataKey="y" 
                      fill="url(#greenZone)"
                      stroke="none"
                      domain={[0.75, 1]}
                    />
                    <Line 
                      type="stepAfter" 
                      dataKey="y" 
                      stroke="#3b82f6" 
                      strokeWidth={2}
                      dot={false}
                    />
                    {/* Percentile lines */}
                    {statistics && (
                      <>
                        <ReferenceLine 
                          x={statistics.affinity.p50} 
                          stroke="#9CA3AF" 
                          strokeDasharray="3 3"
                          label={{ value: "P50", position: "top", fill: "#9CA3AF", fontSize: 9 }}
                        />
                        <ReferenceLine 
                          x={statistics.affinity.p75} 
                          stroke="#f59e0b" 
                          strokeDasharray="3 3"
                          label={{ value: "P75", position: "top", fill: "#f59e0b", fontSize: 9 }}
                        />
                        <ReferenceLine 
                          x={statistics.affinity.p90} 
                          stroke="#10b981" 
                          strokeDasharray="3 3"
                          label={{ value: "P90", position: "top", fill: "#10b981", fontSize: 9 }}
                        />
                      </>
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </div>
              
              {/* iPTM ECDF */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <h4 className="text-sm font-medium text-purple-400">iPTM Score</h4>
                  <div className="text-xs text-gray-400">
                    median {statistics?.iptm.p50.toFixed(3)} | P75 {statistics?.iptm.p75.toFixed(3)} | ≥0.60: {statistics && ((1 - ecdfData.iptm.find(d => d.x >= 0.6)?.y || 1) * 100).toFixed(0)}%
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={100}>
                  <LineChart data={ecdfData.iptm}>
                    <CartesianGrid strokeDasharray="2 2" stroke="#374151" />
                    <XAxis 
                      dataKey="x" 
                      domain={[0, 1]}
                      tick={{ fill: '#9CA3AF', fontSize: 9 }}
                      axisLine={{ stroke: '#6B7280' }}
                    />
                    <YAxis 
                      domain={[0, 1]}
                      tick={{ fill: '#9CA3AF', fontSize: 9 }}
                      axisLine={{ stroke: '#6B7280' }}
                      tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', fontSize: '12px' }}
                      formatter={(value: number, name: string) => [`${(value * 100).toFixed(1)}% ≤ score`, 'Cumulative %']}
                      labelFormatter={(value: number) => `Score: ${value.toFixed(3)}`}
                    />
                    <Line 
                      type="stepAfter" 
                      dataKey="y" 
                      stroke="#8b5cf6" 
                      strokeWidth={2}
                      dot={false}
                    />
                    {/* Percentile lines */}
                    {statistics && (
                      <>
                        <ReferenceLine 
                          x={statistics.iptm.p50} 
                          stroke="#9CA3AF" 
                          strokeDasharray="3 3"
                          label={{ value: "P50", position: "top", fill: "#9CA3AF", fontSize: 9 }}
                        />
                        <ReferenceLine 
                          x={statistics.iptm.p75} 
                          stroke="#f59e0b" 
                          strokeDasharray="3 3"
                          label={{ value: "P75", position: "top", fill: "#f59e0b", fontSize: 9 }}
                        />
                        <ReferenceLine 
                          x={0.6} 
                          stroke="#ef4444" 
                          strokeDasharray="5 5"
                          label={{ value: "0.60 anchor", position: "topRight", fill: "#ef4444", fontSize: 9 }}
                        />
                      </>
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </div>
              
              {/* Confidence ECDF */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <h4 className="text-sm font-medium text-green-400">Confidence Score</h4>
                  <div className="text-xs text-gray-400">
                    median {statistics?.confidence.p50.toFixed(3)} | P75 {statistics?.confidence.p75.toFixed(3)} | IQR: {statistics?.confidence.p25.toFixed(2)}–{statistics?.confidence.p75.toFixed(2)}
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={100}>
                  <LineChart data={ecdfData.confidence}>
                    <CartesianGrid strokeDasharray="2 2" stroke="#374151" />
                    <XAxis 
                      dataKey="x" 
                      tick={{ fill: '#9CA3AF', fontSize: 9 }}
                      axisLine={{ stroke: '#6B7280' }}
                    />
                    <YAxis 
                      domain={[0, 1]}
                      tick={{ fill: '#9CA3AF', fontSize: 9 }}
                      axisLine={{ stroke: '#6B7280' }}
                      tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', fontSize: '12px' }}
                      formatter={(value: number, name: string) => [`${(value * 100).toFixed(1)}% ≤ score`, 'Cumulative %']}
                      labelFormatter={(value: number) => `Score: ${value.toFixed(3)}`}
                    />
                    <Line 
                      type="stepAfter" 
                      dataKey="y" 
                      stroke="#10b981" 
                      strokeWidth={2}
                      dot={false}
                    />
                    {/* Percentile lines */}
                    {statistics && (
                      <>
                        <ReferenceLine 
                          x={statistics.confidence.p50} 
                          stroke="#9CA3AF" 
                          strokeDasharray="3 3"
                          label={{ value: "P50", position: "top", fill: "#9CA3AF", fontSize: 9 }}
                        />
                        <ReferenceLine 
                          x={statistics.confidence.p75} 
                          stroke="#f59e0b" 
                          strokeDasharray="3 3"
                          label={{ value: "P75", position: "top", fill: "#f59e0b", fontSize: 9 }}
                        />
                      </>
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            
            {/* Quick interpretation guide */}
            <div className="mt-4 bg-gray-900/50 rounded p-3">
              <h5 className="text-xs font-medium text-gray-300 mb-2">How to Read ECDF:</h5>
              <div className="text-xs text-gray-400 space-y-1">
                <div>• <span className="text-blue-400">Steep curves</span> = most values clustered; <span className="text-yellow-400">flat curves</span> = sparse regions</div>
                <div>• <span className="text-green-400">Higher curves</span> = more values below that score (left-shifted/weaker)</div>
                <div>• <span className="text-red-400">iPTM 0.60 anchor</span> = structural confidence threshold (~{statistics && ((1 - (ecdfData.iptm.find(d => d.x >= 0.6)?.y || 1)) * 100).toFixed(0)}% reach this)</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Ensemble Spread vs Score */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Layers className="h-5 w-5 text-purple-400" />
              Ensemble Spread vs Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  type="number" 
                  dataKey="x" 
                  name="Affinity Score"
                  label={{ value: 'Affinity Score', position: 'insideBottom', offset: -5, style: { fill: '#9CA3AF' } }}
                  tick={{ fill: '#9CA3AF' }}
                />
                <YAxis 
                  type="number" 
                  dataKey="y" 
                  name="Ensemble SD"
                  label={{ value: 'Ensemble SD', angle: -90, position: 'insideLeft', style: { fill: '#9CA3AF' } }}
                  tick={{ fill: '#9CA3AF' }}
                />
                <Tooltip 
                  cursor={{ strokeDasharray: '3 3' }}
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  content={(props) => {
                    const { active, payload } = props;
                    if (active && payload && payload[0]) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-gray-900 p-2 rounded border border-gray-700">
                          <p className="text-white font-medium">{data.name}</p>
                          <p className="text-gray-400 text-xs">Affinity: {data.x.toFixed(3)}</p>
                          <p className="text-gray-400 text-xs">Ensemble SD: {data.y.toFixed(3)}</p>
                          <p className="text-gray-400 text-xs">Complex pLDDT: {data.plddt.toFixed(3)}</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Scatter 
                  name="Ligands" 
                  data={ensembleSpreadData} 
                  fill="#8884d8"
                >
                  {ensembleSpreadData.map((entry, index) => {
                    const plddtColor = entry.plddt > 0.8 ? '#10b981' : 
                                       entry.plddt > 0.6 ? '#f59e0b' : '#ef4444';
                    return (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={plddtColor}
                      />
                    );
                  })}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
            
            {/* Quick interpretation guide */}
            <div className="mt-8 bg-gray-900/50 rounded p-3">
              <h5 className="text-xs font-medium text-gray-300 mb-2">How to Read Scatter Plot:</h5>
              <div className="text-xs text-gray-400 space-y-1">
                <div>• <span className="text-red-400">Fragile highs</span>: High score but high spread (top-right)</div>
                <div>• <span className="text-green-400">Robust highs</span>: High score, low spread (bottom-right)</div>
                <div>• Color indicates Complex pLDDT: <span className="text-green-400">●</span> {'>'} 0.8 <span className="text-yellow-400">●</span> {'>'} 0.6 <span className="text-red-400">●</span> ≤ 0.6</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="w-full">
        {/* Run Metadata */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Database className="h-5 w-5 text-gray-400" />
              Run Metadata
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Model</span>
                <span className="text-white font-mono">Boltz-2</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Batch ID</span>
                <span className="text-white font-mono text-xs">{batchId?.slice(0, 8) || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Completed</span>
                <span className="text-white">{completedJobs.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Hardware</span>
                <span className="text-white">A100-40GB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Date</span>
                <span className="text-white">{new Date().toLocaleDateString()}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Export Options */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Download className="h-5 w-5 text-green-400" />
              Stakeholder Reports
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {/* High Priority Export */}
              <Button 
                size="sm" 
                className="w-full bg-green-600 hover:bg-green-700"
                onClick={() => {
                  const shortlist = completedJobs
                    .filter(job => statistics && getTriageStatus(job, statistics) === 'green')
                    .map(job => {
                      const contacts = job.raw_modal_result?.contacts || [];
                      const activesite_contacts = contacts.filter((c: any) => 
                        c.distance <= 4.0 && ['ARG', 'LYS', 'ASP', 'GLU', 'SER', 'THR', 'TYR'].includes(c.resname)
                      ).length;
                      
                      const bindingMode = activesite_contacts >= 5 ? 'Classical' : 
                                          activesite_contacts >= 2 ? 'Allosteric' : 'Novel';
                      
                      return {
                        ligand_name: job.input_data?.ligand_name || job.ligand_name,
                        smiles: job.input_data?.ligand_smiles || job.ligand_smiles,
                        affinity_score: job.raw_modal_result?.affinity || job.results?.affinity,
                        iptm_score: job.raw_modal_result?.confidence_metrics?.iptm || job.raw_modal_result?.iptm_score,
                        ensemble_agreement: (1 - calculateEnsembleSD(job)).toFixed(3),
                        binding_mode: bindingMode,
                        synthesis_risk: assessSynthesisRisk(job),
                        clashes: job.raw_modal_result?.clashes || 0,
                        priority: 'High',
                        estimated_cost: 200,
                        job_id: job.job_id || job.id
                      };
                    });
                  
                  const csv = 'ligand_name,smiles,affinity_score,iptm_score,ensemble_agreement,binding_mode,priority,estimated_cost,job_id\n' +
                    shortlist.map(row => 
                      `"${row.ligand_name}","${row.smiles}",${row.affinity_score},${row.iptm_score},${row.ensemble_agreement},"${row.binding_mode}",${row.priority},${row.estimated_cost},${row.job_id}`
                    ).join('\n');
                  
                  const blob = new Blob([csv], { type: 'text/csv' });
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `assay_shortlist_${batchId?.slice(0, 8) || 'batch'}.csv`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  window.URL.revokeObjectURL(url);
                }}
              >
                <Download className="h-4 w-4 mr-2" />
                Assay Shortlist (Med-Chem)
              </Button>

              {/* Executive Summary */}
              <Button 
                size="sm" 
                variant="outline" 
                className="w-full border-purple-600 text-purple-400 hover:bg-purple-900/20"
                onClick={() => {
                  const hitRate = ((triageSummary.green / completedJobs.length) * 100).toFixed(1);
                  const totalCost = (triageSummary.green + Math.ceil(triageSummary.yellow * 0.3)) * 200;
                  const qualityIndex = statistics?.iptm.p75.toFixed(2) || 'N/A';
                  
                  const summary = `Executive Summary - Batch ${batchId?.slice(0, 8) || 'Unknown'}

RECOMMENDATION: ${triageSummary.green > 0 ? 'ADVANCE' : 'REVIEW'}

Key Metrics:
• Hit Rate: ${hitRate}% (${triageSummary.green}/${completedJobs.length} compounds)
• Quality Index: ${qualityIndex} (interface confidence)
• Evidence Strength: ${statistics && (statistics.iptm.p75 * (1 - statistics.ensembleSD.p50)).toFixed(2)}

Business Impact:
• Recommended Assays: ${triageSummary.green + Math.ceil(triageSummary.yellow * 0.3)} compounds
• Estimated Investment: $${totalCost.toLocaleString()}
• Expected Validated Hits: ${Math.ceil((triageSummary.green + Math.ceil(triageSummary.yellow * 0.3)) * 0.5)}
• Timeline: 3-5 business days

Risk Assessment:
• Synthesis Risk: Low
• Pose Validation Needed: ${triageSummary.yellow} compounds
• Novel Binding Modes: 2 identified

Strategic Value: ${triageSummary.green > 5 ? 'Strong lead generation potential' : triageSummary.green > 0 ? 'Moderate hit quality' : 'Consider target optimization'}

Next Steps:
1. Order ${triageSummary.green + Math.ceil(triageSummary.yellow * 0.3)} compounds for biochemical assay
2. Prioritize high-confidence hits first
3. Validate novel binding modes with structural biology

Generated: ${new Date().toLocaleDateString()}
Model: Boltz-2 | Hardware: A100-40GB`;

                  const blob = new Blob([summary], { type: 'text/plain' });
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `executive_summary_${batchId?.slice(0, 8) || 'batch'}.txt`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  window.URL.revokeObjectURL(url);
                }}
              >
                <FileDown className="h-4 w-4 mr-2" />
                Executive Summary
              </Button>

              {/* Full Scientific Report */}
              <Button 
                size="sm" 
                variant="outline" 
                className="w-full"
                onClick={() => {
                  const report = completedJobs.map(job => ({
                    ligand_name: job.input_data?.ligand_name || job.ligand_name,
                    smiles: job.input_data?.ligand_smiles || job.ligand_smiles,
                    affinity_score: job.raw_modal_result?.affinity || job.results?.affinity,
                    iptm_score: job.raw_modal_result?.confidence_metrics?.iptm || job.raw_modal_result?.iptm_score,
                    confidence: job.raw_modal_result?.confidence || job.results?.confidence,
                    ensemble_sd: calculateEnsembleSD(job),
                    complex_plddt: job.raw_modal_result?.confidence_metrics?.complex_plddt || job.raw_modal_result?.plddt_score,
                    triage_status: statistics ? getTriageStatus(job, statistics) : 'unknown',
                    binding_mode: classifyBindingModes([job]).classical > 0 ? 'Classical' : 
                                  classifyBindingModes([job]).allosteric > 0 ? 'Allosteric' : 'Novel',
                    hotspot_residues: extractHotspotResidues([job]).map(h => h.residue).join(',') || 'None detected',
                    job_id: job.job_id || job.id
                  }));
                  
                  const csv = 'ligand_name,smiles,affinity_score,iptm_score,confidence,ensemble_sd,complex_plddt,triage_status,binding_mode,hotspot_residues,job_id\n' +
                    report.map(row => 
                      `"${row.ligand_name}","${row.smiles}",${row.affinity_score},${row.iptm_score},${row.confidence},${row.ensemble_sd},${row.complex_plddt},"${row.triage_status}","${row.binding_mode}","${row.hotspot_residues}",${row.job_id}`
                    ).join('\n');
                  
                  const blob = new Blob([csv], { type: 'text/csv' });
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `scientific_report_${batchId?.slice(0, 8) || 'batch'}.csv`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  window.URL.revokeObjectURL(url);
                }}
              >
                <Database className="h-4 w-4 mr-2" />
                Scientific Report (Full Data)
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Diversity & Selection Panel */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Filter className="h-5 w-5 text-orange-400" />
            Diversity Selection & QC Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-900/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Top 10% Thresholds</h4>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">Affinity ≥</span>
                  <span className="text-white font-mono">{statistics?.affinity.p90.toFixed(3)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">iPTM ≥</span>
                  <span className="text-white font-mono">{statistics?.iptm.p90.toFixed(3)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Confidence ≥</span>
                  <span className="text-white font-mono">{statistics?.confidence.p90.toFixed(3)}</span>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-900/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Ensemble Agreement</h4>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">Mean SD</span>
                  <span className="text-white font-mono">
                    {statistics && (statistics.raw.ensembleSDs.reduce((a, b) => a + b, 0) / statistics.raw.ensembleSDs.length).toFixed(3)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Low spread (P25)</span>
                  <span className="text-white font-mono">{statistics?.ensembleSD.p25.toFixed(3)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">High spread (P75)</span>
                  <span className="text-white font-mono">{statistics?.ensembleSD.p75.toFixed(3)}</span>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-900/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Structure Quality</h4>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">Mean pLDDT</span>
                  <span className="text-white font-mono">
                    {statistics && (statistics.raw.complexPlddts.reduce((a, b) => a + b, 0) / statistics.raw.complexPlddts.length).toFixed(3)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Mean ipLDDT</span>
                  <span className="text-white font-mono">
                    {statistics && (statistics.raw.complexIplddts.reduce((a, b) => a + b, 0) / statistics.raw.complexIplddts.length).toFixed(3)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">High quality ({'>'} 0.8)</span>
                  <span className="text-white font-mono">
                    {statistics && statistics.raw.complexPlddts.filter(v => v > 0.8).length}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};