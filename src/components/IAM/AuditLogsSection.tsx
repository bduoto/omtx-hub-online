
import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Search, FileText, User, Shield, Building, Mail } from 'lucide-react';

const mockAuditLogs = [
  {
    id: '1',
    action: 'User Created',
    user: 'john.doe@company.com',
    target: 'jane.smith@company.com',
    organization: 'Acme Corporation',
    timestamp: '2024-01-15 14:30:22',
    ipAddress: '192.168.1.100',
    type: 'user_management'
  },
  {
    id: '2',
    action: 'Role Updated',
    user: 'john.doe@company.com',
    target: 'Editor Role',
    organization: 'Acme Corporation',
    timestamp: '2024-01-15 13:45:10',
    ipAddress: '192.168.1.100',
    type: 'permission_change'
  },
  {
    id: '3',
    action: 'Organization Created',
    user: 'john.doe@company.com',
    target: 'Tech Startup Inc',
    organization: 'System',
    timestamp: '2024-01-14 16:20:45',
    ipAddress: '192.168.1.100',
    type: 'organization_management'
  },
  {
    id: '4',
    action: 'Invitation Sent',
    user: 'jane.smith@company.com',
    target: 'alice.williams@example.com',
    organization: 'Acme Corporation',
    timestamp: '2024-01-14 11:15:33',
    ipAddress: '192.168.1.101',
    type: 'invitation'
  },
  {
    id: '5',
    action: 'User Login',
    user: 'bob.johnson@startup.com',
    target: 'System',
    organization: 'Tech Startup Inc',
    timestamp: '2024-01-14 09:30:12',
    ipAddress: '192.168.1.102',
    type: 'authentication'
  }
];

const actionTypeFilters = [
  { value: 'all', label: 'All Actions' },
  { value: 'user_management', label: 'User Management' },
  { value: 'permission_change', label: 'Permission Changes' },
  { value: 'organization_management', label: 'Organization Management' },
  { value: 'invitation', label: 'Invitations' },
  { value: 'authentication', label: 'Authentication' }
];

export const AuditLogsSection: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [actionTypeFilter, setActionTypeFilter] = useState('all');

  const filteredLogs = mockAuditLogs.filter(log => {
    const matchesSearch = log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         log.user.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         log.target.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = actionTypeFilter === 'all' || log.type === actionTypeFilter;
    return matchesSearch && matchesType;
  });

  const getActionIcon = (type: string) => {
    switch (type) {
      case 'user_management':
        return <User className="h-4 w-4 text-blue-400" />;
      case 'permission_change':
        return <Shield className="h-4 w-4 text-red-400" />;
      case 'organization_management':
        return <Building className="h-4 w-4 text-green-400" />;
      case 'invitation':
        return <Mail className="h-4 w-4 text-purple-400" />;
      case 'authentication':
        return <FileText className="h-4 w-4 text-yellow-400" />;
      default:
        return <FileText className="h-4 w-4 text-gray-400" />;
    }
  };

  const getActionBadge = (type: string) => {
    const colors = {
      user_management: 'bg-blue-100 text-blue-800',
      permission_change: 'bg-red-100 text-red-800',
      organization_management: 'bg-green-100 text-green-800',
      invitation: 'bg-purple-100 text-purple-800',
      authentication: 'bg-yellow-100 text-yellow-800'
    };
    
    return (
      <Badge className={colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-800'}>
        {type.replace('_', ' ')}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Audit Logs</h1>
        <p className="text-gray-400 mt-2">Track all user activities and system changes</p>
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Activity Log</CardTitle>
          <CardDescription className="text-gray-400">
            Monitor all actions performed within your organizations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-4 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search audit logs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
              />
            </div>
            <Select value={actionTypeFilter} onValueChange={setActionTypeFilter}>
              <SelectTrigger className="w-48 bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700">
                {actionTypeFilters.map((filter) => (
                  <SelectItem 
                    key={filter.value} 
                    value={filter.value}
                    className="text-white hover:bg-gray-700"
                  >
                    {filter.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Table>
            <TableHeader>
              <TableRow className="border-gray-700">
                <TableHead className="text-gray-300">Action</TableHead>
                <TableHead className="text-gray-300">User</TableHead>
                <TableHead className="text-gray-300">Target</TableHead>
                <TableHead className="text-gray-300">Organization</TableHead>
                <TableHead className="text-gray-300">Timestamp</TableHead>
                <TableHead className="text-gray-300">IP Address</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredLogs.map((log) => (
                <TableRow key={log.id} className="border-gray-700 hover:bg-gray-700/50">
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      {getActionIcon(log.type)}
                      <div>
                        <p className="text-white font-medium">{log.action}</p>
                        {getActionBadge(log.type)}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-gray-300">{log.user}</TableCell>
                  <TableCell className="text-gray-300">{log.target}</TableCell>
                  <TableCell className="text-gray-300">{log.organization}</TableCell>
                  <TableCell className="text-gray-400 font-mono text-sm">{log.timestamp}</TableCell>
                  <TableCell className="text-gray-400 font-mono text-sm">{log.ipAddress}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};
