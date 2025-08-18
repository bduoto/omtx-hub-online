
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import React, { useEffect } from "react";
import Index from "./pages/Index";
import MyResults from "./pages/MyResults";
import MyBatches from "./pages/MyBatches";
import BatchResultsFast from "./pages/BatchResultsFast";
import Gallery from "./pages/Gallery";
import Studio from "./pages/Studio";
import User from "./pages/User";
import NotFound from "./pages/NotFound";
import IAM from "./pages/IAM";
import Login from "./pages/Login";
import Boltz2 from "./pages/Boltz2";
import RFAntibody from "./pages/RFAntibody";
import JobView from "./pages/JobView";
import { useTimeout } from "./hooks/useTimeout";
import { unifiedJobStore } from "@/stores/unifiedJobStore";


const queryClient = new QueryClient();

const AppWithTimeout = ({ children }: { children: React.ReactNode }) => {
  useTimeout(20); // 20 minute timeout
  
  // INSTANT NAVIGATION STRATEGY - Preload all user data on app startup
  useEffect(() => {
    console.log('🚀 App startup - initiating INSTANT NAVIGATION preload strategy...');
    
    // Background preload with intelligent timing
    const preloadUserData = async () => {
      try {
        const startTime = performance.now();
        
        // Start preloading immediately in background
        await unifiedJobStore.preloadAllData();
        
        const loadTime = performance.now() - startTime;
        
        if (loadTime < 100) {
          console.log(`⚡ LIGHTNING preload: ${loadTime.toFixed(1)}ms - Navigation will be instant!`);
        } else if (loadTime < 1000) {
          console.log(`⚡ ULTRA-FAST preload: ${loadTime.toFixed(0)}ms - Navigation ready`);
        } else {
          console.log(`✅ Background preload: ${loadTime.toFixed(0)}ms - Data cached for instant access`);
        }
        
        // Show performance stats
        const perf = unifiedJobStore.getPerformance();
        console.log(`📈 Preload complete: ${perf.cache_size} jobs cached, ready for sub-millisecond navigation`);
        
        // Run performance tests in development
        if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
          console.log('🧪 Instant navigation system ready for testing');
          console.log('   Navigate to My Results or My Batches to test performance');
        }
        
      } catch (error) {
        console.warn('⚠️ Background preload failed (non-critical):', error);
        // Non-critical - pages will still work with on-demand loading
      }
    };
    
    // Start preload after a short delay to not block initial page render
    const preloadTimer = setTimeout(preloadUserData, 100);
    
    return () => clearTimeout(preloadTimer);
  }, []);
  
  return <>{children}</>;
};

const App = () => {
  console.log('⚡ OMTX-Hub starting with INSTANT NAVIGATION architecture...');
  
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/*" element={
              <AppWithTimeout>
                <Routes>
                  <Route path="/" element={<Index />} />
                  <Route path="/my-results" element={<MyResults />} />
                  <Route path="/my-batches" element={<MyBatches />} />
                  <Route path="/batch-results/:batchId" element={<BatchResultsFast />} />
                  <Route path="/gallery" element={<Gallery />} />
                  <Route path="/studio" element={<Studio />} />
                  <Route path="/user" element={<User />} />
                  <Route path="/iam" element={<IAM />} />
                  <Route path="/boltz2" element={<Boltz2 />} />
                  <Route path="/rfantibody" element={<RFAntibody />} />
                  <Route path="/boltz2/job/:jobId" element={<JobView />} />
                  <Route path="/rfantibody/job/:jobId" element={<JobView />} />
                  {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </AppWithTimeout>
            } />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
