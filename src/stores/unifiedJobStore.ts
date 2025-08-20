/**
 * Unified Job Store - Single source of truth for all user job data
 * Provides instant navigation and intelligent caching for optimal UX
 */

export interface UnifiedJob {
  id: string;
  job_name: string;
  type: 'individual' | 'batch_parent' | 'batch_child';
  task_type: string;
  status: string;
  created_at: string;
  updated_at?: string;
  user_id: string;
  estimated_completion_time?: string;
  results?: any;
  batch_info?: {
    parent_id?: string;
    child_count?: number;
    completed_count?: number;
    summary?: any;
  };
  // Performance tracking
  _loaded_at?: number;
  _cache_hit?: boolean;
}

export interface StorePerformance {
  last_fetch_time: number;
  cache_hits: number;
  api_calls: number;
  average_response_time: number;
  last_api_response_time: number;
}

class UnifiedJobStore {
  private jobs = new Map<string, UnifiedJob>();
  private lastFetch = 0;
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes
  private readonly PRELOAD_CACHE_TTL = 2 * 60 * 1000; // 2 minutes for preloaded data
  
  // Performance tracking
  private performance: StorePerformance = {
    last_fetch_time: 0,
    cache_hits: 0,
    api_calls: 0,
    average_response_time: 0,
    last_api_response_time: 0
  };
  
  // Subscribers for reactive updates
  private subscribers = new Set<(jobs: UnifiedJob[]) => void>();
  
  // Loading states
  private isPreloading = false;
  private preloadPromise: Promise<void> | null = null;
  private isRefreshing = false;
  
  /**
   * Subscribe to job updates for reactive components with memory leak prevention
   */
  subscribe(callback: (jobs: UnifiedJob[]) => void): () => void {
    this.subscribers.add(callback);
    
    // Track user activity when components subscribe
    this.userActivity.set('last_subscribe', Date.now());
    
    return () => {
      this.subscribers.delete(callback);
      // Clean up if no more subscribers
      if (this.subscribers.size === 0) {
        console.log('🧹 No more subscribers, cleaning up store resources');
        this.stopBackgroundRefresh();
      }
    };
  }
  
  /**
   * Notify all subscribers of data changes
   */
  private notifySubscribers(): void {
    const jobs = Array.from(this.jobs.values());
    this.subscribers.forEach(callback => callback(jobs));
  }
  
  /**
   * Preload all user data in background for instant navigation
   */
  async preloadAllData(): Promise<void> {
    if (this.isPreloading || this.preloadPromise) {
      return this.preloadPromise;
    }
    
    console.log('🔄 Starting background preload...');
    this.isPreloading = true;
    this.preloadPromise = this._doPreload();
    
    try {
      await this.preloadPromise;
    } finally {
      this.isPreloading = false;
      this.preloadPromise = null;
    }
  }
  
