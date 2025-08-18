
import React from 'react';

export const LoginBackground = () => {
  return (
    <div className="absolute inset-0 overflow-hidden">
      {/* Base gradient background with specified colors */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-900 to-black" />
      
      {/* Animated starfield */}
      <div className="absolute inset-0">
        {/* Large stars - using #E2E756 */}
        {Array.from({ length: 30 }, (_, i) => (
          <div
            key={`large-${i}`}
            className="absolute w-2 h-2 rounded-full animate-pulse opacity-80"
            style={{
              backgroundColor: '#E2E756',
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 4}s`,
              animationDuration: `${3 + Math.random() * 2}s`
            }}
          />
        ))}
        
        {/* Medium stars - using #56E7A4 */}
        {Array.from({ length: 50 }, (_, i) => (
          <div
            key={`medium-${i}`}
            className="absolute w-1.5 h-1.5 rounded-full animate-pulse opacity-70"
            style={{
              backgroundColor: '#56E7A4',
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 6}s`,
              animationDuration: `${2 + Math.random() * 3}s`
            }}
          />
        ))}
        
        {/* Small stars - using #5B56E7 */}
        {Array.from({ length: 100 }, (_, i) => (
          <div
            key={`small-${i}`}
            className="absolute w-1 h-1 rounded-full animate-pulse opacity-60"
            style={{
              backgroundColor: '#5B56E7',
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 8}s`,
              animationDuration: `${1.5 + Math.random() * 2}s`
            }}
          />
        ))}
      </div>

      {/* Floating orbs for depth */}
      <div className="absolute inset-0">
        <div 
          className="absolute top-20 left-20 w-32 h-32 rounded-full animate-pulse opacity-10" 
          style={{ 
            backgroundColor: '#E7569A',
            animationDuration: '6s' 
          }} 
        />
        <div 
          className="absolute top-40 right-32 w-24 h-24 rounded-full animate-pulse opacity-10" 
          style={{ 
            backgroundColor: '#E2E756',
            animationDuration: '8s', 
            animationDelay: '2s' 
          }} 
        />
        <div 
          className="absolute bottom-32 left-40 w-20 h-20 rounded-full animate-pulse opacity-10" 
          style={{ 
            backgroundColor: '#56E7A4',
            animationDuration: '5s', 
            animationDelay: '1s' 
          }} 
        />
        <div 
          className="absolute bottom-20 right-20 w-28 h-28 rounded-full animate-pulse opacity-10" 
          style={{ 
            backgroundColor: '#5B56E7',
            animationDuration: '7s', 
            animationDelay: '3s' 
          }} 
        />
      </div>

      {/* Subtle moving gradient overlay */}
      <div 
        className="absolute inset-0 animate-pulse opacity-5" 
        style={{ 
          background: `linear-gradient(to right, transparent, #E7569A, transparent)`,
          animationDuration: '10s' 
        }} 
      />
      
      {/* Bottom gradient for login form contrast */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/40" />
    </div>
  );
};
