/**
 * Simplified Job Store for Cloud Run Native API
 * 
 * Manages job and batch data with the new auth-free backend.
 * Focused on Boltz-2 predictions with clean state management.
 */

import { apiClient, JobStatusResponse, BatchStatusResponse } from '../services/apiClient_simplified';

export interface Job {
  id: string;
  job_name: string;
  type: 'individual' | 'batch';
  status: 'submitted' | 'running' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  completed_at?: string;
  results?: {
    affinity?: number;
    confidence?: number;
    structure_url?: string;
    results_url?: string;
  };
  parameters?: Record<string, any>;
}

export interface Batch {
  id: string;
  batch_name: string;
  status: 'submitted' | 'running' | 'completed' | 'failed';
  progress: number;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  created_at: string;
  completed_at?: string;
  results?: {
    best_affinity?: number;
    average_affinity?: number;
    results_csv?: string;
    individual_jobs?: Array<{
      job_id: string;
      ligand: string;
      affinity: number;
      confidence: number;
    }>;
  };
}

type JobUpdateCallback = (job: Job) => void;
type BatchUpdateCallback = (batch: Batch) => void;

class JobStore {
  private jobs = new Map<string, Job>();
  private batches = new Map<string, Batch>();
  private jobSubscriptions = new Map<string, Set<JobUpdateCallback>>();
  private batchSubscriptions = new Map<string, Set<BatchUpdateCallback>>();
  private pollingIntervals = new Map<string, NodeJS.Timeout>();
  
  // ===== JOB MANAGEMENT =====
  
  /**
   * Submit individual prediction and start monitoring
   */
  async submitPrediction(request: {
    protein_sequence: string;
    ligand_smiles: string;
    job_name: string;
    recycling_steps?: number;
    sampling_steps?: number;
    diffusion_samples?: number;
  }): Promise<Job> {
    try {
      const response = await apiClient.submitPrediction(request);
      
      const job: Job = {
        id: response.job_id,
        job_name: request.job_name,
        type: 'individual',
        status: 'submitted',
        progress: 0,
        created_at: response.created_at,
        parameters: {
          recycling_steps: request.recycling_steps,
          sampling_steps: request.sampling_steps,
          diffusion_samples: request.diffusion_samples
        }
      };
      
      this.jobs.set(job.id, job);
      this.startJobPolling(job.id);
      
      console.log(`✅ Individual prediction submitted: ${job.id}`);
      return job;
      
    } catch (error) {
      console.error('🚨 Failed to submit prediction:', error);
      throw error;
    }
  }
  
  /**
   * Submit batch prediction and start monitoring
   */
  async submitBatchPrediction(request: {
    protein_sequence: string;
    ligands: Array<{ name: string; smiles: string }>;
    batch_name: string;
    max_concurrent?: number;
    recycling_steps?: number;
    sampling_steps?: number;
    diffusion_samples?: number;
  }): Promise<Batch> {
    try {
      const response = await apiClient.submitBatchPrediction(request);
      
      const batch: Batch = {
        id: response.batch_id,
        batch_name: request.batch_name,
        status: 'submitted',
        progress: 0,
        total_jobs: response.total_jobs,
        completed_jobs: 0,
        failed_jobs: 0,
        created_at: response.created_at
      };
      
      this.batches.set(batch.id, batch);
      this.startBatchPolling(batch.id);
      
      console.log(`✅ Batch prediction submitted: ${batch.id} (${batch.total_jobs} jobs)`);
      return batch;
      
    } catch (error) {
      console.error('🚨 Failed to submit batch prediction:', error);
      throw error;
    }
  }
  
  // ===== POLLING AND MONITORING =====
  
  /**
   * Start polling job status
   */
  private startJobPolling(jobId: string) {
    if (this.pollingIntervals.has(jobId)) {
      return; // Already polling
    }
    
    const pollJob = async () => {
      try {
        const status = await apiClient.getJobStatus(jobId);
        this.updateJobFromStatus(status);
        
        // Stop polling if completed or failed
        if (status.status === 'completed' || status.status === 'failed') {
          this.stopJobPolling(jobId);
        }
      } catch (error) {
        console.error(`🚨 Job polling error (${jobId}):`, error);
      }
    };
    
    // Initial poll
    pollJob();
    
    // Set up interval polling
    const interval = setInterval(pollJob, 5000); // Poll every 5 seconds
    this.pollingIntervals.set(jobId, interval);
    
    console.log(`📡 Started polling job: ${jobId}`);
  }
  
  /**
   * Start polling batch status
   */
  private startBatchPolling(batchId: string) {
    if (this.pollingIntervals.has(batchId)) {
      return; // Already polling
    }
    
    const pollBatch = async () => {
      try {
        const status = await apiClient.getBatchStatus(batchId);
        this.updateBatchFromStatus(status);
        
        // Stop polling if completed or failed
        if (status.status === 'completed' || status.status === 'failed') {
          this.stopBatchPolling(batchId);
        }
      } catch (error) {
        console.error(`🚨 Batch polling error (${batchId}):`, error);
      }
    };
    
    // Initial poll
    pollBatch();
    
    // Set up interval polling
    const interval = setInterval(pollBatch, 10000); // Poll every 10 seconds for batches
    this.pollingIntervals.set(batchId, interval);
    
    console.log(`📡 Started polling batch: ${batchId}`);
  }
  
