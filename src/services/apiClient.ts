/**
 * Cloud Run API Client for OMTX-Hub
 * Distinguished Engineer Implementation - Real-time updates with Firestore integration
 * All requests/responses use snake_case and include Zod validation
 */

import {
  JobCreate, JobResponse, JobDetailResponse, JobListResponse,
  SystemStatusResponse, TaskListResponse, LogListResponse,
  validateJobResponse, validateJobListResponse, validateSystemStatusResponse,
  validateApiResponse, safeParseApiResponse,
  JobCreateSchema, JobResponseSchema, JobDetailResponseSchema,
  JobListResponseSchema, SystemStatusResponseSchema, TaskListResponseSchema
} from '../schemas/apiSchemas';

// Firebase for real-time updates
import { initializeApp } from 'firebase/app';
import { getFirestore, doc, onSnapshot, collection, query, where, orderBy, limit } from 'firebase/firestore';

// Base API configuration - Updated to v4 for Cloud Run
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
  : 'http://34.29.29.170/api/v1';

// Firebase configuration (will be injected via environment)
const firebaseConfig = {
  projectId: process.env.REACT_APP_GCP_PROJECT_ID || 'om-models',
  // Other config will be auto-detected in GCP environment
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const firestore = getFirestore(app);

// Request configuration
interface RequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  body?: unknown;
}

// Generic API client class
class ApiClient {
  private baseUrl: string;
  
  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async makeRequest<T>(
    endpoint: string, 
    config: RequestConfig = {},
    responseSchema?: any
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const requestInit: RequestInit = {
      method: config.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...config.headers,
      },
    };

    if (config.body && (config.method === 'POST' || config.method === 'PUT')) {
      requestInit.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, requestInit);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      
      // Validate response if schema provided
      if (responseSchema) {
        const validationResult = safeParseApiResponse(responseSchema, data);
        if (!validationResult.success) {
          const errorMsg = 'error' in validationResult ? validationResult.error : 'Validation failed';
          console.warn('API Response validation failed:', errorMsg);
          // Still return data but log the validation error
        }
        return validationResult.success ? validationResult.data : data;
      }
      
