import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Filter, X, Download } from 'lucide-react';

interface FilterRule {
  id: string;
  column: string;
  operator: string;
  value: string;
}

interface JobsFilterControlsProps {
  onFilterChange?: (filters: FilterRule[]) => void;
  selectedJobsCount?: number;
  canDownload?: boolean;
  canDelete?: boolean;
  onBulkDelete?: () => void;
  onDownload?: () => void;
}

export const JobsFilterControls: React.FC<JobsFilterControlsProps> = ({ 
  onFilterChange,
  selectedJobsCount = 0,
  canDownload = false,
  canDelete = false,
  onBulkDelete,
  onDownload,
}) => {
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<FilterRule[]>([]);

  const columns = [
    { value: 'name', label: 'Job Name' },
    { value: 'type', label: 'Type' },
    { value: 'status', label: 'Status' },
    { value: 'submitted', label: 'Submitted' },
  ];

  const operators = [
    { value: 'contains', label: 'contains' },
    { value: 'equals', label: 'equals' },
    { value: 'startsWith', label: 'starts with' },
    { value: 'endsWith', label: 'ends with' },
    { value: 'isEmpty', label: 'is empty' },
    { value: 'isNotEmpty', label: 'is not empty' },
    { value: 'isAnyOf', label: 'is any of' },
  ];

  const addFilter = () => {
    const newFilter: FilterRule = {
      id: Date.now().toString(),
      column: 'name',
      operator: 'contains',
      value: '',
    };
    const updatedFilters = [...filters, newFilter];
    setFilters(updatedFilters);
    onFilterChange?.(updatedFilters);
  };

  const removeFilter = (filterId: string) => {
    const updatedFilters = filters.filter(f => f.id !== filterId);
    setFilters(updatedFilters);
    onFilterChange?.(updatedFilters);
  };

  const updateFilter = (filterId: string, field: keyof FilterRule, value: string) => {
    const updatedFilters = filters.map(f => 
      f.id === filterId ? { ...f, [field]: value } : f
    );
    setFilters(updatedFilters);
    onFilterChange?.(updatedFilters);
  };

  const clearAllFilters = () => {
    setFilters([]);
    onFilterChange?.([]);
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Button
          onClick={() => setShowFilters(!showFilters)}
          className="bg-[#E2E756] hover:bg-[#d4d347] text-black font-medium border-0"
        >
          <Filter className="w-4 h-4 mr-2" />
          Filters
        </Button>
        <Button className="bg-[#E2E756] hover:bg-[#d4d347] text-black font-medium border-0">
          <Download className="w-4 h-4 mr-2" />
          Export
        </Button>
        <Button 
          variant="ghost" 
          onClick={canDownload ? onDownload : undefined}
          disabled={!canDownload}
          className={`transition-colors ${
            canDownload 
              ? 'text-[#E2E756] hover:text-[#d4d347] hover:bg-[#E2E756]/10 bg-[#E2E756]/5' 
              : 'text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
        >
          Download Results
        </Button>
        <Button 
          variant="ghost" 
          onClick={canDelete ? onBulkDelete : undefined}
          disabled={!canDelete}
          className={`transition-colors ${
            canDelete 
              ? 'text-[#E2E756] hover:text-[#d4d347] hover:bg-[#E2E756]/10 bg-[#E2E756]/5' 
              : 'text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
        >
          Delete Jobs {selectedJobsCount > 0 && `(${selectedJobsCount})`}
        </Button>
        {filters.length > 0 && (
          <Button
            onClick={clearAllFilters}
            variant="outline"
            className="border-gray-600 text-gray-300 hover:bg-gray-700"
          >
            Clear All ({filters.length})
          </Button>
        )}
      </div>

      {showFilters && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-white font-medium">Filter Jobs</h3>
            <Button
              onClick={() => setShowFilters(false)}
              variant="ghost"
              size="sm"
              className="text-gray-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>

          <div className="space-y-3">
            <div className="grid grid-cols-12 gap-3 text-sm text-gray-400">
              <div className="col-span-1"></div>
              <div className="col-span-3">Columns</div>
              <div className="col-span-3">Operator</div>
              <div className="col-span-4">Value</div>
              <div className="col-span-1"></div>
            </div>

            {filters.map((filter, index) => (
              <div key={filter.id} className="grid grid-cols-12 gap-3 items-center">
                <div className="col-span-1">
                  <Checkbox
                    checked={true}
                    className="w-4 h-4 border-gray-500 data-[state=checked]:bg-[#E2E756] data-[state=checked]:border-[#E2E756] data-[state=checked]:text-black"
                  />
                </div>
                <div className="col-span-3">
                  <Select
                    value={filter.column}
                    onValueChange={(value) => updateFilter(filter.id, 'column', value)}
                  >
                    <SelectTrigger className="bg-gray-700 border-gray-600 text-white text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-700 border-gray-600">
                      {columns.map(col => (
                        <SelectItem key={col.value} value={col.value} className="text-white">
                          {col.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="col-span-3">
                  <Select
                    value={filter.operator}
                    onValueChange={(value) => updateFilter(filter.id, 'operator', value)}
                  >
                    <SelectTrigger className="bg-gray-700 border-gray-600 text-white text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-700 border-gray-600">
                      {operators.map(op => (
                        <SelectItem key={op.value} value={op.value} className="text-white">
                          {op.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="col-span-4">
                  <Input
                    placeholder={filter.operator === 'isEmpty' || filter.operator === 'isNotEmpty' ? 'No value needed' : 'Filter value'}
                    value={filter.value}
                    onChange={(e) => updateFilter(filter.id, 'value', e.target.value)}
                    disabled={filter.operator === 'isEmpty' || filter.operator === 'isNotEmpty'}
                    className="bg-gray-700 border-gray-600 text-white placeholder-gray-500 text-sm"
                  />
                </div>
                <div className="col-span-1">
                  <Button
                    onClick={() => removeFilter(filter.id)}
                    variant="ghost"
                    size="sm"
                    className="text-gray-400 hover:text-red-400 p-1"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex gap-2 pt-2 border-t border-gray-700">
            <Button
              onClick={addFilter}
              variant="outline"
              size="sm"
              className="border-[#E2E756] text-[#E2E756] hover:bg-[#E2E756] hover:text-black"
            >
              Add Filter
            </Button>
            {filters.length > 0 && (
              <div className="text-sm text-gray-400 flex items-center">
                {filters.length} filter{filters.length !== 1 ? 's' : ''} applied
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
