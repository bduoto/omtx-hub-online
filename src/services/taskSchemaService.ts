/**
 * Task Schema Service
 * Handles task-specific input/output schemas and validation
 */

export interface ValidationRule {
  rule_type: string;
  value: string | number | boolean;
  message: string;
}

export interface InputField {
  id: string;
  label: string;
  field_type: string;
  description?: string;
  placeholder?: string;
  default_value?: string | number | boolean;
  options?: Array<{ value: string; label: string }>;
  validation?: ValidationRule[];
  conditional?: Record<string, any>;
  help_text?: string;
}

export interface OutputField {
  id: string;
  label: string;
  output_type: string;
  description?: string;
  format?: string;
  visualization?: string;
  required: boolean;
  conditional?: Record<string, any>;
}

export interface TaskSchema {
  task_id: string;
  task_name: string;
  description: string;
  input_fields: InputField[];
  output_fields: OutputField[];
  estimated_time?: number;
  resource_requirements?: Record<string, any>;
  examples?: Array<Record<string, any>>;
}

export interface TaskSchemaResponse {
  schemas: Record<string, TaskSchema>;
  total: number;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

class TaskSchemaService {
  private baseUrl: string;
  private cache: Map<string, TaskSchema> = new Map();

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8002';
  }

  /**
   * Get schema for a specific task
   */
  async getTaskSchema(taskId: string): Promise<TaskSchema> {
    // Check cache first
    if (this.cache.has(taskId)) {
      return this.cache.get(taskId)!;
    }

    const response = await fetch(`${this.baseUrl}/api/v2/tasks/${taskId}/schema`);
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Task schema not found: ${taskId}`);
      }
      throw new Error(`Failed to fetch task schema: ${response.statusText}`);
    }

    const schema: TaskSchema = await response.json();
    this.cache.set(taskId, schema);
    return schema;
  }

  /**
   * Get all task schemas
   */
  async getAllTaskSchemas(): Promise<TaskSchemaResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/tasks/schemas`);
    if (!response.ok) {
      throw new Error(`Failed to fetch task schemas: ${response.statusText}`);
    }

    const result: TaskSchemaResponse = await response.json();
    
    // Cache all schemas
    Object.entries(result.schemas).forEach(([taskId, schema]) => {
      this.cache.set(taskId, schema);
    });

    return result;
  }

  /**
   * Validate input data against task schema
   */
  async validateTaskInput(taskId: string, inputData: Record<string, any>): Promise<ValidationResult> {
    const response = await fetch(`${this.baseUrl}/api/v2/tasks/${taskId}/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(inputData),
    });

    if (!response.ok) {
      throw new Error(`Failed to validate input: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get input fields for a specific task
   */
  async getInputFields(taskId: string): Promise<InputField[]> {
    const schema = await this.getTaskSchema(taskId);
    return schema.input_fields;
  }

  /**
   * Get output fields for a specific task
   */
  async getOutputFields(taskId: string): Promise<OutputField[]> {
    const schema = await this.getTaskSchema(taskId);
    return schema.output_fields;
  }

  /**
   * Get example inputs for a task
   */
  async getExampleInputs(taskId: string): Promise<Record<string, any>[]> {
    const schema = await this.getTaskSchema(taskId);
    return schema.examples || [];
  }

  /**
   * Get default values for a task
   */
  async getDefaultValues(taskId: string): Promise<Record<string, any>> {
    const schema = await this.getTaskSchema(taskId);
    const defaults: Record<string, any> = {};

    schema.input_fields.forEach(field => {
      if (field.default_value !== undefined) {
        defaults[field.id] = field.default_value;
      }
    });

    return defaults;
  }

  /**
   * Generate form configuration for a task
   */
  async getFormConfig(taskId: string): Promise<{
    fields: InputField[];
    defaults: Record<string, any>;
    examples: Record<string, any>[];
    estimatedTime: number;
  }> {
    const schema = await this.getTaskSchema(taskId);
    const defaults = await this.getDefaultValues(taskId);
    const examples = await this.getExampleInputs(taskId);

    return {
      fields: schema.input_fields,
      defaults,
      examples,
      estimatedTime: schema.estimated_time || 300,
    };
  }

  /**
   * Generate output configuration for a task
   */
  async getOutputConfig(taskId: string): Promise<{
    fields: OutputField[];
    hasStructure: boolean;
    hasAffinity: boolean;
    hasConfidence: boolean;
    hasBindingSites: boolean;
    hasScreeningResults: boolean;
    hasMetrics: boolean;
  }> {
    const schema = await this.getTaskSchema(taskId);
    const fields = schema.output_fields;

    // Analyze what types of outputs this task produces
    const hasStructure = fields.some(f => f.output_type === 'structure');
    const hasAffinity = fields.some(f => f.output_type === 'affinity');
    const hasConfidence = fields.some(f => f.output_type === 'confidence');
    const hasBindingSites = fields.some(f => f.output_type === 'binding_sites');
    const hasScreeningResults = fields.some(f => f.output_type === 'screening_results');
    const hasMetrics = fields.some(f => f.output_type === 'metrics');

    return {
      fields,
      hasStructure,
      hasAffinity,
      hasConfidence,
      hasBindingSites,
      hasScreeningResults,
      hasMetrics,
    };
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
  }
}

export const taskSchemaService = new TaskSchemaService();