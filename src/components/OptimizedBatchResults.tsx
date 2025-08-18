import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Download,
  BarChart3,
  Activity,
  Target,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock
} from 'lucide-react';

interface BatchSummary {
  batch_id: string;
  total_jobs: number;
  completed_jobs: number;
  status: string;
  created_at: string;
  performance: {
    response_time_seconds: number;
    cache_hit: boolean;
  };
}

interface BatchResult {
  job_id: string;
  ligand_name: string;
  ligand_smiles: string;
  status: string;
  affinity?: number;
  confidence?: number;
  raw_modal_result?: any;
}

interface OptimizedBatchResultsProps {
  batchId: string;
}

// Smart cache with TTL
const cache = new Map<string, { data: any; timestamp: number; ttl: number }>();

const getCachedData = (key: string) => {
  const cached = cache.get(key);
  if (cached && Date.now() - cached.timestamp < cached.ttl) {
    return cached.data;
  }
  cache.delete(key);
  return null;
};

const setCachedData = (key: string, data: any, ttl: number = 5 * 60 * 1000) => {
  cache.set(key, { data, timestamp: Date.now(), ttl });
};

export const OptimizedBatchResults: React.FC<OptimizedBatchResultsProps> = ({ batchId }) => {
  const [summary, setSummary] = useState<BatchSummary | null>(null);
  const [results, setResults] = useState<BatchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [hasFullData, setHasFullData] = useState(false);

  // Load batch summary first for immediate display
  const loadBatchSummary = useCallback(async () => {
    const cacheKey = `batch_summary_${batchId}`;
    const cached = getCachedData(cacheKey);
    
    if (cached) {
      console.log('✅ Using cached batch summary');
      setSummary(cached);
      return cached;
    }

    try {
      const timerName = `Batch Summary API ${Date.now()}`;
      console.time(timerName);
      
      // Try optimized endpoint first, fallback to enhanced results
      let response = await fetch(`/api/v2/optimized/batch/${batchId}/summary`, {
        headers: {
          'Accept': 'application/json',
          'Accept-Encoding': 'gzip, br'
        }
      });

      if (!response.ok) {
        console.warn('⚠️ Optimized batch summary failed, trying enhanced results...');
        response = await fetch(`/api/v2/results/batch/${batchId}/results?include_results=false`, {
          headers: {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, br'
          }
        });
      }

      if (!response.ok) {
        throw new Error(`Failed to load batch summary: ${response.status}`);
      }

      const summaryData = await response.json();
      console.timeEnd(timerName);
      
      console.log(`⚡ Batch summary loaded in ${summaryData.performance.response_time_seconds}s`);
      
      setSummary(summaryData);
      setCachedData(cacheKey, summaryData, 2 * 60 * 1000); // 2 minute cache
      
      return summaryData;
    } catch (err) {
      console.error('Failed to load batch summary:', err);
      throw err;
    }
  }, [batchId]);

  // Stream batch results with progressive loading
  const streamBatchResults = useCallback(async (page: number = 1, includeRawModal: boolean = false) => {
    const cacheKey = `batch_results_${batchId}_page_${page}_modal_${includeRawModal}`;
    const cached = getCachedData(cacheKey);
    
    if (cached) {
      console.log(`✅ Using cached results for page ${page}`);
      return cached;
    }

    try {
      const timerName = `Batch Results Page ${page} ${Date.now()}`;
      console.time(timerName);
      
      // Try optimized streaming endpoint first, fallback to enhanced results
      let response = await fetch(
        `/api/v2/optimized/batch/${batchId}/results/stream?page=${page}&page_size=500&include_raw_modal=${includeRawModal}`,
        {
          headers: {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, br'
          }
        }
      );

      if (!response.ok) {
        console.warn(`⚠️ Optimized streaming failed for page ${page}, trying enhanced results...`);
        response = await fetch(
          `/api/v2/results/batch/${batchId}/results?include_results=true&limit=500&offset=${(page-1)*500}`,
          {
            headers: {
              'Accept': 'application/json',
              'Accept-Encoding': 'gzip, br'
            }
          }
        );
      }

      if (!response.ok) {
        throw new Error(`Failed to load batch results page ${page}: ${response.status}`);
      }

      const data = await response.json();
      console.timeEnd(timerName);
      
      console.log(`🌊 Page ${page} loaded: ${data.results.length} results in ${data.performance.response_time_seconds}s`);
      
      setCachedData(cacheKey, data, 5 * 60 * 1000); // 5 minute cache
      
      return data;
    } catch (err) {
      console.error(`Failed to load results page ${page}:`, err);
      throw err;
    }
  }, [batchId]);

  // Progressive loading strategy
  const loadBatchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setLoadingProgress(0);

      // Step 1: Load summary immediately (sub-second)
      const summaryData = await loadBatchSummary();
      setLoadingProgress(20);
      setLoading(false); // Show summary immediately

      // Step 2: Load first page of results for immediate display
      setResultsLoading(true);
      const firstPageData = await streamBatchResults(1, false); // Without raw modal for speed
      
      setResults(firstPageData.results || []);
      setTotalPages(firstPageData.pagination?.total_pages || 1);
      setLoadingProgress(60);

      // Step 3: Load remaining pages in background if needed
      if (firstPageData.pagination?.total_pages > 1) {
        const totalPages = Math.min(firstPageData.pagination.total_pages, 10); // Limit to 10 pages for performance
        const pagePromises = [];

        for (let page = 2; page <= totalPages; page++) {
          pagePromises.push(streamBatchResults(page, false));
        }

        // Process pages as they complete
        const allResults = [...firstPageData.results];
        let completedPages = 1;

        for (const pagePromise of pagePromises) {
          try {
            const pageData = await pagePromise;
            allResults.push(...(pageData.results || []));
            completedPages++;
            
            setLoadingProgress(60 + (completedPages / totalPages) * 35);
            setResults([...allResults]);
          } catch (err) {
            console.error('Failed to load additional page:', err);
          }
        }

        // Step 4: Load full data with raw modal results in background
        setTimeout(async () => {
          try {
            const fullDataPromises = [];
            for (let page = 1; page <= totalPages; page++) {
              fullDataPromises.push(streamBatchResults(page, true)); // With raw modal data
            }

            const fullResults = [];
            for (const pagePromise of fullDataPromises) {
              try {
                const pageData = await pagePromise;
                fullResults.push(...(pageData.results || []));
              } catch (err) {
                console.error('Failed to load full data page:', err);
              }
            }

            if (fullResults.length > 0) {
              setResults(fullResults);
              setHasFullData(true);
              console.log('✅ Full data with raw modal results loaded');
            }
          } catch (err) {
            console.error('Failed to load full data:', err);
          }
        }, 1000); // Load full data 1 second after initial display
      }

      setLoadingProgress(100);
      setResultsLoading(false);

    } catch (err) {
      console.error('Failed to load batch data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load batch data');
      setLoading(false);
      setResultsLoading(false);
    }
  }, [batchId, loadBatchSummary, streamBatchResults]);

  // Load data on mount
  useEffect(() => {
    loadBatchData();
  }, [loadBatchData]);

  // Statistics for display
  const stats = useMemo(() => {
    const completed = results.filter(r => r.status === 'completed').length;
    const failed = results.filter(r => r.status === 'failed').length;
    const running = results.filter(r => r.status === 'running').length;
    const successRate = results.length > 0 ? (completed / results.length * 100).toFixed(1) : '0';
    
    return { completed, failed, running, successRate, total: results.length };
  }, [results]);

  // Top performers for quick insights
  const topPerformers = useMemo(() => {
    return results
      .filter(r => r.status === 'completed' && r.affinity)
      .sort((a, b) => (b.affinity || 0) - (a.affinity || 0))
      .slice(0, 10);
  }, [results]);

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-4">
          <Loader2 className="h-12 w-12 text-blue-400 animate-spin mx-auto" />
          <p className="text-gray-400">Loading batch summary...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert className="border-red-700 bg-red-900/20">
        <AlertCircle className="h-4 w-4 text-red-400" />
        <AlertDescription className="text-red-400">{error}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Card - Loads First */}
      {summary && (
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Batch Summary
              </div>
              <div className="flex items-center gap-2 text-sm">
                {summary.performance.cache_hit && (
                  <span className="text-green-400">⚡ Cached</span>
                )}
                <span className="text-gray-400">
                  {(summary.performance.response_time_seconds * 1000).toFixed(0)}ms
                </span>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-900/50 rounded-lg p-3">
                <div className="text-2xl font-bold text-white">{summary.total_jobs}</div>
                <div className="text-xs text-gray-400">Total Jobs</div>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-3">
                <div className="text-2xl font-bold text-green-400">{summary.completed_jobs}</div>
                <div className="text-xs text-gray-400">Completed</div>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-3">
                <div className="text-2xl font-bold text-blue-400">{stats.successRate}%</div>
                <div className="text-xs text-gray-400">Success Rate</div>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-3">
                <div className="text-2xl font-bold text-gray-300">{summary.status}</div>
                <div className="text-xs text-gray-400">Status</div>
              </div>
            </div>
            
            {summary.total_jobs > 0 && (
              <div className="mt-4">
                <Progress value={(summary.completed_jobs / summary.total_jobs) * 100} className="h-2" />
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Progress Bar for Results Loading */}
      {(resultsLoading || loadingProgress < 100) && (
        <Card className="bg-gray-800/50 border-gray-700">
          <CardContent className="p-4">
            <div className="flex justify-between text-sm text-gray-400 mb-2">
              <span>{resultsLoading ? 'Loading results...' : 'Processing complete'}</span>
              <span>{Math.round(loadingProgress)}%</span>
            </div>
            <Progress value={loadingProgress} className="h-2" />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>{results.length} results loaded</span>
              {hasFullData && <span className="text-green-400">✓ Full data available</span>}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4 bg-gray-800">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="top">Top Hits</TabsTrigger>
          <TabsTrigger value="table">Table View</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-400">Completion Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-green-400">Completed</span>
                    <span className="text-white">{stats.completed}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-yellow-400">Running</span>
                    <span className="text-white">{stats.running}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-red-400">Failed</span>
                    <span className="text-white">{stats.failed}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-400">Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Results Loaded</span>
                    <span className="text-white">{results.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Data Quality</span>
                    <span className={hasFullData ? "text-green-400" : "text-yellow-400"}>
                      {hasFullData ? "Full" : "Basic"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Load Time</span>
                    <span className="text-white">
                      {summary?.performance.response_time_seconds 
                        ? `${(summary.performance.response_time_seconds * 1000).toFixed(0)}ms`
                        : 'N/A'
                      }
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-400">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Button size="sm" className="w-full bg-green-600 hover:bg-green-700">
                    <Download className="h-4 w-4 mr-2" />
                    Download CSV
                  </Button>
                  <Button size="sm" variant="outline" className="w-full">
                    <Download className="h-4 w-4 mr-2" />
                    Download Structures
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Top Hits Tab */}
        <TabsContent value="top" className="space-y-4">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Target className="h-5 w-5 text-green-400" />
                Top 10 Performers
              </CardTitle>
            </CardHeader>
            <CardContent>
              {topPerformers.length > 0 ? (
                <div className="space-y-3">
                  {topPerformers.map((result, index) => (
                    <div key={result.job_id} className="bg-gray-900/50 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="text-2xl font-bold text-yellow-400">
                            #{index + 1}
                          </div>
                          <div>
                            <h4 className="text-white font-semibold">{result.ligand_name}</h4>
                            <p className="text-xs text-gray-400 font-mono">{result.ligand_smiles}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-green-400">
                            {result.affinity?.toFixed(3)}
                          </div>
                          <div className="text-xs text-gray-400">
                            {result.confidence ? `${(result.confidence * 100).toFixed(1)}% conf` : ''}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <Alert className="border-yellow-700 bg-yellow-900/20">
                  <AlertCircle className="h-4 w-4 text-yellow-400" />
                  <AlertDescription className="text-yellow-400">
                    {results.length === 0 ? 'No results loaded yet' : 'No completed results to show top performers'}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Table View Tab */}
        <TabsContent value="table" className="space-y-4">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white">Results Table</CardTitle>
            </CardHeader>
            <CardContent>
              {results.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left py-2 px-4 text-gray-400">Ligand</th>
                        <th className="text-left py-2 px-4 text-gray-400">Status</th>
                        <th className="text-left py-2 px-4 text-gray-400">Affinity</th>
                        <th className="text-left py-2 px-4 text-gray-400">Confidence</th>
                        <th className="text-left py-2 px-4 text-gray-400">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.slice(0, 50).map((result) => (
                        <tr key={result.job_id} className="border-b border-gray-800 hover:bg-gray-700/50">
                          <td className="py-2 px-4 text-white">{result.ligand_name}</td>
                          <td className="py-2 px-4">
                            <span className={`px-2 py-1 rounded text-xs ${
                              result.status === 'completed' ? 'bg-green-900 text-green-400' :
                              result.status === 'failed' ? 'bg-red-900 text-red-400' :
                              'bg-yellow-900 text-yellow-400'
                            }`}>
                              {result.status}
                            </span>
                          </td>
                          <td className="py-2 px-4 text-white">
                            {result.affinity ? result.affinity.toFixed(3) : '-'}
                          </td>
                          <td className="py-2 px-4 text-white">
                            {result.confidence ? (result.confidence * 100).toFixed(1) + '%' : '-'}
                          </td>
                          <td className="py-2 px-4">
                            <Button size="sm" variant="outline">
                              View
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {results.length > 50 && (
                    <div className="mt-4 text-center text-gray-400">
                      Showing first 50 of {results.length} results
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-gray-400 py-8">
                  {resultsLoading ? 'Loading results...' : 'No results available'}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-4">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Activity className="h-5 w-5 text-purple-400" />
                Batch Analytics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center text-gray-400 py-8">
                Analytics dashboard coming soon...
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};