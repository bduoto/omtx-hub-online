
import React from 'react';
import { User, Shield, Link, Settings, Bell } from 'lucide-react';
import { cn } from '@/lib/utils';
import { UserSection } from '@/pages/User';

interface UserSidebarProps {
  activeSection: UserSection;
  onSectionChange: (section: UserSection) => void;
}

const sidebarItems = [
  {
    id: 'profile' as UserSection,
    label: 'Profile',
    icon: User,
    category: 'Account Settings'
  },
  {
    id: 'account' as UserSection,
    label: 'Account',
    icon: Settings,
    category: 'Account Settings'
  },
  {
    id: 'security' as UserSection,
    label: 'Security',
    icon: Shield,
    category: 'Security Settings'
  },
  {
    id: 'connected-accounts' as UserSection,
    label: 'Connected Accounts',
    icon: Link,
    category: 'Security Settings'
  },
  {
    id: 'notifications' as UserSection,
    label: 'Notifications',
    icon: Bell,
    category: 'Preferences'
  }
];

export const UserSidebar: React.FC<UserSidebarProps> = ({ activeSection, onSectionChange }) => {
  const categories = Array.from(new Set(sidebarItems.map(item => item.category)));

  return (
    <aside className="w-64 bg-gray-800 rounded-lg p-6 h-fit sticky top-8">
      <h2 className="text-xl font-semibold text-white mb-6">Settings</h2>
      
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
