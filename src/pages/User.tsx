
import React, { useState } from 'react';
import { Header } from '@/components/Header';
import { Navigation } from '@/components/Navigation';
import { UserSidebar } from '@/components/UserSidebar';
import { ProfileSection } from '@/components/UserProfile/ProfileSection';
import { AccountSection } from '@/components/UserProfile/AccountSection';
import { SecuritySection } from '@/components/UserProfile/SecuritySection';
import { ConnectedAccountsSection } from '@/components/UserProfile/ConnectedAccountsSection';
import { NotificationsSection } from '@/components/UserProfile/NotificationsSection';

export type UserSection = 'profile' | 'account' | 'security' | 'connected-accounts' | 'notifications';

const User = () => {
  const [activeSection, setActiveSection] = useState<UserSection>('profile');

  const renderSection = () => {
    switch (activeSection) {
      case 'profile':
        return <ProfileSection />;
      case 'account':
        return <AccountSection />;
      case 'security':
        return <SecuritySection />;
      case 'connected-accounts':
        return <ConnectedAccountsSection />;
      case 'notifications':
        return <NotificationsSection />;
      default:
        return <ProfileSection />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900">
      <Header />
      <Navigation />
      
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex gap-8">
          <UserSidebar activeSection={activeSection} onSectionChange={setActiveSection} />
          
          <main className="flex-1">
            <div className="animate-in fade-in-50 duration-300">
              {renderSection()}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export default User;
