
import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { UserPlus, Mail, Clock, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const mockInvitations = [
  {
    id: '1',
    email: 'alice.williams@example.com',
    role: 'Editor',
    organization: 'Acme Corporation',
    status: 'Pending',
    sentAt: '2 days ago',
    expiresAt: '5 days'
  },
  {
    id: '2',
    email: 'charlie.brown@example.com',
    role: 'Viewer',
    organization: 'Tech Startup Inc',
    status: 'Accepted',
    sentAt: '1 week ago',
    expiresAt: 'Accepted'
  },
  {
    id: '3',
    email: 'diana.prince@example.com',
    role: 'Admin',
    organization: 'Acme Corporation',
    status: 'Expired',
    sentAt: '2 weeks ago',
    expiresAt: 'Expired'
  }
];

export const InvitationsSection: React.FC = () => {
  const [isInviteDialogOpen, setIsInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('');
  const [inviteOrg, setInviteOrg] = useState('');
  const { toast } = useToast();

  const handleSendInvitation = () => {
    if (!inviteEmail.trim() || !inviteRole || !inviteOrg) return;
    
    toast({
      title: "Invitation sent",
      description: `Invitation sent to ${inviteEmail} successfully.`,
    });
    
    setInviteEmail('');
    setInviteRole('');
    setInviteOrg('');
    setIsInviteDialogOpen(false);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Pending':
        return <Badge className="bg-yellow-100 text-yellow-800"><Clock className="mr-1 h-3 w-3" />Pending</Badge>;
      case 'Accepted':
        return <Badge className="bg-green-100 text-green-800"><CheckCircle className="mr-1 h-3 w-3" />Accepted</Badge>;
      case 'Expired':
        return <Badge className="bg-red-100 text-red-800"><XCircle className="mr-1 h-3 w-3" />Expired</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Invitations</h1>
          <p className="text-gray-400 mt-2">Manage pending invitations and invite new users</p>
        </div>
        <Dialog open={isInviteDialogOpen} onOpenChange={setIsInviteDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-[#E2E756] text-gray-900 hover:bg-[#d4d435] font-medium">
              <UserPlus className="mr-2 h-4 w-4" />
              Send Invitation
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-gray-800 border-gray-700 text-white">
            <DialogHeader>
              <DialogTitle>Send Invitation</DialogTitle>
              <DialogDescription className="text-gray-400">
                Invite a new user to join your organization with specific permissions.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="invite-email" className="text-gray-300">Email Address</Label>
                <Input
                  id="invite-email"
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-300">Role</Label>
                <Select value={inviteRole} onValueChange={setInviteRole}>
                  <SelectTrigger className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]">
                    <SelectValue placeholder="Select a role" />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-800 border-gray-700">
                    <SelectItem value="admin" className="text-white hover:bg-gray-700">Admin</SelectItem>
                    <SelectItem value="editor" className="text-white hover:bg-gray-700">Editor</SelectItem>
                    <SelectItem value="viewer" className="text-white hover:bg-gray-700">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-gray-300">Organization</Label>
                <Select value={inviteOrg} onValueChange={setInviteOrg}>
                  <SelectTrigger className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]">
                    <SelectValue placeholder="Select organization" />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-800 border-gray-700">
                    <SelectItem value="acme" className="text-white hover:bg-gray-700">Acme Corporation</SelectItem>
                    <SelectItem value="startup" className="text-white hover:bg-gray-700">Tech Startup Inc</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setIsInviteDialogOpen(false)}
                className="border-gray-600 text-gray-300 hover:bg-gray-700"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSendInvitation}
                className="bg-[#E2E756] text-gray-900 hover:bg-[#d4d435]"
              >
                <Mail className="mr-2 h-4 w-4" />
                Send Invitation
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Pending Invitations</CardTitle>
          <CardDescription className="text-gray-400">
            Track and manage all sent invitations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-gray-700">
                <TableHead className="text-gray-300">Email</TableHead>
                <TableHead className="text-gray-300">Role</TableHead>
                <TableHead className="text-gray-300">Organization</TableHead>
                <TableHead className="text-gray-300">Status</TableHead>
                <TableHead className="text-gray-300">Sent</TableHead>
                <TableHead className="text-gray-300">Expires</TableHead>
                <TableHead className="text-gray-300 w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockInvitations.map((invitation) => (
                <TableRow key={invitation.id} className="border-gray-700 hover:bg-gray-700/50">
                  <TableCell className="text-white">{invitation.email}</TableCell>
                  <TableCell>
                    <Badge 
                      className={
                        invitation.role === 'Admin' 
                          ? 'bg-red-100 text-red-800' 
                          : invitation.role === 'Editor'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }
                    >
                      {invitation.role}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-gray-300">{invitation.organization}</TableCell>
                  <TableCell>{getStatusBadge(invitation.status)}</TableCell>
                  <TableCell className="text-gray-400">{invitation.sentAt}</TableCell>
                  <TableCell className="text-gray-400">{invitation.expiresAt}</TableCell>
                  <TableCell>
                    {invitation.status === 'Pending' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-gray-400 hover:text-[#E2E756] hover:bg-gray-700"
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};
