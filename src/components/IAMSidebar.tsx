
import React from 'react';
import { Users, Building, Shield, UserPlus, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { IAMSection } from '@/pages/IAM';

interface IAMSidebarProps {
  activeSection: IAMSection;
  onSectionChange: (section: IAMSection) => void;
}

const sidebarItems = [
  {
    id: 'users' as IAMSection,
    label: 'Users',
    icon: Users,
    category: 'User Management'
  },
  {
    id: 'organizations' as IAMSection,
    label: 'Organizations',
    icon: Building,
    category: 'User Management'
  },
  {
    id: 'roles' as IAMSection,
    label: 'Roles & Permissions',
    icon: Shield,
    category: 'Access Control'
  },
  {
    id: 'invitations' as IAMSection,
    label: 'Invitations',
    icon: UserPlus,
    category: 'Access Control'
  },
  {
    id: 'audit-logs' as IAMSection,
    label: 'Audit Logs',
    icon: FileText,
    category: 'Monitoring'
  }
];

export const IAMSidebar: React.FC<IAMSidebarProps> = ({ activeSection, onSectionChange }) => {
  const categories = Array.from(new Set(sidebarItems.map(item => item.category)));

  return (
    <aside className="w-64 bg-gray-800 rounded-lg p-6 h-fit sticky top-8">
      <h2 className="text-xl font-semibold text-white mb-6">IAM Management</h2>
      
      <nav className="space-y-6">
        {categories.map(category => (
          <div key={category}>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
              {category}
            </h3>
            <ul className="space-y-1">
              {sidebarItems
                .filter(item => item.category === category)
                .map(item => {
                  const Icon = item.icon;
                  const isActive = activeSection === item.id;
                  
                  return (
                    <li key={item.id}>
                      <button
                        onClick={() => onSectionChange(item.id)}
                        className={cn(
                          "w-full flex items-center px-3 py-2 rounded-md text-sm font-medium transition-all duration-200",
                          "hover:bg-gray-700 hover:text-[#E2E756] focus:outline-none focus:ring-2 focus:ring-[#E2E756] focus:ring-offset-2 focus:ring-offset-gray-800",
                          isActive 
                            ? "bg-[#E2E756] text-gray-900 shadow-lg" 
                            : "text-gray-300"
                        )}
                      >
                        <Icon className={cn(
                          "mr-3 h-4 w-4 transition-all duration-200",
                          isActive ? "text-gray-900" : "text-gray-400"
                        )} />
                        {item.label}
                      </button>
                    </li>
                  );
                })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
};
