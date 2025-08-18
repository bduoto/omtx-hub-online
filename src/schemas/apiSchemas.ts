/**
 * Zod schemas for OMTX-Hub API validation
 * All schemas use snake_case naming to match backend Pydantic models
 */

import { z } from 'zod';

// Enums
export const TaskType = z.enum([
  'protein_ligand_binding',
  'protein_structure',
  'protein_complex',
  'binding_site_prediction',
  'variant_comparison',
  'drug_discovery',
  'nanobody_design',
  'cdr_optimization',
  'epitope_targeted_design',
  'antibody_de_novo_design',
]);

export const JobStatus = z.enum([
  'pending',
  'submitted',
  'running',
  'completed',
  'failed',
  'cancelled',
]);

export const LogLevel = z.enum([
  'DEBUG',
  'INFO',
  'WARNING',
  'ERROR',
  'CRITICAL',
]);

// Base Schemas
export const BaseApiSchema = z.object({
  success: z.boolean().default(true),
  message: z.string().optional(),
  timestamp: z.string().datetime(),
});

export const ErrorResponseSchema = BaseApiSchema.extend({
  success: z.boolean().default(false),
  error_code: z.string().optional(),
  error_details: z.record(z.any()).optional(),
});

// Pagination Schemas
export const PaginationRequestSchema = z.object({
  page: z.number().int().min(1).default(1),
  per_page: z.number().int().min(1).max(100).default(20),
});

export const PaginationResponseSchema = z.object({
  total_items: z.number().int(),
  total_pages: z.number().int(),
  current_page: z.number().int(),
  per_page: z.number().int(),
  has_next: z.boolean(),
  has_previous: z.boolean(),
});

// Job Schemas
export const JobCreateSchema = z.object({
  job_name: z.string().min(1).max(255),
  task_type: TaskType,
  model_id: z.string().default('boltz2'),
  input_data: z.record(z.any()),
  use_msa: z.boolean().default(true),
  use_potentials: z.boolean().default(false),
  batch_name: z.string().optional(),
});

export const JobResponseSchema = BaseApiSchema.extend({
  job_id: z.string(),
  job_name: z.string(),
  task_type: TaskType,
  model_id: z.string(),
  status: JobStatus,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime().optional(),
  completed_at: z.string().datetime().optional(),
  estimated_completion_time: z.number().int().optional(),
  progress: z.number().min(0).max(1).optional(),
  batch_id: z.string().optional(),
  batch_index: z.number().int().optional(),
});

export const JobDetailResponseSchema = JobResponseSchema.extend({
  input_data: z.record(z.any()),
  parameters: z.record(z.any()).default({}),
  results: z.record(z.any()).optional(),
  error_message: z.string().optional(),
  execution_time: z.number().optional(),
  resource_usage: z.record(z.any()).optional(),
});

export const JobListRequestSchema = PaginationRequestSchema.extend({
  status: JobStatus.optional(),
  task_type: TaskType.optional(),
  model_id: z.string().optional(),
  search_query: z.string().optional(),
  created_after: z.string().datetime().optional(),
  created_before: z.string().datetime().optional(),
});

export const JobListResponseSchema = BaseApiSchema.extend({
  jobs: z.array(JobResponseSchema),
  pagination: PaginationResponseSchema,
});

// Task Schemas
export const TaskInfoSchema = z.object({
  task_type: TaskType,
  task_name: z.string(),
  description: z.string(),
  estimated_time: z.number().int(),
  input_schema: z.record(z.any()),
  output_schema: z.record(z.any()),
});

export const TaskListResponseSchema = BaseApiSchema.extend({
  tasks: z.array(TaskInfoSchema),
  total_tasks: z.number().int(),
});

// Batch Schemas
export const BatchCreateSchema = z.object({
  batch_name: z.string().min(1).max(255),
  jobs: z.array(JobCreateSchema).min(1),
});