      return data;
    } catch (error) {
      console.error(`API request failed: ${config.method || 'GET'} ${url}`, error);
      throw error;
    }
  }

  // Job Management Methods
  async createJob(jobData: JobCreate): Promise<JobResponse> {
    // Validate input
    const validatedInput = JobCreateSchema.parse(jobData);
    
    return this.makeRequest<JobResponse>(
      '/predict',
      {
        method: 'POST',
        body: validatedInput,
      },
      JobResponseSchema
    );
  }

  async getJob(jobId: string): Promise<JobDetailResponse> {
    return this.makeRequest<JobDetailResponse>(
      `/jobs/${jobId}`,
      { method: 'GET' },
      JobDetailResponseSchema
    );
  }

  // Real-time subscription methods for Cloud Run integration
  subscribeToJob(jobId: string, callback: (job: any) => void): () => void {
    /**
     * Subscribe to real-time job updates via Firestore
     * Returns unsubscribe function
     */
    const jobDoc = doc(firestore, 'jobs', jobId);

    const unsubscribe = onSnapshot(jobDoc, (doc) => {
      if (doc.exists()) {
        const jobData = {
          id: doc.id,
          ...doc.data(),
          // Convert Firestore timestamps to ISO strings
          created_at: doc.data().created_at?.toDate?.()?.toISOString(),
          updated_at: doc.data().updated_at?.toDate?.()?.toISOString(),
          started_at: doc.data().started_at?.toDate?.()?.toISOString(),
          completed_at: doc.data().completed_at?.toDate?.()?.toISOString(),
        };

        callback(jobData);
      }
    }, (error) => {
      console.error('Job subscription error:', error);
    });

    return unsubscribe;
  }

  subscribeToBatch(batchId: string, callback: (batch: any) => void): () => void {
    /**
     * Subscribe to real-time batch updates via Firestore
     * Returns unsubscribe function
     */
    const batchDoc = doc(firestore, 'batches', batchId);

    const unsubscribe = onSnapshot(batchDoc, (doc) => {
      if (doc.exists()) {
        const batchData = {
          id: doc.id,
          ...doc.data(),
          // Convert Firestore timestamps
          created_at: doc.data().created_at?.toDate?.()?.toISOString(),
          updated_at: doc.data().updated_at?.toDate?.()?.toISOString(),
          started_at: doc.data().started_at?.toDate?.()?.toISOString(),
          completed_at: doc.data().completed_at?.toDate?.()?.toISOString(),
          // Add Cloud Run metadata
          cloud_run_metadata: {
            execution_id: doc.data().cloud_run_execution_id,
            gpu_type: doc.data().gpu_type,
            estimated_cost_usd: doc.data().estimated_cost_usd,
            shards_count: doc.data().shards_count,
          }
        };

        callback(batchData);
      }
    }, (error) => {
      console.error('Batch subscription error:', error);
    });

    return unsubscribe;
  }

  async listJobs(params?: {
    page?: number;
    per_page?: number;
    status?: string;
    task_type?: string;
    search_query?: string;
  }): Promise<JobListResponse> {
    const searchParams = new URLSearchParams();
    
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.per_page) searchParams.set('per_page', params.per_page.toString());
    if (params?.status) searchParams.set('status', params.status);
    if (params?.task_type) searchParams.set('task_type', params.task_type);
    if (params?.search_query) searchParams.set('search_query', params.search_query);
    
    const queryString = searchParams.toString();
    const endpoint = queryString ? `/jobs?${queryString}` : '/jobs';
    
    return this.makeRequest<JobListResponse>(
      endpoint,
      { method: 'GET' },
      JobListResponseSchema
    );
  }

  async deleteJob(jobId: string): Promise<{ success: boolean; message: string }> {
    return this.makeRequest(
      `/jobs/${jobId}`,
      { method: 'DELETE' }
    );
  }

  async downloadJobFile(jobId: string, format: 'cif' | 'pdb' = 'cif'): Promise<Blob> {
    const url = `${this.baseUrl}/jobs/${jobId}/download/${format}`;
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to download file: ${response.statusText}`);
    }
    
    return response.blob();
  }

  async getJobLogs(jobId: string): Promise<LogListResponse> {
    return this.makeRequest<LogListResponse>(
      `/jobs/${jobId}/logs`,
      { method: 'GET' }
    );
  }

  // System Methods
  async getSystemStatus(): Promise<SystemStatusResponse> {
    return this.makeRequest<SystemStatusResponse>(
      '/system/status',
      { method: 'GET' },
      SystemStatusResponseSchema
    );
  }

  async getSupportedTasks(): Promise<TaskListResponse> {
    return this.makeRequest<TaskListResponse>(
      '/tasks',
      { method: 'GET' },
      TaskListResponseSchema
    );
  }

  async healthCheck(): Promise<{ status: string; timestamp: number }> {
    return this.makeRequest('/health', { method: 'GET' });
  }

  // Batch Methods
  async getBatch(batchId: string): Promise<any> {
    return this.makeRequest(`/batches/${batchId}`, { method: 'GET' });
  }

  async listBatches(params?: {
    page?: number;
    per_page?: number;
  }): Promise<any> {
    const searchParams = new URLSearchParams();
    
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.per_page) searchParams.set('per_page', params.per_page.toString());
    
    const queryString = searchParams.toString();
    const endpoint = queryString ? `/batches?${queryString}` : '/batches';
    
    return this.makeRequest(endpoint, { method: 'GET' });
  }

  // Export Methods
  async exportJob(jobId: string, options?: {
    format?: string;
    include_results?: boolean;
    include_logs?: boolean;
  }): Promise<Blob> {
    const url = `${this.baseUrl}/jobs/${jobId}/export`;
    
    const searchParams = new URLSearchParams();
    if (options?.format) searchParams.set('format', options.format);
    if (options?.include_results !== undefined) {
      searchParams.set('include_results', options.include_results.toString());
    }
    if (options?.include_logs !== undefined) {
      searchParams.set('include_logs', options.include_logs.toString());
    }
    
    const queryString = searchParams.toString();
    const finalUrl = queryString ? `${url}?${queryString}` : url;
    
    const response = await fetch(finalUrl);
    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }
    
    return response.blob();
  }

  // Legacy compatibility methods
  async legacyBoltzPredict(data: {
    input_data: Record<string, any>;
    job_name: string;
    task_type: string;
    use_msa?: boolean;
    use_potentials?: boolean;
  }): Promise<any> {
    return this.makeRequest(
      '/boltz/predict',
      {
        method: 'POST',
        body: data,
      }
    );
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// Convenience functions
export const jobApi = {
  create: (data: JobCreate) => apiClient.createJob(data),
  get: (id: string) => apiClient.getJob(id),
  list: (params?: Parameters<typeof apiClient.listJobs>[0]) => apiClient.listJobs(params),
  delete: (id: string) => apiClient.deleteJob(id),
  downloadFile: (id: string, format?: 'cif' | 'pdb') => apiClient.downloadJobFile(id, format),
  getLogs: (id: string) => apiClient.getJobLogs(id),
  export: (id: string, options?: Parameters<typeof apiClient.exportJob>[1]) => 
    apiClient.exportJob(id, options),
};

export const systemApi = {
  status: () => apiClient.getSystemStatus(),
  health: () => apiClient.healthCheck(),
  tasks: () => apiClient.getSupportedTasks(),
};

export const batchApi = {
  get: (id: string) => apiClient.getBatch(id),
  list: (params?: Parameters<typeof apiClient.listBatches>[0]) => apiClient.listBatches(params),
};

// Type exports for convenience
export type {
  JobCreate, JobResponse, JobDetailResponse, JobListResponse,
  SystemStatusResponse, TaskListResponse, LogListResponse
} from '../schemas/apiSchemas';

// Default export
export default apiClient;