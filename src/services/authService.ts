/**
 * Authentication Service - REQUIRED for all API calls
 * Distinguished Engineer Implementation - Handles JWT, API keys, and demo mode
 */

interface AuthToken {
  token: string;
  userId: string;
  email?: string;
  tier?: string;
  expiresAt?: number;
}

interface AuthHeaders {
  'Content-Type': string;
  'Authorization'?: string;
  'X-User-Id'?: string;
  'X-API-Key'?: string;
  'X-Demo-Mode'?: string;
  [key: string]: string | undefined;
}

class AuthService {
  private token: string | null = null;
  private userId: string | null = null;
  private email: string | null = null;
  private tier: string | null = null;
  private apiKey: string | null = null;
  private demoMode: boolean = false;
  
  constructor() {
    this.initializeAuth();
    this.setupMessageListener();
  }
  
  private initializeAuth() {
    // Try to get auth data from various sources
    
    // 1. Check localStorage (for standalone mode)
    this.token = localStorage.getItem('omtx_token');
    this.userId = localStorage.getItem('omtx_user_id');
    this.email = localStorage.getItem('omtx_email');
    this.tier = localStorage.getItem('omtx_tier');
    this.apiKey = localStorage.getItem('omtx_api_key');
    
    // 2. Check URL parameters (for embedded mode)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('token')) {
      this.setAuth({
        token: urlParams.get('token')!,
        userId: urlParams.get('userId') || 'unknown',
        email: urlParams.get('email') || undefined,
        tier: urlParams.get('tier') || 'free'
      });
    }
    
    // 3. Check for demo mode
    if (urlParams.get('demo') === 'true' || window.location.hostname === 'localhost') {
      this.enableDemoMode();
    }
    
    // 4. Request auth from parent window (for iframe embedding)
    if (window.parent !== window) {
      window.parent.postMessage({ type: 'REQUEST_AUTH' }, '*');
    }
    
