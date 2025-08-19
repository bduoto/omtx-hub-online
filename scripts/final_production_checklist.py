#!/usr/bin/env python3
"""
Final Production Checklist - COMPREHENSIVE PRE-DEMO VALIDATION
Distinguished Engineer Implementation - Complete production readiness assessment
"""

import subprocess
import requests
import os
import json
import sys
import logging
from typing import Tuple, List, Dict, Any

try:
    from colorama import Fore, Style, init
    init()
except ImportError:
    # Fallback if colorama not available
    class Fore:
        RED = GREEN = YELLOW = BLUE = CYAN = WHITE = ''
    class Style:
        RESET_ALL = ''

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionChecker:
    """Comprehensive production readiness checker"""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_total = 0
        self.critical_failures = []
        self.warnings = []
        
    def run_check(self, name: str, check_func, critical: bool = False) -> bool:
        """Run a single check with formatting"""
        
        self.checks_total += 1
        
        print(f"Checking {name}...", end=" ")
        
        try:
            result, message = check_func()
            
            if result:
                print(f"{Fore.GREEN}✅ PASSED{Style.RESET_ALL}")
                if message:
                    print(f"  {Fore.CYAN}{message}{Style.RESET_ALL}")
                self.checks_passed += 1
                return True
            else:
                print(f"{Fore.RED}❌ FAILED{Style.RESET_ALL}")
                if message:
                    print(f"  {Fore.YELLOW}{message}{Style.RESET_ALL}")
                
                if critical:
                    self.critical_failures.append((name, message))
                else:
                    self.warnings.append((name, message))
                
                return False
                
        except Exception as e:
            print(f"{Fore.RED}❌ ERROR: {e}{Style.RESET_ALL}")
            
            if critical:
                self.critical_failures.append((name, str(e)))
            else:
                self.warnings.append((name, str(e)))
            
            return False
    
    def check_modal_removed(self) -> Tuple[bool, str]:
        """Check that Modal is completely removed"""
        
        try:
            # Check for Modal imports
            result = subprocess.run(
                ["grep", "-r", "from modal", "backend/", "--include=*.py"],
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                modal_files = result.stdout.strip().split('\n')
                # Filter out comments and stubs
                real_imports = [line for line in modal_files if not line.strip().startswith('#') and 'stub' not in line.lower()]
                
                if real_imports:
                    return False, f"Found {len(real_imports)} Modal imports in: {', '.join([f.split(':')[0] for f in real_imports[:3]])}"
            
            # Check for Modal service references
            result = subprocess.run(
                ["grep", "-r", "modal_batch_executor", "backend/", "--include=*.py"],
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                service_refs = result.stdout.strip().split('\n')
                real_refs = [line for line in service_refs if not line.strip().startswith('#') and 'stub' not in line.lower()]
                
                if real_refs:
                    return False, f"Found {len(real_refs)} Modal service references"
            
            return True, "No Modal references found"
            
        except FileNotFoundError:
            return False, "grep command not found"
        except Exception as e:
            return False, f"Error checking Modal references: {str(e)}"
    
    def check_cloud_run_services(self) -> Tuple[bool, str]:
        """Check Cloud Run services exist"""
        
        required_files = [
            "backend/services/cloud_run_batch_processor.py",
            "backend/services/cloud_run_service.py",
            "backend/Dockerfile.gpu"
        ]
        
        missing_files = []
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            return False, f"Missing files: {', '.join(missing_files)}"
        
        # Check if files have content
        for file_path in required_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if len(content) < 100:  # Very basic check
                        return False, f"{file_path} appears to be empty or incomplete"
            except Exception as e:
                return False, f"Cannot read {file_path}: {str(e)}"
        
        return True, f"All {len(required_files)} Cloud Run service files exist"
    
    def check_environment_variables(self) -> Tuple[bool, str]:
        """Check critical environment variables"""
        
        required_vars = [
            "GCP_PROJECT_ID",
            "GCP_REGION", 
            "GCS_BUCKET_NAME"
        ]
        
        optional_vars = [
            "JWT_SECRET",
            "API_KEY_SALT",
            "DAILY_BUDGET_USD"
        ]
        
        missing_required = []
        missing_optional = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)
        
        for var in optional_vars:
            if not os.getenv(var):
                missing_optional.append(var)
        
        if missing_required:
            return False, f"Missing required vars: {', '.join(missing_required)}"
        
        message = f"All {len(required_vars)} required vars set"
        if missing_optional:
            message += f" (optional missing: {', '.join(missing_optional)})"
        
        return True, message
    
    def check_gcp_credentials(self) -> Tuple[bool, str]:
        """Check GCP credentials and access"""
        
        try:
            # Check if gcloud is available
            result = subprocess.run(
                ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, "gcloud auth failed - run 'gcloud auth login'"
            
            active_accounts = result.stdout.strip().split('\n')
            active_accounts = [acc for acc in active_accounts if acc]
            
            if not active_accounts:
                return False, "No active GCP accounts - run 'gcloud auth login'"
            
            return True, f"GCP authenticated as {active_accounts[0]}"
            
        except subprocess.TimeoutExpired:
            return False, "gcloud command timed out"
        except FileNotFoundError:
            return False, "gcloud CLI not installed"
        except Exception as e:
            return False, f"GCP auth check failed: {str(e)}"
    
    def check_python_imports(self) -> Tuple[bool, str]:
        """Check Python imports work"""
        
        import_tests = [
            ("Cloud Run Batch Processor", "from services.cloud_run_batch_processor import cloud_run_batch_processor"),
            ("Cloud Run Service", "from services.cloud_run_service import cloud_run_service"),
            ("Google Cloud Storage", "from google.cloud import storage"),
            ("Google Cloud Firestore", "from google.cloud import firestore")
        ]
        
        failed_imports = []
        
        for name, import_statement in import_tests:
            try:
                exec(import_statement)
            except ImportError as e:
                failed_imports.append(f"{name}: {str(e)}")
            except Exception as e:
                failed_imports.append(f"{name}: {str(e)}")
        
        if failed_imports:
            return False, f"Import failures: {'; '.join(failed_imports[:2])}"
        
        return True, f"All {len(import_tests)} critical imports successful"
    
    def check_api_health(self) -> Tuple[bool, str]:
        """Check API is responding"""
        
        api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        try:
            response = requests.get(f"{api_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")
                
                if status == "healthy":
                    return True, f"API healthy (response time: {response.elapsed.total_seconds():.2f}s)"
                else:
                    return False, f"API status: {status}"
            else:
                return False, f"API returned HTTP {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to API - is it running?"
        except requests.exceptions.Timeout:
            return False, "API health check timed out"
        except Exception as e:
            return False, f"API health check failed: {str(e)}"
    
    def check_frontend_files(self) -> Tuple[bool, str]:
        """Check frontend files exist"""
        
        frontend_files = [
            "src/services/authService.ts",
            "package.json"
        ]
        
        missing_files = []
        
        for file_path in frontend_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            return False, f"Missing frontend files: {', '.join(missing_files)}"
        
        # Check if authService has key methods
        try:
            with open("src/services/authService.ts", 'r') as f:
                content = f.read()
                
                required_methods = ["makeAuthenticatedRequest", "getHeaders", "submitBatch"]
                missing_methods = []
                
                for method in required_methods:
                    if method not in content:
                        missing_methods.append(method)
                
                if missing_methods:
                    return False, f"AuthService missing methods: {', '.join(missing_methods)}"
        
        except Exception as e:
            return False, f"Cannot validate authService: {str(e)}"
        
        return True, "Frontend files and authService validated"
    
    def check_docker_support(self) -> Tuple[bool, str]:
        """Check Docker and GPU support"""
        
        try:
            # Check if Docker is available
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return False, "Docker not available"
            
            # Check if GPU Dockerfile exists and has CUDA
            if not os.path.exists("backend/Dockerfile.gpu"):
                return False, "GPU Dockerfile missing"
            
            with open("backend/Dockerfile.gpu", 'r') as f:
                dockerfile_content = f.read()
                
                if "nvidia/cuda" not in dockerfile_content:
                    return False, "GPU Dockerfile missing CUDA support"
                
                if "boltz" not in dockerfile_content.lower():
                    return False, "GPU Dockerfile missing Boltz-2 installation"
            
            return True, f"Docker available, GPU Dockerfile validated"
            
        except subprocess.TimeoutExpired:
            return False, "Docker command timed out"
        except FileNotFoundError:
            return False, "Docker not installed"
        except Exception as e:
            return False, f"Docker check failed: {str(e)}"
    
    def check_deployment_scripts(self) -> Tuple[bool, str]:
        """Check deployment scripts exist"""
        
        deployment_scripts = [
            "scripts/deploy_to_cloud_run.sh",
            "scripts/remove_all_modal_references.py",
            "scripts/final_migration_check.sh"
        ]
        
        missing_scripts = []
        
        for script_path in deployment_scripts:
            if not os.path.exists(script_path):
                missing_scripts.append(script_path)
        
        if missing_scripts:
            return False, f"Missing deployment scripts: {', '.join(missing_scripts)}"
        
        return True, f"All {len(deployment_scripts)} deployment scripts exist"
    
    def run_all_checks(self) -> bool:
        """Run all production readiness checks"""
        
        print(f"\n{Fore.CYAN}🔍 PRODUCTION READINESS CHECKLIST{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        # Critical checks (must pass)
        print(f"{Fore.WHITE}🚨 CRITICAL CHECKS:{Style.RESET_ALL}")
        self.run_check("Modal Removal", self.check_modal_removed, critical=True)
        self.run_check("Cloud Run Services", self.check_cloud_run_services, critical=True)
        self.run_check("Environment Variables", self.check_environment_variables, critical=True)
        self.run_check("Python Imports", self.check_python_imports, critical=True)
        
        print(f"\n{Fore.WHITE}🔧 INFRASTRUCTURE CHECKS:{Style.RESET_ALL}")
        self.run_check("GCP Credentials", self.check_gcp_credentials)
        self.run_check("Docker Support", self.check_docker_support)
        self.run_check("API Health", self.check_api_health)
        
        print(f"\n{Fore.WHITE}📁 FILE CHECKS:{Style.RESET_ALL}")
        self.run_check("Frontend Files", self.check_frontend_files)
        self.run_check("Deployment Scripts", self.check_deployment_scripts)
        
        # Print summary
        self._print_summary()
        
        # Return True only if no critical failures
        return len(self.critical_failures) == 0
    
    def _print_summary(self):
        """Print comprehensive summary"""
        
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}📊 PRODUCTION READINESS SUMMARY{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        success_rate = (self.checks_passed / self.checks_total) * 100 if self.checks_total > 0 else 0
        
        print(f"\nTotal Checks: {self.checks_total}")
        print(f"Passed: {Fore.GREEN}{self.checks_passed}{Style.RESET_ALL}")
        print(f"Failed: {Fore.RED}{self.checks_total - self.checks_passed}{Style.RESET_ALL}")
        print(f"Success Rate: {Fore.GREEN if success_rate >= 90 else Fore.YELLOW if success_rate >= 70 else Fore.RED}{success_rate:.1f}%{Style.RESET_ALL}")
        
        if self.critical_failures:
            print(f"\n{Fore.RED}🚨 CRITICAL FAILURES (MUST FIX):{Style.RESET_ALL}")
            for name, message in self.critical_failures:
                print(f"   ❌ {name}: {message}")
        
        if self.warnings:
            print(f"\n{Fore.YELLOW}⚠️  WARNINGS:{Style.RESET_ALL}")
            for name, message in self.warnings[:5]:  # Show first 5
                print(f"   ⚠️  {name}: {message}")
        
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        if len(self.critical_failures) == 0:
            print(f"{Fore.GREEN}🎉 PRODUCTION READINESS: PASSED!{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ System is ready for deployment and demo!{Style.RESET_ALL}")
            
            print(f"\n{Fore.WHITE}🚀 NEXT STEPS:{Style.RESET_ALL}")
            print(f"   1. Run: ./scripts/deploy_to_cloud_run.sh")
            print(f"   2. Run: python3 scripts/create_demo_data.py")
            print(f"   3. Test: python3 scripts/test_cloud_run_live.py")
            print(f"   4. Demo: Your system is ready!")
            
        else:
            print(f"{Fore.RED}❌ PRODUCTION READINESS: FAILED{Style.RESET_ALL}")
            print(f"{Fore.RED}Fix the critical failures above before deploying{Style.RESET_ALL}")
            
            print(f"\n{Fore.WHITE}🔧 QUICK FIXES:{Style.RESET_ALL}")
            print(f"   • Modal removal: python3 scripts/remove_all_modal_references.py --force")
            print(f"   • Environment vars: export GCP_PROJECT_ID=your-project")
            print(f"   • GCP auth: gcloud auth login")
            print(f"   • Dependencies: pip install -r requirements.txt")
        
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

def main():
    """Main function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Production Readiness Checklist")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    checker = ProductionChecker()
    success = checker.run_all_checks()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
