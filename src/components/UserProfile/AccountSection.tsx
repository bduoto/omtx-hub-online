
import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Mail, Building, Crown, Calendar } from 'lucide-react';

export const AccountSection: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Account Settings</h1>
        <p className="text-gray-400 mt-2">Manage your account information and preferences</p>
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <Mail className="mr-2 h-5 w-5 text-[#E2E756]" />
            Email Settings
          </CardTitle>
          <CardDescription className="text-gray-400">
            Manage your email address and communication preferences
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-gray-300">Primary Email</Label>
            <div className="flex items-center space-x-2">
              <Input
                id="email"
                type="email"
                defaultValue="john.doe@company.com"
                className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
              />
              <Badge variant="secondary" className="bg-green-100 text-green-800">
                Verified
              </Badge>
            </div>
          </div>
          <Button variant="outline" className="border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-[#E2E756] hover:border-[#E2E756]">
            Change Email
          </Button>
        </CardContent>
      </Card>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <Building className="mr-2 h-5 w-5 text-[#E2E756]" />
            Organizations
          </CardTitle>
          <CardDescription className="text-gray-400">
            Organizations you're a member of
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg border border-gray-600">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-[#E2E756] to-[#d4d435] rounded-lg flex items-center justify-center">
                  <Building className="h-5 w-5 text-gray-900" />
                </div>
                <div>
                  <p className="text-white font-medium">Acme Corporation</p>
                  <p className="text-gray-400 text-sm">acme-corp</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Badge className="bg-[#E2E756] text-gray-900">
                  <Crown className="mr-1 h-3 w-3" />
                  Owner
                </Badge>
              </div>
            </div>
            
            <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg border border-gray-600">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                  <Building className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className="text-white font-medium">Tech Startup Inc</p>
                  <p className="text-gray-400 text-sm">tech-startup</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Badge variant="secondary">Member</Badge>
              </div>
            </div>
          </div>
          
          <Button variant="outline" className="w-full border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-[#E2E756] hover:border-[#E2E756]">
            Join Organization
          </Button>
        </CardContent>
      </Card>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <Calendar className="mr-2 h-5 w-5 text-[#E2E756]" />
            Account Information
          </CardTitle>
          <CardDescription className="text-gray-400">
            Your account details and status
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-gray-400 text-sm">Account Created</Label>
              <p className="text-white">March 15, 2024</p>
            </div>
            <div>
              <Label className="text-gray-400 text-sm">Last Login</Label>
              <p className="text-white">2 hours ago</p>
            </div>
            <div>
              <Label className="text-gray-400 text-sm">Account ID</Label>
              <p className="text-white font-mono text-sm">usr_123456789</p>
            </div>
            <div>
              <Label className="text-gray-400 text-sm">Plan</Label>
              <Badge className="bg-[#E2E756] text-gray-900">Pro</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
