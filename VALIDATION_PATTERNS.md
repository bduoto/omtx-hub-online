# Validation Patterns & Examples

## Overview

This document provides comprehensive validation patterns for OMTX-Hub, demonstrating how to implement consistent validation across backend (Pydantic) and frontend (Zod) using snake_case naming conventions.

## Architecture Principles

### 1. Consistent Validation
- **Backend**: Pydantic models with comprehensive field validation
- **Frontend**: Zod schemas that mirror backend models exactly
- **Naming**: snake_case convention throughout the entire stack
- **Type Safety**: Full compile-time and runtime validation

### 2. Validation Strategy
- **Request Validation**: All inputs validated before processing
- **Response Validation**: All outputs conform to defined schemas
- **Error Handling**: Standardized error formats with detailed messages
- **Field Validation**: Min/max lengths, enums, custom validators

## Backend Validation (Pydantic)

### Base Model Configuration

```python
from pydantic import BaseModel, Field, ConfigDict, validator
from pydantic.alias_generators import to_camel
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

class BaseApiModel(BaseModel):
    """Base model with standardized configuration"""
    model_config = ConfigDict(
        alias_generator=to_camel,           # Generate camelCase aliases
        populate_by_name=True,              # Accept both snake_case and camelCase
        use_enum_values=True,               # Use enum values in serialization
        validate_assignment=True,           # Validate on assignment
        extra='forbid',                     # Reject extra fields
        str_strip_whitespace=True,          # Strip whitespace from strings
        validate_default=True               # Validate default values
    )

class BaseRequest(BaseApiModel):
    """Base request model"""
    pass

class BaseResponse(BaseApiModel):
    """Base response model with common fields"""
    success: bool = Field(default=True)
    message: str = Field(default="Operation completed successfully")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### Field Validation Examples

#### String Validation
```python
class JobCreate(BaseRequest):
    # Required string with length constraints
    job_name: str = Field(
        ...,                                # Required field
        min_length=1,                       # Minimum 1 character
        max_length=255,                     # Maximum 255 characters
        description="Human-readable job name"
    )
    
    # Optional string with pattern validation
    model_id: str = Field(
        default="boltz2",
        pattern=r"^[a-z0-9_]+$",           # Only lowercase, numbers, underscores
        max_length=50,
        description="Model identifier"
    )

# Custom validator example
@validator('job_name')
def validate_job_name(cls, v):
    if not v or v.isspace():
        raise ValueError('Job name cannot be empty or whitespace only')
    
    # Remove multiple consecutive spaces
    v = ' '.join(v.split())
    
    # Check for prohibited characters
    prohibited = ['<', '>', '"', "'", '&', '\\', '/', '|']
    if any(char in v for char in prohibited):
        raise ValueError(f'Job name cannot contain: {", ".join(prohibited)}')
    
    return v
```

#### Enum Validation
```python
from enum import Enum

class TaskType(str, Enum):
    """Supported task types"""
    PROTEIN_LIGAND_BINDING = "protein_ligand_binding"
    PROTEIN_STRUCTURE = "protein_structure"
    PROTEIN_COMPLEX = "protein_complex"
    BINDING_SITE_PREDICTION = "binding_site_prediction"
    VARIANT_COMPARISON = "variant_comparison"
    DRUG_DISCOVERY = "drug_discovery"

