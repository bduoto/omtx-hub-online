import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { unifiedJobStore } from '@/stores/unifiedJobStore';
import { Header } from '@/components/Header';
import { Navigation } from '@/components/Navigation';
import { UserInfoSection } from '@/components/UserInfoSection';
import { SearchControls } from '@/components/SearchControls';
import { JobsFilterControls } from '@/components/JobsFilterControls';
import LazyTable from '@/components/LazyTable';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { PaginationControls } from '@/components/PaginationControls';
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

interface SavedBatch {
  id: string;
  batch_id: string;
  batch_name: string;
  status: string;
  created_at: string;
  saved_at: string;
  inputs: any;
  results: any;
  user_id: string;
  model_name?: string;
  total_jobs?: number;
  completed_jobs?: number;
  failed_jobs?: number;
  // New indexer fields
  file_count?: number;
  file_types?: string[];
  has_structure?: boolean;
  bucket_path?: string;
  auto_indexed?: boolean;
}

interface BatchRow {
  id: string;
  name: string;
  type: string;
  status: 'Complete' | 'Failed' | 'In Progress' | 'Running';
  submitted: string;
  original?: SavedBatch; // Store original saved batch data
}

interface ColumnVisibility {
  checkbox: boolean;
  name: boolean;
  type: boolean;
  status: boolean;
  submitted: boolean;
  actions: boolean;
}

