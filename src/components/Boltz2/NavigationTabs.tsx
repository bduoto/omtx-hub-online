import React from 'react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface NavigationTabsProps {
  children: React.ReactNode;
}

export const NavigationTabs = ({ children }: NavigationTabsProps) => {
  return (
    <div className="border-b border-gray-700">
      <div className="w-full px-6">
        <Tabs defaultValue="playground" className="w-full">
          <TabsList className="bg-transparent border-0 h-12">
            <TabsTrigger value="playground" className="bg-transparent border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-transparent rounded-none text-gray-300 data-[state=active]:text-white">
              Playground
            </TabsTrigger>
            <TabsTrigger value="api" className="bg-transparent border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-transparent rounded-none text-gray-300 data-[state=active]:text-white">
              API
            </TabsTrigger>
            <TabsTrigger value="examples" className="bg-transparent border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-transparent rounded-none text-gray-300 data-[state=active]:text-white">
              Examples
            </TabsTrigger>
            <TabsTrigger value="readme" className="bg-transparent border-b-2 border-transparent data-[state=active]:border-blue-500 data-[state=active]:bg-transparent rounded-none text-gray-300 data-[state=active]:text-white">
              README
            </TabsTrigger>
          </TabsList>
          {children}
        </Tabs>
      </div>
    </div>
  );
};