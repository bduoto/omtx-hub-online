/**
 * Job Service for OMTX-Hub
 * Handles API communication for job management
 */

export interface Job {
  id: string;
  name: string;
  type: string;
  status: 'completed' | 'failed' | 'running' | 'pending';
  submitted: string;
  model_name: string;
  created_at: string;
  completed_at?: string;
  error_message?: string;
  output_data?: any;
  input_data?: any;
  batch_id?: string;
  ligand_name?: string;
}

export interface JobBatch {
  batch_id: string;
  batch_name: string;
  status: string;
  model_name: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  created_at: string;
  completed_at?: string;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  per_page: number;
}

export interface BatchListResponse {
  batches: JobBatch[];
  total: number;
  page: number;
  per_page: number;
}

class JobService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = 'http://localhost:8000';
  }

  /**
   * Get all jobs with pagination
   */
  async getJobs(page: number = 1, perPage: number = 50): Promise<JobListResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/jobs?page=${page}&per_page=${perPage}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching jobs:', error);
      throw error;
    }
  }

  /**
   * Get a specific job by ID
   */
  async getJob(jobId: string): Promise<Job> {
    try {
      const response = await fetch(`${this.baseUrl}/jobs/${jobId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching job:', error);
      throw error;
    }
  }

  /**
   * Get all batches with pagination
   */
  async getBatches(page: number = 1, perPage: number = 50): Promise<BatchListResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/batches?page=${page}&per_page=${perPage}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching batches:', error);
      throw error;
    }
  }

  /**
   * Get a specific batch by ID
   */
  async getBatch(batchId: string): Promise<JobBatch> {
    try {
      const response = await fetch(`${this.baseUrl}/batches/${batchId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching batch:', error);
      throw error;
    }
  }

  /**
   * Get jobs in a specific batch
   */
  async getBatchJobs(batchId: string): Promise<{ batch_id: string; jobs: Job[] }> {
    try {
      const response = await fetch(`${this.baseUrl}/batches/${batchId}/jobs`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching batch jobs:', error);
      throw error;
    }
  }

  /**
   * Download structure file for a job
   */
  async downloadStructure(jobId: string, format: 'cif' | 'pdb' | 'mmcif' = 'cif'): Promise<Blob> {
    try {
      const response = await fetch(`${this.baseUrl}/jobs/${jobId}/download-structure?format=${format}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.blob();
    } catch (error) {
      console.error('Error downloading structure:', error);
      throw error;
    }
  }

  /**
   * Export job data
   */
  async exportJobData(jobId: string, format: string = 'json', includeStructure: boolean = true): Promise<Blob> {
    try {
      const response = await fetch(`${this.baseUrl}/jobs/${jobId}/export?format=${format}&include_structure=${includeStructure}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.blob();
    } catch (error) {
      console.error('Error exporting job data:', error);
      throw error;
    }
  }

  /**
   * Get quality report for a job
   */
  async getQualityReport(jobId: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/jobs/${jobId}/quality-report`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching quality report:', error);
      throw error;
    }
  }

  /**
   * Map database status to UI status
   */
  mapStatus(dbStatus: string): 'completed' | 'failed' | 'running' | 'pending' {
    switch (dbStatus.toLowerCase()) {
      case 'completed':
        return 'completed';
      case 'failed':
        return 'failed';
      case 'running':
        return 'running';
      case 'pending':
        return 'pending';
      default:
        return 'pending';
    }
  }

  /**
   * Map UI status to display status
   */
  mapDisplayStatus(status: string): 'Complete' | 'Failed' | 'Running' | 'In Progress' {
    switch (status) {
      case 'completed':
        return 'Complete';
      case 'failed':
        return 'Failed';
      case 'running':
        return 'Running';
      case 'pending':
        return 'In Progress';
      default:
        return 'In Progress';
    }
  }

  /**
   * Format job name for display
   */
  formatJobName(job: Job): string {
    if (job.batch_id && job.ligand_name) {
      return `${job.ligand_name}`;
    }
    
    // Extract task type from input data
    const taskType = job.input_data?.task_type || 'boltz2';
    const modelName = job.model_name || 'boltz2';
    
    // Create a descriptive name based on task type
    const taskNames: Record<string, string> = {
      'protein_structure': 'protein-structure',
      'protein_complex': 'protein-complex',
      'protein_ligand_binding': 'protein-ligand',
      'binding_site_prediction': 'binding-sites',
      'variant_comparison': 'variant-analysis',
      'drug_discovery': 'drug-discovery'
    };
    
    const taskName = taskNames[taskType] || taskType;
    return `omtx-${taskName}`;
  }

  /**
   * Get recent jobs (last 10 completed)
   */
  async getRecentJobs(): Promise<Job[]> {
    try {
      const response = await this.getJobs(1, 10);
      return response.jobs
        .filter(job => job.status === 'completed')
        .slice(0, 10);
    } catch (error) {
      console.error('Error fetching recent jobs:', error);
      return [];
    }
  }
}

export const jobService = new JobService();