class JobStatus(str, Enum):
    """Job status values"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobCreate(BaseRequest):
    task_type: TaskType = Field(
        ...,
        description="Type of prediction task to perform"
    )
    
    status: JobStatus = Field(
        default=JobStatus.PENDING,
        description="Current job status"
    )
```

#### Numeric Validation
```python
class JobListRequest(BaseRequest):
    page: int = Field(
        default=1,
        ge=1,                               # Greater than or equal to 1
        description="Page number for pagination"
    )
    
    per_page: int = Field(
        default=20,
        ge=1,                               # At least 1 item
        le=100,                             # At most 100 items
        description="Number of items per page"
    )
    
    # Optional numeric with custom validation
    timeout_seconds: Optional[int] = Field(
        default=None,
        ge=30,                              # Minimum 30 seconds
        le=7200,                            # Maximum 2 hours
        description="Request timeout in seconds"
    )
```

#### Complex Field Validation
```python
class JobCreate(BaseRequest):
    # Dict with specific structure validation
    input_data: Dict[str, Any] = Field(
        ...,
        description="Task-specific input data"
    )
    
    # List validation
    tags: Optional[List[str]] = Field(
        default=None,
        max_items=10,                       # Maximum 10 tags
        description="Optional job tags"
    )
    
    # Custom dict validation
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional job parameters"
    )

@validator('input_data')
def validate_input_data(cls, v, values):
    """Validate input_data based on task_type"""
    task_type = values.get('task_type')
    
    if task_type == TaskType.PROTEIN_LIGAND_BINDING:
        required_fields = ['protein_sequence', 'ligand_smiles']
        for field in required_fields:
            if field not in v:
                raise ValueError(f'Missing required field for {task_type}: {field}')
    
    elif task_type == TaskType.PROTEIN_STRUCTURE:
        if 'protein_sequence' not in v:
            raise ValueError('protein_sequence is required for protein structure prediction')
    
    return v

@validator('tags', each_item=True)
def validate_tag(cls, v):
    """Validate each tag in the tags list"""
    if len(v) > 50:
        raise ValueError('Each tag must be 50 characters or less')
    
    if not v.replace('_', '').replace('-', '').isalnum():
        raise ValueError('Tags can only contain letters, numbers, hyphens, and underscores')
    
    return v.lower()
```

#### Protein Sequence Validation
```python
import re

class BiochemicalValidators:
    """Custom validators for biochemical data"""
    
    @staticmethod
    def validate_protein_sequence(sequence: str) -> str:
        """Validate protein sequence format"""
        if not sequence:
            raise ValueError('Protein sequence cannot be empty')
        
        # Remove whitespace and convert to uppercase
        sequence = ''.join(sequence.split()).upper()
        
        # Check minimum length
        if len(sequence) < 10:
            raise ValueError('Protein sequence must be at least 10 amino acids long')
        
        # Check maximum length (practical limit)
        if len(sequence) > 10000:
            raise ValueError('Protein sequence must be less than 10,000 amino acids long')
        
        # Valid amino acid codes
        valid_aa = set('ACDEFGHIKLMNPQRSTVWY')
        
        # Check for invalid characters
        invalid_chars = set(sequence) - valid_aa
        if invalid_chars:
            raise ValueError(f'Invalid amino acid codes: {", ".join(sorted(invalid_chars))}')
        
        return sequence
    
    @staticmethod
    def validate_smiles_string(smiles: str) -> str:
        """Validate SMILES chemical notation"""
        if not smiles:
            raise ValueError('SMILES string cannot be empty')
        
        # Remove whitespace
        smiles = smiles.strip()
        
        # Basic SMILES validation (can be enhanced with chemistry libraries)
        if len(smiles) < 1:
            raise ValueError('SMILES string too short')
        
        if len(smiles) > 1000:
            raise ValueError('SMILES string too long')
        
        # Check for basic SMILES characters
        valid_chars = set('CNOPSFClBrI[]()=#@+-1234567890cnosp\\/')
        invalid_chars = set(smiles) - valid_chars
        if invalid_chars:
            raise ValueError(f'Invalid SMILES characters: {", ".join(sorted(invalid_chars))}')
        
        return smiles

# Usage in models
class ProteinLigandInput(BaseModel):
    protein_sequence: str = Field(
        ...,
        description="Protein amino acid sequence"
    )
    
    ligand_smiles: str = Field(
        ..., 
        description="Ligand SMILES chemical notation"
    )
    
    @validator('protein_sequence')
    def validate_protein_sequence(cls, v):
        return BiochemicalValidators.validate_protein_sequence(v)
    
    @validator('ligand_smiles')
    def validate_ligand_smiles(cls, v):
        return BiochemicalValidators.validate_smiles_string(v)
```

### Response Validation
```python
class JobDetailResponse(BaseResponse):
    # Core job information
    job_id: str = Field(..., min_length=1, max_length=100)
    job_name: str = Field(..., min_length=1, max_length=255)
    task_type: TaskType
    model_id: str = Field(..., max_length=50)
    status: JobStatus
    
    # Timestamps
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Job data
    input_data: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = Field(None)
    error_message: Optional[str] = Field(None, max_length=1000)
    
    # Computed fields
    @validator('updated_at')
    def updated_at_must_be_after_created_at(cls, v, values):
        if v and 'created_at' in values and v < values['created_at']:
            raise ValueError('updated_at must be after created_at')
        return v
```

## Frontend Validation (Zod)

### Base Schema Configuration

```typescript
import { z } from 'zod';

// Base schema with common validation
const BaseApiSchema = z.object({
  success: z.boolean().default(true),
  message: z.string().default("Operation completed successfully"),
  timestamp: z.string().datetime()
});

const BaseRequestSchema = z.object({});

const BaseResponseSchema = BaseApiSchema;

// Enum schemas
const TaskType = z.enum([
  'protein_ligand_binding',
  'protein_structure', 
  'protein_complex',
  'binding_site_prediction',
  'variant_comparison',
  'drug_discovery'
]);

const JobStatus = z.enum([
  'pending',
  'submitted',
  'running', 
  'completed',
  'failed',
  'cancelled'
]);
```

### Field Validation Examples

#### String Validation
```typescript
// Job name validation (mirrors backend)
const jobNameSchema = z.string()
  .min(1, "Job name is required")
  .max(255, "Job name must be 255 characters or less")
  .refine((val) => val.trim().length > 0, "Job name cannot be only whitespace")
  .transform((val) => val.trim().replace(/\s+/g, ' ')) // Normalize whitespace
  .refine(
    (val) => !/[<>"'&\\\/|]/.test(val),
    "Job name cannot contain: < > \" ' & \\ / |"
  );

// Model ID validation
const modelIdSchema = z.string()
  .regex(/^[a-z0-9_]+$/, "Model ID can only contain lowercase letters, numbers, and underscores")
  .max(50, "Model ID must be 50 characters or less")
  .default("boltz2");

// Usage in schemas
export const JobCreateSchema = BaseRequestSchema.extend({
  job_name: jobNameSchema,
  model_id: modelIdSchema,
  task_type: TaskType,
  input_data: z.record(z.any()),
  use_msa: z.boolean().default(true),
  use_potentials: z.boolean().default(false)
});
```

#### Numeric Validation
```typescript
// Pagination validation
export const JobListRequestSchema = BaseRequestSchema.extend({
  page: z.number().int().min(1, "Page must be at least 1").default(1),
  per_page: z.number().int().min(1).max(100, "Per page must be between 1 and 100").default(20),
  
  // Optional timeout
  timeout_seconds: z.number().int().min(30).max(7200).optional()
});

// Transform string inputs to numbers
export const JobListRequestFromQuerySchema = z.object({
  page: z.string().optional().transform(val => val ? parseInt(val, 10) : 1),
  per_page: z.string().optional().transform(val => val ? parseInt(val, 10) : 20)
}).pipe(JobListRequestSchema);
```

#### Biochemical Data Validation
```typescript
// Protein sequence validation
const proteinSequenceSchema = z.string()
  .min(1, "Protein sequence is required")
  .transform(val => val.replace(/\s/g, '').toUpperCase()) // Remove whitespace, uppercase
  .refine(
    val => val.length >= 10,
    "Protein sequence must be at least 10 amino acids long"
  )
  .refine(
    val => val.length <= 10000,
    "Protein sequence must be less than 10,000 amino acids long"
  )
  .refine(
    val => /^[ACDEFGHIKLMNPQRSTVWY]+$/.test(val),
    "Protein sequence contains invalid amino acid codes"
  );

// SMILES validation
const smilesSchema = z.string()
  .min(1, "SMILES string is required")
  .max(1000, "SMILES string too long")
  .transform(val => val.trim())
  .refine(
    val => /^[CNOPSFClBrI\[\]()=#@+\-1234567890cnosp\\/]+$/.test(val),
    "SMILES string contains invalid characters"
  );

// Task-specific input validation
const ProteinLigandInputSchema = z.object({
  protein_sequence: proteinSequenceSchema,
  ligand_smiles: smilesSchema
});

const ProteinStructureInputSchema = z.object({
  protein_sequence: proteinSequenceSchema
});

const ProteinComplexInputSchema = z.object({
  protein_sequences: z.array(proteinSequenceSchema).min(2, "At least 2 protein sequences required")
});
```

#### Conditional Validation
```typescript
// Dynamic input_data validation based on task_type
export const JobCreateSchema = BaseRequestSchema.extend({
  job_name: jobNameSchema,
  task_type: TaskType,
  model_id: modelIdSchema,
  input_data: z.record(z.any()),
  use_msa: z.boolean().default(true),
  use_potentials: z.boolean().default(false)
}).superRefine((data, ctx) => {
  // Validate input_data based on task_type
  switch (data.task_type) {
    case 'protein_ligand_binding':
      const plResult = ProteinLigandInputSchema.safeParse(data.input_data);
      if (!plResult.success) {
        plResult.error.issues.forEach(issue => {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['input_data', ...issue.path],
            message: issue.message
          });
        });
      }
      break;
      
    case 'protein_structure':
      const psResult = ProteinStructureInputSchema.safeParse(data.input_data);
      if (!psResult.success) {
        psResult.error.issues.forEach(issue => {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['input_data', ...issue.path],
            message: issue.message
          });
        });
      }
      break;
      
    case 'protein_complex':
      const pcResult = ProteinComplexInputSchema.safeParse(data.input_data);
      if (!pcResult.success) {
        pcResult.error.issues.forEach(issue => {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ['input_data', ...issue.path],
            message: issue.message
          });
        });
      }
      break;
      
    default:
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['task_type'],
        message: `Unsupported task type: ${data.task_type}`
      });
  }
});
```

#### Array and Object Validation
```typescript
// Tags validation
const tagsSchema = z.array(
  z.string()
    .max(50, "Each tag must be 50 characters or less")
    .regex(/^[a-zA-Z0-9_-]+$/, "Tags can only contain letters, numbers, hyphens, and underscores")
    .transform(val => val.toLowerCase())
).max(10, "Maximum 10 tags allowed").optional();

// Parameters validation
const parametersSchema = z.record(z.any())
  .refine(
    val => Object.keys(val).length <= 20,
    "Maximum 20 parameters allowed"
  )
  .refine(
    val => Object.keys(val).every(key => key.length <= 50),
    "Parameter names must be 50 characters or less"
  );

// Results validation
const resultsSchema = z.object({
  affinity: z.number().optional(),
  affinity_probability: z.number().min(0).max(1).optional(),
  confidence: z.number().min(0).max(1).optional(),
  ptm_score: z.number().min(0).max(1).optional(),
  plddt_score: z.number().min(0).max(1).optional(),
  execution_time: z.number().positive().optional(),
  gpu_type: z.string().optional(),
  structure_file_base64: z.string().optional()
}).optional();
```

## Validation Utilities

### Backend Utilities
```python
from typing import Any, Dict, List, Tuple

class ValidationUtils:
    """Utility functions for validation"""
    
    @staticmethod
    def validate_and_clean_dict(
        data: Dict[str, Any], 
        allowed_keys: List[str],
        required_keys: List[str] = None
    ) -> Dict[str, Any]:
        """Validate and clean dictionary data"""
        required_keys = required_keys or []
        
        # Check required keys
        missing_keys = set(required_keys) - set(data.keys())
        if missing_keys:
            raise ValueError(f"Missing required keys: {', '.join(missing_keys)}")
        
        # Filter to allowed keys
        cleaned = {k: v for k, v in data.items() if k in allowed_keys}
        
        return cleaned
    
    @staticmethod
    def validate_pagination(
        page: int, 
        per_page: int, 
        max_per_page: int = 100
    ) -> Tuple[int, int]:
        """Validate pagination parameters"""
        if page < 1:
            raise ValueError("Page must be at least 1")
        
        if per_page < 1:
            raise ValueError("Per page must be at least 1") 
        
        if per_page > max_per_page:
            raise ValueError(f"Per page cannot exceed {max_per_page}")
        
        return page, per_page
    
    @staticmethod
    def validate_file_upload(
        file_content: bytes,
        max_size: int = 10 * 1024 * 1024,  # 10MB
        allowed_extensions: List[str] = None
    ) -> bool:
        """Validate file upload"""
        if len(file_content) > max_size:
            raise ValueError(f"File size exceeds {max_size} bytes")
        
        return True

# Usage in endpoints
@router.post("/predict", response_model=JobResponse)
async def submit_prediction(request: JobCreate):
    # Validation is automatic via Pydantic
    # Additional business logic validation if needed
    
    if request.task_type == TaskType.PROTEIN_LIGAND_BINDING:
        # Validate specific business rules
        if len(request.input_data.get('protein_sequence', '')) > 5000:
            raise HTTPException(
                status_code=400,
                detail="Protein sequence too long for ligand binding analysis"
            )
    
    # Process request...
```

### Frontend Utilities
```typescript
import { z } from 'zod';

export class ValidationUtils {
  /**
   * Safely parse and validate data with user-friendly error handling
   */
  static safeParseWithErrors<T>(
    schema: z.ZodSchema<T>,
    data: unknown
  ): { success: true; data: T } | { success: false; errors: Record<string, string[]> } {
    const result = schema.safeParse(data);
    
    if (result.success) {
      return { success: true, data: result.data };
    }
    
    // Convert Zod errors to user-friendly format
    const errors: Record<string, string[]> = {};
    
    result.error.issues.forEach((issue) => {
      const path = issue.path.join('.');
      const key = path || 'root';
      
      if (!errors[key]) {
        errors[key] = [];
      }
      
      errors[key].push(issue.message);
    });
    
    return { success: false, errors };
  }
  
  /**
   * Validate form data and return field-specific errors
   */
  static validateForm<T>(
    schema: z.ZodSchema<T>,
    formData: Record<string, any>
  ): { isValid: boolean; data?: T; fieldErrors: Record<string, string> } {
    const result = this.safeParseWithErrors(schema, formData);
    
    if (result.success) {
      return {
        isValid: true,
        data: result.data,
        fieldErrors: {}
      };
    }
    
    // Convert to field errors (take first error per field)
    const fieldErrors: Record<string, string> = {};
    Object.entries(result.errors).forEach(([field, messages]) => {
      fieldErrors[field] = messages[0];
    });
    
    return {
      isValid: false,
      fieldErrors
    };
  }
  
  /**
   * Validate protein sequence with detailed feedback
   */
  static validateProteinSequence(sequence: string): {
    isValid: boolean;
    warnings: string[];
    errors: string[];
  } {
    const warnings: string[] = [];
    const errors: string[] = [];
    
    if (!sequence) {
      errors.push("Protein sequence is required");
      return { isValid: false, warnings, errors };
    }
    
    const cleaned = sequence.replace(/\s/g, '').toUpperCase();
    
    if (cleaned.length < 10) {
      errors.push("Protein sequence must be at least 10 amino acids long");
    }
    
    if (cleaned.length > 10000) {
      errors.push("Protein sequence must be less than 10,000 amino acids long");
    }
    
    // Check for unusual amino acids
    const standardAA = new Set('ACDEFGHIKLMNPQRSTVWY');
    const unusualAA = new Set(cleaned.split('').filter(aa => !standardAA.has(aa)));
    
    if (unusualAA.size > 0) {
      errors.push(`Invalid amino acid codes: ${Array.from(unusualAA).join(', ')}`);
    }
    
    // Performance warnings
    if (cleaned.length > 1000) {
      warnings.push("Large proteins may take longer to process");
    }
    
    return {
      isValid: errors.length === 0,
      warnings,
      errors
    };
  }
}

// React hook for form validation
export function useFormValidation<T>(schema: z.ZodSchema<T>) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isValid, setIsValid] = useState(false);
  
  const validate = useCallback((data: unknown) => {
    const result = ValidationUtils.validateForm(schema, data);
    
    setErrors(result.fieldErrors);
    setIsValid(result.isValid);
    
    return result;
  }, [schema]);
  
  const clearErrors = useCallback(() => {
    setErrors({});
    setIsValid(false);
  }, []);
  
  const getFieldError = useCallback((field: string) => {
    return errors[field];
  }, [errors]);
  
  return {
    validate,
    errors,
    isValid,
    clearErrors,
    getFieldError,
    hasErrors: Object.keys(errors).length > 0
  };
}
```

## Error Handling Patterns

### Standardized Error Responses
```python
# Backend error models
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    code: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool = Field(default=False)
    message: str
    error_code: str
    details: List[ErrorDetail] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Error handler
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    details = []
    for error in exc.errors():
        details.append(ErrorDetail(
            field=".".join(str(x) for x in error.get("loc", [])),
            message=error.get("msg", "Validation error"),
            code=error.get("type")
        ))
    
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            details=details
        ).dict()
    )
```

```typescript
// Frontend error schemas
export const ErrorDetailSchema = z.object({
  field: z.string().optional(),
  message: z.string(),
  code: z.string().optional()
});

export const ErrorResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  error_code: z.string(),
  details: z.array(ErrorDetailSchema),
  timestamp: z.string().datetime()
});

export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;

// Error handling utility
export function handleApiError(error: unknown): {
  type: string;
  message: string;
  fieldErrors?: Record<string, string>;
} {
  if (error instanceof z.ZodError) {
    const fieldErrors: Record<string, string> = {};
    error.issues.forEach(issue => {
      const field = issue.path.join('.');
      fieldErrors[field] = issue.message;
    });
    
    return {
      type: 'validation',
      message: 'Validation failed',
      fieldErrors
    };
  }
  
  // Handle API error responses
  if (error instanceof Error && error.message.includes('HTTP')) {
    try {
      const errorData = JSON.parse(error.message.split('HTTP')[1]);
      const parsedError = ErrorResponseSchema.safeParse(errorData);
      
      if (parsedError.success) {
        const fieldErrors: Record<string, string> = {};
        parsedError.data.details.forEach(detail => {
          if (detail.field) {
            fieldErrors[detail.field] = detail.message;
          }
        });
        
        return {
          type: parsedError.data.error_code,
          message: parsedError.data.message,
          fieldErrors: Object.keys(fieldErrors).length > 0 ? fieldErrors : undefined
        };
      }
    } catch {
      // Fall through to generic error
    }
  }
  
  return {
    type: 'unknown',
    message: error instanceof Error ? error.message : 'Unknown error occurred'
  };
}
```

## Testing Validation

### Backend Tests
```python
import pytest
from pydantic import ValidationError
from schemas.api_models import JobCreate, TaskType

class TestJobCreateValidation:
    def test_valid_job_create(self):
        """Test valid job creation"""
        data = {
            "job_name": "Test Job",
            "task_type": "protein_ligand_binding",
            "model_id": "boltz2",
            "input_data": {
                "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQ",
                "ligand_smiles": "CCO"
            }
        }
        
        job = JobCreate(**data)
        assert job.job_name == "Test Job"
        assert job.task_type == TaskType.PROTEIN_LIGAND_BINDING
    
    def test_invalid_job_name(self):
        """Test job name validation"""
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(
                job_name="",  # Empty name
                task_type="protein_ligand_binding",
                input_data={}
            )
        
        errors = exc_info.value.errors()
        assert any(error["type"] == "value_error" for error in errors)
    
    def test_protein_sequence_validation(self):
        """Test protein sequence validation"""
        with pytest.raises(ValidationError):
            JobCreate(
                job_name="Test",
                task_type="protein_ligand_binding",
                input_data={
                    "protein_sequence": "INVALID123",  # Invalid amino acids
                    "ligand_smiles": "CCO"
                }
            )
```

### Frontend Tests
```typescript
import { describe, it, expect } from 'vitest';
import { JobCreateSchema, ValidationUtils } from './apiSchemas';

describe('JobCreate Validation', () => {
  it('should validate correct job data', () => {
    const validData = {
      job_name: 'Test Job',
      task_type: 'protein_ligand_binding' as const,
      model_id: 'boltz2',
      input_data: {
        protein_sequence: 'MKTAYIAKQRQISFVKSHFSRQ',
        ligand_smiles: 'CCO'
      }
    };
    
    const result = JobCreateSchema.safeParse(validData);
    expect(result.success).toBe(true);
    
    if (result.success) {
      expect(result.data.job_name).toBe('Test Job');
      expect(result.data.task_type).toBe('protein_ligand_binding');
    }
  });
  
  it('should reject invalid job name', () => {
    const invalidData = {
      job_name: '', // Empty name
      task_type: 'protein_ligand_binding' as const,
      input_data: {}
    };
    
    const result = JobCreateSchema.safeParse(invalidData);
    expect(result.success).toBe(false);
    
    if (!result.success) {
      const jobNameErrors = result.error.issues.filter(
        issue => issue.path.includes('job_name')
      );
      expect(jobNameErrors.length).toBeGreaterThan(0);
    }
  });
  
  it('should validate protein sequence', () => {
    const { isValid, errors, warnings } = ValidationUtils.validateProteinSequence('MKTAYIAKQRQISFVKSHFSRQ');
    
    expect(isValid).toBe(true);
    expect(errors).toHaveLength(0);
  });
  
  it('should reject invalid protein sequence', () => {
    const { isValid, errors } = ValidationUtils.validateProteinSequence('INVALID123');
    
    expect(isValid).toBe(false);
    expect(errors.length).toBeGreaterThan(0);
    expect(errors[0]).toContain('Invalid amino acid codes');
  });
});
```

## Best Practices

### 1. Consistency
- Use identical validation rules in both backend and frontend
- Maintain snake_case naming throughout the stack
- Keep error messages consistent and user-friendly

### 2. Security
- Always validate on the server side (frontend validation is for UX)
- Sanitize inputs to prevent injection attacks
- Use allow-lists rather than deny-lists when possible

### 3. Performance
- Use efficient validation patterns
- Cache compiled schemas where possible
- Validate early and fail fast

### 4. Maintainability
- Keep validation logic in centralized utilities
- Use clear, descriptive error messages
- Document custom validation rules

### 5. User Experience
- Provide real-time validation feedback
- Show field-specific errors
- Offer suggestions for fixing validation errors

---

This comprehensive validation pattern ensures data integrity, type safety, and excellent user experience across the entire OMTX-Hub platform.