  private async _doPreload(): Promise<void> {
    try {
      const startTime = performance.now();
      
      // Load lightweight data for instant navigation
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://34.29.29.170';
      const response = await fetch(`${apiBase}/api/v1/jobs?user_id=current_user&limit=200`, {
        headers: {
          'Accept': 'application/json',
          'Cache-Control': 'no-cache'
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      const loadTime = performance.now() - startTime;
      
      // Update performance metrics
      this.performance.api_calls++;
      this.performance.last_api_response_time = loadTime;
      this.performance.average_response_time = 
        (this.performance.average_response_time + loadTime) / 2;
      
      // Populate cache with preloaded data
      this.populateCache(data.jobs, true);
      this.lastFetch = Date.now();
      
      console.log(`✅ Preload completed: ${data.jobs.length} jobs in ${Math.round(loadTime)}ms`);
      console.log(`   Performance: ${data.performance?.response_time_seconds}s backend, cache_hit: ${data.performance?.cache_hit}`);
      
    } catch (error) {
      console.warn('⚠️ Background preload failed:', error);
      // Don't throw - preload failures should be silent
    }
  }
  
  /**
   * Get all jobs with intelligent caching
   */
  async getAllJobs(forceRefresh = false): Promise<UnifiedJob[]> {
    const now = Date.now();
    const cacheAge = now - this.lastFetch;
    
    // Return cached data if fresh and not forcing refresh
    if (!forceRefresh && cacheAge < this.CACHE_TTL && this.jobs.size > 0) {
      this.performance.cache_hits++;
      console.log(`⚡ CACHE HIT: ${this.jobs.size} jobs (age: ${Math.round(cacheAge/1000)}s)`);
      return Array.from(this.jobs.values());
    }
    
    // Load fresh data
    return await this._fetchFreshData(false); // Full data
  }
  
  /**
   * Get cached jobs immediately (for instant rendering)
   */
  getCachedJobs(): UnifiedJob[] {
    return Array.from(this.jobs.values());
  }
  
  /**
   * Get cached individual jobs only
   */
  getCachedIndividualJobs(): UnifiedJob[] {
    return Array.from(this.jobs.values()).filter(job => job.type === 'individual');
  }
  
  /**
   * Get cached batch jobs only  
   */
  getCachedBatchJobs(): UnifiedJob[] {
    return Array.from(this.jobs.values()).filter(job => job.type === 'batch_parent');
  }
  
  /**
   * Ensure individual jobs are loaded (for nav prefetching)
   */
  async ensureIndividualJobsLoaded(): Promise<void> {
    const individualJobs = this.getCachedIndividualJobs();
    if (individualJobs.length === 0 || this._isCacheStale()) {
      await this._loadIndividualJobs();
    }
  }
  
  /**
   * Ensure batch jobs are loaded (for nav prefetching)
   */
  async ensureBatchJobsLoaded(): Promise<void> {
    const batchJobs = this.getCachedBatchJobs();
    if (batchJobs.length === 0 || this._isCacheStale()) {
      await this._loadBatchJobs();
    }
  }
  
  /**
   * Refresh data in background without blocking UI
   */
  async refreshData(): Promise<UnifiedJob[]> {
    if (this.isRefreshing) {
      return this.getCachedJobs();
    }
    
    this.isRefreshing = true;
    
    try {
      console.log('🔄 Background refresh started...');
      const freshJobs = await this._fetchFreshData(false);
      
      // Notify subscribers of updates
      this.notifySubscribers();
      
      console.log(`✅ Background refresh completed: ${freshJobs.length} jobs`);
      return freshJobs;
      
    } finally {
      this.isRefreshing = false;
    }
  }
  
  /**
   * Start background refresh interval with intelligent polling
   */
  startBackgroundRefresh(): void {
    // Use intelligent polling - more frequent when user is active
    let refreshInterval = 2 * 60 * 1000; // Default 2 minutes
    
    const refreshWithBackoff = async () => {
      try {
        // Only refresh if cache is getting stale or user was recently active
        const now = Date.now();
        const cacheAge = now - this.lastFetch;
        const lastActivity = Math.max(...Object.values(this.userActivity));
        const timeSinceActivity = now - lastActivity;
        
        // Adjust refresh frequency based on activity
        if (timeSinceActivity < 5 * 60 * 1000) { // Active within 5 minutes
          refreshInterval = 1 * 60 * 1000; // 1 minute
        } else if (timeSinceActivity < 30 * 60 * 1000) { // Active within 30 minutes
          refreshInterval = 5 * 60 * 1000; // 5 minutes
        } else {
          refreshInterval = 10 * 60 * 1000; // 10 minutes (low activity)
        }
        
        // Only refresh if cache is actually stale or user needs fresh data
        if (cacheAge > refreshInterval / 2) {
          await this.refreshData();
        }
        
      } catch (error) {
        console.warn('⚠️ Background refresh failed:', error);
        // Exponential backoff on errors
        refreshInterval = Math.min(refreshInterval * 1.5, 10 * 60 * 1000);
      }
      
      // Schedule next refresh with current interval
      this.backgroundRefreshTimer = setTimeout(refreshWithBackoff, refreshInterval);
    };
    
    // Start the intelligent refresh cycle
    this.backgroundRefreshTimer = setTimeout(refreshWithBackoff, refreshInterval);
    console.log('🔄 Started intelligent background refresh with exponential backoff');
  }
  
  /**
   * Stop background refresh to prevent memory leaks
   */
  stopBackgroundRefresh(): void {
    if (this.backgroundRefreshTimer) {
      clearTimeout(this.backgroundRefreshTimer);
      this.backgroundRefreshTimer = null;
      console.log('🛑 Background refresh stopped');
    }
  }
  
  // Track user activity for intelligent polling
  private userActivity = new Map<string, number>();
  private backgroundRefreshTimer: NodeJS.Timeout | null = null;
  
  /**
   * Get performance statistics
   */
  getPerformance(): StorePerformance & { cache_size: number; cache_age_seconds: number } {
    return {
      ...this.performance,
      cache_size: this.jobs.size,
      cache_age_seconds: Math.round((Date.now() - this.lastFetch) / 1000)
    };
  }
  
  /**
   * Clear cache (useful for testing and debugging)
   */
  clearCache(): void {
    this.jobs.clear();
    this.lastFetch = 0;
    this.performance.cache_hits = 0;
    this.performance.api_calls = 0;
    console.log('🧹 Cache cleared');
  }
  
  // Private helper methods
  
  private async _fetchFreshData(lightweight = false): Promise<UnifiedJob[]> {
    const startTime = performance.now();
    
    try {
      // Try ultra-fast API first
      let response = await this._tryUltraFastAPI(lightweight);
      let apiUsed = 'ultra-fast';
      
      // Fallback to unified API if ultra-fast fails
      if (!response || !response.ok) {
        console.warn('⚠️ Ultra-fast API failed, falling back to unified API');
        const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://34.29.29.170';
        response = await fetch(`${apiBase}/api/v1/batches?user_id=current_user&limit=200`);
        apiUsed = 'unified-fallback';
        
        if (!response.ok) {
          throw new Error(`API failed: ${response.status} ${response.statusText}`);
        }
      }
      
      const data = await response.json();
      const loadTime = performance.now() - startTime;
      
      // Update performance metrics
      this.performance.api_calls++;
      this.performance.last_api_response_time = loadTime;
      this.performance.last_fetch_time = Date.now();
      
      // Handle different response formats
      const jobs = this._normalizeJobData(data, apiUsed);
      
      // Populate cache
      this.populateCache(jobs, false);
      this.lastFetch = Date.now();
      
      console.log(`✅ Fresh data loaded: ${jobs.length} jobs in ${Math.round(loadTime)}ms via ${apiUsed}`);
      
      return jobs;
      
    } catch (error) {
      console.error('❌ Failed to fetch fresh data:', error);
      
      // Return cached data if available
      const cachedJobs = this.getCachedJobs();
      if (cachedJobs.length > 0) {
        console.log('🔄 Returning stale cached data due to API failure');
        return cachedJobs;
      }
      
      throw error;
    }
  }
  
  private async _tryUltraFastAPI(lightweight: boolean): Promise<Response | null> {
    try {
      // Track API usage for intelligent polling
      this.userActivity.set('api_request', Date.now());
      
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://34.29.29.170';
      const url = `${apiBase}/api/v1/jobs?user_id=current_user&limit=200`;
      
      // Create timeout that works across browsers
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
      
      try {
        const response = await fetch(url, {
          headers: {
            'Accept': 'application/json',
            'Cache-Control': 'no-cache' // Prevent stale cache responses
          },
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        return response;
        
      } catch (fetchError) {
        clearTimeout(timeoutId);
        throw fetchError;
      }
      
    } catch (error) {
      // Don't log 404s - they're expected for ultra-fast API
      if (error instanceof TypeError && error.message.includes('404')) {
        return null; // Silent fallback
      }
      console.warn('Ultra-fast API request failed:', error);
      return null;
    }
  }
  
  private _normalizeJobData(data: any, apiSource: string): UnifiedJob[] {
    // Handle different API response formats
    let jobs: any[] = [];
    
    if (apiSource === 'ultra-fast' && data.jobs) {
      jobs = data.jobs;
    } else if (data.batches) {
      // Handle unified batch API format
      jobs = data.batches.map((batch: any) => ({
        ...batch,
        type: 'batch_parent',
        job_name: batch.batch_name || batch.name || 'Unnamed Batch',
        task_type: batch.batch_type || batch.task_type || 'batch'
      }));
    } else if (data.results) {
      // Handle results API format
      jobs = data.results.map((result: any) => ({
        ...result,
        type: 'individual',
        job_name: result.job_name || result.name || 'Unnamed Job'
      }));
    }
    
    // Ensure all jobs have required fields
    return jobs.map(job => ({
      id: job.id || job.job_id,
      job_name: job.job_name || job.name || 'Unnamed Job',
      type: job.type || (job.task_type?.includes('batch') ? 'batch_parent' : 'individual'),
      task_type: job.task_type || 'unknown',
      status: job.status || 'pending',
      created_at: job.created_at || new Date().toISOString(),
      updated_at: job.updated_at,
      user_id: job.user_id || 'current_user',
      estimated_completion_time: job.estimated_completion_time,
      results: job.results,
      batch_info: job.batch_info,
      _loaded_at: Date.now(),
      _cache_hit: data.performance?.cache_hit || false
    }));
  }
  
  private populateCache(jobs: UnifiedJob[], isPreload: boolean): void {
    // Clear cache before populating with fresh data
    if (!isPreload) {
      this.jobs.clear();
    }
    
    // Add jobs to cache
    jobs.forEach(job => {
      this.jobs.set(job.id, {
        ...job,
        _loaded_at: Date.now()
      });
    });
    
    console.log(`📦 Cache populated with ${this.jobs.size} jobs (preload: ${isPreload})`);
  }
  
  private _isCacheStale(): boolean {
    const age = Date.now() - this.lastFetch;
    return age > this.CACHE_TTL;
  }
  
  /**
   * Load individual jobs specifically
   */
  private async _loadIndividualJobs(): Promise<void> {
    try {
      // Try multiple APIs in order of preference - NEW INDIVIDUAL JOBS API FIRST
      const apiEndpoints = [
        '/api/individual-jobs?user_id=current_user&limit=200', // NEW: Extract from batch child jobs
        '/api/v2/my-results?user_id=current_user&limit=200',
        '/api/v2/my-results?limit=200', // Without user_id param
        '/api/v2/results/ultra-fast?user_id=current_user&limit=200&page=1'
      ];
      
      let data = null;
      let apiUsed = 'none';
      
      for (const endpoint of apiEndpoints) {
        try {
          const response = await fetch(endpoint);
          if (response.ok) {
            data = await response.json();
            apiUsed = endpoint;
            break;
          } else {
            console.warn(`API ${endpoint} failed with status ${response.status}`);
          }
        } catch (err) {
          console.warn(`API ${endpoint} request failed:`, err);
        }
      }
      
      if (!data) {
        console.warn('All individual job APIs failed, trying to extract from unified job data');
        
        // Fallback: use any cached jobs that might be individual jobs
        const allCachedJobs = Array.from(this.jobs.values());
        const potentialIndividualJobs = allCachedJobs.filter(job => 
          !job.type || job.type === 'individual' || 
          (!job.task_type?.includes('batch') && job.job_name && !job.job_name.includes('Batch'))
        );
        
        console.log(`️ Using ${potentialIndividualJobs.length} cached jobs as individual jobs fallback`);
        return;
      }
      
      const results = data.results || data.jobs || [];
      
      // Convert to unified format and add to cache
      const individualJobs = results.map((job: any) => ({
        id: job.id,
        job_name: job.job_name || job.name || 'Unnamed Job',
        type: 'individual' as const,
        task_type: job.task_type || 'unknown',
        status: job.status || 'pending',
        created_at: job.created_at,
        updated_at: job.updated_at,
        user_id: job.user_id,
        results: job.results,
        input_data: job.inputs || {},
        _loaded_at: Date.now()
      }));
      
      // Add individual jobs to cache without clearing existing batch jobs
      individualJobs.forEach(job => this.jobs.set(job.id, job));
      this.lastFetch = Date.now();
      
      console.log(`✅ Loaded ${individualJobs.length} individual jobs from ${apiUsed}`);
    } catch (error) {
      console.error('Failed to load individual jobs:', error);
    }
  }
  
  /**
   * Load batch jobs specifically
   */
  private async _loadBatchJobs(): Promise<void> {
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://34.29.29.170';
      const response = await fetch(`${apiBase}/api/v1/batches?user_id=current_user&limit=200`);
      if (response.ok) {
        const data = await response.json();
        const batches = data.batches || [];
        
        // Convert to unified format and add to cache
        const batchJobs = batches.map((batch: any) => ({
          id: batch.id,
          job_name: batch.name || batch.batch_name || 'Unnamed Batch',
          type: 'batch_parent' as const,
          task_type: batch.model_name || 'batch',
          status: batch.status || 'pending',
          created_at: batch.created_at,
          updated_at: batch.updated_at,
          user_id: batch.user_id,
          batch_info: {
            child_count: batch.total_jobs || 0,
            completed_count: batch.completed_jobs || 0,
            summary: batch.results || {}
          },
          _loaded_at: Date.now()
        }));
        
        // Add batch jobs to cache without clearing existing individual jobs
        batchJobs.forEach(job => this.jobs.set(job.id, job));
        this.lastFetch = Date.now();
        
        console.log(`✅ Loaded ${batchJobs.length} batch jobs`);
      }
    } catch (error) {
      console.error('Failed to load batch jobs:', error);
    }
  }
}

// Global store instance
export const unifiedJobStore = new UnifiedJobStore();

// Auto-start background refresh with cleanup on page unload
if (typeof window !== 'undefined') {
  unifiedJobStore.startBackgroundRefresh();
  
  // Clean up resources on page unload to prevent memory leaks
  window.addEventListener('beforeunload', () => {
    unifiedJobStore.stopBackgroundRefresh();
    unifiedJobStore.clearCache();
  });
  
  // Also clean up on visibility change (tab switch)
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      // Reduce refresh frequency when tab is hidden
      unifiedJobStore.userActivity.set('tab_hidden', Date.now());
    } else {
      // Resume normal refresh when tab becomes visible
      unifiedJobStore.userActivity.set('tab_visible', Date.now());
    }
  });
}

// Development helper
if (typeof window !== 'undefined') {
  (window as any).jobStore = unifiedJobStore;
}