  /**
   * Stop job polling
   */
  private stopJobPolling(jobId: string) {
    const interval = this.pollingIntervals.get(jobId);
    if (interval) {
      clearInterval(interval);
      this.pollingIntervals.delete(jobId);
      console.log(`⏹️ Stopped polling job: ${jobId}`);
    }
  }
  
  /**
   * Stop batch polling
   */
  private stopBatchPolling(batchId: string) {
    const interval = this.pollingIntervals.get(batchId);
    if (interval) {
      clearInterval(interval);
      this.pollingIntervals.delete(batchId);
      console.log(`⏹️ Stopped polling batch: ${batchId}`);
    }
  }
  
  // ===== STATUS UPDATES =====
  
  /**
   * Update job from API status response
   */
  private updateJobFromStatus(status: JobStatusResponse) {
    const existingJob = this.jobs.get(status.job_id);
    if (!existingJob) {
      return; // Job not found in store
    }
    
    const updatedJob: Job = {
      ...existingJob,
      status: status.status,
      progress: status.progress,
      completed_at: status.completed_at,
      results: status.results ? {
        affinity: status.results.affinity,
        confidence: status.results.confidence,
        structure_url: status.results.structure_url,
        results_url: status.results.results_url
      } : undefined
    };
    
    this.jobs.set(status.job_id, updatedJob);
    this.notifyJobSubscribers(status.job_id, updatedJob);
  }
  
  /**
   * Update batch from API status response
   */
  private updateBatchFromStatus(status: BatchStatusResponse) {
    const existingBatch = this.batches.get(status.batch_id);
    if (!existingBatch) {
      return; // Batch not found in store
    }
    
    const updatedBatch: Batch = {
      ...existingBatch,
      status: status.status,
      progress: status.progress,
      completed_jobs: status.completed_jobs,
      failed_jobs: status.failed_jobs,
      completed_at: status.completed_at,
      results: status.results
    };
    
    this.batches.set(status.batch_id, updatedBatch);
    this.notifyBatchSubscribers(status.batch_id, updatedBatch);
  }
  
  // ===== SUBSCRIPTIONS =====
  
  /**
   * Subscribe to job updates
   */
  subscribeToJob(jobId: string, callback: JobUpdateCallback): () => void {
    if (!this.jobSubscriptions.has(jobId)) {
      this.jobSubscriptions.set(jobId, new Set());
    }
    
    this.jobSubscriptions.get(jobId)!.add(callback);
    
    // Return unsubscribe function
    return () => {
      const callbacks = this.jobSubscriptions.get(jobId);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.jobSubscriptions.delete(jobId);
        }
      }
    };
  }
  
  /**
   * Subscribe to batch updates
   */
  subscribeToBatch(batchId: string, callback: BatchUpdateCallback): () => void {
    if (!this.batchSubscriptions.has(batchId)) {
      this.batchSubscriptions.set(batchId, new Set());
    }
    
    this.batchSubscriptions.get(batchId)!.add(callback);
    
    // Return unsubscribe function
    return () => {
      const callbacks = this.batchSubscriptions.get(batchId);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.batchSubscriptions.delete(batchId);
        }
      }
    };
  }
  
  /**
   * Notify job subscribers
   */
  private notifyJobSubscribers(jobId: string, job: Job) {
    const callbacks = this.jobSubscriptions.get(jobId);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(job);
        } catch (error) {
          console.error('🚨 Job callback error:', error);
        }
      });
    }
  }
  
  /**
   * Notify batch subscribers
   */
  private notifyBatchSubscribers(batchId: string, batch: Batch) {
    const callbacks = this.batchSubscriptions.get(batchId);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(batch);
        } catch (error) {
          console.error('🚨 Batch callback error:', error);
        }
      });
    }
  }
  
  // ===== GETTER METHODS =====
  
  /**
   * Get job by ID
   */
  getJob(jobId: string): Job | undefined {
    return this.jobs.get(jobId);
  }
  
  /**
   * Get batch by ID
   */
  getBatch(batchId: string): Batch | undefined {
    return this.batches.get(batchId);
  }
  
  /**
   * Get all jobs
   */
  getAllJobs(): Job[] {
    return Array.from(this.jobs.values()).sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }
  
  /**
   * Get all batches
   */
  getAllBatches(): Batch[] {
    return Array.from(this.batches.values()).sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }
  
  // ===== CLEANUP =====
  
  /**
   * Clean up all polling intervals
   */
  cleanup() {
    this.pollingIntervals.forEach((interval) => {
      clearInterval(interval);
    });
    this.pollingIntervals.clear();
    this.jobSubscriptions.clear();
    this.batchSubscriptions.clear();
    
    console.log('🧹 JobStore cleaned up');
  }
}

// Global singleton instance
export const jobStore = new JobStore();

// Default export
export default jobStore;