    console.log('🔐 AuthService initialized', {
      hasToken: !!this.token,
      hasUserId: !!this.userId,
      demoMode: this.demoMode
    });
  }
  
  private setupMessageListener() {
    // Listen for messages from parent app
    window.addEventListener('message', (event) => {
      if (event.data.type === 'AUTH_TOKEN') {
        this.setAuth({
          token: event.data.token,
          userId: event.data.userId,
          email: event.data.email,
          tier: event.data.tier
        });
      } else if (event.data.type === 'AUTH_LOGOUT') {
        this.clearAuth();
      }
    });
  }
  
  setAuth(authData: AuthToken) {
    this.token = authData.token;
    this.userId = authData.userId;
    this.email = authData.email || null;
    this.tier = authData.tier || 'free';
    
    // Store in localStorage
    localStorage.setItem('omtx_token', this.token);
    localStorage.setItem('omtx_user_id', this.userId);
    if (this.email) localStorage.setItem('omtx_email', this.email);
    if (this.tier) localStorage.setItem('omtx_tier', this.tier);
    
    this.demoMode = false;
    
    console.log('✅ Auth set for user:', this.userId);
  }
  
  setApiKey(apiKey: string) {
    this.apiKey = apiKey;
    localStorage.setItem('omtx_api_key', apiKey);
    console.log('🔑 API key set');
  }
  
  enableDemoMode() {
    this.demoMode = true;
    this.userId = 'demo-user';
    this.email = 'demo@omtx.com';
    this.tier = 'pro';
    this.token = null; // Demo mode doesn't use JWT
    
    localStorage.setItem('omtx_demo_mode', 'true');
    localStorage.setItem('omtx_user_id', this.userId);
    localStorage.setItem('omtx_email', this.email);
    localStorage.setItem('omtx_tier', this.tier);
    
    console.log('🎭 Demo mode enabled');
  }
  
  clearAuth() {
    this.token = null;
    this.userId = null;
    this.email = null;
    this.tier = null;
    this.apiKey = null;
    this.demoMode = false;
    
    // Clear localStorage
    localStorage.removeItem('omtx_token');
    localStorage.removeItem('omtx_user_id');
    localStorage.removeItem('omtx_email');
    localStorage.removeItem('omtx_tier');
    localStorage.removeItem('omtx_api_key');
    localStorage.removeItem('omtx_demo_mode');
    
    console.log('🚪 Auth cleared');
  }
  
  getHeaders(): AuthHeaders {
    const headers: AuthHeaders = {
      'Content-Type': 'application/json',
    };
    
    // JWT token (highest priority)
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    // API key (alternative auth)
    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }
    
    // User ID (always include if available)
    if (this.userId) {
      headers['X-User-Id'] = this.userId;
    }
    
    // Demo mode
    if (this.demoMode) {
      headers['X-Demo-Mode'] = 'true';
      headers['X-User-Id'] = 'demo-user';
    }
    
    return headers;
  }
  
  async makeAuthenticatedRequest(url: string, options: RequestInit = {}): Promise<Response> {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      }
    });
    
    // Handle authentication errors
    if (response.status === 401) {
      console.warn('🔒 Authentication failed - token may be expired');
      
      // Try to refresh token from parent app
      if (window.parent !== window) {
        window.parent.postMessage({ type: 'TOKEN_EXPIRED' }, '*');
      }
      
      // If in demo mode, continue anyway
      if (this.demoMode) {
        console.log('🎭 Demo mode - ignoring auth error');
      }
    }
    
    return response;
  }
  
  // Convenience methods for common API patterns
  async get(url: string): Promise<Response> {
    return this.makeAuthenticatedRequest(url, { method: 'GET' });
  }
  
  async post(url: string, data: any): Promise<Response> {
    return this.makeAuthenticatedRequest(url, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }
  
  async put(url: string, data: any): Promise<Response> {
    return this.makeAuthenticatedRequest(url, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }
  
  async delete(url: string): Promise<Response> {
    return this.makeAuthenticatedRequest(url, { method: 'DELETE' });
  }
  
  // Getters
  getToken(): string | null {
    return this.token;
  }
  
  getUserId(): string | null {
    return this.userId;
  }
  
  getEmail(): string | null {
    return this.email;
  }
  
  getTier(): string | null {
    return this.tier;
  }
  
  isDemoMode(): boolean {
    return this.demoMode;
  }
  
  isAuthenticated(): boolean {
    return !!(this.token || this.apiKey || this.demoMode);
  }
  
  // User info for display
  getUserInfo() {
    return {
      userId: this.userId,
      email: this.email,
      tier: this.tier,
      authenticated: this.isAuthenticated(),
      demoMode: this.demoMode
    };
  }
  
  // API endpoint helpers with proper versioning
  getApiUrl(endpoint: string): string {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://34.29.29.170';

    // Use v1 API for all endpoints - clean consolidated API
    return `${baseUrl}/api/v1${endpoint}`;
  }
  
  // Batch-specific methods
  async submitBatch(batchData: any): Promise<Response> {
    return this.post(this.getApiUrl('/batches/submit'), batchData);
  }
  
  async getBatchStatus(batchId: string): Promise<Response> {
    return this.get(this.getApiUrl(`/batches/${batchId}`));
  }
  
  async getBatchResults(batchId: string): Promise<Response> {
    return this.get(this.getApiUrl(`/batches/${batchId}/results`));
  }
  
  // Job-specific methods
  async submitJob(jobData: any): Promise<Response> {
    return this.post(this.getApiUrl('/predict'), jobData);
  }
  
  async getJobStatus(jobId: string): Promise<Response> {
    return this.get(this.getApiUrl(`/jobs/${jobId}`));
  }
  
  async getJobLogs(jobId: string): Promise<Response> {
    return this.get(this.getApiUrl(`/jobs/${jobId}/logs`));
  }
  
  // Usage and analytics
  async getUserUsage(): Promise<Response> {
    return this.get(this.getApiUrl('/usage'));
  }
  
  async getUserAnalytics(): Promise<Response> {
    return this.get(this.getApiUrl('/analytics'));
  }
}

// Global singleton instance
export const authService = new AuthService();

// Export types for TypeScript
export type { AuthToken, AuthHeaders };

// Default export
export default authService;
