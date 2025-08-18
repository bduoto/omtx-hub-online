
import React, { Suspense } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

const TableContent = React.lazy(() => import('./TableContent'));

interface ColumnVisibility {
  checkbox: boolean;
  name: boolean;
  type: boolean;
  status: boolean;
  submitted: boolean;
  actions: boolean;
}

interface LazyTableProps {
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

const TableSkeleton = () => (
  <Card className="bg-gray-800 border-gray-700 shadow-sm">
    <CardContent className="p-0">
      <div className="space-y-4 p-4">
        <div className="flex space-x-4">
          <Skeleton className="h-6 w-6 bg-gray-700" />
          <Skeleton className="h-6 w-32 bg-gray-700" />
          <Skeleton className="h-6 w-24 bg-gray-700" />
          <Skeleton className="h-6 w-20 bg-gray-700" />
          <Skeleton className="h-6 w-28 bg-gray-700" />
        </div>
        {[...Array(3)].map((_, i) => (
          <div key={i} className="flex space-x-4">
            <Skeleton className="h-6 w-6 bg-gray-700" />
            <Skeleton className="h-6 w-32 bg-gray-700" />
            <Skeleton className="h-6 w-24 bg-gray-700" />
            <Skeleton className="h-6 w-20 bg-gray-700" />
            <Skeleton className="h-6 w-28 bg-gray-700" />
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
);

const LazyTable: React.FC<LazyTableProps> = (props) => {
  if (props.isLoading) {
    return <TableSkeleton />;
  }

  return (
    <Suspense fallback={<TableSkeleton />}>
      <TableContent {...props} />
    </Suspense>
  );
};

export default LazyTable;
