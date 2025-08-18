/**
 * Dynamic Task Form Component
 * Generates forms based on task schemas
 */

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { taskSchemaService, TaskSchema, InputField } from '@/services/taskSchemaService';
import { Info, Clock, HelpCircle } from 'lucide-react';

interface DynamicTaskFormProps {
  taskId: string;
  onSubmit: (data: Record<string, any>) => void;
  loading?: boolean;
  initialValues?: Record<string, any>;
  hideSubmitButton?: boolean;
}

export const DynamicTaskForm: React.FC<DynamicTaskFormProps> = ({
  taskId,
  onSubmit,
  loading = false,
  initialValues = {},
  hideSubmitButton = false,
}) => {
  const [schema, setSchema] = useState<TaskSchema | null>(null);
  const [formLoading, setFormLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validationSchema, setValidationSchema] = useState<z.ZodSchema | null>(null);

  const form = useForm({
    resolver: validationSchema ? zodResolver(validationSchema) : undefined,
    defaultValues: initialValues,
  });

  useEffect(() => {
    loadTaskSchema();
  }, [taskId]);

  const loadTaskSchema = async () => {
    try {
      setFormLoading(true);
      setError(null);
      
      const taskSchema = await taskSchemaService.getTaskSchema(taskId);
      setSchema(taskSchema);
      
      // Create Zod validation schema
      const zodSchema = createZodSchema(taskSchema.input_fields);
      setValidationSchema(zodSchema);
      
      // Set default values
      const defaults = await taskSchemaService.getDefaultValues(taskId);
      const merged = { ...defaults, ...initialValues };
      form.reset(merged);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load task schema');
      console.error('Error loading task schema:', err);
    } finally {
      setFormLoading(false);
    }
  };

  const createZodSchema = (fields: InputField[]): z.ZodSchema => {
    const shape: Record<string, z.ZodTypeAny> = {};
    
    fields.forEach(field => {
      let fieldSchema: z.ZodTypeAny;
      
      // Base type
      switch (field.field_type) {
        case 'number':
          fieldSchema = z.number();
          break;
        case 'checkbox':
          fieldSchema = z.boolean();
          break;
        default:
          fieldSchema = z.string();
      }
      
      // Apply validation rules
      if (field.validation) {
        field.validation.forEach(rule => {
          switch (rule.rule_type) {
            case 'required':
              if (rule.value && field.field_type === 'text') {
                fieldSchema = (fieldSchema as z.ZodString).min(1, rule.message);
              }
              break;
            case 'min_length':
              if (field.field_type === 'text') {
                fieldSchema = (fieldSchema as z.ZodString).min(Number(rule.value), rule.message);
              }
              break;
            case 'max_length':
              if (field.field_type === 'text') {
                fieldSchema = (fieldSchema as z.ZodString).max(Number(rule.value), rule.message);
              }
              break;
            case 'pattern':
              if (field.field_type === 'text') {
                fieldSchema = (fieldSchema as z.ZodString).regex(new RegExp(String(rule.value)), rule.message);
              }
              break;
          }
        });
      }
      
      // Check if field is required
      const isRequired = field.validation?.some(rule => rule.rule_type === 'required' && rule.value);
      if (!isRequired) {
        fieldSchema = fieldSchema.optional();
      }
      
      shape[field.id] = fieldSchema;
    });
    
    return z.object(shape);
  };

  const formatEstimatedTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `~${hours}h ${minutes % 60}m`;
    }
    return `~${minutes}m`;
  };

  const renderField = (field: InputField) => {
    const { id, label, field_type, description, placeholder, options, help_text } = field;
    
    return (
      <FormField
        key={id}
        control={form.control}
        name={id}
        render={({ field: formField }) => (
          <FormItem>
            <FormLabel className="text-white">
              {label}
              {field.validation?.some(rule => rule.rule_type === 'required' && rule.value) && (
                <span className="text-red-400 ml-1">*</span>
              )}
            </FormLabel>
            
            <FormControl>
              {field_type === 'text' || field_type === 'sequence' || field_type === 'smiles' ? (
                <Input
                  {...formField}
                  placeholder={placeholder}
                  className="bg-gray-800 border-gray-700 text-white"
                />
              ) : field_type === 'textarea' ? (
                <Textarea
                  {...formField}
                  placeholder={placeholder}
                  className="bg-gray-800 border-gray-700 text-white min-h-[100px]"
                />
              ) : field_type === 'number' ? (
                <Input
                  {...formField}
                  type="number"
                  placeholder={placeholder}
                  className="bg-gray-800 border-gray-700 text-white"
                  onChange={(e) => formField.onChange(Number(e.target.value))}
                />
              ) : field_type === 'select' ? (
                <Select onValueChange={formField.onChange} value={formField.value}>
                  <SelectTrigger className="bg-gray-800 border-gray-700 text-white">
                    <SelectValue placeholder={placeholder} />
                  </SelectTrigger>
                  <SelectContent>
                    {options?.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : field_type === 'checkbox' ? (
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id={id}
                    checked={formField.value}
                    onCheckedChange={formField.onChange}
                  />
                  <Label htmlFor={id} className="text-sm text-gray-300">
                    {description || label}
                  </Label>
                </div>
              ) : (
                <Input
                  {...formField}
                  placeholder={placeholder}
                  className="bg-gray-800 border-gray-700 text-white"
                />
              )}
            </FormControl>
            
            {description && field_type !== 'checkbox' && (
              <FormDescription className="text-gray-400">
                {description}
              </FormDescription>
            )}
            
            {help_text && (
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <HelpCircle className="h-3 w-3" />
                {help_text}
              </div>
            )}
            
            <FormMessage />
          </FormItem>
        )}
      />
    );
  };

  const handleSubmit = (data: Record<string, any>) => {
    // Add task type to submission data
    const submitData = {
      ...data,
      task_type: taskId,
    };
    
    onSubmit(submitData);
  };

  if (formLoading) {
    return (
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-96" />
        </CardHeader>
        <CardContent className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-gray-800/50 border-gray-700">
        <CardContent className="pt-6">
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!schema) {
    return null;
  }

  return (
    <Card className="bg-gray-800/50 border-gray-700">
      <CardHeader>
        <CardTitle className="text-xl font-bold bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 bg-clip-text text-transparent tracking-wide">
          {schema.task_name}
        </CardTitle>
        <CardDescription className="text-gray-400">
          {schema.description}
        </CardDescription>
        
        {schema.estimated_time && (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Clock className="h-4 w-4" />
            <span>Estimated time: {formatEstimatedTime(schema.estimated_time)}</span>
          </div>
        )}
      </CardHeader>
      
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {schema.input_fields.map(renderField)}
            
            {schema.examples && schema.examples.length > 0 && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-2">
                    <p className="font-medium">Example inputs:</p>
                    {schema.examples.map((example, index) => (
                      <div key={index} className="bg-gray-900 p-2 rounded text-xs">
                        <pre>{JSON.stringify(example, null, 2)}</pre>
                      </div>
                    ))}
                  </div>
                </AlertDescription>
              </Alert>
            )}
            
            {!hideSubmitButton && !taskId.includes('batch') && (
              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white"
              >
                {loading ? 'Submitting...' : 'Submit Prediction'}
              </Button>
            )}
          </form>
        </Form>
      </CardContent>
    </Card>
  );
};