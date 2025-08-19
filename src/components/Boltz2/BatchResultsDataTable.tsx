import React, { useState } from 'react';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  getFilteredRowModel,
  useReactTable,
  SortingState,
  ColumnFiltersState,
} from '@tanstack/react-table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Download,
  Eye,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ArrowUpDown,
  CheckCircle,
  XCircle,
  Clock,
  FileDown,
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { 
  getAffinityColor, 
  getProbabilityColor,
  getConfidenceColor,
  getPLDDTColor,
  getIPDEColor,
  getMetricColor,
  getMetricDescription
} from '@/utils/boltz2Metrics';

interface IndividualJob {
  id: string;
  name: string;
  status: string;
  ligand_name?: string;
  ligand_smiles?: string;
  input_data?: {
    ligand_name?: string;
    ligand_smiles?: string;
    batch_index?: number;
  };
  results?: {
    affinity?: number;
    confidence?: number;
    ptm_score?: number;
    execution_time?: number;
    // Additional fields for better data mapping
    binding_score?: number;
    affinity_pred_value?: number;
    confidence_score?: number;
    ptm?: number;
  };
  output_data?: {
    affinity?: number;
    confidence?: number;
    ptm_score?: number;
    execution_time?: number;
    // Additional fields for better data mapping
    binding_score?: number;
    affinity_pred_value?: number;
    confidence_score?: number;
    ptm?: number;
  };
  // Raw modal data for comprehensive metrics
  raw_modal_result?: any;
  affinity_ensemble?: any;
  confidence_metrics?: any;
  prediction_confidence?: any;
  binding_affinity?: any;
}

interface BatchResultsDataTableProps {
  data: IndividualJob[];
  onViewStructure: (jobId: string) => void;
  onDownloadStructure: (jobId: string) => void;
  onDownloadAll: () => void;
}

