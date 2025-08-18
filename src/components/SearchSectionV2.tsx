/**
 * Enhanced SearchSection component with API-driven model discovery
 * Replaces hardcoded models with dynamic API integration
 */

import React, { useState, useEffect } from 'react';
import { SearchBar } from '@/components/SearchBar';
import { FilterPanel } from '@/components/FilterPanel';
import { ModelGrid } from '@/components/ModelGrid';
import { ModelList } from '@/components/ModelList';
import { ModelSearchControls } from '@/components/ModelSearchControls';
import { modelService, ModelDefinition, ModelListResponse } from '@/services/modelService';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';

interface SearchSectionProps {
  className?: string;
}

export const SearchSectionV2: React.FC<SearchSectionProps> = ({ className }) => {
  const [models, setModels] = useState<ModelDefinition[]>([]);
  const [filteredModels, setFilteredModels] = useState<ModelDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedProvider, setSelectedProvider] = useState<string>('all');
  const [showInactive, setShowInactive] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [statistics, setStatistics] = useState<any>(null);

  // Load models on component mount
  useEffect(() => {
    loadModels();
    loadStatistics();
  }, [showInactive]);

  const loadModels = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response: ModelListResponse = await modelService.getModels({
        activeOnly: !showInactive
      });
      
      setModels(response.models);
      setFilteredModels(response.models);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load models');
      console.error('Error loading models:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const stats = await modelService.getModelStatistics();
      setStatistics(stats);
    } catch (err) {
      console.error('Error loading statistics:', err);
    }
  };

  // Filter models based on search term and filters
  useEffect(() => {
    let filtered = [...models];

    // Search term filter
    if (searchTerm) {
      filtered = filtered.filter(model =>
        model.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        model.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        model.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    // Category filter
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(model => {
        const category = getCategoryFromTasks(model.capabilities.supported_tasks);
        return category.toLowerCase() === selectedCategory.toLowerCase();
      });
    }

    // Provider filter
    if (selectedProvider !== 'all') {
      filtered = filtered.filter(model => 
        model.provider.toLowerCase() === selectedProvider.toLowerCase()
      );
    }

    setFilteredModels(filtered);
  }, [models, searchTerm, selectedCategory, selectedProvider]);

  const getCategoryFromTasks = (tasks: string[]): string => {
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
  };

  const getUniqueCategories = (): string[] => {
    const categories = new Set<string>();
    models.forEach(model => {
      const category = getCategoryFromTasks(model.capabilities.supported_tasks);
      categories.add(category);
    });
    return Array.from(categories);
  };

  const getUniqueProviders = (): string[] => {
    const providers = new Set<string>();
    models.forEach(model => {
      providers.add(model.provider);
    });
    return Array.from(providers);
  };

  // Convert models to display format for existing components
  const displayModels = filteredModels.map(model => ({
    id: model.id,
    title: model.name,
    description: model.description,
    author: getAuthorFromTags(model.tags),
    category: getCategoryFromTasks(model.capabilities.supported_tasks),
    bookmarked: false,
    version: model.version,
    provider: model.provider,
    tags: model.tags,
    is_active: model.is_active,
    capabilities: model.capabilities,
    resources: model.resources,
    documentation_url: model.documentation_url,
    paper_url: model.paper_url,
    license: model.license
  }));

  const getAuthorFromTags = (tags: string[]): string => {
    const authorTag = tags.find(tag => tag.includes('author:'));
    if (authorTag) {
      return authorTag.replace('author:', '');
    }
    return 'Research Team';
  };

  if (loading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-96" />
          </div>
          <Skeleton className="h-10 w-32" />
        </div>
        
        <div className="flex gap-4">
          <Skeleton className="h-10 flex-1" />
          <Skeleton className="h-10 w-32" />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`space-y-6 ${className}`}>
        <Alert variant="destructive">
          <AlertDescription>
            {error}
          </AlertDescription>
        </Alert>
        <button
          onClick={loadModels}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header with statistics */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold">Model Registry</h2>
          <p className="text-gray-600">
            Discover and explore {statistics?.active_models || models.length} available models
          </p>
        </div>
        
        {statistics && (
          <div className="flex gap-2">
            <Badge variant="secondary">
              {statistics.active_models} Active
            </Badge>
            <Badge variant="outline">
              {statistics.total_models} Total
            </Badge>
          </div>
        )}
      </div>

      {/* Search and controls */}
      <ModelSearchControls
        searchQuery={searchTerm}
        onSearchChange={setSearchTerm}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onFilterToggle={() => {}} // Placeholder for filter toggle
        showNewButton={false}
      />

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="px-3 py-2 border rounded-md bg-gray-800 border-gray-700 text-white"
        >
          <option value="all">All Categories</option>
          {getUniqueCategories().map(category => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>

        <select
          value={selectedProvider}
          onChange={(e) => setSelectedProvider(e.target.value)}
          className="px-3 py-2 border rounded-md bg-gray-800 border-gray-700 text-white"
        >
          <option value="all">All Providers</option>
          {getUniqueProviders().map(provider => (
            <option key={provider} value={provider}>
              {provider.charAt(0).toUpperCase() + provider.slice(1)}
            </option>
          ))}
        </select>

        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="show-inactive"
            checked={showInactive}
            onChange={(e) => setShowInactive(e.target.checked)}
            className="rounded"
          />
          <label htmlFor="show-inactive" className="text-sm text-gray-300">
            Show Inactive
          </label>
        </div>

        <Badge variant="outline">
          {filteredModels.length} models
        </Badge>
      </div>

      {/* Results */}
      {filteredModels.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No models found matching your criteria.</p>
        </div>
      ) : (
        <>
          {viewMode === 'grid' ? (
            <ModelGrid models={displayModels} />
          ) : (
            <ModelList models={displayModels} />
          )}
        </>
      )}
    </div>
  );
};