export const BatchResponseSchema = BaseApiSchema.extend({
  batch_id: z.string(),
  batch_name: z.string(),
  total_jobs: z.number().int(),
  completed_jobs: z.number().int().default(0),
  failed_jobs: z.number().int().default(0),
  status: z.string(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime().optional(),
  estimated_completion_time: z.number().int().optional(),
});

export const BatchDetailResponseSchema = BatchResponseSchema.extend({
  jobs: z.array(JobResponseSchema),
  common_parameters: z.record(z.any()).default({}),
});

export const BatchListResponseSchema = BaseApiSchema.extend({
  batches: z.array(BatchResponseSchema),
  pagination: PaginationResponseSchema,
});

// Log Schemas
export const LogEntrySchema = z.object({
  timestamp: z.string(),
  level: LogLevel,
  message: z.string(),
  source: z.string(),
  function_name: z.string().optional(),
  app_id: z.string().optional(),
  execution_id: z.string().optional(),
  raw_line: z.string().optional(),
});

export const LogListRequestSchema = PaginationRequestSchema.extend({
  app_id: z.string().optional(),
  level: LogLevel.optional(),
  search_query: z.string().optional(),
  start_time: z.string().datetime().optional(),
  end_time: z.string().datetime().optional(),
});

export const LogListResponseSchema = BaseApiSchema.extend({
  logs: z.array(LogEntrySchema),
  pagination: PaginationResponseSchema,
});

// System Schemas
export const SystemHealthSchema = z.object({
  status: z.string(),
  database_status: z.string(),
  storage_status: z.string(),
  modal_status: z.string(),
  active_jobs: z.number().int(),
  total_jobs_today: z.number().int(),
  average_response_time: z.number().optional(),
  uptime: z.number().optional(),
});

export const SystemStatusResponseSchema = BaseApiSchema.extend({
  health: SystemHealthSchema,
  supported_tasks: z.array(z.string()),
  recent_jobs_count: z.number().int(),
});

// File Schemas
export const FileDownloadResponseSchema = z.object({
  file_name: z.string(),
  content_type: z.string(),
  file_size: z.number().int().optional(),
  download_url: z.string().optional(),
});

// Update/Delete Schemas
export const JobUpdateSchema = z.object({
  status: JobStatus.optional(),
  results: z.record(z.any()).optional(),
  error_message: z.string().optional(),
  progress: z.number().min(0).max(1).optional(),
});

export const JobDeleteResponseSchema = BaseApiSchema.extend({
  job_id: z.string(),
});

export const BatchDeleteResponseSchema = BaseApiSchema.extend({
  batch_id: z.string(),
  deleted_jobs: z.number().int(),
});

// Export Schemas
export const JobExportRequestSchema = z.object({
  format: z.string().default('json'),
  include_results: z.boolean().default(true),
  include_logs: z.boolean().default(false),
});

export const JobExportResponseSchema = BaseApiSchema.extend({
  export_url: z.string(),
  file_name: z.string(),
  expires_at: z.string().datetime(),
});

// Search Schemas
export const SearchRequestSchema = PaginationRequestSchema.extend({
  query: z.string().min(1),
  filters: z.record(z.any()).optional(),
  sort_by: z.string().optional(),
  sort_order: z.enum(['asc', 'desc']).default('desc'),
});

export const SearchResponseSchema = BaseApiSchema.extend({
  results: z.array(z.record(z.any())),
  pagination: PaginationResponseSchema,
  search_query: z.string(),
  total_matches: z.number().int(),
});

// Task-specific Input Schemas
export const ProteinLigandBindingInputSchema = z.object({
  protein_sequence: z.string().min(1),
  ligand_smiles: z.string().min(1),
  binding_site: z.string().optional(),
});

export const ProteinStructureInputSchema = z.object({
  protein_sequence: z.string().min(1),
  template_structure: z.string().optional(),
});

export const ProteinComplexInputSchema = z.object({
  protein_sequences: z.array(z.string().min(1)).min(2),
  stoichiometry: z.string().optional(),
});

export const BindingSitePredictionInputSchema = z.object({
  protein_structure: z.string().min(1), // PDB content
  cavity_detection_method: z.string().optional(),
});

export const VariantComparisonInputSchema = z.object({
  reference_sequence: z.string().min(1),
  variant_sequences: z.array(z.string().min(1)).min(1),
  mutation_positions: z.array(z.number().int()).optional(),
});

export const NanobodyDesignInputSchema = z.object({
  target_pdb: z.string().min(1),
  target_chain: z.string().min(1),
  hotspot_residues: z.array(z.string()).min(1),
  num_designs: z.number().int().min(1).max(100).default(10),
  framework: z.enum(['vhh', 'humanized', 'camelid']).default('vhh'),
});

// Type exports
export type TaskType = z.infer<typeof TaskType>;
export type JobStatus = z.infer<typeof JobStatus>;
export type LogLevel = z.infer<typeof LogLevel>;

export type BaseApiResponse = z.infer<typeof BaseApiSchema>;
export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;

export type PaginationRequest = z.infer<typeof PaginationRequestSchema>;
export type PaginationResponse = z.infer<typeof PaginationResponseSchema>;

export type JobCreate = z.infer<typeof JobCreateSchema>;
export type JobResponse = z.infer<typeof JobResponseSchema>;
export type JobDetailResponse = z.infer<typeof JobDetailResponseSchema>;
export type JobListRequest = z.infer<typeof JobListRequestSchema>;
export type JobListResponse = z.infer<typeof JobListResponseSchema>;

export type TaskInfo = z.infer<typeof TaskInfoSchema>;
export type TaskListResponse = z.infer<typeof TaskListResponseSchema>;

export type BatchCreate = z.infer<typeof BatchCreateSchema>;
export type BatchResponse = z.infer<typeof BatchResponseSchema>;
export type BatchDetailResponse = z.infer<typeof BatchDetailResponseSchema>;
export type BatchListResponse = z.infer<typeof BatchListResponseSchema>;

export type LogEntry = z.infer<typeof LogEntrySchema>;
export type LogListRequest = z.infer<typeof LogListRequestSchema>;
export type LogListResponse = z.infer<typeof LogListResponseSchema>;

export type SystemHealth = z.infer<typeof SystemHealthSchema>;
export type SystemStatusResponse = z.infer<typeof SystemStatusResponseSchema>;

export type FileDownloadResponse = z.infer<typeof FileDownloadResponseSchema>;

export type JobUpdate = z.infer<typeof JobUpdateSchema>;
export type JobDeleteResponse = z.infer<typeof JobDeleteResponseSchema>;
export type BatchDeleteResponse = z.infer<typeof BatchDeleteResponseSchema>;

export type JobExportRequest = z.infer<typeof JobExportRequestSchema>;
export type JobExportResponse = z.infer<typeof JobExportResponseSchema>;

export type SearchRequest = z.infer<typeof SearchRequestSchema>;
export type SearchResponse = z.infer<typeof SearchResponseSchema>;

// Task-specific input types
export type ProteinLigandBindingInput = z.infer<typeof ProteinLigandBindingInputSchema>;
export type ProteinStructureInput = z.infer<typeof ProteinStructureInputSchema>;
export type ProteinComplexInput = z.infer<typeof ProteinComplexInputSchema>;
export type BindingSitePredictionInput = z.infer<typeof BindingSitePredictionInputSchema>;
export type VariantComparisonInput = z.infer<typeof VariantComparisonInputSchema>;
export type NanobodyDesignInput = z.infer<typeof NanobodyDesignInputSchema>;

// Helper functions for validation
export const validateJobCreate = (data: unknown): JobCreate => {
  return JobCreateSchema.parse(data);
};

export const validateJobResponse = (data: unknown): JobResponse => {
  return JobResponseSchema.parse(data);
};

export const validateJobListResponse = (data: unknown): JobListResponse => {
  return JobListResponseSchema.parse(data);
};

export const validateSystemStatusResponse = (data: unknown): SystemStatusResponse => {
  return SystemStatusResponseSchema.parse(data);
};

// Input validation helpers
export const validateProteinLigandBindingInput = (data: unknown): ProteinLigandBindingInput => {
  return ProteinLigandBindingInputSchema.parse(data);
};

export const validateProteinStructureInput = (data: unknown): ProteinStructureInput => {
  return ProteinStructureInputSchema.parse(data);
};

export const validateNanobodyDesignInput = (data: unknown): NanobodyDesignInput => {
  return NanobodyDesignInputSchema.parse(data);
};

// API response validation helper
export const validateApiResponse = <T>(schema: z.ZodSchema<T>, data: unknown): T => {
  try {
    return schema.parse(data);
  } catch (error) {
    console.error('API Response validation failed:', error);
    throw new Error('Invalid API response format');
  }
};

// Safe parsing helper (doesn't throw)
export const safeParseApiResponse = <T>(
  schema: z.ZodSchema<T>, 
  data: unknown
): { success: true; data: T } | { success: false; error: string } => {
  const result = schema.safeParse(data);
  if (result.success) {
    return { success: true, data: result.data };
  } else {
    return { 
      success: false, 
      error: result.error.issues.map(i => i.message).join(', ')
    };
  }
};