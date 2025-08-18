
import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Shield, Key, Smartphone, AlertTriangle, CheckCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export const SecuritySection: React.FC = () => {
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const { toast } = useToast();

  const handleTwoFactorToggle = (enabled: boolean) => {
    setTwoFactorEnabled(enabled);
    toast({
      title: enabled ? "Two-factor authentication enabled" : "Two-factor authentication disabled",
      description: enabled 
        ? "Your account is now more secure with 2FA enabled."
        : "Two-factor authentication has been disabled.",
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Security Settings</h1>
        <p className="text-gray-400 mt-2">Keep your account secure with these settings</p>
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <Key className="mr-2 h-5 w-5 text-[#E2E756]" />
            Password
          </CardTitle>
          <CardDescription className="text-gray-400">
            Change your password to keep your account secure
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!showPasswordForm ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white">Password</p>
                <p className="text-gray-400 text-sm">Last changed 30 days ago</p>
              </div>
              <Button 
                variant="outline"
                className="border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-[#E2E756] hover:border-[#E2E756]"
                onClick={() => setShowPasswordForm(true)}
              >
                Change Password
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="currentPassword" className="text-gray-300">Current Password</Label>
                <Input
                  id="currentPassword"
                  type="password"
                  className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="newPassword" className="text-gray-300">New Password</Label>
                <Input
                  id="newPassword"
                  type="password"
                  className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-gray-300">Confirm New Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
                />
              </div>
              <div className="flex space-x-2">
                <Button className="bg-[#E2E756] text-gray-900 hover:bg-[#d4d435]">
                  Update Password
                </Button>
                <Button 
                  variant="outline" 
                  className="border-gray-600 text-gray-300 hover:bg-gray-700"
                  onClick={() => setShowPasswordForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <Smartphone className="mr-2 h-5 w-5 text-[#E2E756]" />
            Two-Factor Authentication
          </CardTitle>
          <CardDescription className="text-gray-400">
            Add an extra layer of security to your account
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <p className="text-white">Two-Factor Authentication</p>
                {twoFactorEnabled ? (
                  <Badge className="bg-green-100 text-green-800">
                    <CheckCircle className="mr-1 h-3 w-3" />
                    Enabled
                  </Badge>
                ) : (
                  <Badge variant="destructive">
                    <AlertTriangle className="mr-1 h-3 w-3" />
                    Disabled
                  </Badge>
                )}
              </div>
              <p className="text-gray-400 text-sm">
                {twoFactorEnabled 
                  ? "Your account is protected with 2FA" 
                  : "Enable 2FA for enhanced security"
                }
              </p>
            </div>
            <Switch
              checked={twoFactorEnabled}
              onCheckedChange={handleTwoFactorToggle}
            />
          </div>
          
          {twoFactorEnabled && (
            <div className="mt-4 p-4 bg-gray-700 rounded-lg border border-gray-600">
              <h4 className="text-white font-medium mb-2">Backup Codes</h4>
              <p className="text-gray-400 text-sm mb-3">
                Save these backup codes in a safe place. You can use them to access your account if you lose your phone.
              </p>
              <Button variant="outline" className="border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-[#E2E756] hover:border-[#E2E756]">
                View Backup Codes
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <Shield className="mr-2 h-5 w-5 text-[#E2E756]" />
            Login Activity
          </CardTitle>
          <CardDescription className="text-gray-400">
            Recent login activity on your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-gray-700 rounded-lg border border-gray-600">
              <div>
                <p className="text-white text-sm">Current session</p>
                <p className="text-gray-400 text-xs">San Francisco, CA • Chrome on macOS</p>
              </div>
              <Badge className="bg-green-100 text-green-800">Active</Badge>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-gray-700 rounded-lg border border-gray-600">
              <div>
                <p className="text-white text-sm">2 hours ago</p>
                <p className="text-gray-400 text-xs">New York, NY • Safari on iPhone</p>
              </div>
              <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300 hover:bg-red-900/20">
                Revoke
              </Button>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-gray-700 rounded-lg border border-gray-600">
              <div>
                <p className="text-white text-sm">1 day ago</p>
                <p className="text-gray-400 text-xs">London, UK • Firefox on Windows</p>
              </div>
              <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300 hover:bg-red-900/20">
                Revoke
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
