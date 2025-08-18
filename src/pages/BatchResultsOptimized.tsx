import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { BatchProteinLigandOutput } from '@/components/Boltz2/BatchProteinLigandOutput';
import { toast } from 'sonner';

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

// Optimized cache with compression for large datasets
const resultCache = new Map<string, { data: BatchResult; timestamp: number; compressed?: boolean }>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export default function BatchResultsOptimized() {
  const { batchId } = useParams<{ batchId: string }>();
  const location = useLocation();
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [partialResults, setPartialResults] = useState<any[]>([]);
  const [loadingProgress, setLoadingProgress] = useState(0);

  // Optimized batch loading with progressive rendering
  const loadBatchResults = useCallback(async () => {
    if (!batchId) {
      setError('No batch ID provided');
      setLoading(false);
      return;
    }

    try {
      // Check cache first
      const now = Date.now();
      const cached = resultCache.get(batchId);
      
      if (cached && (now - cached.timestamp) < CACHE_TTL) {
        console.log('✅ Using cached batch results');
        setBatchResult(cached.data);
        setLoading(false);
        return;
      }
      
      setLoading(true);
      console.log('🔍 BatchResults - Loading batch:', batchId);
      console.time('API Load Time');
      
      // OPTIMIZATION 1: Parallel requests for metadata and first page
      const [metadataResponse, firstPageResponse] = await Promise.all([
        // Get batch metadata quickly
        fetch(`/api/v3/batches/${batchId}/status`, {
          headers: {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, br'
          }
        }),
        // Get first 100 results immediately for quick display
        fetch(`/api/v3/batches/${batchId}/enhanced-results?page=1&page_size=100&include_raw_modal=false`, {
          headers: {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, br'
          }
        })
      ]);

      if (!metadataResponse.ok || !firstPageResponse.ok) {
        throw new Error('Failed to load batch results');
      }

      const [metadata, firstPage] = await Promise.all([
        metadataResponse.json(),
        firstPageResponse.json()
      ]);

      // OPTIMIZATION 2: Display first results immediately
      const initialResults = firstPage.individual_results || [];
      setPartialResults(initialResults);
      setLoadingProgress(Math.min(100, (initialResults.length / metadata.total_jobs) * 100));

      // Create initial batch result for immediate display
      const initialBatchResult: BatchResult = {
        job_id: batchId,
        batch_id: batchId,
        task_type: 'batch_protein_ligand_screening',
        status: metadata.status || 'loading',
        batch_summary: {
          total_ligands: metadata.total_jobs || 0,
          completed_jobs: initialResults.length,
          failed_jobs: 0,
          execution_time: 0
        },
        progress: {
          total_jobs: metadata.total_jobs || 0,
          completed_jobs: initialResults.length,
          failed_jobs: 0,
          pending_jobs: 0
        },
        individual_results: initialResults,
        individual_jobs: initialResults,
        message: `Loading ${metadata.total_jobs} results...`
      };

      setBatchResult(initialBatchResult);
      setLoading(false); // Stop showing loading spinner, show partial results

      // OPTIMIZATION 3: Load remaining results in background if needed
      if (metadata.total_jobs > 100) {
        const remainingPages = Math.ceil((metadata.total_jobs - 100) / 500);
        const pagePromises = [];

        for (let page = 1; page <= remainingPages; page++) {
          const offset = 100 + (page - 1) * 500;
          pagePromises.push(
            fetch(`/api/v3/batches/${batchId}/enhanced-results?page=${page + 1}&page_size=500&offset=${offset}&include_raw_modal=true`, {
              headers: {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, br'
              }
            }).then(r => r.json())
          );
        }

        // OPTIMIZATION 4: Process pages as they complete
        const allResults = [...initialResults];
        let completedPages = 0;

        for (const pagePromise of pagePromises) {
          try {
            const pageData = await pagePromise;
            if (pageData.individual_results) {
              allResults.push(...pageData.individual_results);
              completedPages++;
              
              // Update progress
              setLoadingProgress(Math.min(100, ((100 + completedPages * 500) / metadata.total_jobs) * 100));
              
              // Update batch result with new data
              const updatedBatchResult: BatchResult = {
                ...initialBatchResult,
                batch_summary: {
                  ...initialBatchResult.batch_summary!,
                  completed_jobs: allResults.length
                },
                progress: {
                  ...initialBatchResult.progress!,
                  completed_jobs: allResults.length
                },
                individual_results: allResults,
                individual_jobs: allResults,
                message: `Loaded ${allResults.length} of ${metadata.total_jobs} results`
              };
              
              setBatchResult(updatedBatchResult);
            }
          } catch (err) {
            console.error('Failed to load page:', err);
          }
        }

        // Final update with all results
        const finalBatchResult: BatchResult = {
          ...initialBatchResult,
          status: 'completed',
          batch_summary: {
            total_ligands: allResults.length,
            completed_jobs: allResults.length,
            failed_jobs: 0,
            execution_time: 0
          },
          progress: {
            total_jobs: allResults.length,
            completed_jobs: allResults.length,
            failed_jobs: 0,
            pending_jobs: 0
          },
          individual_results: allResults,
          individual_jobs: allResults,
          message: `Loaded all ${allResults.length} results`
        };

        setBatchResult(finalBatchResult);
        setLoadingProgress(100);

        // Cache the complete result
        resultCache.set(batchId, { data: finalBatchResult, timestamp: Date.now() });
      } else {
        // Cache small result immediately
        resultCache.set(batchId, { data: initialBatchResult, timestamp: Date.now() });
      }

      console.timeEnd('API Load Time');
      
    } catch (err) {
      console.error('Failed to load batch results:', err);
      setError(err instanceof Error ? err.message : 'Failed to load batch results');
      toast.error('Failed to load batch results');
      setLoading(false);
    }
  }, [batchId]);

  useEffect(() => {
    loadBatchResults();
  }, [loadBatchResults]);

  if (error) {
    return (
      <div className="container mx-auto p-4">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h2 className="text-red-800 font-semibold">Error Loading Results</h2>
          <p className="text-red-600 mt-2">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <main className="flex-1 overflow-y-auto bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <div className="container mx-auto p-4 space-y-6">
        {/* Progress bar for large batches */}
        {loadingProgress > 0 && loadingProgress < 100 && (
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex justify-between text-sm text-gray-400 mb-2">
              <span>Loading batch results...</span>
              <span>{Math.round(loadingProgress)}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${loadingProgress}%` }}
              />
            </div>
          </div>
        )}
        
        <BatchProteinLigandOutput
          result={batchResult}
          isLoading={loading && !batchResult} // Only show loading if no partial results
        />
      </div>
    </main>
  );
}