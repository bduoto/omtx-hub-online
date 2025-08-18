
import React from 'react';
import { Header } from '@/components/Header';
import { Navigation } from '@/components/Navigation';
import { ToolsGrid } from '@/components/ToolsGrid';
import { SearchSection } from '@/components/SearchSection';

const Index = () => {
  return (
    <div className="min-h-screen bg-gray-900">
      <Header />
      <Navigation />
      
      <main className="max-w-7xl mx-auto px-6 py-8">
        <ToolsGrid />
        <SearchSection />
      </main>
    </div>
  );
};

export default Index;
