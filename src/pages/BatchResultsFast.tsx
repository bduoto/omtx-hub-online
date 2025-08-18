import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Activity } from 'lucide-react';
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
  };
  individual_results?: any[];
  individual_jobs?: any[];
  message?: string;
}

// Global cache for ultra-fast loads
const globalBatchCache = new Map<string, { data: BatchResult; timestamp: number }>();

const BatchResultsFast = () => {
  const { batchId } = useParams();
  const navigate = useNavigate();
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Memoize the batch result to prevent unnecessary re-renders
  const memoizedBatchResult = useMemo(() => batchResult, [batchResult]);

  // ULTRA-FAST loading with progressive enhancement
  const loadBatchUltraFast = useCallback(async () => {
    if (!batchId) return;

    // Check global cache first (instant load)
    const cached = globalBatchCache.get(batchId);
    const now = Date.now();
    
    if (cached && (now - cached.timestamp) < 600000) { // 10 minutes
      console.log('⚡⚡ INSTANT cache hit!');
      setBatchResult(cached.data);
      setLoading(false);
      return;
    }

    const startTime = performance.now();
    console.log('🚀 ULTRA-FAST batch loading starting...');

    // Cancel any previous requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      setLoading(true);
      
      // Load FULL enhanced results directly - no intermediate steps
      const fullResponse = await fetch(
        `/api/v3/batches/${batchId}/enhanced-results?page=1&page_size=500&include_raw_modal=true`,
        {
          headers: {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, br',
            'Cache-Control': 'max-age=600'
          },
          signal: abortControllerRef.current.signal
        }
      );

      if (!fullResponse.ok) {
        throw new Error(`API failed: ${fullResponse.status}`);
      }

      const fullData = await fullResponse.json();
      const loadTime = performance.now() - startTime;
      console.log(`⚡ Full enhanced results loaded in ${loadTime.toFixed(0)}ms`);

      // Process complete results with all data
      const fullResults = (fullData.individual_results || []).map((result: any, index: number) => ({
        id: result.job_id || `${batchId}_${index}`,
        job_id: result.job_id,
        ligand_name: result.ligand_name || result.input_data?.ligand_name || `${index + 1}`,
        ligand_smiles: result.ligand_smiles || result.input_data?.ligand_smiles || '',
        status: result.status || 'completed',
        affinity: result.affinity || result.raw_modal_result?.affinity || 0,
        confidence: result.confidence || result.raw_modal_result?.confidence || 0,
        input_data: {
          ligand_name: result.ligand_name || `${index + 1}`,
          ligand_smiles: result.ligand_smiles || '',
          batch_index: index
        },
        results: {
          affinity: result.affinity || result.raw_modal_result?.affinity || 0,
          confidence: result.confidence || result.raw_modal_result?.confidence || 0,
          binding_score: result.affinity || result.raw_modal_result?.affinity || 0
        },
        raw_modal_result: result.raw_modal_result || {},
        affinity_ensemble: result.affinity_ensemble || {},
        confidence_metrics: result.confidence_metrics || {}
      }));

      const completeBatchResult: BatchResult = {
        job_id: batchId,
        batch_id: batchId,
        task_type: 'batch_protein_ligand_screening',
        status: fullData.batch_status || 'completed',
        batch_summary: {
          total_ligands: fullData.total_ligands_screened || fullResults.length,
          completed_jobs: fullData.successful_predictions || fullResults.length,
          failed_jobs: fullData.failed_predictions || 0,
          execution_time: 0
        },
        progress: {
          total_jobs: fullData.total_ligands_screened || fullResults.length,
          completed_jobs: fullData.successful_predictions || fullResults.length,
          failed_jobs: fullData.failed_predictions || 0,
          pending_jobs: 0
        },
        individual_results: fullResults,
        individual_jobs: fullResults,
        message: `Loaded ${fullResults.length} results`
      };

      // Set the complete result directly
      setBatchResult(completeBatchResult);
      setLoading(false);
      
      // Cache the complete result
      globalBatchCache.set(batchId, { data: completeBatchResult, timestamp: now });
      
      console.log(`✅ All ${fullResults.length} enhanced results loaded in ${loadTime.toFixed(0)}ms`);

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('Request cancelled');
        return;
      }
      
      console.error('Failed to load batch results:', err);
      setError(err instanceof Error ? err.message : 'Failed to load batch results');
      toast.error('Failed to load batch results');
      setLoading(false);
    }
  }, [batchId]);

  useEffect(() => {
    loadBatchUltraFast();
    
    // Cleanup on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadBatchUltraFast]);

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

        {/* Show loading skeleton for instant feedback */}
        {loading && !memoizedBatchResult && (
          <div className="animate-pulse">
            <div className="bg-gray-800 rounded-lg p-6 mb-4">
              <div className="flex items-center justify-between mb-4">
                <div className="h-6 bg-gray-700 rounded w-32"></div>
                <Activity className="h-5 w-5 text-blue-400 animate-spin" />
              </div>
              <div className="grid grid-cols-4 gap-4">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="bg-gray-700 rounded h-20"></div>
                ))}
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-6">
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="h-12 bg-gray-700 rounded"></div>
                ))}
              </div>
            </div>
          </div>
        )}
        
        {/* Use the functional BatchProteinLigandOutput component with memoized result */}
        <BatchProteinLigandOutput
          result={memoizedBatchResult}
          isLoading={loading && !!memoizedBatchResult}
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

export default BatchResultsFast;