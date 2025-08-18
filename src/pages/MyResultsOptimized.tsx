import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { Navigation } from '@/components/Navigation';
import { UserInfoSection } from '@/components/UserInfoSection';
import { SearchControls } from '@/components/SearchControls';
import { JobsFilterControls } from '@/components/JobsFilterControls';
import { PaginationControls } from '@/components/PaginationControls';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Eye, 
  Download, 
  Trash2, 
  Calendar,
  Activity,
  Settings,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  Loader2,
  RefreshCw
} from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

interface SavedJob {
  id: string;
  job_id: string;
  task_type: string;
  job_name: string;
  status: string;
  created_at: string;
  saved_at: string;
  inputs: any;
  results: any;
  user_id: string;
  file_count?: number;
  file_types?: string[];
  has_structure?: boolean;
  bucket_path?: string;
  auto_indexed?: boolean;
}

interface JobRow {
  id: string;
  name: string;
  type: string;
  status: 'Complete' | 'Failed' | 'In Progress' | 'Running';
  submitted: string;
  original?: SavedJob;
}

// Optimized cache with compression for large datasets
const jobCache = new Map<string, { data: any; timestamp: number; compressed?: boolean }>();
const CACHE_TTL = 2 * 60 * 1000; // 2 minutes

const MyResultsOptimized = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOrganization, setSelectedOrganization] = useState('none');
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(25);
  const [jobRows, setJobRows] = useState<JobRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalJobs, setTotalJobs] = useState(0);
  const [loadingProgress, setLoadingProgress] = useState(0);

  // Statistics for dashboard cards
  const jobStats = useMemo(() => {
    const completed = jobRows.filter(job => job.status === 'Complete').length;
    const failed = jobRows.filter(job => job.status === 'Failed').length;
    const running = jobRows.filter(job => job.status === 'Running').length;
    const inProgress = jobRows.filter(job => job.status === 'In Progress').length;
    
    return { completed, failed, running: running + inProgress, total: jobRows.length };
  }, [jobRows]);

  // Optimized job fetching with progressive loading
  const fetchJobs = useCallback(async (page: number = 1, refresh: boolean = false) => {
    const cacheKey = `jobs_page_${page}_${itemsPerPage}`;
    const now = Date.now();
    
    // Check cache first (unless refresh requested)
    if (!refresh) {
      const cached = jobCache.get(cacheKey);
      if (cached && (now - cached.timestamp) < CACHE_TTL) {
        console.log('✅ Using cached job data for page', page);
        return cached.data;
      }
    }

    try {
      const timerName = `Jobs API Page ${page} ${Date.now()}`;
      console.time(timerName);
      
      // Use ultra-fast endpoint first (it has full job data)
      let response = await fetch(
        `/api/v2/results/ultra-fast?user_id=current_user&limit=${itemsPerPage}&page=${page}`,
        {
          headers: {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, br',
            'Cache-Control': refresh ? 'no-cache' : 'max-age=120'
          }
        }
      );
      
      let apiUsed = 'ultra-fast';

      if (!response.ok) {
        console.warn('⚠️ Ultra-fast API failed, trying legacy endpoint...');
        response = await fetch(
          `/api/v2/my-results?user_id=current_user&page=${page}&limit=${itemsPerPage}`
        );
        apiUsed = 'legacy';
      }

      if (!response.ok) {
        console.warn('⚠️ APIs failed, trying optimized endpoint...');
        response = await fetch(
          `/api/v2/optimized/jobs?user_id=current_user&page=${page}&page_size=${itemsPerPage}`,
          {
            headers: {
              'Accept': 'application/json',
              'Accept-Encoding': 'gzip, br'
            }
          }
        );
        apiUsed = 'optimized';
      }
      
      if (!response.ok) {
        throw new Error(`API failed: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.timeEnd(timerName);
      
      // Handle different API response formats
      let jobs = [];
      let total = 0;
      
      if (apiUsed === 'optimized') {
        jobs = data.jobs || [];
        total = data.total || 0;
      } else {
        // Ultra-fast and legacy APIs use 'results' field
        jobs = data.results || data.jobs || data.batches || [];
        total = data.total || data.totalCount || jobs.length;
      }
      
      const responseTime = data.performance?.response_time_seconds || 'N/A';

      console.log(`📊 Page ${page}: Loaded ${jobs.length} jobs (${total} total) from ${apiUsed} in ${responseTime}s`);
      
      // Cache the result
      jobCache.set(cacheKey, { data: { jobs, total, apiUsed }, timestamp: now });
      
      return { jobs, total, apiUsed };
      
    } catch (err) {
      console.error(`❌ Failed to fetch jobs page ${page}:`, err);
      throw err;
    }
  }, [itemsPerPage]);

  // Progressive job loading
  const loadJobsProgressively = useCallback(async (refresh: boolean = false) => {
    try {
      setError(null);
      if (refresh) {
        setRefreshing(true);
        // Clear cache on refresh
        jobCache.clear();
      } else {
        setInitialLoading(true);
      }
      
      setLoadingProgress(0);

      // Load first page immediately for fast initial display
      const firstPageData = await fetchJobs(1, refresh);
      const firstPageJobs = firstPageData.jobs || [];
      
      // Process and display first page jobs immediately
      const mappedJobs = firstPageJobs.map((savedJob: any) => {
        // Handle both optimized API format and legacy format
        const inputs = savedJob.inputs || savedJob.input_data || {};
        const proteinName = inputs.protein_name || inputs.target_name || '';
        const jobBaseName = savedJob.job_name || savedJob.name || `${savedJob.task_type || savedJob.type || 'Unknown'} Prediction`;
        const enhancedName = proteinName ? `${jobBaseName} (${proteinName})` : jobBaseName;
        
        return {
          id: savedJob.id,
          name: enhancedName,
          type: getJobTypeDisplay(savedJob.task_type || savedJob.type),
          status: mapJobStatus(savedJob.status),
          submitted: savedJob.created_at ? new Date(savedJob.created_at).toLocaleString() : 'Unknown',
          original: savedJob // Keep the complete original job data without modification
        };
      });

      setJobRows(mappedJobs);
      setTotalJobs(firstPageData.total || 0);
      setLoadingProgress(Math.min(100, (firstPageJobs.length / (firstPageData.total || firstPageJobs.length)) * 100));
      
      // Stop loading spinner after first page
      setInitialLoading(false);
      setLoading(false);

      // Load remaining pages in background if there are more
      const totalPages = Math.ceil((firstPageData.total || 0) / itemsPerPage);
      if (totalPages > 1) {
        const remainingPagePromises = [];
        
        for (let page = 2; page <= Math.min(totalPages, 5); page++) { // Load up to 5 pages
          remainingPagePromises.push(fetchJobs(page, refresh));
        }

        // Process pages as they complete
        const allJobsFromFirstPage = [...mappedJobs];
        let completedPages = 1;

        for (const pagePromise of remainingPagePromises) {
          try {
            const pageData = await pagePromise;
            const pageJobs = pageData.jobs || [];
            
            const mappedPageJobs = pageJobs.map((savedJob: any) => {
              // Handle both optimized API format and legacy format
              const inputs = savedJob.inputs || savedJob.input_data || {};
              const proteinName = inputs.protein_name || inputs.target_name || '';
              const jobBaseName = savedJob.job_name || savedJob.name || `${savedJob.task_type || savedJob.type || 'Unknown'} Prediction`;
              const enhancedName = proteinName ? `${jobBaseName} (${proteinName})` : jobBaseName;
              
              return {
                id: savedJob.id,
                name: enhancedName,
                type: getJobTypeDisplay(savedJob.task_type || savedJob.type),
                status: mapJobStatus(savedJob.status),
                submitted: savedJob.created_at ? new Date(savedJob.created_at).toLocaleString() : 'Unknown',
                original: savedJob // Keep the complete original job data without modification
              };
            });

            allJobsFromFirstPage.push(...mappedPageJobs);
            completedPages++;
            
            // Update progress and data
            setLoadingProgress(Math.min(100, (completedPages / totalPages) * 100));
            setJobRows([...allJobsFromFirstPage]);
            
          } catch (err) {
            console.error('Failed to load additional page:', err);
          }
        }
      }

      setLoadingProgress(100);
      
    } catch (err) {
      console.error('Failed to load jobs:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      
      if (errorMessage.includes('404')) {
        setError('Results API endpoint not found. Please check your backend configuration.');
      } else if (errorMessage.includes('500')) {
        setError('Server error while loading results. Please try again later.');
      } else {
        setError('Failed to load results. Please check your connection and try again.');
      }
      
      setJobRows([]);
      setInitialLoading(false);
      setLoading(false);
    } finally {
      setRefreshing(false);
    }
  }, [fetchJobs, itemsPerPage]);

  // Load jobs on mount
  useEffect(() => {
    loadJobsProgressively();
  }, [loadJobsProgressively]);

  // Refresh jobs when items per page changes
  useEffect(() => {
    if (!initialLoading) {
      setCurrentPage(1);
      loadJobsProgressively();
    }
  }, [itemsPerPage]);

  // Map job status to display format
  const mapJobStatus = (status: string): 'Complete' | 'Failed' | 'In Progress' | 'Running' => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'Complete';
      case 'failed':
      case 'error':
        return 'Failed';
      case 'running':
      case 'in_progress':
        return 'Running';
      default:
        return 'In Progress';
    }
  };

  // Map job type to display format
  const getJobTypeDisplay = (taskType: string): string => {
    switch (taskType) {
      case 'protein_ligand_binding':
        return 'Boltz-2 Protein-Ligand';
      case 'batch_protein_ligand_screening':
        return 'Batch Protein-Ligand Screening';
      case 'nanobody_design':
        return 'RFAntibody Nanobody Design';
      case 'structure_prediction':
        return 'Chai-1 Structure Prediction';
      default:
        return (taskType || 'Unknown').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
  };

  // Handle job view with optimized navigation
  const handleViewJob = useCallback(async (jobId: string) => {
    const job = jobRows.find(j => j.id === jobId);
    if (!job?.original) {
      console.error('No job data found for ID:', jobId);
      return;
    }

    const taskType = job.original.task_type;
    
    // Navigate based on task type
    const targetPage = taskType?.includes('batch') ? '/batches' : '/boltz2';
    
    // Check if results are already available
    if (job.original.results && Object.keys(job.original.results).length > 0) {
      navigate(targetPage, { 
        state: { 
          savedJob: job.original,
          viewMode: true,
          predictionResult: job.original.results,
          taskType: taskType
        } 
      });
      return;
    }

    // For batch jobs, navigate to batch results page
    if (taskType?.includes('batch')) {
      navigate(`/batch-results/${job.original.job_id}`);
      return;
    }

    // For individual jobs, try to fetch fresh data
    try {
      const response = await fetch(`/api/v2/jobs/${job.original.job_id}`);
      if (response.ok) {
        const fullJobData = await response.json();
        navigate(targetPage, { 
          state: { 
            savedJob: job.original,
            viewMode: true,
            predictionResult: fullJobData.result_data || fullJobData.results || job.original.results,
            taskType: taskType
          } 
        });
      } else {
        // Use saved results as fallback
        navigate(targetPage, { 
          state: { 
            savedJob: job.original,
            viewMode: true,
            predictionResult: job.original.results || {},
            taskType: taskType
          } 
        });
      }
    } catch (fetchError) {
      console.warn(`Failed to fetch job ${job.original.job_id}:`, fetchError);
      navigate(targetPage, { 
        state: { 
          savedJob: job.original,
          viewMode: true,
          predictionResult: job.original.results || {},
          taskType: taskType
        } 
      });
    }
  }, [jobRows, navigate]);

  // Optimized delete handlers
  const handleDeleteJob = useCallback((jobId: string) => {
    // Implementation here
  }, []);

  const handleRefresh = useCallback(() => {
    loadJobsProgressively(true);
  }, [loadJobsProgressively]);

  // Filter jobs based on search query (client-side for better performance)
  const filteredJobs = useMemo(() => {
    if (!searchQuery) return jobRows;
    const searchLower = searchQuery.toLowerCase();
    return jobRows.filter(job => 
      job.name.toLowerCase().includes(searchLower) ||
      job.type.toLowerCase().includes(searchLower) ||
      job.status.toLowerCase().includes(searchLower)
    );
  }, [jobRows, searchQuery]);

  // Optimized pagination
  const totalFilteredJobs = filteredJobs.length;
  const totalPages = Math.ceil(totalFilteredJobs / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedJobs = filteredJobs.slice(startIndex, endIndex);

  return (
    <div className="min-h-screen bg-gray-900">
      <Header />
      <Navigation />
      
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* User Info Section */}
        <div className="mb-8">
          <UserInfoSection
            userName="Bryan Duoto"
            userEmail="bryanduoto@gmail.com"
            jobsLeft={10}
            selectedOrganization={selectedOrganization}
            onOrganizationChange={setSelectedOrganization}
          />
        </div>

        {/* Search and Controls */}
        <div className="mb-6 space-y-4">
          <div className="flex justify-between items-center">
            <SearchControls
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              onReset={() => {
                setSearchQuery('');
                setCurrentPage(1);
              }}
            />
            
            <Button
              onClick={handleRefresh}
              disabled={refreshing}
              variant="outline"
              size="sm"
              className="border-gray-600 text-gray-300 hover:bg-gray-700"
            >
              {refreshing ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Refresh
            </Button>
          </div>

          {/* Progress bar for loading */}
          {(initialLoading || refreshing) && loadingProgress < 100 && (
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="flex justify-between text-sm text-gray-400 mb-2">
                <span>{refreshing ? 'Refreshing results...' : 'Loading results...'}</span>
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

          <JobsFilterControls 
            selectedJobsCount={selectedJobs.size}
            canDownload={false}
            canDelete={selectedJobs.size > 0}
            onBulkDelete={() => {}}
            onDownload={() => {}}
          />
        </div>

        {/* Enhanced Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Total Jobs</p>
                  <p className="text-2xl font-bold text-white">{jobStats.total}</p>
                  <p className="text-xs text-gray-500 mt-1">All time</p>
                </div>
                <FileText className="h-8 w-8 text-blue-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Completed</p>
                  <p className="text-2xl font-bold text-green-400">{jobStats.completed}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {jobStats.total > 0 ? Math.round((jobStats.completed / jobStats.total) * 100) : 0}% success rate
                  </p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Running</p>
                  <p className="text-2xl font-bold text-yellow-400">{jobStats.running}</p>
                  <p className="text-xs text-gray-500 mt-1">In progress</p>
                </div>
                <Clock className="h-8 w-8 text-yellow-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Failed</p>
                  <p className="text-2xl font-bold text-red-400">{jobStats.failed}</p>
                  <p className="text-xs text-gray-500 mt-1">Need attention</p>
                </div>
                <AlertCircle className="h-8 w-8 text-red-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Error Display */}
        {error && (
          <Alert className="mb-6 bg-red-900/20 border-red-800">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-red-400">{error}</AlertDescription>
          </Alert>
        )}

        {/* Results Table */}
        {paginatedJobs.length > 0 && (
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white">My Results</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left py-3 px-4 text-gray-400">Name</th>
                      <th className="text-left py-3 px-4 text-gray-400">Type</th>
                      <th className="text-left py-3 px-4 text-gray-400">Status</th>
                      <th className="text-left py-3 px-4 text-gray-400">Submitted</th>
                      <th className="text-left py-3 px-4 text-gray-400">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedJobs.map((job) => (
                      <tr key={job.id} className="border-b border-gray-800 hover:bg-gray-700/50">
                        <td className="py-3 px-4 text-white">{job.name}</td>
                        <td className="py-3 px-4 text-gray-300">{job.type}</td>
                        <td className="py-3 px-4">
                          <Badge 
                            variant={job.status === 'Complete' ? 'default' : 
                                   job.status === 'Failed' ? 'destructive' : 'secondary'}
                          >
                            {job.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-gray-300 text-sm">{job.submitted}</td>
                        <td className="py-3 px-4">
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              onClick={() => handleViewJob(job.id)}
                              className="bg-blue-600 hover:bg-blue-700"
                            >
                              <Eye className="h-4 w-4 mr-1" />
                              View
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Empty State */}
        {!initialLoading && !loading && jobRows.length === 0 && !error && (
          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-8 text-center">
              <FileText className="h-16 w-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No saved results yet</h3>
              <p className="text-gray-400 mb-6">
                Completed prediction jobs are automatically saved here. Run a prediction to see your results.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button 
                  onClick={() => navigate('/boltz2')}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  Run Boltz-2 Prediction
                </Button>
                <Button 
                  onClick={() => navigate('/boltz2')}
                  variant="outline"
                  className="border-gray-600 text-gray-300 hover:bg-gray-700"
                >
                  Batch Screening
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Pagination */}
        {!initialLoading && !loading && jobRows.length > 0 && (
          <PaginationControls
            currentPage={currentPage}
            totalItems={totalFilteredJobs}
            itemsPerPage={itemsPerPage}
            onPageChange={setCurrentPage}
            onItemsPerPageChange={(newItemsPerPage) => {
              setItemsPerPage(newItemsPerPage);
              setCurrentPage(1);
            }}
          />
        )}

        <div className="mt-8 text-center">
          <p className="text-gray-400">
            If you have questions about your saved jobs, please contact info@omtx.ai.
          </p>
        </div>
      </main>
    </div>
  );
};

export default MyResultsOptimized;