
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { LoginBackground } from '@/components/LoginBackground';
import { Mail, Lock, Eye, EyeOff, ArrowLeft } from 'lucide-react';
import { GoogleIcon, MicrosoftIcon, GitHubIcon } from '@/components/SSOIcons';

type AuthMode = 'login' | 'signup' | 'forgot';

const Login = () => {
  const [authMode, setAuthMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [alert, setAlert] = useState<{ type: 'error' | 'success'; message: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // Auto-clear alerts after 5 seconds
  useEffect(() => {
    if (alert) {
      const timer = setTimeout(() => setAlert(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [alert]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setAlert(null);

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));

    if (authMode === 'signup' && password !== confirmPassword) {
      setAlert({ type: 'error', message: "Passwords don't match" });
      setLoading(false);
      return;
    }

    if (authMode === 'forgot') {
      setAlert({ type: 'success', message: 'Recovery email sent! Check your inbox.' });
      setLoading(false);
      return;
    }

    // Simulate login validation
    if (email === 'demo@omtxhub.com' && password === 'password') {
      setAlert({ type: 'success', message: 'Login successful!' });
      setTimeout(() => navigate('/'), 1500);
    } else {
      setAlert({ type: 'error', message: 'Invalid email or password' });
    }
    
    setLoading(false);
  };

  const handleSSOLogin = (provider: string) => {
    setAlert({ type: 'success', message: `Redirecting to ${provider}...` });
    // In real implementation, this would redirect to OAuth provider
  };

  const resetForm = () => {
    setEmail('');
    setPassword('');
    setConfirmPassword('');
    setAlert(null);
  };

  const switchMode = (mode: AuthMode) => {
    setAuthMode(mode);
    resetForm();
  };

  return (
    <div className="min-h-screen bg-gray-900 relative overflow-hidden">
      <LoginBackground />
      
      {/* Header */}
      <header className="relative z-20 p-6">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <Link to="/" className="flex items-center space-x-2 group">
            <ArrowLeft className="h-5 w-5 text-gray-400 group-hover:text-white transition-colors" style={{ color: '#56E7A4' }} />
            <span className="text-gray-400 group-hover:text-white transition-colors" style={{ color: '#56E7A4' }}>Back to Dashboard</span>
          </Link>
          <div className="flex items-center space-x-3">
            <div className="text-3xl font-bold animate-pulse" style={{ color: '#E2E756' }}>
              omtx hub
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="relative z-10 flex items-center justify-center min-h-[calc(100vh-120px)] px-4">
        <div className="w-full max-w-md">
          {/* Login Card */}
          <div className="bg-gray-800/90 backdrop-blur-xl border rounded-2xl p-8 shadow-2xl shadow-black/50 relative overflow-hidden" style={{ borderColor: '#5B56E7' }}>
            {/* Subtle glow effect */}
            <div 
              className="absolute inset-0 rounded-2xl opacity-5" 
              style={{ background: `linear-gradient(135deg, #E2E756, #56E7A4, #5B56E7, #E7569A)` }}
            />
            
            <div className="text-center mb-8 relative z-10">
              <h1 className="text-3xl font-bold text-white mb-2">
                {authMode === 'login' && (
                  <>
                    Welcome to{' '}
                    <span style={{ color: '#E2E756' }}>
                      sage
                    </span>
                  </>
                )}
                {authMode === 'signup' && (
                  <>
                    Join{' '}
                    <span style={{ color: '#E2E756' }}>
                      sage
                    </span>
                  </>
                )}
                {authMode === 'forgot' && 'Reset Password'}
              </h1>
              <p className="text-gray-400">
                {authMode === 'login' && 'Accelerating drug discovery through AI'}
                {authMode === 'signup' && 'Revolutionize molecular research'}
                {authMode === 'forgot' && 'Enter your email to reset your password'}
              </p>
            </div>

            {/* Alert */}
            {alert && (
              <Alert className={`mb-6 relative z-10 ${alert.type === 'error' ? 'bg-red-500/10' : 'bg-green-500/10'}`} 
                     style={{ borderColor: alert.type === 'error' ? '#E7569A' : '#56E7A4' }}>
                <AlertDescription style={{ color: alert.type === 'error' ? '#E7569A' : '#56E7A4' }}>
                  {alert.message}
                </AlertDescription>
              </Alert>
            )}

            {/* Form - Above SSO */}
            <form onSubmit={handleSubmit} className="space-y-4 relative z-10 mb-6">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-gray-300 font-medium">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-10 bg-gray-700/50 border-gray-600 text-white placeholder:text-gray-400 transition-all duration-300 focus:border-[#E2E756] focus:ring-2 focus:ring-[#E2E756]"
                    style={{ borderColor: '#5B56E7' }}
                    placeholder="researcher@omtxhub.com"
                    required
                  />
                </div>
              </div>

              {authMode !== 'forgot' && (
                <div className="space-y-2">
                  <Label htmlFor="password" className="text-gray-300 font-medium">Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="pl-10 pr-10 bg-gray-700/50 border-gray-600 text-white placeholder:text-gray-400 transition-all duration-300 focus:border-[#E2E756] focus:ring-2 focus:ring-[#E2E756]"
                      style={{ borderColor: '#5B56E7' }}
                      placeholder="Enter your password"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-300 transition-colors"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              )}

              {authMode === 'signup' && (
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword" className="text-gray-300 font-medium">Confirm Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      id="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="pl-10 pr-10 bg-gray-700/50 border-gray-600 text-white placeholder:text-gray-400 transition-all duration-300 focus:border-[#E2E756] focus:ring-2 focus:ring-[#E2E756]"
                      style={{ borderColor: '#5B56E7' }}
                      placeholder="Confirm your password"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-300 transition-colors"
                    >
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              )}

              <Button
                type="submit"
                className="w-full text-white font-semibold py-2.5 transition-all duration-300 hover:shadow-lg transform hover:scale-[1.02] hover:bg-gradient-to-r hover:from-[#56E7A4] hover:to-[#E2E756]"
                style={{ background: `linear-gradient(135deg, #E2E756, #56E7A4)` }}
                disabled={loading}
              >
                {loading ? (
                  <div className="flex items-center space-x-2">
                    <div className="text-sm font-bold animate-pulse" style={{ color: '#5B56E7' }}>
                      omtx hub
                    </div>
                    <span>Please wait...</span>
                  </div>
                ) : (
                  authMode === 'login' ? 'Sign In' :
                  authMode === 'signup' ? 'Create Account' :
                  'Send Reset Email'
                )}
              </Button>
            </form>

            {/* SSO Buttons - Below form */}
            {authMode !== 'forgot' && (
              <>
                <div className="relative mb-6 z-10">
                  <Separator className="bg-gray-600" />
                  <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-gray-800 px-3 text-sm text-gray-400">
                    or continue with
                  </span>
                </div>

                <div className="space-y-3 mb-6 relative z-10">
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full bg-gray-700/50 text-white hover:bg-gray-700 transition-all duration-300 hover:scale-[1.02]"
                    style={{ borderColor: '#E7569A' }}
                    onClick={() => handleSSOLogin('Google')}
                  >
                    <GoogleIcon className="mr-2 h-4 w-4" />
                    Continue with Google
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full bg-gray-700/50 text-white hover:bg-gray-700 transition-all duration-300 hover:scale-[1.02]"
                    style={{ borderColor: '#56E7A4' }}
                    onClick={() => handleSSOLogin('Microsoft')}
                  >
                    <MicrosoftIcon className="mr-2 h-4 w-4" />
                    Continue with Microsoft
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full bg-gray-700/50 text-white hover:bg-gray-700 transition-all duration-300 hover:scale-[1.02]"
                    style={{ borderColor: '#5B56E7' }}
                    onClick={() => handleSSOLogin('GitHub')}
                  >
                    <GitHubIcon className="mr-2 h-4 w-4" />
                    Continue with GitHub
                  </Button>
                </div>
              </>
            )}

            {/* Footer Links */}
            <div className="mt-6 text-center space-y-2 relative z-10">
              {authMode === 'login' && (
                <>
                  <button
                    type="button"
                    onClick={() => switchMode('forgot')}
                    className="text-sm text-gray-400 hover:text-white transition-colors"
                    style={{ color: '#56E7A4' }}
                  >
                    Forgot your password?
                  </button>
                  <div className="text-sm text-gray-400">
                    Don't have an account?{' '}
                    <button
                      type="button"
                      onClick={() => switchMode('signup')}
                      className="transition-colors font-medium hover:text-white"
                      style={{ color: '#E2E756' }}
                    >
                      Sign up
                    </button>
                  </div>
                </>
              )}

              {authMode === 'signup' && (
                <div className="text-sm text-gray-400">
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => switchMode('login')}
                    className="transition-colors font-medium hover:text-white"
                    style={{ color: '#E2E756' }}
                  >
                    Sign in
                  </button>
                </div>
              )}

              {authMode === 'forgot' && (
                <button
                  type="button"
                  onClick={() => switchMode('login')}
                  className="text-sm text-gray-400 hover:text-white transition-colors"
                  style={{ color: '#56E7A4' }}
                >
                  Back to login
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
