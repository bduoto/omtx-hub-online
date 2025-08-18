
import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { 
  ChevronUp, 
  ChevronDown, 
  MoreVertical, 
  ArrowUp, 
  ArrowDown, 
  Filter, 
  EyeOff 
} from 'lucide-react';

interface ColumnVisibility {
  checkbox: boolean;
  name: boolean;
  type: boolean;
  status: boolean;
  submitted: boolean;
  actions: boolean;
}

interface TableContentProps {
  jobRows: Array<{
    id: string;
    name: string;
    type: string;
    status: 'Complete' | 'Failed' | 'In Progress' | 'Running';
    submitted: string;
  }>;
  selectedJobs: Set<string>;
  columnVisibility: ColumnVisibility;
  sortColumn: string | null;
  sortDirection: 'asc' | 'desc';
  onJobSelect: (jobId: string, checked: boolean) => void;
  onSelectAll: (checked: boolean) => void;
  onSort: (column: string) => void;
  onColumnSort: (column: string, direction: 'asc' | 'desc') => void;
  onHideColumn: (columnKey: keyof ColumnVisibility) => void;
  onColumnToggle: (columnKey: keyof ColumnVisibility) => void;
  onShowAll: () => void;
  onHideAll: () => void;
  onViewJob?: (jobId: string) => void;
  isLoading?: boolean;
}

