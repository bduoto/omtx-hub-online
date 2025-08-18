/**
 * Model Service for dynamic model discovery
 * Provides API integration for model registry
 */

export interface ModelCapabilities {
  supported_tasks: string[];
  input_formats: string[];
  output_formats: string[];
  max_sequence_length?: number;
  max_ligands?: number;
  supports_batch: boolean;
}

export interface ModelResources {
  gpu_required: boolean;
  gpu_memory_gb?: number;
  cpu_cores?: number;
  memory_gb?: number;
  estimated_time_seconds?: number;
}

export interface ModelDefinition {
  id: string;
  name: string;
  description: string;
  version: string;
  provider: string;
  capabilities: ModelCapabilities;
  resources: ModelResources;
  endpoint_url?: string;
  documentation_url?: string;
  paper_url?: string;
  license?: string;
  tags: string[];
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ModelListResponse {
  models: ModelDefinition[];
  total: number;
  active: number;
  inactive: number;
}

export interface TaskDefinition {
  id: string;
  name: string;
  description: string;
}

export interface ProviderDefinition {
  id: string;
  name: string;
  description: string;
}

export interface TaskSupportResponse {
  task_type: string;
  supported_models: ModelDefinition[];
  count: number;
}

export interface ModelStatistics {
  total_models: number;
  active_models: number;
  inactive_models: number;
  provider_distribution: Record<string, number>;
  task_support: Record<string, number>;
}

class ModelService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8002';
  }

  /**
   * Get all available models
   */
  async getModels(params?: {
    activeOnly?: boolean;
    provider?: string;
    task?: string;
  }): Promise<ModelListResponse> {
    const searchParams = new URLSearchParams();
    
    if (params?.activeOnly !== undefined) {
      searchParams.append('active_only', params.activeOnly.toString());
    }
    if (params?.provider) {
      searchParams.append('provider', params.provider);
    }
    if (params?.task) {
      searchParams.append('task', params.task);
    }

    const response = await fetch(`${this.baseUrl}/api/v2/models?${searchParams}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch models: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get a specific model by ID
   */
  async getModel(modelId: string): Promise<ModelDefinition> {
    const response = await fetch(`${this.baseUrl}/api/v2/models/${modelId}`);
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Model not found: ${modelId}`);
      }
      throw new Error(`Failed to fetch model: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get models that support a specific task
   */
  async getModelsForTask(taskType: string, activeOnly: boolean = true): Promise<TaskSupportResponse> {
    const searchParams = new URLSearchParams();
    searchParams.append('active_only', activeOnly.toString());

    const response = await fetch(`${this.baseUrl}/api/v2/models/tasks/${taskType}?${searchParams}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch models for task: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get models from a specific provider
   */
  async getModelsByProvider(provider: string, activeOnly: boolean = true): Promise<ModelListResponse> {
    const searchParams = new URLSearchParams();
    searchParams.append('active_only', activeOnly.toString());

    const response = await fetch(`${this.baseUrl}/api/v2/models/providers/${provider}?${searchParams}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch models by provider: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get model registry statistics
   */
  async getModelStatistics(): Promise<ModelStatistics> {
    const response = await fetch(`${this.baseUrl}/api/v2/models/statistics`);
    if (!response.ok) {
      throw new Error(`Failed to fetch model statistics: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get all available task types
   */
  async getAvailableTasks(): Promise<{ tasks: TaskDefinition[]; total: number }> {
    const response = await fetch(`${this.baseUrl}/api/v2/tasks`);
    if (!response.ok) {
      throw new Error(`Failed to fetch available tasks: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get all available providers
   */
  async getAvailableProviders(): Promise<{ providers: ProviderDefinition[]; total: number }> {
    const response = await fetch(`${this.baseUrl}/api/v2/providers`);
    if (!response.ok) {
      throw new Error(`Failed to fetch available providers: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Convert ModelDefinition to the format expected by existing components
   */
  modelToDisplayFormat(model: ModelDefinition) {
    return {
      id: model.id,
      title: model.name,
      description: model.description,
      author: this.getAuthorFromTags(model.tags),
      category: this.getCategoryFromTasks(model.capabilities.supported_tasks),
      bookmarked: false, // This could be managed by user preferences
      version: model.version,
      provider: model.provider,
      tags: model.tags,
      is_active: model.is_active,
      capabilities: model.capabilities,
      resources: model.resources,
      documentation_url: model.documentation_url,
      paper_url: model.paper_url,
      license: model.license
    };
  }

  private getAuthorFromTags(tags: string[]): string {
    // Try to extract author from tags or use provider
    const authorTag = tags.find(tag => tag.includes('author:'));
    if (authorTag) {
      return authorTag.replace('author:', '');
    }
    return 'Research Team';
  }

  private getCategoryFromTasks(tasks: string[]): string {
    // Map task types to categories
    const taskCategoryMap: Record<string, string> = {
      'protein_ligand_binding': 'Structure Prediction',
      'protein_structure': 'Structure Prediction',
      'protein_complex': 'Structure Prediction',
      'binding_site_prediction': 'Analysis',
      'variant_comparison': 'Analysis',
      'drug_discovery': 'Drug Discovery'
    };

    const primaryTask = tasks[0];
    return taskCategoryMap[primaryTask] || 'Prediction';
  }
}

export const modelService = new ModelService();