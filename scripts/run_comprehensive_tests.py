#!/usr/bin/env python3
"""
Comprehensive Test Runner for OMTX-Hub
Runs all tests in the correct order with proper setup and teardown
"""

import asyncio
import subprocess
import sys
import os
import time
import signal
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import argparse

class OMTXTestRunner:
    """Comprehensive test runner for OMTX-Hub"""
    
    def __init__(self, backend_url: str = "http://localhost:8000", frontend_url: str = "http://localhost:8081"):
        self.backend_url = backend_url
        self.frontend_url = frontend_url
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self.test_results: Dict[str, Any] = {}
        
    def setup_environment(self):
        """Setup test environment"""
        print("🔧 Setting up test environment...")
        
        # Ensure we're in the right directory
        project_root = Path(__file__).parent.parent
        os.chdir(project_root)
        
        # Set test environment variables
        os.environ['ENVIRONMENT'] = 'test'
        os.environ['DEBUG'] = 'true'
        os.environ['TEST_BASE_URL'] = self.backend_url
        os.environ['TEST_FRONTEND_URL'] = self.frontend_url
        
        print("✅ Environment configured")
    
    def start_backend(self) -> bool:
        """Start backend server"""
        print("🚀 Starting backend server...")
        
        try:
            # Change to backend directory
            backend_dir = Path("backend")
            
            # Start backend process
            self.backend_process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=backend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, 'PYTHONPATH': str(backend_dir.absolute())}
            )
            
            # Wait for backend to start
            for attempt in range(30):  # 30 seconds timeout
                try:
                    import httpx
                    with httpx.Client() as client:
                        response = client.get(f"{self.backend_url}/health", timeout=2.0)
                        if response.status_code == 200:
                            print("✅ Backend started successfully")
                            return True
                except:
                    pass
                
                time.sleep(1)
                
                # Check if process died
                if self.backend_process.poll() is not None:
                    stdout, stderr = self.backend_process.communicate()
                    print(f"❌ Backend process died:")
                    print(f"STDOUT: {stdout.decode()}")
                    print(f"STDERR: {stderr.decode()}")
                    return False
            
            print("❌ Backend failed to start within timeout")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return False
    
    def start_frontend(self) -> bool:
        """Start frontend server"""
        print("🎨 Starting frontend server...")
        
        try:
            # Check if node_modules exists
            if not Path("node_modules").exists():
                print("📦 Installing frontend dependencies...")
                result = subprocess.run(["npm", "install"], capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"❌ npm install failed: {result.stderr}")
                    return False
            
            # Start frontend process
            self.frontend_process = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", "8081"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for frontend to start
            for attempt in range(30):  # 30 seconds timeout
                try:
                    import httpx
                    with httpx.Client() as client:
                        response = client.get(f"{self.frontend_url}", timeout=2.0)
                        if response.status_code == 200:
                            print("✅ Frontend started successfully")
                            return True
                except:
                    pass
                
                time.sleep(1)
                
                # Check if process died
                if self.frontend_process.poll() is not None:
                    stdout, stderr = self.frontend_process.communicate()
                    print(f"❌ Frontend process died:")
                    print(f"STDOUT: {stdout.decode()}")
                    print(f"STDERR: {stderr.decode()}")
                    return False
            
            print("❌ Frontend failed to start within timeout")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start frontend: {e}")
            return False
    
    def run_unit_tests(self) -> bool:
        """Run unit tests"""
        print("🧪 Running unit tests...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/unit/", 
                "-v", 
                "--tb=short",
                "--durations=10"
            ], capture_output=True, text=True)
            
            self.test_results['unit_tests'] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            if result.returncode == 0:
                print("✅ Unit tests passed")
                return True
            else:
                print("❌ Unit tests failed")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Failed to run unit tests: {e}")
            return False
    
    def run_integration_tests(self) -> bool:
        """Run integration tests"""
        print("🔗 Running integration tests...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/integration/", 
                "-v", 
                "--tb=short",
                "--durations=10",
                "-s"  # Don't capture output for integration tests
            ], capture_output=True, text=True)
            
            self.test_results['integration_tests'] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            if result.returncode == 0:
                print("✅ Integration tests passed")
                return True
            else:
                print("❌ Integration tests failed")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Failed to run integration tests: {e}")
            return False
    
    def run_validation_tests(self) -> bool:
        """Run environment validation tests"""
        print("✅ Running environment validation...")
        
        try:
            result = subprocess.run([
                sys.executable, "scripts/validate_local_dev.py"
            ], capture_output=True, text=True)
            
            self.test_results['validation_tests'] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            print(result.stdout)
            
            if result.returncode == 0:
                print("✅ Environment validation passed")
                return True
            else:
                print("❌ Environment validation failed")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Failed to run validation tests: {e}")
            return False
    
    def cleanup(self):
        """Cleanup test environment"""
        print("🧹 Cleaning up test environment...")
        
        # Stop backend
        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=10)
                print("✅ Backend stopped")
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
                print("⚠️ Backend force killed")
            except Exception as e:
                print(f"⚠️ Error stopping backend: {e}")
        
        # Stop frontend
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=10)
                print("✅ Frontend stopped")
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
                print("⚠️ Frontend force killed")
            except Exception as e:
                print(f"⚠️ Error stopping frontend: {e}")
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("📊 TEST REPORT")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['returncode'] == 0)
        
        print(f"Total Test Suites: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result['returncode'] == 0 else "❌ FAILED"
            print(f"\n{test_name}: {status}")
            
            if result['returncode'] != 0 and result['stderr']:
                print(f"Error: {result['stderr'][:200]}...")
        
        # Save detailed report
        report_file = f"test_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return passed_tests == total_tests
    
    def run_all_tests(self, skip_frontend: bool = False, skip_unit: bool = False, skip_integration: bool = False) -> bool:
        """Run all tests"""
        print("🚀 Starting comprehensive OMTX-Hub testing")
        print("="*60)
        
        success = True
        
        try:
            # Setup
            self.setup_environment()
            
            # Start services
            if not self.start_backend():
                return False
            
            if not skip_frontend and not self.start_frontend():
                print("⚠️ Frontend failed to start, continuing without frontend tests")
                skip_frontend = True
            
            # Run validation first
            if not self.run_validation_tests():
                success = False
            
            # Run unit tests
            if not skip_unit and not self.run_unit_tests():
                success = False
            
            # Run integration tests
            if not skip_integration and not self.run_integration_tests():
                success = False
            
        finally:
            self.cleanup()
        
        # Generate report
        report_success = self.generate_report()
        
        return success and report_success

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="OMTX-Hub Comprehensive Test Runner")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend tests")
    parser.add_argument("--skip-unit", action="store_true", help="Skip unit tests")
    parser.add_argument("--skip-integration", action="store_true", help="Skip integration tests")
    parser.add_argument("--backend-url", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--frontend-url", default="http://localhost:8081", help="Frontend URL")
    
    args = parser.parse_args()
    
    runner = OMTXTestRunner(args.backend_url, args.frontend_url)
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n🛑 Test run interrupted")
        runner.cleanup()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    success = runner.run_all_tests(
        skip_frontend=args.skip_frontend,
        skip_unit=args.skip_unit,
        skip_integration=args.skip_integration
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
