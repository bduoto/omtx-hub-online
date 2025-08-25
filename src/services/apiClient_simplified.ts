/**
 * Simplified API Client for OMTX-Hub Cloud Run Native
 * 
 * No authentication required - handled by company API gateway.
 * Direct integration with Cloud Run backend.
 */

import { apiService } from './apiService';

// TypeScript interfaces for type safety
export interface PredictionRequest {
  protein_sequence: string;
  ligand_smiles: string;
  job_name: string;
  recycling_steps?: number;
  sampling_steps?: number;
  diffusion_samples?: number;
}

export interface BatchPredictionRequest {
  protein_sequence: string;
  ligands: Array<{ name: string; smiles: string }>;
  batch_name: string;
  max_concurrent?: number;
  recycling_steps?: number;
  sampling_steps?: number;
  diffusion_samples?: number;
}

export interface JobResponse {
  job_id: string;
  status: string;
  message: string;
  created_at: string;
  estimated_completion_time?: string;
}

export interface BatchResponse {
  batch_id: string;
  status: string;
  message: string;
  total_jobs: number;
  created_at: string;
  estimated_completion_time?: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'submitted' | 'running' | 'completed' | 'failed';
  progress: number;
  message: string;
  created_at: string;
  completed_at?: string;
  results?: {
    affinity: number;
    confidence: number;
    structure_url: string;
    results_url: string;
  };
  parameters: Record<string, any>;
}

export interface BatchStatusResponse {
  batch_id: string;
  status: 'submitted' | 'running' | 'completed' | 'failed';
  progress: number;
  message: string;
  created_at: string;
  completed_at?: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  results?: {
    best_affinity: number;
    average_affinity: number;
    results_csv: string;
    individual_jobs: Array<{
      job_id: string;
      ligand: string;
      affinity: number;
      confidence: number;
    }>;
  };
}

class ApiClient {
  
  // ===== PREDICTION METHODS =====
  
  /**
   * Submit individual Boltz-2 prediction
   */
  async submitPrediction(request: PredictionRequest): Promise<JobResponse> {
    try {
      const response = await apiService.submitPrediction(request);
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Prediction submission failed: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('🚨 Submit prediction error:', error);
      throw error;
    }
  }
  
  /**
   * Submit batch Boltz-2 predictions
   */
  async submitBatchPrediction(request: BatchPredictionRequest): Promise<BatchResponse> {
    try {
      const response = await apiService.submitBatchPrediction(request);
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Batch submission failed: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('🚨 Submit batch prediction error:', error);
      throw error;
    }
  }
  
  // ===== STATUS METHODS =====
  
  /**
   * Get job status and results
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    try {
      const response = await apiService.getJobStatus(jobId);
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Get job status failed: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`🚨 Get job status error (${jobId}):`, error);
      throw error;
    }
  }
  
  /**
   * Get batch status and results
   */
  async getBatchStatus(batchId: string): Promise<BatchStatusResponse> {
    try {
      const response = await apiService.getBatchStatus(batchId);
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Get batch status failed: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`🚨 Get batch status error (${batchId}):`, error);
      throw error;
    }
  }
  
  // ===== DOWNLOAD METHODS =====
  
  /**
   * Download job structure file
   */
  async downloadJobStructure(jobId: string): Promise<Blob> {
    try {
      const response = await apiService.downloadJobStructure(jobId);
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Download structure failed: ${error}`);
      }
      
      return await response.blob();
    } catch (error) {
      console.error(`🚨 Download structure error (${jobId}):`, error);
      throw error;
    }
  }
  
  /**
   * Download job results JSON
   */
  async downloadJobResults(jobId: string): Promise<any> {
    try {
      const response = await apiService.downloadJobResults(jobId);
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Download results failed: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`🚨 Download results error (${jobId}):`, error);
      throw error;
    }
  }
  
  // ===== HEALTH AND UTILITY METHODS =====
  
  /**
   * Check API health
   */
  async getHealthStatus(): Promise<{
    status: string;
    timestamp: string;
    architecture: string;
    gpu_status: string;
    gpu_memory_gb: number;
    models: string[];
    ready_for_predictions: boolean;
  }> {
    try {
      const response = await apiService.getHealthStatus();
      
      if (!response.ok) {
        throw new Error('Health check failed');
      }
      
      return await response.json();
    } catch (error) {
      console.error('🚨 Health check error:', error);
      throw error;
    }
  }
  
  /**
   * Check if API is available
   */
  async isHealthy(): Promise<boolean> {
    try {
      await this.getHealthStatus();
      return true;
    } catch {
      return false;
    }
  }
  
  // ===== POLLING HELPERS =====
  
  /**
   * Poll job status until completion
   */
  async pollJobUntilComplete(
    jobId: string,
    onUpdate?: (status: JobStatusResponse) => void,
    intervalMs: number = 5000,
    timeoutMs: number = 300000 // 5 minutes
  ): Promise<JobStatusResponse> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeoutMs) {
      try {
        const status = await this.getJobStatus(jobId);
        
        if (onUpdate) {
          onUpdate(status);
        }
        
        if (status.status === 'completed' || status.status === 'failed') {
          return status;
        }
        
        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, intervalMs));
        
      } catch (error) {
        console.error(`🚨 Polling error for job ${jobId}:`, error);
        throw error;
      }
    }
    
    throw new Error(`Job ${jobId} polling timed out after ${timeoutMs}ms`);
  }
  
  /**
   * Poll batch status until completion
   */
  async pollBatchUntilComplete(
    batchId: string,
    onUpdate?: (status: BatchStatusResponse) => void,
    intervalMs: number = 10000, // Longer interval for batches
    timeoutMs: number = 1800000 // 30 minutes
  ): Promise<BatchStatusResponse> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeoutMs) {
      try {
        const status = await this.getBatchStatus(batchId);
        
        if (onUpdate) {
          onUpdate(status);
        }
        
        if (status.status === 'completed' || status.status === 'failed') {
          return status;
        }
        
        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, intervalMs));
        
      } catch (error) {
        console.error(`🚨 Polling error for batch ${batchId}:`, error);
        throw error;
      }
    }
    
    throw new Error(`Batch ${batchId} polling timed out after ${timeoutMs}ms`);
  }
  
  // ===== UTILITY METHODS =====
  
  getApiUrl(): string {
    return apiService.getBaseUrl();
  }
  
  getApiDocsUrl(): string {
    return apiService.getApiDocs();
  }
  
  setUserId(userId: string) {
    apiService.setUserId(userId);
  }
  
  getUserId(): string {
    return apiService.getUserId();
  }
}

// Global singleton instance
export const apiClient = new ApiClient();

// Default export
export default apiClient;