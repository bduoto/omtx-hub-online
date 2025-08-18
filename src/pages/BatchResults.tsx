import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { BatchProteinLigandOutput } from '@/components/Boltz2/BatchProteinLigandOutput';

interface BatchResult {
  job_id: string;
  batch_id?: string;
  task_type: string;
  status: string;
  batch_summary?: {
    total_ligands: number;
    completed_jobs: number;
    failed_jobs: number;
    execution_time: number;
  };
  progress?: {
    total_jobs: number;
    completed_jobs: number;
    failed_jobs: number;
    pending_jobs: number;
    total?: number;
    completed?: number;
    failed?: number;
    running?: number;
  };
  individual_results?: any[];
  individual_jobs?: any[];
  individual_job_ids?: string[];
  estimated_completion?: number;
  message?: string;
  results?: {
    individual_jobs?: any[];
  };
}

const BatchResults = () => {
  const { batchId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cacheRef = useRef<Map<string, {data: BatchResult, timestamp: number}>>(new Map());

  useEffect(() => {
    const loadBatchResults = async () => {
      if (!batchId) return;
      
      try {
        // Check cache first (5 minute TTL)
        const cache = cacheRef.current;
        const cached = cache.get(batchId);
        const now = Date.now();
        
        if (cached && (now - cached.timestamp) < 300000) { // 5 minutes
          console.log('✅ Using cached batch results');
          setBatchResult(cached.data);
          setLoading(false);
          return;
        }
        
        setLoading(true);
        console.log('🔍 BatchResults - Loading batch:', batchId);
        console.time('API Load Time');
        
        // OPTIMIZED: Single API call to enhanced results with raw modal data for comprehensive metrics
        const response = await fetch(
          `/api/v3/batches/${batchId}/enhanced-results?page=1&page_size=100&include_raw_modal=true`, {
          headers: {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, br',
            'Cache-Control': 'no-cache'
          }
        });
        
        if (!response.ok) {
          throw new Error(`Enhanced results failed: ${response.status}`);
        }
        
        const enhancedData = await response.json();
        console.log('✅ Enhanced API response:', enhancedData);
        
        // OPTIMIZED: Process results with comprehensive raw modal data extraction
        const individualResults = enhancedData.individual_results || [];
        const processedResults = individualResults.map((result: any, index: number) => {
          // Extract data from the enhanced API response structure
          const affinity = result.affinity || result.raw_modal_result?.affinity || 0;
          const confidence = result.confidence || result.raw_modal_result?.confidence || 0;
          const ligandName = result.ligand_name || result.input_data?.ligand_name || `${index + 1}`;
          const smiles = result.ligand_smiles || result.input_data?.ligand_smiles || '';
          
          return {
            id: result.job_id || `${batchId}_${index}`,
            job_id: result.job_id,
            ligand_name: ligandName,
            ligand_smiles: smiles,
            status: result.status || 'completed',
            affinity: affinity,
            confidence: confidence,
            input_data: {
              ligand_name: ligandName,
              ligand_smiles: smiles,
              batch_index: index
            },
            results: {
              affinity: affinity,
              confidence: confidence,
              binding_score: affinity
            },
            // Include all raw modal data for comprehensive metrics
            raw_modal_result: result.raw_modal_result || {},
            affinity_ensemble: result.affinity_ensemble || {},
            confidence_metrics: result.confidence_metrics || {},
            prediction_confidence: result.prediction_confidence || {},
            binding_affinity: result.binding_affinity || {}
          };
        });

        // OPTIMIZED: Streamlined batch result format
        const batchResult: BatchResult = {
          job_id: batchId || '',
          batch_id: batchId,
          task_type: 'batch_protein_ligand_screening',
          status: enhancedData.batch_status || 'completed',
          batch_summary: {
            total_ligands: enhancedData.total_ligands_screened || processedResults.length,
            completed_jobs: enhancedData.successful_predictions || processedResults.length,
            failed_jobs: enhancedData.failed_predictions || 0,
            execution_time: 0
          },
          progress: {
            total_jobs: enhancedData.total_ligands_screened || processedResults.length,
            completed_jobs: enhancedData.successful_predictions || processedResults.length,
            failed_jobs: enhancedData.failed_predictions || 0,
            pending_jobs: 0
          },
          individual_results: processedResults,
          individual_jobs: processedResults,
          message: `Loaded ${processedResults.length} results`
        };
        
        console.timeEnd('API Load Time');
        
        // Cache the result
        cache.set(batchId, { data: batchResult, timestamp: now });
        
        setBatchResult(batchResult);
        setLoading(false);
        return;
        
      } catch (err) {
        console.error('Failed to load batch results:', err);
        setError(err instanceof Error ? err.message : 'Failed to load batch results');
        toast.error('Failed to load batch results');
        setLoading(false);
      }
    };

    loadBatchResults();
  }, [batchId]);

  return (
    <div className="min-h-screen bg-gray-900">
      <Header />
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/my-batches')}
            className="text-gray-400 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Batches
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-white">
              Batch Results
            </h1>
            <p className="text-gray-400">
              {batchResult?.batch_summary?.total_ligands || 0} ligands • {batchId?.slice(0, 8)}...
            </p>
          </div>
        </div>

        {/* Use the functional BatchProteinLigandOutput component */}
        <BatchProteinLigandOutput
          result={batchResult}
          isLoading={loading}
        />

        {/* Error Display */}
        {error && !loading && (
          <div className="mt-6 p-4 bg-red-900/20 border border-red-800 rounded-lg">
            <div className="text-red-400">
              <p className="font-medium">Error loading batch results:</p>
              <p className="text-sm mt-1">{error}</p>
              <p className="text-sm mt-2 text-red-300">
                Try refreshing the page or contact support if the issue persists.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default BatchResults;