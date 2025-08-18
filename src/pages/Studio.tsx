
import React from 'react';
import { Header } from '@/components/Header';
import { Navigation } from '@/components/Navigation';

const Studio = () => {
  return (
    <div className="min-h-screen bg-gray-900">
      <Header />
      <Navigation />
      
      {/* Blank studio page */}
      <div className="flex-1 p-8">
        <div className="text-center text-gray-400">
          <h1 className="text-2xl font-bold mb-4">Studio</h1>
          <p>This is the Studio page.</p>
        </div>
      </div>
    </div>
  );
};

export default Studio;
