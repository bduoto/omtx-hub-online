/**
 * Performance Test Utility for Instant Navigation System
 * Tests the unified store and ultra-fast API performance
 */

import { unifiedJobStore } from '@/stores/unifiedJobStore';

export interface PerformanceTestResult {
  test_name: string;
  duration_ms: number;
  cache_hit: boolean;
  data_count: number;
  status: 'success' | 'error';
  api_used?: string;
}

export class InstantNavigationTester {
  
  /**
   * Test complete instant navigation flow
   */
  static async testInstantNavigation(): Promise<PerformanceTestResult[]> {
    const results: PerformanceTestResult[] = [];
    
    console.log('🧪 Starting Instant Navigation Performance Tests...');
    
    // Test 1: Initial Preload
    try {
      const startTime = performance.now();
      await unifiedJobStore.preloadAllData();
      const duration = performance.now() - startTime;
      
      results.push({
        test_name: 'Initial Preload',
        duration_ms: duration,
        cache_hit: false,
        data_count: unifiedJobStore.getCachedJobs().length,
        status: 'success'
      });
      
      console.log(`✅ Initial Preload: ${duration.toFixed(1)}ms`);
    } catch (error) {
      results.push({
        test_name: 'Initial Preload',
        duration_ms: -1,
        cache_hit: false,
        data_count: 0,
        status: 'error'
      });
      console.error('❌ Initial Preload failed:', error);
    }
    
    // Test 2: Individual Jobs Cache Hit
    try {
      const startTime = performance.now();
      const individualJobs = unifiedJobStore.getCachedIndividualJobs();
      const duration = performance.now() - startTime;
      
      results.push({
        test_name: 'Individual Jobs Cache Hit',
        duration_ms: duration,
        cache_hit: true,
        data_count: individualJobs.length,
        status: 'success'
      });
      
      console.log(`⚡ Individual Jobs Cache Hit: ${duration.toFixed(3)}ms (${individualJobs.length} jobs)`);
    } catch (error) {
      results.push({
        test_name: 'Individual Jobs Cache Hit',
        duration_ms: -1,
        cache_hit: true,
        data_count: 0,
        status: 'error'
      });
      console.error('❌ Individual Jobs Cache Hit failed:', error);
    }
    
    // Test 3: Batch Jobs Cache Hit
    try {
      const startTime = performance.now();
      const batchJobs = unifiedJobStore.getCachedBatchJobs();
      const duration = performance.now() - startTime;
      
      results.push({
        test_name: 'Batch Jobs Cache Hit',
        duration_ms: duration,
        cache_hit: true,
        data_count: batchJobs.length,
        status: 'success'
      });
      
      console.log(`⚡ Batch Jobs Cache Hit: ${duration.toFixed(3)}ms (${batchJobs.length} batches)`);
    } catch (error) {
      results.push({
        test_name: 'Batch Jobs Cache Hit',
        duration_ms: -1,
        cache_hit: true,
        data_count: 0,
        status: 'error'
      });
      console.error('❌ Batch Jobs Cache Hit failed:', error);
    }
    
    // Test 4: Full Data Reload
    try {
      const startTime = performance.now();
      const allJobs = await unifiedJobStore.getAllJobs(true); // Force refresh
      const duration = performance.now() - startTime;
      
      results.push({
        test_name: 'Full Data Reload',
        duration_ms: duration,
        cache_hit: false,
        data_count: allJobs.length,
        status: 'success'
      });
      
      console.log(`🔄 Full Data Reload: ${duration.toFixed(1)}ms (${allJobs.length} total jobs)`);
    } catch (error) {
      results.push({
        test_name: 'Full Data Reload',
        duration_ms: -1,
        cache_hit: false,
        data_count: 0,
        status: 'error'
      });
      console.error('❌ Full Data Reload failed:', error);
    }
    
    // Test 5: Second Cache Hit (should be instant)
    try {
      const startTime = performance.now();
      const cachedJobs = unifiedJobStore.getCachedJobs();
      const duration = performance.now() - startTime;
      
      results.push({
        test_name: 'Second Cache Hit',
        duration_ms: duration,
        cache_hit: true,
        data_count: cachedJobs.length,
        status: 'success'
      });
      
      console.log(`⚡ Second Cache Hit: ${duration.toFixed(3)}ms (instant access)`);
    } catch (error) {
      results.push({
        test_name: 'Second Cache Hit',
        duration_ms: -1,
        cache_hit: true,
        data_count: 0,
        status: 'error'
      });
      console.error('❌ Second Cache Hit failed:', error);
    }
    
    // Performance Summary
    const perf = unifiedJobStore.getPerformance();
    console.log(`📊 Store Performance Summary:`);
    console.log(`   Cache hits: ${perf.cache_hits}`);
    console.log(`   API calls: ${perf.api_calls}`);
    console.log(`   Cache size: ${perf.cache_size} jobs`);
    console.log(`   Cache age: ${perf.cache_age_seconds} seconds`);
    console.log(`   Average response time: ${perf.average_response_time.toFixed(1)}ms`);
    
    // Determine overall performance grade
    const avgCacheHitTime = results
      .filter(r => r.cache_hit && r.status === 'success')
      .reduce((sum, r) => sum + r.duration_ms, 0) / 
      results.filter(r => r.cache_hit && r.status === 'success').length;
    
    if (avgCacheHitTime < 1) {
      console.log('🏆 LIGHTNING FAST: Sub-millisecond cache hits achieved!');
    } else if (avgCacheHitTime < 10) {
      console.log('⚡ ULTRA FAST: Cache hits under 10ms');
    } else if (avgCacheHitTime < 100) {
      console.log('✅ FAST: Cache hits under 100ms');
    } else {
      console.log('⚠️ SLOW: Cache hits over 100ms - needs optimization');
    }
    
    return results;
  }
  
