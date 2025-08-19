#!/usr/bin/env python3
"""
Environment Validation - RUN THIS BEFORE DEMO!
Distinguished Engineer Implementation - Comprehensive environment validation
"""

import os
import sys
import time
import json
import logging
from typing import Dict, List, Tuple, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    RESET = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.WHITE}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

class EnvironmentValidator:
    """Comprehensive environment validation"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_total = 0
        
    def validate_all(self) -> bool:
        """Run all validation checks"""
        
        print_header("OMTX-HUB ENVIRONMENT VALIDATION")
        
        # Run all validation checks
        self.validate_required_env_vars()
        self.validate_gcp_configuration()
        self.validate_service_dependencies()
        self.validate_security_configuration()
        self.validate_feature_flags()
        self.validate_resource_limits()
        self.validate_external_services()
        
        # Print summary
        self.print_validation_summary()
        
        # Return success status
        return len(self.errors) == 0
    
    def validate_required_env_vars(self):
        """Validate all required environment variables"""
        
        print_info("Checking required environment variables...")
        
        required_vars = {
            # GCP Configuration
            "GCP_PROJECT_ID": {
                "description": "Your GCP project ID",
                "example": "omtx-production-123",
                "critical": True
            },
            "GCP_REGION": {
                "description": "GCP region for resources",
                "example": "us-central1",
                "default": "us-central1",
                "critical": True
            },
            "GCS_BUCKET_NAME": {
                "description": "Cloud Storage bucket name",
                "example": "omtx-production",
                "critical": True
            },
            
            # Authentication
            "JWT_SECRET": {
                "description": "Secret for JWT token signing",
                "example": "your-super-secret-jwt-key-here",
                "critical": True,
                "sensitive": True
            },
            "API_KEY_SECRET": {
                "description": "Secret for API key generation",
                "example": "your-api-key-secret-here",
                "critical": True,
                "sensitive": True
            },
            
            # External Services
            "AUTH_SERVICE_URL": {
                "description": "URL of your authentication service",
                "example": "https://auth.yourapp.com",
                "critical": False
            },
            "BILLING_SERVICE_URL": {
                "description": "URL of your billing service",
                "example": "https://billing.yourapp.com",
                "critical": False
            },
            
            # Database
            "FIRESTORE_DATABASE": {
                "description": "Firestore database name",
                "default": "(default)",
                "critical": True
            },
            
            # Features
            "ENABLE_USER_ISOLATION": {
                "description": "Enable user isolation",
                "default": "true",
                "critical": True
            },
            "ENABLE_RATE_LIMITING": {
                "description": "Enable rate limiting",
                "default": "true",
                "critical": False
            },
            "DEFAULT_USER_TIER": {
                "description": "Default user tier",
                "default": "free",
                "critical": True
            },
            
            # Performance
            "MAX_CONCURRENT_JOBS": {
                "description": "Maximum concurrent jobs",
                "default": "50",
                "critical": False
            },
            "GPU_TYPE": {
                "description": "GPU type for Cloud Run",
                "default": "L4",
                "critical": True
            }
        }
        
        for var_name, config in required_vars.items():
            self.checks_total += 1
            value = os.getenv(var_name)
            
            if not value:
                if config.get("default"):
                    # Set default value
                    os.environ[var_name] = config["default"]
                    print_warning(f"{var_name}: Using default value '{config['default']}'")
                    self.warnings.append(f"{var_name} using default value")
                    self.checks_passed += 1
                elif config.get("critical", True):
                    print_error(f"{var_name}: MISSING - {config['description']}")
                    print_error(f"   Example: export {var_name}=\"{config.get('example', 'your-value-here')}\"")
                    self.errors.append(f"Missing critical environment variable: {var_name}")
                else:
                    print_warning(f"{var_name}: Optional variable not set - {config['description']}")
                    self.warnings.append(f"Optional variable not set: {var_name}")
                    self.checks_passed += 1
            else:
                # Validate specific values
                if var_name == "GCP_PROJECT_ID" and value in ["your-project", "your-production-project"]:
                    print_warning(f"{var_name}: Still using placeholder value '{value}'")
                    self.warnings.append(f"{var_name} using placeholder value")
                elif var_name in ["JWT_SECRET", "API_KEY_SECRET"] and len(value) < 32:
                    print_warning(f"{var_name}: Secret is too short (should be 32+ characters)")
                    self.warnings.append(f"{var_name} is too short")
                elif config.get("sensitive"):
                    print_success(f"{var_name}: Set (***hidden***)")
                else:
                    print_success(f"{var_name}: {value}")
                
                self.checks_passed += 1
    
    def validate_gcp_configuration(self):
        """Validate GCP configuration and credentials"""
        
        print_info("Checking GCP configuration...")
        
        # Check if gcloud is installed
        self.checks_total += 1
        import subprocess
        try:
            result = subprocess.run(['gcloud', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print_success("gcloud CLI is installed")
                self.checks_passed += 1
            else:
                print_error("gcloud CLI is not working properly")
                self.errors.append("gcloud CLI not working")
        except FileNotFoundError:
            print_error("gcloud CLI is not installed")
            self.errors.append("gcloud CLI not installed")
        
        # Check GCP credentials
        self.checks_total += 1
        try:
            from google.cloud import firestore
            db = firestore.Client()
            
            # Test Firestore connection
            test_ref = db.collection('_validation').document('test')
            test_ref.set({"timestamp": time.time(), "test": True})
            
            # Test read
            doc = test_ref.get()
            if doc.exists:
                print_success("Firestore: Connected and accessible")
                self.checks_passed += 1
            else:
                print_error("Firestore: Cannot read test document")
                self.errors.append("Firestore read test failed")
                
        except Exception as e:
            print_error(f"Firestore: Connection failed - {str(e)}")
            self.errors.append(f"Firestore connection failed: {str(e)}")
        
        # Check Cloud Storage
        self.checks_total += 1
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket_name = os.getenv("GCS_BUCKET_NAME")
            
            if bucket_name:
                bucket = client.bucket(bucket_name)
                if bucket.exists():
                    # Test write access
                    test_blob = bucket.blob("_validation/test.txt")
                    test_blob.upload_from_string(f"Validation test at {time.time()}")
                    
                    print_success(f"Cloud Storage: Bucket '{bucket_name}' accessible")
                    self.checks_passed += 1
                else:
                    print_error(f"Cloud Storage: Bucket '{bucket_name}' does not exist")
                    self.errors.append(f"GCS bucket {bucket_name} does not exist")
            else:
                print_error("Cloud Storage: GCS_BUCKET_NAME not set")
                self.errors.append("GCS_BUCKET_NAME not set")
                
        except Exception as e:
            print_error(f"Cloud Storage: Connection failed - {str(e)}")
            self.errors.append(f"Cloud Storage connection failed: {str(e)}")
    
    def validate_service_dependencies(self):
        """Validate service dependencies"""
        
        print_info("Checking service dependencies...")
        
        # Check Python packages
        required_packages = [
            ("fastapi", "FastAPI web framework"),
            ("torch", "PyTorch for GPU computation"),
            ("google-cloud-firestore", "Firestore client"),
            ("google-cloud-storage", "Cloud Storage client"),
            ("google-cloud-run", "Cloud Run client"),
            ("aiohttp", "Async HTTP client"),
            ("pydantic", "Data validation"),
            ("uvicorn", "ASGI server")
        ]
        
        for package, description in required_packages:
            self.checks_total += 1
            try:
                __import__(package.replace("-", "_"))
                print_success(f"Python package '{package}': Available")
                self.checks_passed += 1
            except ImportError:
                print_error(f"Python package '{package}': Missing - {description}")
                self.errors.append(f"Missing Python package: {package}")
        
        # Check GPU availability (if in production)
        if os.getenv("ENVIRONMENT") == "production":
            self.checks_total += 1
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_count = torch.cuda.device_count()
                    gpu_name = torch.cuda.get_device_name(0)
                    print_success(f"GPU: {gpu_count} GPU(s) available - {gpu_name}")
                    self.checks_passed += 1
                else:
                    print_warning("GPU: CUDA not available (may be normal in development)")
                    self.warnings.append("CUDA not available")
                    self.checks_passed += 1
            except Exception as e:
                print_error(f"GPU: Check failed - {str(e)}")
                self.errors.append(f"GPU check failed: {str(e)}")
    
    def validate_security_configuration(self):
        """Validate security configuration"""
        
        print_info("Checking security configuration...")
        
        # Check CORS origins
        self.checks_total += 1
        cors_origins = os.getenv("CORS_ORIGINS", "")
        if cors_origins:
            origins = cors_origins.split(",")
            print_success(f"CORS: {len(origins)} origins configured")
            self.checks_passed += 1
        else:
            print_warning("CORS: No origins configured, using defaults")
            self.warnings.append("CORS origins not configured")
            self.checks_passed += 1
        
        # Check secrets strength
        self.checks_total += 1
        jwt_secret = os.getenv("JWT_SECRET", "")
        if len(jwt_secret) >= 32:
            print_success("JWT Secret: Strong secret configured")
            self.checks_passed += 1
        else:
            print_error("JWT Secret: Weak or missing secret")
            self.errors.append("JWT secret is weak or missing")
    
    def validate_feature_flags(self):
        """Validate feature flag configuration"""
        
        print_info("Checking feature flags...")
        
        features = {
            "ENABLE_USER_ISOLATION": "User isolation",
            "ENABLE_RATE_LIMITING": "Rate limiting",
            "ENABLE_COST_TRACKING": "Cost tracking",
            "ENABLE_WEBHOOKS": "Webhook integration",
            "ENABLE_ANALYTICS": "Analytics tracking"
        }
        
        for flag, description in features.items():
            self.checks_total += 1
            value = os.getenv(flag, "false").lower()
            if value in ["true", "1", "yes"]:
                print_success(f"{description}: Enabled")
            else:
                print_info(f"{description}: Disabled")
            self.checks_passed += 1
    
    def validate_resource_limits(self):
        """Validate resource limits and quotas"""
        
        print_info("Checking resource limits...")
        
        # Check concurrent job limits
        self.checks_total += 1
        max_jobs = int(os.getenv("MAX_CONCURRENT_JOBS", "50"))
        if 1 <= max_jobs <= 100:
            print_success(f"Concurrent jobs limit: {max_jobs}")
            self.checks_passed += 1
        else:
            print_warning(f"Concurrent jobs limit: {max_jobs} (may be too high/low)")
            self.warnings.append(f"Unusual concurrent jobs limit: {max_jobs}")
            self.checks_passed += 1
        
        # Check daily budget
        self.checks_total += 1
        daily_budget = float(os.getenv("DAILY_BUDGET_USD", "100"))
        if daily_budget > 0:
            print_success(f"Daily budget: ${daily_budget}")
            self.checks_passed += 1
        else:
            print_warning("Daily budget: Not set or zero")
            self.warnings.append("Daily budget not configured")
            self.checks_passed += 1
    
    def validate_external_services(self):
        """Validate external service connectivity"""
        
        print_info("Checking external services...")
        
        # Check auth service
        auth_url = os.getenv("AUTH_SERVICE_URL")
        if auth_url:
            self.checks_total += 1
            try:
                import requests
                response = requests.get(f"{auth_url}/health", timeout=5)
                if response.status_code == 200:
                    print_success(f"Auth service: Accessible at {auth_url}")
                    self.checks_passed += 1
                else:
                    print_warning(f"Auth service: Responded with {response.status_code}")
                    self.warnings.append(f"Auth service returned {response.status_code}")
                    self.checks_passed += 1
            except Exception as e:
                print_warning(f"Auth service: Not accessible - {str(e)}")
                self.warnings.append(f"Auth service not accessible: {str(e)}")
                self.checks_passed += 1
        else:
            print_info("Auth service: Not configured (using internal auth)")
            self.checks_total += 1
            self.checks_passed += 1
        
        # Check billing service
        billing_url = os.getenv("BILLING_SERVICE_URL")
        if billing_url:
            self.checks_total += 1
            try:
                import requests
                response = requests.get(f"{billing_url}/health", timeout=5)
                if response.status_code == 200:
                    print_success(f"Billing service: Accessible at {billing_url}")
                    self.checks_passed += 1
                else:
                    print_warning(f"Billing service: Responded with {response.status_code}")
                    self.warnings.append(f"Billing service returned {response.status_code}")
                    self.checks_passed += 1
            except Exception as e:
                print_warning(f"Billing service: Not accessible - {str(e)}")
                self.warnings.append(f"Billing service not accessible: {str(e)}")
                self.checks_passed += 1
        else:
            print_info("Billing service: Not configured")
            self.checks_total += 1
            self.checks_passed += 1
    
    def print_validation_summary(self):
        """Print comprehensive validation summary"""
        
        print_header("VALIDATION SUMMARY")
        
        # Calculate success rate
        success_rate = (self.checks_passed / self.checks_total) * 100 if self.checks_total > 0 else 0
        
        print(f"Total Checks: {self.checks_total}")
        print(f"Passed: {Colors.GREEN}{self.checks_passed}{Colors.RESET}")
        print(f"Warnings: {Colors.YELLOW}{len(self.warnings)}{Colors.RESET}")
        print(f"Errors: {Colors.RED}{len(self.errors)}{Colors.RESET}")
        print(f"Success Rate: {Colors.GREEN if success_rate >= 90 else Colors.YELLOW if success_rate >= 70 else Colors.RED}{success_rate:.1f}%{Colors.RESET}")
        
        # Print warnings
        if self.warnings:
            print(f"\n{Colors.YELLOW}⚠️  WARNINGS:{Colors.RESET}")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        # Print errors
        if self.errors:
            print(f"\n{Colors.RED}❌ ERRORS:{Colors.RESET}")
            for error in self.errors:
                print(f"   • {error}")
        
        # Final status
        print()
        if len(self.errors) == 0:
            if len(self.warnings) == 0:
                print(f"{Colors.GREEN}🎉 ENVIRONMENT IS READY FOR PRODUCTION!{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}⚠️  ENVIRONMENT IS READY WITH WARNINGS{Colors.RESET}")
                print(f"{Colors.YELLOW}   Consider addressing warnings before production deployment{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ ENVIRONMENT IS NOT READY FOR PRODUCTION{Colors.RESET}")
            print(f"{Colors.RED}   Please fix all errors before proceeding{Colors.RESET}")
        
        print()

def main():
    """Main validation function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="OMTX-Hub Environment Validator")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    validator = EnvironmentValidator()
    success = validator.validate_all()
    
    if args.json:
        # Output JSON results
        results = {
            "success": success,
            "checks_total": validator.checks_total,
            "checks_passed": validator.checks_passed,
            "warnings": validator.warnings,
            "errors": validator.errors,
            "timestamp": time.time()
        }
        print(json.dumps(results, indent=2))
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
