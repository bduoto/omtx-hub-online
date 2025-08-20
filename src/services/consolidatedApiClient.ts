/**
 * Consolidated OMTX-Hub API Client v1
 * Clean, minimal client for the consolidated 11-endpoint API
 * Supports Boltz-2, RFAntibody, and Chai-1 predictions
 */

// API Types
export type Model = 'boltz2' | 'rfantibody' | 'chai1';
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';
export type BatchStatus = 'pending' | 'running' | 'completed' | 'failed';
export type Priority = 'low' | 'normal' | 'high';
export type FileType = 'cif' | 'pdb' | 'json';
export type ExportFormat = 'csv' | 'json' | 'zip';

export interface PredictionRequest {
  model: Model;
  protein_sequence: string;
  ligand_smiles?: string; // Required for Boltz-2
  job_name: string;
  user_id?: string;
  parameters?: Record<string, any>;
}

export interface BatchPredictionRequest {
  model: Model;
  protein_sequence: string;
  ligands: Array<{ name: string; smiles: string }>;
  batch_name: string;
  user_id?: string;
  max_concurrent?: number;
  priority?: Priority;
  parameters?: Record<string, any>;
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  model: string;
  job_name: string;
  created_at: string;
  updated_at: string;
  estimated_completion_seconds?: number;
  results?: Record<string, any>;
  error_message?: string;
  download_links?: Record<string, string>;
}

export interface BatchResponse {
  batch_id: string;
  status: BatchStatus;
  model: string;
  batch_name: string;
  created_at: string;
  updated_at: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  running_jobs: number;
  summary?: Record<string, any>;
  export_links?: Record<string, string>;
}

