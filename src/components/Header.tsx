
import React from 'react';
import { Button } from '@/components/ui/button';
import { Link, useLocation } from 'react-router-dom';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Atom, Settings, LogOut, DollarSign, User } from 'lucide-react';

export const Header = () => {
  const location = useLocation();

  return (
    <header className="bg-gray-800 border-b border-gray-700">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            {location.pathname === '/login' ? (
              <Link to="/" className="group">
                <div className="text-3xl font-bold text-[#E2E756] hover:text-[#f0f168] transition-colors cursor-pointer">
                  omtx hub
                </div>
              </Link>
            ) : (
              <Link to="/login" className="group">
                <img 
                  src="/lovable-uploads/0fe9001f-8e54-4fec-ac0c-898a9cbef2ca.png" 
                  alt="OM Logo" 
                  className="h-16 w-auto hover:opacity-80 transition-opacity rounded-lg"
                />
              </Link>
            )}
          </div>
          
          <nav className="hidden md:flex items-center space-x-8">
            <a href="#" className="text-gray-300 hover:text-[#E2E756] transition-colors">Contact</a>
            <Link to="/my-results" className="text-gray-300 hover:text-[#E2E756] transition-colors">My Jobs</Link>
            <a href="#" className="text-gray-300 hover:text-[#E2E756] transition-colors">Blog</a>
            <a href="#" className="text-gray-300 hover:text-[#E2E756] transition-colors">Docs</a>
            <a href="#" className="text-gray-300 hover:text-[#E2E756] transition-colors">API</a>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="relative h-8 w-8 rounded-full p-0 group overflow-hidden
                    hover:ring-2 hover:ring-[#E2E756] hover:ring-offset-2 hover:ring-offset-gray-800 
                    hover:shadow-2xl hover:shadow-[#E2E756]/30 
                    active:scale-95 active:shadow-inner active:shadow-[#E2E756]/50
                    transition-all duration-300 ease-out
                    before:absolute before:inset-0 before:rounded-full before:bg-gradient-to-r 
                    before:from-[#E2E756]/20 before:to-transparent before:opacity-0 
                    hover:before:opacity-100 before:transition-opacity before:duration-300
                    after:absolute after:inset-0 after:rounded-full after:border-2 
                    after:border-transparent hover:after:border-[#E2E756]/20
                    after:transition-all after:duration-300"
                >
                  <Avatar className="h-8 w-8 relative z-10 transition-all duration-300 group-hover:scale-110 group-active:scale-105">
                    <AvatarImage 
                      src="" 
                      alt="User" 
                      className="transition-all duration-300 group-hover:brightness-110 group-hover:contrast-110"
                    />
                    <AvatarFallback className="bg-gradient-to-br from-[#E2E756] to-[#d4d435] text-gray-900 font-bold text-xs
                      transition-all duration-300 group-hover:from-[#f0f168] group-hover:to-[#E2E756]
                      group-active:from-[#d4d435] group-active:to-[#c4c420]
                      shadow-inner shadow-black/20">
                      <Atom className="h-4 w-4 transition-all duration-300 group-hover:scale-110 group-active:rotate-12 group-hover:animate-pulse" />
                    </AvatarFallback>
                  </Avatar>
                  
                  {/* Animated glow ring */}
                  <div className="absolute inset-0 rounded-full border-2 border-[#E2E756]/0 
                    group-hover:border-[#E2E756]/60 group-hover:animate-pulse 
                    transition-all duration-300 pointer-events-none" />
                  
                  {/* Ripple effect */}
                  <div className="absolute inset-0 rounded-full bg-[#E2E756]/10 scale-0 
                    group-active:scale-150 group-active:opacity-0 
                    transition-all duration-500 pointer-events-none" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent 
                className="w-56 bg-gray-800 border-gray-700 text-gray-200 shadow-2xl shadow-black/50
                  animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-200" 
                align="end" 
                forceMount
              >
                <DropdownMenuItem className="hover:bg-gray-700 hover:text-[#E2E756] cursor-pointer transition-colors duration-200" asChild>
                  <Link to="/user">
                    <Atom className="mr-2 h-4 w-4" />
                    <span>Account</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem className="hover:bg-gray-700 hover:text-[#E2E756] cursor-pointer transition-colors duration-200">
                  <Settings className="mr-2 h-4 w-4" />
                  <span>Settings</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="hover:bg-gray-700 hover:text-[#E2E756] cursor-pointer transition-colors duration-200">
                  <DollarSign className="mr-2 h-4 w-4" />
                  <span>Billing</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="hover:bg-gray-700 hover:text-[#E2E756] cursor-pointer transition-colors duration-200" asChild>
                  <Link to="/iam">
                    <User className="mr-2 h-4 w-4" />
                    <span>IAM</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-gray-700" />
                <DropdownMenuItem className="hover:bg-gray-700 hover:text-red-400 cursor-pointer transition-colors duration-200 focus:text-red-400" asChild>
                  <Link to="/login">
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Sign Out</span>
                  </Link>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </nav>
        </div>
      </div>
    </header>
  );
};
