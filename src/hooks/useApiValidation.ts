/**
 * Custom hooks for API validation using Zod schemas
 */

import { useState, useCallback } from 'react';
import { z } from 'zod';
import { 
  safeParseApiResponse,
  JobCreateSchema, JobResponseSchema, JobDetailResponseSchema,
  JobListResponseSchema, SystemStatusResponseSchema,
  type JobCreate, type JobResponse, type JobDetailResponse,
  type JobListResponse, type SystemStatusResponse
} from '../schemas/apiSchemas';

// Generic validation hook
export function useApiValidation<T>(schema: z.ZodSchema<T>) {
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isValid, setIsValid] = useState(true);

  const validate = useCallback((data: unknown): T | null => {
    const result = safeParseApiResponse(schema, data);
    
    if (result.success) {
      setValidationErrors([]);
      setIsValid(true);
      return result.data;
    } else {
      setValidationErrors(['error' in result ? result.error : 'Validation failed']);
      setIsValid(false);
      return null;
    }
  }, [schema]);

  const clearErrors = useCallback(() => {
    setValidationErrors([]);
    setIsValid(true);
  }, []);

  return {
    validate,
    validationErrors,
    isValid,
    clearErrors,
  };
}

// Specific hooks for common API operations
export function useJobValidation() {
  const createValidation = useApiValidation(JobCreateSchema);
  const responseValidation = useApiValidation(JobResponseSchema);
  const detailValidation = useApiValidation(JobDetailResponseSchema);
  const listValidation = useApiValidation(JobListResponseSchema);

  return {
    validateCreate: createValidation.validate,
    validateResponse: responseValidation.validate,
    validateDetail: detailValidation.validate,
    validateList: listValidation.validate,
    errors: {
      create: createValidation.validationErrors,
      response: responseValidation.validationErrors,
      detail: detailValidation.validationErrors,
      list: listValidation.validationErrors,
    },
    isValid: {
      create: createValidation.isValid,
      response: responseValidation.isValid,
      detail: detailValidation.isValid,
      list: listValidation.isValid,
    },
    clearErrors: () => {
      createValidation.clearErrors();
      responseValidation.clearErrors();
      detailValidation.clearErrors();
      listValidation.clearErrors();
    },
  };
}

export function useSystemValidation() {
  const statusValidation = useApiValidation(SystemStatusResponseSchema);

  return {
    validateStatus: statusValidation.validate,
    errors: statusValidation.validationErrors,
    isValid: statusValidation.isValid,
    clearErrors: statusValidation.clearErrors,
  };
}

// Form validation hook for creating jobs
export function useJobFormValidation() {
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  const validateJobForm = useCallback((formData: Partial<JobCreate>): JobCreate | null => {
    try {
      const validatedData = JobCreateSchema.parse(formData);
      setErrors({});
      return validatedData;
    } catch (error) {
      if (error instanceof z.ZodError) {
        const fieldErrors: Record<string, string> = {};
        error.issues.forEach((issue) => {
          const path = issue.path.join('.');
          fieldErrors[path] = issue.message;
        });
        setErrors(fieldErrors);
      }
      return null;
    }
  }, []);

  const clearFormErrors = useCallback(() => {
    setErrors({});
  }, []);

  const getFieldError = useCallback((fieldName: string): string | undefined => {
    return errors[fieldName];
  }, [errors]);

  return {
    validateJobForm,
    errors,
    clearFormErrors,
    getFieldError,
    hasErrors: Object.keys(errors).length > 0,
  };
}

// Hook for validating API responses with retry logic
export function useApiResponseValidation<T>(
  schema: z.ZodSchema<T>,
  onValidationError?: (errors: string[]) => void
) {
  const [lastValidData, setLastValidData] = useState<T | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const validateResponse = useCallback((data: unknown): T | null => {
    const result = safeParseApiResponse(schema, data);
    
    if (result.success) {
      setLastValidData(result.data);
      setValidationErrors([]);
      return result.data;
    } else {
      const errors = ['error' in result ? result.error : 'Validation failed'];
      setValidationErrors(errors);
      onValidationError?.(errors);
      return null;
    }
  }, [schema, onValidationError]);

  return {
    validateResponse,
    lastValidData,
    validationErrors,
    hasErrors: validationErrors.length > 0,
  };
}