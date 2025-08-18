
import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Link, CheckCircle, AlertCircle } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface ConnectedAccount {
  id: string;
  name: string;
  email: string;
  provider: string;
  connected: boolean;
  lastUsed?: string;
  logo: string;
}

const accounts: ConnectedAccount[] = [
  {
    id: '1',
    name: 'Google',
    email: 'john.doe@gmail.com',
    provider: 'google',
    connected: true,
    lastUsed: '2 hours ago',
    logo: '🔍'
  },
  {
    id: '2',
    name: 'Microsoft',
    email: 'john.doe@outlook.com',
    provider: 'microsoft',
    connected: true,
    lastUsed: '1 day ago',  
    logo: '🪟'
  },
  {
    id: '3',
    name: 'GitHub',
    email: 'johndoe',
    provider: 'github',
    connected: false,
    logo: '🐙'
  },
  {
    id: '4',
    name: 'LinkedIn',
    email: '',
    provider: 'linkedin',
    connected: false,
    logo: '💼'
  }
];

export const ConnectedAccountsSection: React.FC = () => {
  const { toast } = useToast();

  const handleConnect = (accountName: string) => {
    toast({
      title: `${accountName} connected`,
      description: `Your ${accountName} account has been successfully connected.`,
    });
  };

  const handleDisconnect = (accountName: string) => {
    toast({
      title: `${accountName} disconnected`,
      description: `Your ${accountName} account has been disconnected.`,
      variant: "destructive",
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Connected Accounts</h1>
        <p className="text-gray-400 mt-2">Manage your connected social and work accounts</p>
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <Link className="mr-2 h-5 w-5 text-[#E2E756]" />
            Social Sign-On (SSO)
          </CardTitle>
          <CardDescription className="text-gray-400">
            Connect your accounts to sign in quickly and securely
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {accounts.map((account) => (
              <div
                key={account.id}
                className="flex items-center justify-between p-4 bg-gray-700 rounded-lg border border-gray-600 hover:border-gray-500 transition-colors duration-200"
              >
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-gray-600 rounded-lg flex items-center justify-center text-2xl">
                    {account.logo}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <h3 className="text-white font-medium">{account.name}</h3>
                      {account.connected ? (
                        <Badge className="bg-green-100 text-green-800">
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Connected
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="bg-gray-600 text-gray-300">
                          <AlertCircle className="mr-1 h-3 w-3" />
                          Not Connected
                        </Badge>
                      )}
                    </div>
                    {account.connected && (
                      <div className="text-sm text-gray-400 space-y-1">
                        <p>{account.email}</p>
                        {account.lastUsed && (
                          <p>Last used: {account.lastUsed}</p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="flex space-x-2">
                  {account.connected ? (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-[#E2E756] hover:border-[#E2E756]"
                      >
                        Manage
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-red-600 text-red-400 hover:bg-red-900/20 hover:text-red-300 hover:border-red-500"
                        onClick={() => handleDisconnect(account.name)}
                      >
                        Disconnect
                      </Button>
                    </>
                  ) : (
                    <Button
                      className="bg-[#E2E756] text-gray-900 hover:bg-[#d4d435]"
                      size="sm"
                      onClick={() => handleConnect(account.name)}
                    >
                      Connect
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Account Permissions</CardTitle>
          <CardDescription className="text-gray-400">
            Manage what information connected accounts can access
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-gray-700 rounded-lg border border-gray-600">
              <div>
                <p className="text-white text-sm font-medium">Profile Information</p>
                <p className="text-gray-400 text-xs">Name, email, and profile picture</p>
              </div>
              <span className="text-green-400 text-sm">Allowed</span>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-gray-700 rounded-lg border border-gray-600">
              <div>
                <p className="text-white text-sm font-medium">Organization Access</p>
                <p className="text-gray-400 text-xs">Access to organization data and settings</p>
              </div>
              <span className="text-green-400 text-sm">Allowed</span>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-gray-700 rounded-lg border border-gray-600">
              <div>
                <p className="text-white text-sm font-medium">File Access</p>
                <p className="text-gray-400 text-xs">Read and write access to your files</p>
              </div>
              <span className="text-yellow-400 text-sm">Limited</span>
            </div>
          </div>
          
          <Button 
            variant="outline" 
            className="w-full border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-[#E2E756] hover:border-[#E2E756]"
          >
            Review All Permissions
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};