const TableContent: React.FC<TableContentProps> = ({
  jobRows,
  selectedJobs,
  columnVisibility,
  sortColumn,
  sortDirection,
  onJobSelect,
  onSelectAll,
  onSort,
  onColumnSort,
  onHideColumn,
  onColumnToggle,
  onShowAll,
  onHideAll,
  onViewJob,
  isLoading,
}) => {
  const getStatusBadge = React.useCallback((status: string) => {
    switch (status) {
      case 'Complete':
        return (
          <span className="px-3 py-1 rounded-full text-xs bg-green-900 text-green-300 border border-green-700 font-medium">
            {status}
          </span>
        );
      case 'Running':
        return (
          <span className="px-3 py-1 rounded-full text-xs bg-orange-900 text-orange-300 border border-orange-700 font-medium">
            {status}
          </span>
        );
      case 'Failed':
        return (
          <span className="px-3 py-1 rounded-full text-xs bg-red-900 text-red-300 border border-red-700 font-medium">
            {status}
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 rounded-full text-xs bg-gray-900 text-gray-300 border border-gray-700 font-medium">
            {status}
          </span>
        );
    }
  }, []);

  const ColumnHeaderDropdown = React.memo(({ column, label }: { column: string; label: string }) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="p-1 hover:bg-gray-600 rounded">
          <MoreVertical className="w-4 h-4 cursor-pointer hover:text-[#E2E756]" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="bg-gray-700 border-gray-600 text-white">
        <DropdownMenuItem 
          onClick={() => onColumnSort(column, 'asc')}
          className="cursor-pointer hover:bg-gray-600"
        >
          <ArrowUp className="w-4 h-4 mr-2" />
          Sort by ASC
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => onColumnSort(column, 'desc')}
          className="cursor-pointer hover:bg-gray-600"
        >
          <ArrowDown className="w-4 h-4 mr-2" />
          Sort by DESC
        </DropdownMenuItem>
        <DropdownMenuSeparator className="bg-gray-600" />
        <Popover>
          <PopoverTrigger asChild>
            <DropdownMenuItem 
              onSelect={(e) => e.preventDefault()}
              className="cursor-pointer hover:bg-gray-600"
            >
              <Filter className="w-4 h-4 mr-2" />
              Filter
            </DropdownMenuItem>
          </PopoverTrigger>
          <PopoverContent className="bg-gray-700 border-gray-600 text-white w-80">
            <div className="space-y-4">
              <h4 className="font-medium">Filter {label}</h4>
              <div className="space-y-2">
                <label className="text-sm text-gray-300">Column</label>
                <Select>
                  <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                    <SelectValue placeholder="Select column" />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-700 border-gray-600">
                    <SelectItem value={column} className="text-white">{label}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm text-gray-300">Operator</label>
                <Select>
                  <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                    <SelectValue placeholder="Select operator" />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-700 border-gray-600">
                    <SelectItem value="equals" className="text-white">Equals</SelectItem>
                    <SelectItem value="contains" className="text-white">Contains</SelectItem>
                    <SelectItem value="startsWith" className="text-white">Starts with</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm text-gray-300">Value</label>
                <Input 
                  placeholder="Enter value"
                  className="bg-gray-800 border-gray-600 text-white"
                />
              </div>
              <div className="flex gap-2">
                <Button size="sm" className="bg-[#E2E756] hover:bg-[#d4d347] text-black">
                  Apply
                </Button>
                <Button size="sm" variant="outline" className="border-gray-600 text-gray-300">
                  Clear
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
        <DropdownMenuItem 
          onClick={() => onHideColumn(column as keyof ColumnVisibility)}
          className="cursor-pointer hover:bg-gray-600"
        >
          <EyeOff className="w-4 h-4 mr-2" />
          Hide column
        </DropdownMenuItem>
        <DropdownMenuSeparator className="bg-gray-600" />
        <Popover>
          <PopoverTrigger asChild>
            <DropdownMenuItem 
              onSelect={(e) => e.preventDefault()}
              className="cursor-pointer hover:bg-gray-600"
            >
              <div className="flex items-center mr-2">
                <div className="w-1 h-4 bg-current mr-0.5"></div>
                <div className="w-1 h-4 bg-current mr-0.5"></div>
                <div className="w-1 h-4 bg-current"></div>
              </div>
              Manage columns
            </DropdownMenuItem>
          </PopoverTrigger>
          <PopoverContent className="bg-gray-700 border-gray-600 text-white w-64">
            <div className="space-y-4">
              <h4 className="font-medium">Manage Columns</h4>
              <div className="space-y-3">
                {[
                  { key: 'checkbox', label: 'Checkbox' },
                  { key: 'name', label: 'Job Name' },
                  { key: 'type', label: 'Type' },
                  { key: 'status', label: 'Status' },
                  { key: 'submitted', label: 'Submitted' },
                  { key: 'actions', label: 'Actions' },
                ].map(col => (
                  <div key={col.key} className="flex items-center justify-between">
                    <span className="text-sm">{col.label}</span>
                    <Checkbox
                      checked={columnVisibility[col.key as keyof ColumnVisibility]}
                      onCheckedChange={() => onColumnToggle(col.key as keyof ColumnVisibility)}
                      className="w-4 h-4 border-gray-500 data-[state=checked]:bg-[#E2E756] data-[state=checked]:border-[#E2E756] data-[state=checked]:text-black"
                    />
                  </div>
                ))}
              </div>
              <div className="flex gap-2 pt-2 border-t border-gray-600">
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={onShowAll}
                  className="flex-1 border-gray-600 text-gray-300 text-xs"
                >
                  Show All
                </Button>
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={onHideAll}
                  className="flex-1 border-gray-600 text-gray-300 text-xs"
                >
                  Hide All
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      </DropdownMenuContent>
    </DropdownMenu>
  ));

  return (
    <Card className="bg-gray-800 border-gray-700 shadow-sm">
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow className="border-gray-700 hover:bg-gray-700">
              {columnVisibility.checkbox && (
                <TableHead className="w-12 text-gray-400">
                  <Checkbox
                    checked={selectedJobs.size === jobRows.length}
                    onCheckedChange={onSelectAll}
                    className="w-6 h-6 border-2 border-gray-500 data-[state=checked]:bg-[#E2E756] data-[state=checked]:border-[#E2E756] data-[state=checked]:text-black"
                  />
                </TableHead>
              )}
              {columnVisibility.name && (
                <TableHead 
                  className="text-gray-300 font-semibold cursor-pointer hover:text-white group"
                  onClick={() => onSort('name')}
                >
                  <div className="flex items-center justify-between">
                    <span>Job Name</span>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {sortColumn === 'name' ? (
                        sortDirection === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronUp className="w-4 h-4" />
                      )}
                      <ColumnHeaderDropdown column="name" label="Job Name" />
                    </div>
                  </div>
                </TableHead>
              )}
              {columnVisibility.type && (
                <TableHead 
                  className="text-gray-300 font-semibold cursor-pointer hover:text-white group"
                  onClick={() => onSort('type')}
                >
                  <div className="flex items-center justify-between">
                    <span>Type</span>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {sortColumn === 'type' ? (
                        sortDirection === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronUp className="w-4 h-4" />
                      )}
                      <ColumnHeaderDropdown column="type" label="Type" />
                    </div>
                  </div>
                </TableHead>
              )}
              {columnVisibility.status && (
                <TableHead 
                  className="text-gray-300 font-semibold cursor-pointer hover:text-white group"
                  onClick={() => onSort('status')}
                >
                  <div className="flex items-center justify-between">
                    <span>Status</span>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {sortColumn === 'status' ? (
                        sortDirection === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronUp className="w-4 h-4" />
                      )}
                      <ColumnHeaderDropdown column="status" label="Status" />
                    </div>
                  </div>
                </TableHead>
              )}
              {columnVisibility.submitted && (
                <TableHead 
                  className="text-gray-300 font-semibold cursor-pointer hover:text-white group"
                  onClick={() => onSort('submitted')}
                >
                  <div className="flex items-center justify-between">
                    <span>Submitted</span>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {sortColumn === 'submitted' ? (
                        sortDirection === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronUp className="w-4 h-4" />
                      )}
                      <ColumnHeaderDropdown column="submitted" label="Submitted" />
                    </div>
                  </div>
                </TableHead>
              )}
              {columnVisibility.actions && (
                <TableHead className="text-gray-300 font-semibold"></TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobRows.map((job, index) => (
              <TableRow key={job.id || job.job_id || `job-${index}`} className="border-gray-700 hover:bg-gray-700">
                {columnVisibility.checkbox && (
                  <TableCell>
                    <Checkbox
                      checked={selectedJobs.has(job.id)}
                      onCheckedChange={(checked) => onJobSelect(job.id, !!checked)}
                      className="w-6 h-6 border-2 border-gray-500 data-[state=checked]:bg-[#E2E756] data-[state=checked]:border-[#E2E756] data-[state=checked]:text-black"
                    />
                  </TableCell>
                )}
                {columnVisibility.name && (
                  <TableCell className="text-white font-medium">{job.name}</TableCell>
                )}
                {columnVisibility.type && (
                  <TableCell className="text-gray-300">{job.type}</TableCell>
                )}
                {columnVisibility.status && (
                  <TableCell>
                    {getStatusBadge(job.status)}
                  </TableCell>
                )}
                {columnVisibility.submitted && (
                  <TableCell className="text-gray-300">{job.submitted}</TableCell>
                )}
                {columnVisibility.actions && (
                  <TableCell>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-blue-400 hover:text-blue-300 hover:bg-blue-900/20"
                      onClick={() => onViewJob?.(job.id)}
                    >
                      View
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export default TableContent;