export const BatchResultsDataTable: React.FC<BatchResultsDataTableProps> = ({
  data,
  onViewStructure,
  onDownloadStructure,
  onDownloadAll,
}) => {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  // Define columns
  const columns: ColumnDef<IndividualJob>[] = [
    {
      accessorKey: 'index',
      header: '#',
      cell: ({ row }) => {
        // Use ligand_name as the index since it contains the correct numbering (1, 2, 3...)
        // Fallback to row index + 1 if ligand_name is not a number
        const ligandName = row.original.ligand_name;
        const ligandNumber = ligandName && !isNaN(Number(ligandName)) ? Number(ligandName) : row.index + 1;
        return <span className="font-mono text-sm">{ligandNumber}</span>;
      },
      size: 50,
      // Add sorting function for numeric index
      sortingFn: (rowA, rowB) => {
        const indexA = Number(rowA.original.input_data?.batch_index || 0);
        const indexB = Number(rowB.original.input_data?.batch_index || 0);
        return indexA - indexB;
      },
    },
    {
      accessorKey: 'ligand_name',
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2"
          >
            Ligand Name
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => {
        // Try multiple paths for ligand name from enhanced results
        const name = row.original.input_data?.ligand_name || 
                     row.original.ligand_name || 
                     row.original.metadata?.ligand_name ||
                     row.original.name || 
                     `Ligand ${(row.original.input_data?.batch_index ?? 0) + 1}`;
        
        console.log('🔧 BatchDataTable ligand_name for row:', {
          original: row.original,
          input_data: row.original.input_data,
          metadata: row.original.metadata,
          extracted_name: name
        });
        
        return <span className="font-medium">{name}</span>;
      },
    },
    {
      accessorKey: 'ligand_smiles',
      header: 'SMILES',
      cell: ({ row }) => {
        // Try multiple paths for SMILES from enhanced results
        const smiles = row.original.input_data?.ligand_smiles || 
                       row.original.ligand_smiles ||
                       row.original.metadata?.ligand_smiles ||
                       '';
        
        console.log('🔧 BatchDataTable ligand_smiles for row:', {
          original: row.original,
          input_data: row.original.input_data,
          metadata: row.original.metadata,
          extracted_smiles: smiles
        });
        
        return (
          <code className="text-xs bg-gray-800 px-2 py-1 rounded max-w-[200px] truncate block">
            {smiles || 'N/A'}
          </code>
        );
      },
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const status = row.original.status;
        const statusConfig = {
          completed: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-900/20' },
          failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-900/20' },
          running: { icon: Clock, color: 'text-blue-400', bg: 'bg-blue-900/20' },
          pending: { icon: Clock, color: 'text-gray-400', bg: 'bg-gray-900/20' },
        };
        const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
        const Icon = config.icon;
        
        return (
          <Badge variant="secondary" className={cn(config.bg, 'border-0')}>
            <Icon className={cn('h-3 w-3 mr-1', config.color)} />
            <span className={config.color}>{status}</span>
          </Badge>
        );
      },
    },
    // === DIRECT BINDING OUTPUTS (Most Important) ===
    {
      accessorKey: 'affinity',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
            title="Log scale with 1 µM reference. More negative = stronger binding"
          >
            Affinity
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const results = row.original.results || row.original.result || row.original.output_data;
        const raw_modal = row.original.raw_modal_result || {};
        const affinity = raw_modal.affinity || results?.affinity || row.original.affinity;
        
        if (affinity === undefined || affinity === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className={cn(
              'font-mono text-sm',
              getAffinityColor(affinity)
            )}>
              {Number(affinity).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 90,
      sortingFn: (rowA, rowB) => {
        const getAffinity = (row: any) => {
          const results = row.original.results || row.original.result || row.original.output_data;
          const raw_modal = row.original.raw_modal_result || {};
          return raw_modal.affinity || results?.affinity || row.original.affinity || 0;
        };
        return Number(getAffinity(rowA)) - Number(getAffinity(rowB));
      },
    },
    {
      accessorKey: 'affinity_probability',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Affinity Prob
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const affinity_prob = raw_modal.affinity_probability;
        
        if (affinity_prob === undefined || affinity_prob === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className={cn(
              'font-mono text-sm',
              affinity_prob > 0.7 ? 'text-green-400' : affinity_prob > 0.4 ? 'text-yellow-400' : 'text-red-400'
            )}>
              {Number(affinity_prob).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 100,
    },
    // === ENSEMBLE SUPPORT (Consensus first) ===
    {
      accessorKey: 'affinity_ensemble_pred_value',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Ens. Affinity
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const ensemble_affinity = raw_modal.affinity_ensemble?.affinity_pred_value;
        
        if (ensemble_affinity === undefined || ensemble_affinity === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className={cn(
              'font-mono text-sm',
              getAffinityColor(ensemble_affinity)
            )}>
              {Number(ensemble_affinity).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 110,
    },
    {
      accessorKey: 'affinity_ensemble_prob_binary',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Ens. Prob
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const ensemble_prob = raw_modal.affinity_ensemble?.affinity_probability_binary;
        
        if (ensemble_prob === undefined || ensemble_prob === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className={cn(
              'font-mono text-sm',
              getProbabilityColor(ensemble_prob)
            )}>
              {Number(ensemble_prob).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 90,
      sortingFn: (rowA, rowB) => {
        const getEnsembleProb = (row: any) => {
          const raw_modal = row.original.raw_modal_result || {};
          return raw_modal.affinity_ensemble?.affinity_probability_binary || 0;
        };
        return Number(getEnsembleProb(rowA)) - Number(getEnsembleProb(rowB));
      },
    },
    {
      accessorKey: 'affinity_ensemble_pred_value2',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Ens. Aff 2
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const ensemble_affinity2 = raw_modal.affinity_ensemble?.affinity_pred_value2;
        
        if (ensemble_affinity2 === undefined || ensemble_affinity2 === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className={cn(
              'font-mono text-sm',
              getAffinityColor(ensemble_affinity2)
            )}>
              {Number(ensemble_affinity2).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 90,
    },
    {
      accessorKey: 'affinity_ensemble_prob_binary2',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Ens. Prob 2
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const ensemble_prob2 = raw_modal.affinity_ensemble?.affinity_probability_binary2;
        
        if (ensemble_prob2 === undefined || ensemble_prob2 === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className={cn(
              'font-mono text-sm',
              getProbabilityColor(ensemble_prob2)
            )}>
              {Number(ensemble_prob2).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 100,
    },
    {
      accessorKey: 'affinity_ensemble_pred_value1',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Ens. Aff 1
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const ensemble_affinity1 = raw_modal.affinity_ensemble?.affinity_pred_value1;
        
        if (ensemble_affinity1 === undefined || ensemble_affinity1 === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className="font-mono text-sm text-cyan-400">
              {Number(ensemble_affinity1).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 90,
    },
    {
      accessorKey: 'affinity_ensemble_prob_binary1',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Ens. Prob 1
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const ensemble_prob1 = raw_modal.affinity_ensemble?.affinity_probability_binary1;
        
        if (ensemble_prob1 === undefined || ensemble_prob1 === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className="font-mono text-sm text-cyan-400">
              {Number(ensemble_prob1).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 100,
    },
    // === MODEL-LEVEL RELIABILITY ===
    {
      accessorKey: 'confidence',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Confidence
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const results = row.original.results || row.original.result || row.original.output_data;
        const confidence = raw_modal.confidence || raw_modal.confidence_metrics?.confidence_score || 
                          results?.confidence || row.original.confidence;
        
        if (confidence === undefined || confidence === null) return <div className="text-center text-gray-500">-</div>;
        
        const colorClass = confidence > 0.8 ? 'text-green-400' : 
                          confidence > 0.6 ? 'text-yellow-400' : 'text-red-400';
        
        return (
          <div className="text-center">
            <span className={cn('font-mono text-sm', colorClass)}>
              {Number(confidence).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 90,
      sortingFn: (rowA, rowB) => {
        const getConfidence = (row: any) => {
          const raw_modal = row.original.raw_modal_result || {};
          const results = row.original.results || row.original.result || row.original.output_data;
          return raw_modal.confidence || raw_modal.confidence_metrics?.confidence_score || 
                 results?.confidence || row.original.confidence || 0;
        };
        return Number(getConfidence(rowA)) - Number(getConfidence(rowB));
      },
    },
    // === INTERFACE-SPECIFIC STRUCTURE CONFIDENCE ===
    {
      accessorKey: 'iptm_score',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            iPTM
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const iptm = raw_modal.confidence_metrics?.iptm || raw_modal.iptm_score;
        
        if (iptm === undefined || iptm === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className="font-mono text-sm text-indigo-400">
              {Number(iptm).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 80,
    },
    {
      accessorKey: 'ligand_iptm_score',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Ligand iPTM
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const ligand_iptm = raw_modal.confidence_metrics?.ligand_iptm;
        
        if (ligand_iptm === undefined || ligand_iptm === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className="font-mono text-sm text-indigo-400">
              {Number(ligand_iptm).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 110,
    },
    {
      accessorKey: 'complex_iplddt',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Complex ipLDDT
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const complex_iplddt = raw_modal.confidence_metrics?.complex_iplddt;
        
        if (complex_iplddt === undefined || complex_iplddt === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className="font-mono text-sm text-teal-400">
              {Number(complex_iplddt).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 120,
    },
    {
      accessorKey: 'complex_ipde',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Complex iPDE
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const complex_ipde = raw_modal.confidence_metrics?.complex_ipde;
        
        if (complex_ipde === undefined || complex_ipde === null) return <div className="text-center text-gray-500">-</div>;
        
        const colorClass = complex_ipde < 5 ? 'text-green-400' : complex_ipde < 10 ? 'text-yellow-400' : 'text-red-400';
        
        return (
          <div className="text-center">
            <span className={cn('font-mono text-sm', colorClass)}>
              {Number(complex_ipde).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 110,
    },
    // === GLOBAL/MONOMER STRUCTURE CONFIDENCE ===
    {
      accessorKey: 'complex_plddt',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            Complex pLDDT
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const complex_plddt = raw_modal.confidence_metrics?.complex_plddt || raw_modal.plddt_score;
        
        if (complex_plddt === undefined || complex_plddt === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className="font-mono text-sm text-amber-400">
              {Number(complex_plddt).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 120,
    },
    {
      accessorKey: 'ptm_score',
      header: ({ column }) => (
        <div className="flex justify-center">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-8 px-2 whitespace-nowrap"
          >
            PTM
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      ),
      cell: ({ row }) => {
        const raw_modal = row.original.raw_modal_result || {};
        const ptm = raw_modal.confidence_metrics?.ptm || raw_modal.ptm_score;
        
        if (ptm === undefined || ptm === null) return <div className="text-center text-gray-500">-</div>;
        
        return (
          <div className="text-center">
            <span className="font-mono text-sm text-amber-400">
              {Number(ptm).toFixed(4)}
            </span>
          </div>
        );
      },
      size: 80,
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const isCompleted = row.original.status === 'completed';
        
        return (
          <div className="flex gap-1">
            <Button
              size="sm"
              onClick={() => onDownloadStructure(row.original.id)}
              disabled={!isCompleted}
              className="h-8 px-2 bg-gradient-to-r from-cyan-400 to-blue-500 to-purple-600 hover:from-cyan-500 hover:to-blue-600 hover:to-purple-700 text-white border-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className="h-4 w-4" />
              <span className="ml-1 hidden lg:inline">.CIF</span>
            </Button>
          </div>
        );
      },
    },
  ];

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    initialState: {
      pagination: {
        pageSize: 25,
      },
    },
  });

  return (
    <div className="space-y-4">
      {/* Metric Legend */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3">
        <div className="text-xs text-gray-400 space-y-1">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="font-semibold">Affinity Color Legend:</span>
              <span className="text-green-400">≤ -1 (Strong, {'<'}0.1 µM)</span>
              <span className="text-yellow-400">-1 to 0 (Moderate, 0.1-1 µM)</span>
              <span className="text-orange-400">0 to 1 (Weak, 1-10 µM)</span>
              <span className="text-red-400">{'>'}1 (Poor, {'>'}10 µM)</span>
            </div>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            <strong>Note:</strong> Affinity uses log scale with 1 µM reference. More negative = stronger binding (per Boltz-2 paper)
          </div>
        </div>
      </div>

      {/* Header with search */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Input
            placeholder="Search all columns..."
            value={globalFilter ?? ''}
            onChange={(event) => setGlobalFilter(event.target.value)}
            className="h-8 w-[250px] bg-gray-800 border-gray-700"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border border-gray-700 overflow-hidden">
        <div className="overflow-x-auto max-w-full">
        <Table className="min-w-[2000px]">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id} className="border-gray-700 bg-gray-800/50">
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead
                      key={header.id}
                      className="text-gray-300"
                      style={{ width: header.getSize() }}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && 'selected'}
                  className="border-gray-700 hover:bg-gray-800/30"
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="text-gray-100">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center text-gray-400"
                >
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-400">
            {table.getFilteredRowModel().rows.length} result(s)
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-400">Show</span>
            <Select
              value={`${table.getState().pagination.pageSize}`}
              onValueChange={(value) => {
                table.setPageSize(Number(value));
              }}
            >
              <SelectTrigger className="h-8 w-[70px] bg-gray-800 border-gray-700 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700">
                <SelectItem value="25" className="text-white focus:bg-gray-700 focus:text-white data-[state=checked]:text-white">25</SelectItem>
                <SelectItem value="50" className="text-white focus:bg-gray-700 focus:text-white data-[state=checked]:text-white">50</SelectItem>
                <SelectItem value="100" className="text-white focus:bg-gray-700 focus:text-white data-[state=checked]:text-white">100</SelectItem>
              </SelectContent>
            </Select>
            <span className="text-sm text-gray-400">entries</span>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
            className="h-8 w-8 p-0"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="h-8 w-8 p-0"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm text-gray-400">
            Page {table.getState().pagination.pageIndex + 1} of{' '}
            {table.getPageCount()}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="h-8 w-8 p-0"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
            className="h-8 w-8 p-0"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};