import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Download, 
  Search, 
  SortAsc, 
  SortDesc,
  TrendingDown,
  TrendingUp,
  Activity,
  Target,
  FileText,
  Database
} from 'lucide-react';

interface LigandResult {
  ligand_id: string;
  ligand_name: string;
  smiles: string;
  affinity_kcal_mol?: number;
  confidence_score?: number;
  ptm?: number;
  iplddt?: number;
  iptm?: number;
  interactions?: any[];
  status?: string;
}

interface BatchResultsData {
  batch_id: string;
  batch_info: {
    total_jobs: number;
    completed: number;
    failed: number;
    status: string;
    protein_sequence: string;
  };
  results: {
    affinity: LigandResult[];
    confidence: LigandResult[];
    interactions: LigandResult[];
  };
  summary: {
    total_predictions: number;
    successful_predictions: number;
    failed_predictions: number;
    best_affinity: number | null;
    worst_affinity: number | null;
  };
}

interface BatchResultsOutputProps {
  results: BatchResultsData;
  onDownloadResults: () => void;
}

type SortDirection = 'asc' | 'desc' | null;

export const BatchResultsOutput: React.FC<BatchResultsOutputProps> = ({
  results,
  onDownloadResults
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  // Sort and filter data
  const processData = (data: LigandResult[], searchTerm: string, sortField: string | null, sortDirection: SortDirection) => {
    let filtered = data;

    // Apply search filter
    if (searchTerm) {
      filtered = data.filter(item => 
        item.ligand_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.ligand_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.smiles.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply sorting
    if (sortField && sortDirection) {
      filtered = [...filtered].sort((a, b) => {
        let aVal = (a as any)[sortField];
        let bVal = (b as any)[sortField];

        if (aVal === null || aVal === undefined) aVal = sortDirection === 'asc' ? Infinity : -Infinity;
        if (bVal === null || bVal === undefined) bVal = sortDirection === 'asc' ? Infinity : -Infinity;

        if (typeof aVal === 'string') {
          return sortDirection === 'asc' 
            ? aVal.localeCompare(bVal)
            : bVal.localeCompare(aVal);
        }

        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      });
    }

    return filtered;
  };

  const handleSort = (field: string) => {
    if (sortField === field) {
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortField(null);
        setSortDirection(null);
      } else {
        setSortDirection('asc');
      }
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const SortIcon = ({ field }: { field: string }) => {
    if (sortField !== field) return null;
    return sortDirection === 'asc' ? <SortAsc className="h-3 w-3" /> : <SortDesc className="h-3 w-3" />;
  };

  const processedAffinityData = useMemo(() => 
    processData(results.results.affinity, searchTerm, sortField, sortDirection),
    [results.results.affinity, searchTerm, sortField, sortDirection]
  );

  const processedConfidenceData = useMemo(() => 
    processData(results.results.confidence, searchTerm, sortField, sortDirection),
    [results.results.confidence, searchTerm, sortField, sortDirection]
  );

  const processedInteractionData = useMemo(() => 
    processData(results.results.interactions, searchTerm, sortField, sortDirection),
    [results.results.interactions, searchTerm, sortField, sortDirection]
  );

  // Data table component
  const DataTable = ({ 
    data, 
    columns 
  }: { 
    data: any[], 
    columns: { key: string, label: string, sortable?: boolean, render?: (value: any, row: any) => React.ReactNode }[] 
  }) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700">
            {columns.map(column => (
              <th 
                key={column.key} 
                className={`text-left p-3 text-gray-300 font-medium ${
                  column.sortable ? 'cursor-pointer hover:text-white' : ''
                }`}
                onClick={column.sortable ? () => handleSort(column.key) : undefined}
              >
                <div className="flex items-center gap-2">
                  {column.label}
                  {column.sortable && <SortIcon field={column.key} />}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => (
            <tr key={index} className="border-b border-gray-800 hover:bg-gray-800/30">
              {columns.map(column => (
                <td key={column.key} className="p-3 text-gray-200">
                  {column.render ? column.render(row[column.key], row) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-white text-lg flex items-center gap-2">
                <Database className="h-5 w-5" />
                Batch Screening Results
              </CardTitle>
              <p className="text-gray-400 text-sm mt-1">
                Batch ID: {results.batch_id}
              </p>
            </div>
            <Button
              onClick={onDownloadResults}
              className="bg-green-600 hover:bg-green-700 text-white gap-2"
            >
              <Download className="h-4 w-4" />
              Download ZIP
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gray-800/50 border-gray-700">
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">
                {results.summary.successful_predictions}
              </div>
              <div className="text-xs text-gray-400">Successful</div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gray-800/50 border-gray-700">
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-red-400">
                {results.summary.failed_predictions}
              </div>
              <div className="text-xs text-gray-400">Failed</div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gray-800/50 border-gray-700">
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-400 flex items-center justify-center gap-1">
                {results.summary.best_affinity !== null ? (
                  <>
                    <TrendingDown className="h-4 w-4" />
                    {results.summary.best_affinity.toFixed(2)}
                  </>
                ) : (
                  'N/A'
                )}
              </div>
              <div className="text-xs text-gray-400">Best Affinity</div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gray-800/50 border-gray-700">
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-400 flex items-center justify-center gap-1">
                {results.summary.worst_affinity !== null ? (
                  <>
                    <TrendingUp className="h-4 w-4" />
                    {results.summary.worst_affinity.toFixed(2)}
                  </>
                ) : (
                  'N/A'
                )}
              </div>
              <div className="text-xs text-gray-400">Worst Affinity</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filter */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search by ligand ID, name, or SMILES..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-gray-800/50 border-gray-700 text-white"
              />
            </div>
            <Badge variant="secondary" className="text-xs">
              {results.results.affinity.length} compounds
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Results Tabs */}
      <Tabs defaultValue="affinity" className="w-full">
        <TabsList className="grid w-full grid-cols-3 bg-gray-800/50">
          <TabsTrigger value="affinity" className="flex items-center gap-2">
            <Target className="h-4 w-4" />
            Affinity Results
          </TabsTrigger>
          <TabsTrigger value="confidence" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Confidence Scores
          </TabsTrigger>
          <TabsTrigger value="interactions" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Interactions
          </TabsTrigger>
        </TabsList>

        <TabsContent value="affinity" className="mt-4">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white text-sm">Binding Affinity Results</CardTitle>
              <p className="text-gray-400 text-xs">
                Predicted binding affinities in kcal/mol (lower values indicate stronger binding)
              </p>
            </CardHeader>
            <CardContent>
              {processedAffinityData.length > 0 ? (
                <DataTable
                  data={processedAffinityData}
                  columns={[
                    { key: 'ligand_id', label: 'Ligand ID', sortable: true },
                    { key: 'ligand_name', label: 'Name', sortable: true },
                    { 
                      key: 'smiles', 
                      label: 'SMILES', 
                      render: (value) => (
                        <span className="font-mono text-xs bg-gray-900/50 px-2 py-1 rounded">
                          {value.length > 30 ? `${value.substring(0, 30)}...` : value}
                        </span>
                      )
                    },
                    { 
                      key: 'affinity_kcal_mol', 
                      label: 'Affinity (kcal/mol)', 
                      sortable: true,
                      render: (value) => value !== null && value !== undefined ? (
                        <span className={`font-medium ${
                          value < -8 ? 'text-green-400' : 
                          value < -6 ? 'text-yellow-400' : 'text-red-400'
                        }`}>
                          {value.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )
                    },
                    { 
                      key: 'confidence_score', 
                      label: 'Confidence', 
                      sortable: true,
                      render: (value) => value !== null && value !== undefined ? (
                        <span className="text-blue-400">
                          {(value * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )
                    }
                  ]}
                />
              ) : (
                <div className="text-center py-8 text-gray-400">
                  No affinity results found
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="confidence" className="mt-4">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white text-sm">Confidence Scores</CardTitle>
              <p className="text-gray-400 text-xs">
                Model confidence metrics for each prediction
              </p>
            </CardHeader>
            <CardContent>
              {processedConfidenceData.length > 0 ? (
                <DataTable
                  data={processedConfidenceData}
                  columns={[
                    { key: 'ligand_id', label: 'Ligand ID', sortable: true },
                    { key: 'ligand_name', label: 'Name', sortable: true },
                    { 
                      key: 'ptm', 
                      label: 'PTM Score', 
                      sortable: true,
                      render: (value) => value !== null && value !== undefined ? (
                        <span className="text-green-400">{(value * 100).toFixed(1)}%</span>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )
                    },
                    { 
                      key: 'iplddt', 
                      label: 'ipLDDT Score', 
                      sortable: true,
                      render: (value) => value !== null && value !== undefined ? (
                        <span className="text-blue-400">{(value * 100).toFixed(1)}%</span>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )
                    },
                    { 
                      key: 'iptm', 
                      label: 'ipTM Score', 
                      sortable: true,
                      render: (value) => value !== null && value !== undefined ? (
                        <span className="text-purple-400">{(value * 100).toFixed(1)}%</span>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )
                    }
                  ]}
                />
              ) : (
                <div className="text-center py-8 text-gray-400">
                  No confidence data found
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="interactions" className="mt-4">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white text-sm">Interaction Analysis</CardTitle>
              <p className="text-gray-400 text-xs">
                Detailed molecular interactions (when available)
              </p>
            </CardHeader>
            <CardContent>
              {processedInteractionData.length > 0 ? (
                <DataTable
                  data={processedInteractionData}
                  columns={[
                    { key: 'ligand_id', label: 'Ligand ID', sortable: true },
                    { key: 'ligand_name', label: 'Name', sortable: true },
                    { 
                      key: 'interactions', 
                      label: 'Interactions', 
                      render: (value) => value && value.length > 0 ? (
                        <Badge variant="secondary" className="text-xs">
                          {value.length} interactions
                        </Badge>
                      ) : (
                        <span className="text-gray-500">No data</span>
                      )
                    }
                  ]}
                />
              ) : (
                <div className="text-center py-8 text-gray-400">
                  No interaction data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};