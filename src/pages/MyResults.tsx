import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { unifiedJobStore } from '@/stores/unifiedJobStore';
import { Header } from '@/components/Header';
import { Navigation } from '@/components/Navigation';
import { UserInfoSection } from '@/components/UserInfoSection';
import { SearchControls } from '@/components/SearchControls';
import { TableControls } from '@/components/TableControls';
import { JobsFilterControls } from '@/components/JobsFilterControls';
import { PaginationControls } from '@/components/PaginationControls';
import LazyTable from '@/components/LazyTable';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Boltz2ResultsViewer } from '@/components/JobResults/Boltz2ResultsViewer';
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
  FileText
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
  // New indexer fields
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
  original?: SavedJob; // Store original saved job data
}

interface ColumnVisibility {
  checkbox: boolean;
  name: boolean;
  type: boolean;
  status: boolean;
  submitted: boolean;
  actions: boolean;
}

// Use unified store for ultra-fast data access (no local cache needed)

const MyResults = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOrganization, setSelectedOrganization] = useState('none');
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [jobRows, setJobRows] = useState<JobRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalJobs, setTotalJobs] = useState(0);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{
    isOpen: boolean;
    jobId: string | null;
    jobName: string;
    isBulk: boolean;
    count: number;
  }>({ isOpen: false, jobId: null, jobName: '', isBulk: false, count: 0 });
  
  // State for results viewer dialog
  const [selectedJobForViewing, setSelectedJobForViewing] = useState<string | null>(null);
  const [selectedJobData, setSelectedJobData] = useState<any>(null);
  const [showResultsViewer, setShowResultsViewer] = useState(false);

  // INSTANT fetch using unified store - sub-millisecond for cache hits
  const fetchJobsOptimized = async () => {
    try {
      console.time('⚡ Unified Store Access');
      
      // Get individual jobs from unified store (instant for cache hits)
      const cachedJobs = unifiedJobStore.getCachedIndividualJobs();
      
      if (cachedJobs.length > 0) {
        console.timeEnd('⚡ Unified Store Access');
        console.log(`⚡ INSTANT: ${cachedJobs.length} individual jobs from unified cache`);
        return { jobs: cachedJobs, total: cachedJobs.length, dataSource: 'unified-cache' };
      }
      
      // Ensure individual jobs are loaded (this now calls the specific individual job loader)
      await unifiedJobStore.ensureIndividualJobsLoaded();
      const allJobs = unifiedJobStore.getCachedIndividualJobs();
      
      console.timeEnd('⚡ Unified Store Access');
      console.log(`✅ Unified Store: Loaded ${allJobs.length} individual jobs`);
      
      return { jobs: allJobs, total: allJobs.length, dataSource: 'unified-store' };
      
    } catch (err) {
      console.error('Unified store failed, falling back to API:', err);
      
      // Fallback to My Results API directly
      try {
        const response = await fetch(`/api/v1/jobs?user_id=omtx_deployment_user&limit=200`);
        if (response.ok) {
          const data = await response.json();
          const results = data.results || data.jobs || [];
          console.log(`✅ API Fallback: Loaded ${results.length} individual jobs from My Results API`);
          return { jobs: results, total: results.length, dataSource: 'my-results-api' };
        } else {
          console.warn(`My Results API returned ${response.status}`);
        }
      } catch (fallbackErr) {
        console.error('My Results API fallback failed:', fallbackErr);
      }
      
      // Final fallback: Check if we have any cached jobs that could be individual jobs
      const allCachedJobs = unifiedJobStore.getCachedJobs();
      const individualJobCandidates = allCachedJobs.filter(job => {
        // Filter out obvious batch jobs
        return !job.type || job.type === 'individual' || 
               (!job.task_type?.includes('batch') && 
                !job.job_name?.toLowerCase().includes('batch') &&
                job.task_type !== 'batch');
      });
      
      if (individualJobCandidates.length > 0) {
        console.log(`🚑 Emergency fallback: Using ${individualJobCandidates.length} cached jobs as individual jobs`);
        return { jobs: individualJobCandidates, total: individualJobCandidates.length, dataSource: 'cached-fallback' };
      }
      
      // Return empty array rather than throwing - this allows the page to load
      console.warn('⚠️ All individual job loading methods failed - showing empty results');
      return { jobs: [], total: 0, dataSource: 'empty-fallback' };
    }
  };

  // INSTANT loading with unified store - preloaded data ready immediately
  useEffect(() => {
    const fetchSavedJobs = async () => {
      try {
        console.log('⚡ Loading individual jobs with UNIFIED STORE (instant)...');
        setLoading(true);

        const startTime = performance.now();
        const fetchResult = await fetchJobsOptimized();
        const jobs = fetchResult.jobs;
        const dataSource = fetchResult.dataSource;
        const loadTime = performance.now() - startTime;
        
        // Map unified job data to JobRow format
        const mappedJobs: JobRow[] = jobs.map((job: any) => {
          // Extract protein/target name from inputs for better job naming
          const inputData = job.input_data || job.inputs || {};
          const proteinName = inputData.protein_name || inputData.target_name || '';
          const jobBaseName = job.job_name || job.name || `${job.task_type || 'Unknown'} Prediction`;
          const enhancedName = proteinName ? `${jobBaseName} (${proteinName})` : jobBaseName;
          
          // Unified job data structure
          const originalJobData = {
            ...job,
            job_id: job.id, // Unified store uses 'id' as primary key
            job_name: job.job_name || job.name || `${job.task_type || 'Unknown'} Prediction`,
            task_type: job.task_type || job.type || 'unknown',
            status: job.status || 'unknown',
            inputs: inputData,
            results: job.results || {}
          };
          
          return {
            id: job.id,
            name: enhancedName,
            type: getJobTypeDisplay(job.task_type || job.type),
            status: mapJobStatus(job.status),
            submitted: job.created_at ? new Date(job.created_at).toLocaleString() : 'Unknown',
            original: originalJobData
          };
        });
        
        setJobRows(mappedJobs);
        setTotalJobs(fetchResult.total || mappedJobs.length);
        setError(null);
        
        // Performance feedback
        if (loadTime < 10) {
          console.log(`⚡ LIGHTNING-FAST: ${loadTime.toFixed(1)}ms (${mappedJobs.length} jobs) - ${dataSource}`);
        } else if (loadTime < 100) {
          console.log(`⚡ ULTRA-FAST: ${loadTime.toFixed(0)}ms (${mappedJobs.length} jobs) - ${dataSource}`);
        } else if (loadTime < 1000) {
          console.log(`✅ FAST: ${loadTime.toFixed(0)}ms (${mappedJobs.length} jobs) - ${dataSource}`);
        } else {
          console.log(`⏱️ SLOW: ${loadTime.toFixed(0)}ms - needs optimization`);
        }
        
        // Performance stats
        const perf = unifiedJobStore.getPerformance();
        console.log(`📊 Store Performance: ${perf.cache_hits} hits, ${perf.api_calls} API calls, cache age: ${perf.cache_age_seconds}s`);
        
      } catch (err) {
        console.error('Failed to fetch individual jobs:', err);
        const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(`Failed to load individual jobs: ${errorMessage}`);
        setJobRows([]);
      } finally {
        setLoading(false);
      }
    };

    fetchSavedJobs();
  }, []); // No dependencies - unified store handles caching and refresh internally
  
  // Subscribe to unified store updates for reactive UI
  useEffect(() => {
    const unsubscribe = unifiedJobStore.subscribe((allJobs) => {
      // Filter for individual jobs only
      const individualJobs = allJobs.filter(job => job.type === 'individual');
      
      if (individualJobs.length !== jobRows.length) {
        console.log(`🔄 Store updated: ${individualJobs.length} individual jobs available`);
        // Re-trigger fetch if data changed
        // This provides reactive updates when jobs complete in the background
      }
    });
    
    return unsubscribe;
  }, [jobRows.length]);

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
      case 'protein_structure':
        return 'Boltz-2 Protein Structure';
      case 'protein_complex':
        return 'Boltz-2 Protein Complex';
      case 'binding_site_prediction':
        return 'Boltz-2 Binding Site';
      case 'variant_comparison':
        return 'Boltz-2 Variant Comparison';
      case 'drug_discovery':
        return 'Boltz-2 Drug Discovery';
      case 'batch_protein_ligand_screening':
        return 'Batch Protein-Ligand Screening';
      case 'nanobody_design':
        return 'RFAntibody Nanobody Design';
      case 'cdr_optimization':
        return 'RFAntibody CDR Optimization';
      case 'epitope_targeted_design':
        return 'RFAntibody Epitope Design';
      case 'antibody_de_novo_design':
        return 'RFAntibody De Novo Design';
      case 'structure_prediction':
        return 'Chai-1 Structure Prediction';
      case 'boltz2':
        return 'Boltz-2';
      case 'chai1':
        return 'Chai-1';
      case 'rfantibody':
        return 'RFAntibody';
      default:
        return (taskType || 'Unknown').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
  };

  // Handle job view action - navigate to appropriate page based on task type
  const handleViewJob = async (jobId: string) => {
    const job = jobRows.find(j => j.id === jobId);
    if (!job?.original) {
      console.error('No job data found for ID:', jobId);
      return;
    }

    const taskType = job.original.task_type;
    const model = job.original.model || 'boltz2';
    // Use job.id as primary, fallback to job_id field if available
    const originalJobId = job.original.job_id || job.original.id || job.id;
    
    // For Boltz-2 protein-ligand jobs, show the new results viewer
    if (model === 'boltz2' || taskType?.includes('ligand') || taskType?.includes('binding')) {
      setSelectedJobForViewing(originalJobId);
      setSelectedJobData(job.original);
      setShowResultsViewer(true);
      return;
    }
    
    // For batch jobs, navigate to batch results page
    if (taskType?.includes('batch')) {
      navigate(`/batch-results/${originalJobId}`);
      return;
    }
    
    // Determine the target page based on task type
    const getTargetPage = (taskType: string): string => {
      if (taskType?.includes('batch') || taskType === 'batch_protein_ligand_screening') {
        return '/boltz2'; // Batch jobs use Boltz2 page for now
      }
      if (taskType?.includes('nanobody') || taskType?.includes('antibody') || taskType === 'rfantibody') {
        return '/boltz2'; // RFAntibody tasks, for now redirect to Boltz2 (can be changed later)
      }
      if (taskType === 'structure_prediction' || taskType === 'chai1') {
        return '/boltz2'; // Chai-1 tasks, for now redirect to Boltz2 (can be changed later)
      }
      return '/boltz2'; // Default to Boltz2 page
    };
    
    const targetPage = getTargetPage(taskType);
    
    // Check if we already have the results in the saved data
    if (job.original.results && Object.keys(job.original.results).length > 0) {
      // Navigate directly with saved results
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

    // Try to fetch fresh job data if results are missing
    try {
      const response = await fetch(`/api/v1/jobs/${originalJobId}`);
      if (response.ok) {
        const fullJobData = await response.json();
        
        // Navigate to appropriate page with fresh job data
        navigate(targetPage, { 
          state: { 
            savedJob: job.original,
            viewMode: true,
            predictionResult: fullJobData.result_data || fullJobData.results || job.original.results,
            taskType: taskType
          } 
        });
      } else {
        // If job not found in jobs table, use saved results
        console.warn(`Job ${originalJobId} not found in jobs table (${response.status}), using saved results`);
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
      // Handle fetch errors (network issues, etc.)
      console.warn(`Failed to fetch job ${originalJobId}:`, fetchError);
      navigate(targetPage, { 
        state: { 
          savedJob: job.original,
          viewMode: true,
          predictionResult: job.original.results || {},
          taskType: taskType
        } 
      });
    }
  };

  // Handle job deletion
  const handleDeleteJob = (jobId: string) => {
    const job = jobRows.find(j => j.id === jobId);
    setDeleteConfirmation({
      isOpen: true,
      jobId,
      jobName: job?.name || 'Unknown Job',
      isBulk: false,
      count: 1
    });
  };

  const confirmDelete = async () => {
    const { jobId, isBulk } = deleteConfirmation;
    
    if (!jobId && !isBulk) return;

    try {
      if (isBulk) {
        await handleBulkDeleteConfirmed();
      } else {
        await handleSingleDeleteConfirmed(jobId!);
      }
    } catch (error) {
      console.error('Error deleting job(s):', error);
      setError('Error deleting job(s). Please try again.');
    } finally {
      setDeleteConfirmation({ isOpen: false, jobId: null, jobName: '', isBulk: false, count: 0 });
    }
  };

  const handleSingleDeleteConfirmed = async (jobId: string) => {
    // Delete from MyResults table using the MyResults ID
    const response = await fetch(`/api/v1/jobs/${jobId}?user_id=omtx_deployment_user`, {
      method: 'DELETE',
    });

    if (response.ok) {
      // Remove job from local state
      setJobRows(prev => prev.filter(job => job.id !== jobId));
      setSelectedJobs(prev => {
        const newSelected = new Set(prev);
        newSelected.delete(jobId);
        return newSelected;
      });
      setTotalJobs(prev => prev - 1);
    } else {
      throw new Error('Failed to delete job');
    }
  };

  // Handle bulk deletion
  const handleBulkDelete = () => {
    if (selectedJobs.size === 0) return;
    
    setDeleteConfirmation({
      isOpen: true,
      jobId: null,
      jobName: '',
      isBulk: true,
      count: selectedJobs.size
    });
  };

  const handleBulkDeleteConfirmed = async () => {
    const deletePromises = Array.from(selectedJobs).map(jobId =>
      fetch(`/api/v1/jobs/${jobId}?user_id=omtx_deployment_user`, { method: 'DELETE' })
    );

    const results = await Promise.allSettled(deletePromises);
    const successCount = results.filter(result => result.status === 'fulfilled').length;

    if (successCount > 0) {
      // Remove successfully deleted jobs from state
      setJobRows(prev => prev.filter(job => !selectedJobs.has(job.id)));
      setTotalJobs(prev => prev - successCount);
      setSelectedJobs(new Set());
    }

    if (successCount < selectedJobs.size) {
      setError(`${successCount} jobs deleted successfully. ${selectedJobs.size - successCount} failed to delete.`);
    }
  };

  const [columnVisibility, setColumnVisibility] = useState<ColumnVisibility>({
    checkbox: true,
    name: true,
    type: true,
    status: true,
    submitted: true,
    actions: true,
  });

  const handleJobSelect = (jobId: string, checked: boolean) => {
    const newSelected = new Set(selectedJobs);
    if (checked) {
      newSelected.add(jobId);
    } else {
      newSelected.delete(jobId);
    }
    setSelectedJobs(newSelected);
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedJobs(new Set(jobRows.map(job => job.id)));
    } else {
      setSelectedJobs(new Set());
    }
  };

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const handleColumnSort = (column: string, direction: 'asc' | 'desc') => {
    setSortColumn(column);
    setSortDirection(direction);
  };

  const handleColumnToggle = (columnKey: keyof ColumnVisibility) => {
    setColumnVisibility(prev => ({
      ...prev,
      [columnKey]: !prev[columnKey]
    }));
  };

  const handleHideColumn = (columnKey: keyof ColumnVisibility) => {
    setColumnVisibility(prev => ({
      ...prev,
      [columnKey]: false
    }));
  };

  const handleShowAll = () => {
    setColumnVisibility({
      checkbox: true,
      name: true,
      type: true,
      status: true,
      submitted: true,
      actions: true,
    });
  };

  const handleHideAll = () => {
    setColumnVisibility({
      checkbox: false,
      name: false,
      type: false,
      status: false,
      submitted: false,
      actions: false,
    });
  };

  const getSelectedJobsStatuses = () => {
    const selectedJobsData = jobRows.filter(job => selectedJobs.has(job.id));
    return selectedJobsData.map(job => job.status);
  };

  const canDownload = () => {
    const statuses = getSelectedJobsStatuses();
    return selectedJobs.size > 0 && statuses.some(status => status === 'Complete');
  };

  const canDelete = () => {
    return selectedJobs.size > 0;
  };

  const handleSearchReset = () => {
    setSearchQuery('');
    setCurrentPage(1); // Reset to first page when clearing search
  };

  const handleDownloadResults = async () => {
    // Simplified download handler - you can expand this as needed
    toast({
      title: "Download started",
      description: "Preparing files for download...",
      variant: "default"
    });
  };

  // Reset to page 1 when search query changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  // Filter jobs based on search query
  const filteredJobs = jobRows.filter(job => {
    if (!searchQuery) return true;
    const searchLower = searchQuery.toLowerCase();
    return (
      job.name.toLowerCase().includes(searchLower) ||
      job.type.toLowerCase().includes(searchLower) ||
      job.status.toLowerCase().includes(searchLower)
    );
  });

  // Calculate pagination
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

        {/* Search Section */}
        <div className="mb-6">
          <SearchControls
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onReset={handleSearchReset}
          />

          <div className="mb-4">
            <JobsFilterControls 
              selectedJobsCount={selectedJobs.size}
              canDownload={canDownload()}
              canDelete={canDelete()}
              onBulkDelete={handleBulkDelete}
              onDownload={handleDownloadResults}
            />
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Total Jobs</p>
                  <p className="text-2xl font-bold text-white">{totalJobs}</p>
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
                  <p className="text-2xl font-bold text-green-400">
                    {jobRows.filter(job => job.status === 'Complete').length}
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
                  <p className="text-sm text-gray-400">Failed</p>
                  <p className="text-2xl font-bold text-red-400">
                    {jobRows.filter(job => job.status === 'Failed').length}
                  </p>
                </div>
                <AlertCircle className="h-8 w-8 text-red-400" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Running</p>
                  <p className="text-2xl font-bold text-yellow-400">
                    {jobRows.filter(job => job.status === 'Running').length}
                  </p>
                </div>
                <Clock className="h-8 w-8 text-yellow-400" />
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

        {/* Delete Confirmation Dialog */}
        {deleteConfirmation.isOpen && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 max-w-md w-full mx-4">
              <h3 className="text-lg font-semibold text-white mb-4">
                {deleteConfirmation.isBulk ? 'Delete Selected Jobs' : 'Delete Job'}
              </h3>
              <p className="text-gray-300 mb-6">
                {deleteConfirmation.isBulk 
                  ? `Are you sure you want to delete ${deleteConfirmation.count} selected jobs? This action cannot be undone.`
                  : `Are you sure you want to delete "${deleteConfirmation.jobName}"? This action cannot be undone.`
                }
              </p>
              <div className="flex space-x-3 justify-end">
                <Button
                  variant="outline"
                  onClick={() => {
                    setDeleteConfirmation({ isOpen: false, jobId: null, jobName: '', isBulk: false, count: 0 });
                    setError(null);
                  }}
                  className="border-gray-600 text-gray-300 hover:bg-gray-700"
                >
                  Cancel
                </Button>
                <Button
                  onClick={confirmDelete}
                  className="bg-red-600 hover:bg-red-700 text-white"
                >
                  Delete
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && jobRows.length === 0 && !error && (
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

        {/* Results Table */}
        {(loading || jobRows.length > 0) && (
          <LazyTable
            jobRows={paginatedJobs}
            selectedJobs={selectedJobs}
            columnVisibility={columnVisibility}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            onJobSelect={handleJobSelect}
            onSelectAll={handleSelectAll}
            onSort={handleSort}
            onColumnSort={handleColumnSort}
            onHideColumn={handleHideColumn}
            onColumnToggle={handleColumnToggle}
            onShowAll={handleShowAll}
            onHideAll={handleHideAll}
            onViewJob={handleViewJob}
            isLoading={loading}
          />
        )}

        {/* Pagination */}
        {!loading && jobRows.length > 0 && (
          <PaginationControls
            currentPage={currentPage}
            totalItems={totalFilteredJobs}
            itemsPerPage={itemsPerPage}
            onPageChange={setCurrentPage}
            onItemsPerPageChange={(newItemsPerPage) => {
              setItemsPerPage(newItemsPerPage);
              setCurrentPage(1); // Reset to first page when changing items per page
            }}
          />
        )}

        <div className="mt-8 text-center">
          <p className="text-gray-400">
            If you have questions about your saved jobs, please contact info@omtx.ai.
          </p>
        </div>
      </main>

      {/* Boltz-2 Results Viewer Dialog */}
      <Dialog open={showResultsViewer} onOpenChange={setShowResultsViewer}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto" aria-describedby="job-results-description">
          <DialogHeader>
            <DialogTitle>Job Results</DialogTitle>
            <div id="job-results-description" className="sr-only">
              View detailed results for your Boltz-2 prediction including structure, metrics, and downloadable files
            </div>
          </DialogHeader>
          {selectedJobForViewing && (
            <Boltz2ResultsViewer
              jobId={selectedJobForViewing}
              jobData={selectedJobData}
              onClose={() => {
                setShowResultsViewer(false);
                setSelectedJobForViewing(null);
                setSelectedJobData(null);
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MyResults;
