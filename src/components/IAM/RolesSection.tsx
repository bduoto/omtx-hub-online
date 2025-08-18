
import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Shield, Plus, Edit, Users } from 'lucide-react';

const mockRoles = [
  {
    id: '1',
    name: 'Admin',
    description: 'Full access to all features and settings',
    userCount: 3,
    permissions: ['read', 'write', 'delete', 'manage_users', 'manage_settings'],
    color: 'red'
  },
  {
    id: '2',
    name: 'Editor',
    description: 'Can create and edit content',
    userCount: 8,
    permissions: ['read', 'write'],
    color: 'blue'
  },
  {
    id: '3',
    name: 'Viewer',
    description: 'Read-only access to content',
    userCount: 12,
    permissions: ['read'],
    color: 'gray'
  }
];

const allPermissions = [
  { id: 'read', label: 'Read', description: 'View content and data' },
  { id: 'write', label: 'Write', description: 'Create and edit content' },
  { id: 'delete', label: 'Delete', description: 'Remove content and data' },
  { id: 'manage_users', label: 'Manage Users', description: 'Add, edit, and remove users' },
  { id: 'manage_settings', label: 'Manage Settings', description: 'Modify system settings' },
  { id: 'manage_billing', label: 'Manage Billing', description: 'Handle billing and subscriptions' }
];

export const RolesSection: React.FC = () => {
  const [selectedRole, setSelectedRole] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Roles & Permissions</h1>
          <p className="text-gray-400 mt-2">Manage user roles and their associated permissions</p>
        </div>
        <Button className="bg-[#E2E756] text-gray-900 hover:bg-[#d4d435] font-medium">
          <Plus className="mr-2 h-4 w-4" />
          Create Role
        </Button>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white">Available Roles</CardTitle>
            <CardDescription className="text-gray-400">
              Click on a role to view and edit its permissions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {mockRoles.map((role) => (
              <div
                key={role.id}
                className={`p-4 rounded-lg border transition-all duration-200 cursor-pointer ${
                  selectedRole === role.id
                    ? 'border-[#E2E756] bg-[#E2E756]/10'
                    : 'border-gray-600 hover:border-gray-500 hover:bg-gray-700/50'
                }`}
                onClick={() => setSelectedRole(role.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Shield className={`h-5 w-5 ${
                      role.color === 'red' ? 'text-red-400' :
                      role.color === 'blue' ? 'text-blue-400' : 'text-gray-400'
                    }`} />
                    <div>
                      <h3 className="text-white font-medium">{role.name}</h3>
                      <p className="text-gray-400 text-sm">{role.description}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center text-gray-400 text-sm">
                      <Users className="mr-1 h-3 w-3" />
                      {role.userCount}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-gray-400 hover:text-[#E2E756] p-1"
                    >
                      <Edit className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white">
              {selectedRole ? `${mockRoles.find(r => r.id === selectedRole)?.name} Permissions` : 'Permissions'}
            </CardTitle>
            <CardDescription className="text-gray-400">
              {selectedRole 
                ? 'Manage permissions for the selected role'
                : 'Select a role to view and edit its permissions'
              }
            </CardDescription>
          </CardHeader>
          <CardContent>
            {selectedRole ? (
              <div className="space-y-4">
                {allPermissions.map((permission) => {
                  const selectedRoleData = mockRoles.find(r => r.id === selectedRole);
                  const hasPermission = selectedRoleData?.permissions.includes(permission.id) || false;
                  
                  return (
                    <div key={permission.id} className="flex items-start space-x-3">
                      <Checkbox
                        id={permission.id}
                        checked={hasPermission}
                        className="mt-1 border-gray-600 data-[state=checked]:bg-[#E2E756] data-[state=checked]:border-[#E2E756]"
                      />
                      <div className="flex-1">
                        <label
                          htmlFor={permission.id}
                          className="text-white font-medium cursor-pointer"
                        >
                          {permission.label}
                        </label>
                        <p className="text-gray-400 text-sm">{permission.description}</p>
                      </div>
                    </div>
                  );
                })}
                
                <div className="pt-4 border-t border-gray-700">
                  <Button className="bg-[#E2E756] text-gray-900 hover:bg-[#d4d435] font-medium">
                    Save Changes
                  </Button>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Shield className="mx-auto h-12 w-12 text-gray-500 mb-4" />
                <p className="text-gray-400">Select a role to view its permissions</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