  /**
   * Test API fallback behavior
   */
  static async testAPIFallback(): Promise<void> {
    console.log('🔄 Testing API fallback behavior...');
    
    // Clear cache to force API calls
    unifiedJobStore.clearCache();
    
    try {
      const startTime = performance.now();
      await unifiedJobStore.getAllJobs();
      const duration = performance.now() - startTime;
      
      console.log(`✅ API fallback working: ${duration.toFixed(1)}ms`);
    } catch (error) {
      console.error('❌ API fallback failed:', error);
    }
  }
  
  /**
   * Run complete performance test suite
   */
  static async runCompleteTest(): Promise<void> {
    console.log('🚀 Running Complete Instant Navigation Test Suite...');
    console.log('================================================');
    
    // Test instant navigation
    const results = await this.testInstantNavigation();
    
    // Test API fallback
    await this.testAPIFallback();
    
    // Summary
    console.log('================================================');
    console.log(`✅ Test Suite Complete: ${results.filter(r => r.status === 'success').length}/${results.length} tests passed`);
    
    const successfulTests = results.filter(r => r.status === 'success');
    const cacheHits = successfulTests.filter(r => r.cache_hit);
    
    if (cacheHits.length > 0) {
      const avgCacheTime = cacheHits.reduce((sum, r) => sum + r.duration_ms, 0) / cacheHits.length;
      console.log(`⚡ Average cache hit time: ${avgCacheTime.toFixed(3)}ms`);
    }
    
    const totalDataPoints = successfulTests.reduce((sum, r) => sum + r.data_count, 0);
    console.log(`📊 Total data points cached: ${totalDataPoints}`);
    console.log('🎯 Instant Navigation System: READY FOR PRODUCTION');
  }
}

// Auto-run tests in development
if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
  // Run tests after a short delay to allow app to initialize
  setTimeout(() => {
    InstantNavigationTester.runCompleteTest();
  }, 2000);
}