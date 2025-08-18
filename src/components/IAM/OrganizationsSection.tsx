
import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Building, Users, Plus, Settings, Trash2, Crown } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const mockOrganizations = [
  {
    id: '1',
    name: 'Acme Corporation',
    slug: 'acme-corp',
    memberCount: 25,
    role: 'Owner',
    createdAt: 'March 15, 2024',
    description: 'Main company organization'
  },
  {
    id: '2',
    name: 'Tech Startup Inc',
    slug: 'tech-startup',
    memberCount: 8,
    role: 'Member',
    createdAt: 'April 2, 2024',
    description: 'Innovation focused startup'
  }
];

export const OrganizationsSection: React.FC = () => {
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [newOrgDescription, setNewOrgDescription] = useState('');
  const { toast } = useToast();

  const handleCreateOrganization = () => {
    if (!newOrgName.trim()) return;
    
    toast({
      title: "Organization created",
      description: `${newOrgName} has been successfully created.`,
    });
    
    setNewOrgName('');
    setNewOrgDescription('');
    setIsCreateDialogOpen(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Organizations</h1>
          <p className="text-gray-400 mt-2">Manage your organizations and their settings</p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-[#E2E756] text-gray-900 hover:bg-[#d4d435] font-medium">
              <Plus className="mr-2 h-4 w-4" />
              Create Organization
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-gray-800 border-gray-700 text-white">
            <DialogHeader>
              <DialogTitle>Create New Organization</DialogTitle>
              <DialogDescription className="text-gray-400">
                Create a new organization to manage users and projects separately.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="org-name" className="text-gray-300">Organization Name</Label>
                <Input
                  id="org-name"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  placeholder="Enter organization name"
                  className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="org-description" className="text-gray-300">Description (Optional)</Label>
                <Input
                  id="org-description"
                  value={newOrgDescription}
                  onChange={(e) => setNewOrgDescription(e.target.value)}
                  placeholder="Brief description of the organization"
                  className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setIsCreateDialogOpen(false)}
                className="border-gray-600 text-gray-300 hover:bg-gray-700"
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreateOrganization}
                className="bg-[#E2E756] text-gray-900 hover:bg-[#d4d435]"
              >
                Create Organization
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-6">
        {mockOrganizations.map((org) => (
          <Card key={org.id} className="bg-gray-800 border-gray-700">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-[#E2E756] to-[#d4d435] rounded-lg flex items-center justify-center">
                    <Building className="h-6 w-6 text-gray-900" />
                  </div>
                  <div>
                    <CardTitle className="text-white flex items-center">
                      {org.name}
                      {org.role === 'Owner' && (
                        <Badge className="ml-2 bg-[#E2E756] text-gray-900">
                          <Crown className="mr-1 h-3 w-3" />
                          Owner
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription className="text-gray-400">
                      {org.description}
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-[#E2E756] hover:border-[#E2E756]"
                  >
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Button>
                  {org.role === 'Owner' && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="border-red-600 text-red-400 hover:bg-red-600 hover:text-white"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label className="text-gray-400 text-sm">Organization ID</Label>
                  <p className="text-white font-mono text-sm">{org.slug}</p>
                </div>
                <div>
                  <Label className="text-gray-400 text-sm">Members</Label>
                  <div className="flex items-center text-white">
                    <Users className="mr-1 h-4 w-4 text-gray-400" />
                    {org.memberCount}
                  </div>
                </div>
                <div>
                  <Label className="text-gray-400 text-sm">Created</Label>
                  <p className="text-white">{org.createdAt}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};
