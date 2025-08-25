/**
 * Simplified API Service - No Authentication Required
 * 
 * Company API Gateway handles all authentication upstream.
 * This service focuses purely on API communication with the Cloud Run backend.
 */

interface ApiHeaders {
  'Content-Type': string;
  'X-User-Id'?: string;
  [key: string]: string | undefined;
}

class ApiService {
  private userId: string = 'default';
  private baseUrl: string;
  
  constructor() {
    // Get API base URL from environment or default to localhost for development
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080';
    
    // Try to get user ID from URL parameters (set by API gateway)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('userId')) {
      this.userId = urlParams.get('userId')!;
    }
    
    console.log('🌐 ApiService initialized', {
      baseUrl: this.baseUrl,
      userId: this.userId
    });
  }
  
  private getHeaders(): ApiHeaders {
    return {
      'Content-Type': 'application/json',
      'X-User-Id': this.userId, // Optional - backend defaults to "default"
    };
  }
  
  private getApiUrl(endpoint: string): string {
    // Use v1 API for all endpoints
    return `${this.baseUrl}/api/v1${endpoint}`;
  }
  
  async makeRequest(url: string, options: RequestInit = {}): Promise<Response> {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      }
    });
    
    // Log any errors for debugging
    if (!response.ok) {
      console.error(`🚨 API Error: ${response.status} ${response.statusText} for ${url}`);
    }
    
    return response;
  }
  
  // HTTP method helpers
  async get(url: string): Promise<Response> {
    return this.makeRequest(url, { method: 'GET' });
  }
  
  async post(url: string, data: any): Promise<Response> {
    return this.makeRequest(url, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }
  
  // ===== BOLTZ-2 PREDICTION METHODS =====
  
  async submitPrediction(predictionData: {
    protein_sequence: string;
    ligand_smiles: string;
    job_name: string;
    recycling_steps?: number;
    sampling_steps?: number;
    diffusion_samples?: number;
  }): Promise<Response> {
    const payload = {
      model: 'boltz2',
      ...predictionData,
      user_id: this.userId
    };
    
    return this.post(this.getApiUrl('/predict'), payload);
  }
  
  async submitBatchPrediction(batchData: {
    protein_sequence: string;
    ligands: Array<{ name: string; smiles: string }>;
    batch_name: string;
    max_concurrent?: number;
    recycling_steps?: number;
    sampling_steps?: number;
    diffusion_samples?: number;
  }): Promise<Response> {
    const payload = {
      model: 'boltz2',
      ...batchData,
      user_id: this.userId
    };
    
    return this.post(this.getApiUrl('/predict/batch'), payload);
  }
  
  // ===== JOB STATUS AND RESULTS =====
  
  async getJobStatus(jobId: string): Promise<Response> {
    return this.get(this.getApiUrl(`/jobs/${jobId}`));
  }
  
  async getBatchStatus(batchId: string): Promise<Response> {
    return this.get(this.getApiUrl(`/batches/${batchId}`));
  }
  
  async downloadJobStructure(jobId: string): Promise<Response> {
    return this.get(this.getApiUrl(`/jobs/${jobId}/structure`));
  }
  
  async downloadJobResults(jobId: string): Promise<Response> {
    return this.get(this.getApiUrl(`/jobs/${jobId}/results`));
  }
  
  // ===== HEALTH AND MONITORING =====
  
  async getHealthStatus(): Promise<Response> {
    return this.get(`${this.baseUrl}/health`);
  }
  
  async getApiDocs(): string {
    return `${this.baseUrl}/docs`;
  }
  
  // ===== USER MANAGEMENT (SIMPLIFIED) =====
  
  setUserId(userId: string) {
    this.userId = userId;
    console.log(`👤 User ID set to: ${userId}`);
  }
  
  getUserId(): string {
    return this.userId;
  }
  
  getUserInfo() {
    return {
      userId: this.userId,
      authenticated: true, // Always authenticated via API gateway
      authProvider: 'api_gateway'
    };
  }
  
  // ===== UTILITY METHODS =====
  
  isHealthy(): Promise<boolean> {
    return this.getHealthStatus()
      .then(response => response.ok)
      .catch(() => false);
  }
  
  getBaseUrl(): string {
    return this.baseUrl;
  }
  
  // Update base URL (for switching environments)
  setBaseUrl(newBaseUrl: string) {
    this.baseUrl = newBaseUrl;
    console.log(`🔄 API base URL updated to: ${newBaseUrl}`);
  }
}

// Global singleton instance
export const apiService = new ApiService();

// Export types for TypeScript
export type { ApiHeaders };

// Default export
export default apiService;