const MyBatches = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOrganization, setSelectedOrganization] = useState('none');
  const [selectedBatches, setSelectedBatches] = useState<Set<string>>(new Set());
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [batchRows, setBatchRows] = useState<BatchRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalBatches, setTotalBatches] = useState(0);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{
    isOpen: boolean;
    batchId: string | null;
    batchName: string;
    isBulk: boolean;
    count: number;
  }>({ isOpen: false, batchId: null, batchName: '', isBulk: false, count: 0 });

  // INSTANT batch loading using unified store - sub-millisecond for cache hits
  const fetchBatchesOptimized = async () => {
    try {
      console.time('⚡ Unified Store Batch Access');
      
      // Get batch jobs from unified store (instant for cache hits)
      const cachedBatches = unifiedJobStore.getCachedBatchJobs();
      
      if (cachedBatches.length > 0) {
        console.timeEnd('⚡ Unified Store Batch Access');
        console.log(`⚡ INSTANT: ${cachedBatches.length} batch jobs from unified cache`);
        return { batches: cachedBatches, total: cachedBatches.length, dataSource: 'unified-cache' };
      }
      
      // Ensure batch jobs are loaded (this now calls the specific batch job loader)
      await unifiedJobStore.ensureBatchJobsLoaded();
      const allBatches = unifiedJobStore.getCachedBatchJobs();
      
      console.timeEnd('⚡ Unified Store Batch Access');
      console.log(`✅ Unified Store: Loaded ${allBatches.length} batch jobs`);
      
      return { batches: allBatches, total: allBatches.length, dataSource: 'unified-store' };
      
    } catch (err) {
      console.error('Unified store failed, falling back to API:', err);
      
      // Fallback to Batch API directly
      try {
        const response = await fetch(`/api/v3/batches/?user_id=current_user&limit=200`);
        if (response.ok) {
          const data = await response.json();
          const batches = data.batches || [];
          console.log(`✅ API Fallback: Loaded ${batches.length} batch jobs from Batch API`);
          return { batches: batches, total: batches.length, dataSource: 'batch-api' };
        }
      } catch (fallbackErr) {
        console.error('Batch API fallback also failed:', fallbackErr);
      }
      
      throw new Error('Both unified store and Batch API fallback failed');
    }
  };

  // INSTANT loading with unified store - preloaded data ready immediately
  useEffect(() => {
    const fetchSavedBatches = async () => {
      try {
        console.log('⚡ Loading batch jobs with UNIFIED STORE (instant)...');
        setLoading(true);

        const startTime = performance.now();
        const fetchResult = await fetchBatchesOptimized();
        const batches = fetchResult.batches;
        const dataSource = fetchResult.dataSource;
        const loadTime = performance.now() - startTime;
        
        // Map unified batch job data to BatchRow format
        const mappedBatches: BatchRow[] = batches.map((batch: any) => {
          // Extract batch info for better naming
          const inputData = batch.input_data || batch.inputs || {};
          const batchBaseName = batch.job_name || batch.name || batch.batch_name || `Batch Prediction`;
          
          // Extract batch statistics from batch_info
          const batchInfo = batch.batch_info || {};
          const totalJobs = batchInfo.child_count || batch.total_jobs || 0;
          const completedJobs = batchInfo.completed_count || batch.completed_jobs || 0;
          const failedJobs = batch.failed_jobs || 0;

          return {
            id: batch.id,
            name: batchBaseName,
            type: getBatchTypeDisplay(batch.task_type || batch.model_name || 'batch'),
            status: mapBatchStatus(batch.status),
            submitted: batch.created_at ? new Date(batch.created_at).toLocaleString() : 'Unknown',
            original: {
              id: batch.id,
              batch_id: batch.id, // Unified store uses 'id' as primary key
              batch_name: batchBaseName,
              status: batch.status,
              created_at: batch.created_at,
              saved_at: batch.updated_at || batch.created_at,
              inputs: inputData,
              results: batch.results || {},
              user_id: batch.user_id,
              model_name: batch.task_type || batch.model_name,
              total_jobs: totalJobs,
              completed_jobs: completedJobs,
              failed_jobs: failedJobs,
              // Include unified store metadata
              file_count: 0, // Will be populated from batch_info if available
              file_types: [],
              has_structure: completedJobs > 0,
              bucket_path: `batches/${batch.id}`,
              auto_indexed: true
            }
          };
        });
        
        setBatchRows(mappedBatches);
        setTotalBatches(fetchResult.total || mappedBatches.length);
        setError(null);
        
        // Performance feedback
        if (loadTime < 10) {
          console.log(`⚡ LIGHTNING-FAST: ${loadTime.toFixed(1)}ms (${mappedBatches.length} batches) - ${dataSource}`);
        } else if (loadTime < 100) {
          console.log(`⚡ ULTRA-FAST: ${loadTime.toFixed(0)}ms (${mappedBatches.length} batches) - ${dataSource}`);
        } else if (loadTime < 1000) {
          console.log(`✅ FAST: ${loadTime.toFixed(0)}ms (${mappedBatches.length} batches) - ${dataSource}`);
        } else {
          console.log(`⏱️ SLOW: ${loadTime.toFixed(0)}ms - needs optimization`);
        }
        
        // Performance stats
        const perf = unifiedJobStore.getPerformance();
        console.log(`📊 Store Performance: ${perf.cache_hits} hits, ${perf.api_calls} API calls, cache age: ${perf.cache_age_seconds}s`);
        
      } catch (err) {
        console.error('Failed to fetch batch jobs:', err);
        const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(`Failed to load batch jobs: ${errorMessage}`);
        setBatchRows([]);
      } finally {
        setLoading(false);
      }
    };

    fetchSavedBatches();
  }, []); // No dependencies - unified store handles caching and refresh internally
  
  // Subscribe to unified store updates for reactive UI
  useEffect(() => {
    const unsubscribe = unifiedJobStore.subscribe((allJobs) => {
      // Filter for batch jobs only
      const batchJobs = allJobs.filter(job => job.type === 'batch_parent');
      
      if (batchJobs.length !== batchRows.length) {
        console.log(`🔄 Store updated: ${batchJobs.length} batch jobs available`);
        // Re-trigger fetch if data changed
        // This provides reactive updates when batches complete in the background
      }
    });
    
    return unsubscribe;
  }, [batchRows.length]);

  // Map batch status to display format
  const mapBatchStatus = (status: string): 'Complete' | 'Failed' | 'In Progress' | 'Running' => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'Complete';
      case 'failed':
      case 'error':
        return 'Failed';
      case 'running':
        return 'Running';
      case 'in_progress':
      case 'pending':
        return 'In Progress';
      default:
        // Use intelligent status logic for unknown statuses
        return 'In Progress';
    }
  };

  // Map batch type to display format - enhanced for unified store
  const getBatchTypeDisplay = (taskType: string): string => {
    switch (taskType) {
      case 'batch_protein_ligand_screening':
      case 'protein_ligand_binding':
        return 'Batch Protein-Ligand Screening';
      case 'boltz2':
        return 'Boltz-2 Batch';
      case 'chai1':
        return 'Chai-1 Batch';
      case 'rfantibody':
      case 'nanobody_design':
        return 'RFAntibody Batch';
      case 'batch':
        return 'Batch Processing';
      default:
        // Enhanced display for unified store task types
        if (taskType?.includes('batch')) {
          return (taskType || 'Batch').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }
        return `${(taskType || 'Unknown').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} Batch`;
    }
  };

  // Handle batch view action
  const handleViewBatch = async (batchId: string) => {
    const batch = batchRows.find(b => b.id === batchId);
    if (!batch?.original) {
      console.error('No batch data found for ID:', batchId);
      return;
    }

    const originalBatchId = batch.original.batch_id;

    console.log('🔍 Navigating to batch results for:', originalBatchId);

    // Navigate to dedicated BatchResults page for enhanced results
    navigate(`/batch-results/${originalBatchId}`, {
      state: {
        batchJob: batch.original,
        fromBatchList: true
      }
    });
  };

  // Handle batch deletion
  const handleDeleteBatch = (batchId: string) => {
    const batch = batchRows.find(b => b.id === batchId);
    setDeleteConfirmation({
      isOpen: true,
      batchId,
      batchName: batch?.name || 'Unknown Batch',
      isBulk: false,
      count: 1
    });
  };

  const confirmDelete = async () => {
    const { batchId, isBulk } = deleteConfirmation;
    
    if (!batchId && !isBulk) return;

    try {
      if (isBulk) {
        await handleBulkDeleteConfirmed();
      } else {
        await handleSingleDeleteConfirmed(batchId!);
      }
    } catch (error) {
      console.error('Error deleting batch(es):', error);
      setError('Error deleting batch(es). Please try again.');
    } finally {
      setDeleteConfirmation({ isOpen: false, batchId: null, batchName: '', isBulk: false, count: 0 });
    }
  };

  const handleSingleDeleteConfirmed = async (batchId: string) => {
    // Use unified API v3 for batch deletion with fallback
    let response = await fetch(`/api/v3/batches/${batchId}?user_id=current_user`, {
      method: 'DELETE',
    });
    
    // Fallback to legacy API if v3 not available
    if (!response.ok && response.status === 404) {
      response = await fetch(`/api/v2/my-batches/${batchId}?user_id=current_user`, {
        method: 'DELETE',
      });
    }

    if (response.ok) {
      // Remove batch from local state
      setBatchRows(prev => prev.filter(batch => batch.id !== batchId));
      setSelectedBatches(prev => {
        const newSelected = new Set(prev);
        newSelected.delete(batchId);
        return newSelected;
      });
      setTotalBatches(prev => prev - 1);
    } else {
      throw new Error('Failed to delete batch');
    }
  };

  // Handle bulk deletion
  const handleBulkDelete = () => {
    if (selectedBatches.size === 0) return;
    
    setDeleteConfirmation({
      isOpen: true,
      batchId: null,
      batchName: '',
      isBulk: true,
      count: selectedBatches.size
    });
  };

  const handleBulkDeleteConfirmed = async () => {
    const deletePromises = Array.from(selectedBatches).map(async (batchId) => {
      // Try unified API v3 first, fallback to legacy
      let response = await fetch(`/api/v3/batches/${batchId}?user_id=current_user`, { method: 'DELETE' });
      if (!response.ok && response.status === 404) {
        response = await fetch(`/api/v2/my-batches/${batchId}?user_id=current_user`, { method: 'DELETE' });
      }
      return response;
    });

    const results = await Promise.allSettled(deletePromises);
    const successCount = results.filter(result => result.status === 'fulfilled').length;

    if (successCount > 0) {
      // Remove successfully deleted batches from state
      setBatchRows(prev => prev.filter(batch => !selectedBatches.has(batch.id)));
      setTotalBatches(prev => prev - successCount);
      setSelectedBatches(new Set());
    }

    if (successCount < selectedBatches.size) {
      setError(`${successCount} batches deleted successfully. ${selectedBatches.size - successCount} failed to delete.`);
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

  const handleBatchSelect = (batchId: string, checked: boolean) => {
    const newSelected = new Set(selectedBatches);
    if (checked) {
      newSelected.add(batchId);
    } else {
      newSelected.delete(batchId);
    }
    setSelectedBatches(newSelected);
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedBatches(new Set(batchRows.map(batch => batch.id)));
    } else {
      setSelectedBatches(new Set());
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

  const getSelectedBatchesStatuses = () => {
    const selectedBatchesData = batchRows.filter(batch => selectedBatches.has(batch.id));
    return selectedBatchesData.map(batch => batch.status);
  };

  const canDownload = () => {
    const statuses = getSelectedBatchesStatuses();
    return selectedBatches.size > 0 && statuses.some(status => status === 'Complete');
  };

  const canDelete = () => {
    return selectedBatches.size > 0;
  };

  const handleSearchReset = () => {
    setSearchQuery('');
    setCurrentPage(1); // Reset to first page when clearing search
  };

  const handleDownloadResults = async () => {
    const selectedBatchesData = batchRows.filter(batch => selectedBatches.has(batch.id) && batch.status === 'Complete');
    
    if (selectedBatchesData.length === 0) {
      toast({
        title: "No batches selected",
        description: "Please select completed batches to download their results.",
        variant: "destructive"
      });
      return;
    }

    try {
      let downloadCount = 0;
      
      for (const batch of selectedBatchesData) {
        const batchId = batch.original?.batch_id;
        if (!batchId) continue;

        try {
          // First, get download info from the new API
          const downloadInfoResponse = await fetch(`/api/v2/my-batches/${batchId}/download-info`);
          
          if (downloadInfoResponse.ok) {
            const downloadInfo = await downloadInfoResponse.json();
            const availableEndpoints = downloadInfo.download_endpoints || [];
            const userFriendlyNames = downloadInfo.user_friendly_names || {};
            
            console.log(`📁 ${batch.name}: Found ${availableEndpoints.length} download options`);
            
            // Try downloading from available endpoints
            let downloadSuccess = false;
            
            for (const endpoint of availableEndpoints) {
              try {
                const response = await fetch(endpoint);
                
                if (response.ok) {
                  const blob = await response.blob();
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  
                  // Determine file type and use user-friendly name
                  const fileExt = endpoint.includes('/cif') ? 'cif' : 
                                 endpoint.includes('/pdb') ? 'pdb' : 
                                 endpoint.includes('zip') ? 'zip' : 'file';
                  
                  const friendlyName = userFriendlyNames[fileExt];
                  
                  if (friendlyName) {
                    a.download = friendlyName;
                  } else {
                    // Fallback to original naming logic
                    const inputs = batch.original?.inputs || {};
                    const batchName = batch.original?.batch_name || 'batch';
                    a.download = `${batchName}_results.${fileExt}`;
                  }
                  
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  window.URL.revokeObjectURL(url);
                  
                  console.log(`✅ Downloaded ${a.download} for ${batch.name}`);
                  downloadSuccess = true;
                  downloadCount++;
                  break; // Download first available format
                }
              } catch (error) {
                console.warn(`Failed to download from ${endpoint} for ${batch.name}:`, error);
              }
            }
            
            if (!downloadSuccess && availableEndpoints.length === 0) {
              console.warn(`No download endpoints available for ${batch.name}`);
            }
          } else {
            // Fallback to original method if download info API fails
            console.log(`📋 ${batch.name}: Falling back to original download method`);
            await downloadUsingFallbackMethod(batch);
            downloadCount++;
          }
        } catch (error) {
          console.warn(`Error getting download info for ${batch.name}, trying fallback:`, error);
          await downloadUsingFallbackMethod(batch);
          downloadCount++;
        }
      }
      
      // Show success message
      if (downloadCount > 0) {
        toast({
          title: "Download complete",
          description: `Downloaded files for ${downloadCount} of ${selectedBatchesData.length} batch(es).`,
          variant: "default"
        });
      } else {
        toast({
          title: "No files downloaded",
          description: "No downloadable files were found for the selected batches.",
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Error downloading batch results:', error);
      toast({
        title: "Download error",
        description: "Some files could not be downloaded. Check console for details.",
        variant: "destructive"
      });
    }
  };
  
  // Fallback download method for backward compatibility
  const downloadUsingFallbackMethod = async (batch: BatchRow) => {
    const batchId = batch.original?.batch_id;
    const modelName = batch.original?.model_name;
    if (!batchId) return false;

    const downloadEndpoints = [
      `/api/v2/batches/${batchId}/download-all`,
      `/api/batches/${batchId}/download-all`,
      `/api/v2/batches/${batchId}/download/zip`,
      `/api/batches/${batchId}/download/zip`,
    ];
    
    for (const endpoint of downloadEndpoints) {
      try {
        const response = await fetch(endpoint);
        
        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          
          const fileExt = endpoint.includes('download-all') || endpoint.includes('/zip') ? 'zip' : 'file';
          
          const inputs = batch.original?.inputs || {};
          const batchName = batch.original?.batch_name || 'batch';
          
          a.download = `${batchName}_results.${fileExt}`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
          
          console.log(`✅ Downloaded ${fileExt} file for ${batch.name} (fallback)`);
          return true;
        }
      } catch (error) {
        console.warn(`Failed to download from ${endpoint} for ${batch.name}:`, error);
      }
    }
    
    return false;
  };

  // Reset to page 1 when search query changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  // Filter batches based on search query
  const filteredBatches = batchRows.filter(batch => {
    if (!searchQuery) return true;
    const searchLower = searchQuery.toLowerCase();
    return (
      batch.name.toLowerCase().includes(searchLower) ||
      batch.type.toLowerCase().includes(searchLower) ||
      batch.status.toLowerCase().includes(searchLower)
    );
  });

  // Calculate pagination
  const totalFilteredBatches = filteredBatches.length;
  const totalPages = Math.ceil(totalFilteredBatches / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedBatches = filteredBatches.slice(startIndex, endIndex);

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
              selectedJobsCount={selectedBatches.size}
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
                  <p className="text-sm text-gray-400">Total Batches</p>
                  <p className="text-2xl font-bold text-white">{totalBatches}</p>
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
                    {batchRows.filter(batch => batch.status === 'Complete').length}
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
                    {batchRows.filter(batch => batch.status === 'Failed').length}
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
                    {batchRows.filter(batch => batch.status === 'Running').length}
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
                {deleteConfirmation.isBulk ? 'Delete Selected Batches' : 'Delete Batch'}
              </h3>
              <p className="text-gray-300 mb-6">
                {deleteConfirmation.isBulk 
                  ? `Are you sure you want to delete ${deleteConfirmation.count} selected batches? This action cannot be undone.`
                  : `Are you sure you want to delete "${deleteConfirmation.batchName}"? This action cannot be undone.`
                }
              </p>
              <div className="flex space-x-3 justify-end">
                <Button
                  variant="outline"
                  onClick={() => {
                    setDeleteConfirmation({ isOpen: false, batchId: null, batchName: '', isBulk: false, count: 0 });
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
        {!loading && batchRows.length === 0 && !error && (
          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-8 text-center">
              <FileText className="h-16 w-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No saved batches yet</h3>
              <p className="text-gray-400 mb-6">
                Completed batch predictions are automatically saved here. Run a batch prediction to see your results.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button 
                  onClick={() => navigate('/boltz2')}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  Run Batch Prediction
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
        {(loading || batchRows.length > 0) && (
          <LazyTable
            jobRows={paginatedBatches}
            selectedJobs={selectedBatches}
            columnVisibility={columnVisibility}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            onJobSelect={handleBatchSelect}
            onSelectAll={handleSelectAll}
            onSort={handleSort}
            onColumnSort={handleColumnSort}
            onHideColumn={handleHideColumn}
            onColumnToggle={handleColumnToggle}
            onShowAll={handleShowAll}
            onHideAll={handleHideAll}
            onViewJob={handleViewBatch}
            isLoading={loading}
          />
        )}

        {/* Pagination */}
        {!loading && batchRows.length > 0 && (
          <PaginationControls
            currentPage={currentPage}
            totalItems={totalFilteredBatches}
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
            If you have questions about your saved batches, please contact info@omtx.ai.
          </p>
        </div>
      </main>
    </div>
  );
};

export default MyBatches;