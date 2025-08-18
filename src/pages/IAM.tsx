
import React, { useState } from 'react';
import { Header } from '@/components/Header';
import { Navigation } from '@/components/Navigation';
import { IAMSidebar } from '@/components/IAMSidebar';
import { UsersSection } from '@/components/IAM/UsersSection';
import { OrganizationsSection } from '@/components/IAM/OrganizationsSection';
import { RolesSection } from '@/components/IAM/RolesSection';
import { InvitationsSection } from '@/components/IAM/InvitationsSection';
import { AuditLogsSection } from '@/components/IAM/AuditLogsSection';

export type IAMSection = 'users' | 'organizations' | 'roles' | 'invitations' | 'audit-logs';

const IAM = () => {
  const [activeSection, setActiveSection] = useState<IAMSection>('users');

  const renderSection = () => {
    switch (activeSection) {
      case 'users':
        return <UsersSection />;
      case 'organizations':
        return <OrganizationsSection />;
      case 'roles':
        return <RolesSection />;
      case 'invitations':
        return <InvitationsSection />;
      case 'audit-logs':
        return <AuditLogsSection />;
      default:
        return <UsersSection />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900">
      <Header />
      <Navigation />
      
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex gap-8">
          <IAMSidebar activeSection={activeSection} onSectionChange={setActiveSection} />
          
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

export default IAM;
