
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

export const Navigation = () => {
  const location = useLocation();
  
  const getActiveTab = () => {
    switch (location.pathname) {
      case '/':
        return 'All Models';
      case '/my-results':
        return 'My Results';
      case '/my-batches':
        return 'My Batches';
      case '/gallery':
        return 'Gallery';
      case '/studio':
        return 'Studio';
      default:
        return 'All Models';
    }
  };
  
  const activeTab = getActiveTab();
  
  const tabs = [
    { name: 'All Models', path: '/' },
    { name: 'My Results', path: '/my-results' },
    { name: 'My Batches', path: '/my-batches' },
    { name: 'Gallery', path: '/gallery' },
    { name: 'Studio', path: '/studio' }
  ];
  
  return (
    <div className="bg-gray-800 border-b border-gray-700">
      <div className="max-w-7xl mx-auto px-6">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <Link
              key={tab.name}
              to={tab.path}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.name
                  ? 'border-[#E2E756] text-[#E2E756]'
                  : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600'
              }`}
            >
              {tab.name}
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
};