export interface JobListResponse {
  jobs: JobResponse[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface BatchListResponse {
  batches: BatchResponse[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface SystemStatusResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  components: {
    database: string;
    storage: string;
  };
  statistics: Record<string, any>;
  api_version: string;
}

/**
 * Clean API Client for OMTX-Hub v1
 * 11 endpoints total - no version confusion
 */
export class ConsolidatedApiClient {
  private baseUrl: string;
  private defaultUserId: string;

  constructor(
    baseUrl: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    defaultUserId: string = 'default'
  ) {
    this.baseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    this.defaultUserId = defaultUserId;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}/api/v1${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    return response.json();
  }

  // ===== PREDICTION ENDPOINTS =====

  /**
   * Submit single prediction job
   * Supports Boltz-2, RFAntibody, and Chai-1
   */
  async submitPrediction(request: PredictionRequest): Promise<JobResponse> {
    return this.request<JobResponse>('/predict', {
      method: 'POST',
      body: JSON.stringify({
        ...request,
        user_id: request.user_id || this.defaultUserId,
      }),
    });
  }

  /**
   * Submit batch prediction job
   * Process multiple ligands against one protein
   */
  async submitBatchPrediction(request: BatchPredictionRequest): Promise<BatchResponse> {
    return this.request<BatchResponse>('/predict/batch', {
      method: 'POST',
      body: JSON.stringify({
        ...request,
        user_id: request.user_id || this.defaultUserId,
      }),
    });
  }

  // ===== JOB MANAGEMENT ENDPOINTS =====

  /**
   * Get job status and results
   */
  async getJob(jobId: string): Promise<JobResponse> {
    return this.request<JobResponse>(`/jobs/${jobId}`);
  }

  /**
   * List user jobs with pagination
   */
  async listJobs(options: {
    page?: number;
    limit?: number;
    status?: JobStatus;
    model?: Model;
    userId?: string;
  } = {}): Promise<JobListResponse> {
    const params = new URLSearchParams();
    
    if (options.page) params.set('page', options.page.toString());
    if (options.limit) params.set('limit', options.limit.toString());
    if (options.status) params.set('status', options.status);
    if (options.model) params.set('model', options.model);
    params.set('user_id', options.userId || this.defaultUserId);

    const queryString = params.toString();
    const endpoint = queryString ? `/jobs?${queryString}` : '/jobs';
    
    return this.request<JobListResponse>(endpoint);
  }

  /**
   * Delete a job
   */
  async deleteJob(jobId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/jobs/${jobId}`, {
      method: 'DELETE',
    });
  }

  // ===== BATCH MANAGEMENT ENDPOINTS =====

  /**
   * Get batch status and results
   */
  async getBatch(batchId: string): Promise<BatchResponse> {
    return this.request<BatchResponse>(`/batches/${batchId}`);
  }

  /**
   * List user batches with pagination
   */
  async listBatches(options: {
    page?: number;
    limit?: number;
    status?: BatchStatus;
    model?: Model;
    userId?: string;
  } = {}): Promise<BatchListResponse> {
    const params = new URLSearchParams();
    
    if (options.page) params.set('page', options.page.toString());
    if (options.limit) params.set('limit', options.limit.toString());
    if (options.status) params.set('status', options.status);
    if (options.model) params.set('model', options.model);
    params.set('user_id', options.userId || this.defaultUserId);

    const queryString = params.toString();
    const endpoint = queryString ? `/batches?${queryString}` : '/batches';
    
    return this.request<BatchListResponse>(endpoint);
  }

  /**
   * Delete a batch
   */
  async deleteBatch(batchId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/batches/${batchId}`, {
      method: 'DELETE',
    });
  }

  // ===== FILE DOWNLOAD ENDPOINTS =====

  /**
   * Download job result file
   */
  async downloadJobFile(jobId: string, fileType: FileType): Promise<Blob> {
    const url = `${this.baseUrl}/api/v1/jobs/${jobId}/files/${fileType}`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`);
    }
    
    return response.blob();
  }

  /**
   * Export batch results
   */
  async exportBatch(batchId: string, format: ExportFormat): Promise<Blob> {
    const url = `${this.baseUrl}/api/v1/batches/${batchId}/export?format=${format}`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }
    
    return response.blob();
  }

  // ===== SYSTEM ENDPOINTS =====

  /**
   * Get system health status
   */
  async getSystemStatus(): Promise<SystemStatusResponse> {
    return this.request<SystemStatusResponse>('/system/status');
  }

  /**
   * Simple health check
   */
  async healthCheck(): Promise<{ status: string; api_version: string; available_models: Model[] }> {
    const url = `${this.baseUrl}/health`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }
    
    return response.json();
  }

  // ===== CONVENIENCE METHODS =====

  /**
   * Submit Boltz-2 protein-ligand prediction
   */
  async submitBoltz2Prediction(
    proteinSequence: string,
    ligandSmiles: string,
    jobName: string,
    parameters?: Record<string, any>
  ): Promise<JobResponse> {
    return this.submitPrediction({
      model: 'boltz2',
      protein_sequence: proteinSequence,
      ligand_smiles: ligandSmiles,
      job_name: jobName,
      parameters,
    });
  }

  /**
   * Submit Boltz-2 batch screening
   */
  async submitBoltz2BatchScreening(
    proteinSequence: string,
    ligands: Array<{ name: string; smiles: string }>,
    batchName: string,
    parameters?: Record<string, any>
  ): Promise<BatchResponse> {
    return this.submitBatchPrediction({
      model: 'boltz2',
      protein_sequence: proteinSequence,
      ligands,
      batch_name: batchName,
      parameters,
    });
  }

  /**
   * Submit RFAntibody design
   */
  async submitRFAntibodyDesign(
    proteinSequence: string,
    jobName: string,
    parameters?: Record<string, any>
  ): Promise<JobResponse> {
    return this.submitPrediction({
      model: 'rfantibody',
      protein_sequence: proteinSequence,
      job_name: jobName,
      parameters,
    });
  }

  /**
   * Submit Chai-1 structure prediction
   */
  async submitChai1Prediction(
    proteinSequence: string,
    jobName: string,
    parameters?: Record<string, any>
  ): Promise<JobResponse> {
    return this.submitPrediction({
      model: 'chai1',
      protein_sequence: proteinSequence,
      job_name: jobName,
      parameters,
    });
  }

  /**
   * Wait for job completion (polling)
   */
  async waitForJobCompletion(
    jobId: string,
    timeoutMs: number = 300000, // 5 minutes
    pollIntervalMs: number = 5000 // 5 seconds
  ): Promise<JobResponse> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeoutMs) {
      const job = await this.getJob(jobId);
      
      if (job.status === 'completed' || job.status === 'failed') {
        return job;
      }
      
      await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
    }
    
    throw new Error(`Job ${jobId} timed out after ${timeoutMs}ms`);
  }

  /**
   * Wait for batch completion (polling)
   */
  async waitForBatchCompletion(
    batchId: string,
    timeoutMs: number = 1800000, // 30 minutes
    pollIntervalMs: number = 10000 // 10 seconds
  ): Promise<BatchResponse> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeoutMs) {
      const batch = await this.getBatch(batchId);
      
      if (batch.status === 'completed' || batch.status === 'failed') {
        return batch;
      }
      
      await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
    }
    
    throw new Error(`Batch ${batchId} timed out after ${timeoutMs}ms`);
  }
}

// Create singleton instance
export const apiClient = new ConsolidatedApiClient();

// Export commonly used functions
export const {
  submitPrediction,
  submitBatchPrediction,
  getJob,
  listJobs,
  getBatch,
  listBatches,
  downloadJobFile,
  exportBatch,
  healthCheck,
  submitBoltz2Prediction,
  submitBoltz2BatchScreening,
  submitRFAntibodyDesign,
  submitChai1Prediction,
} = apiClient;

export default apiClient;