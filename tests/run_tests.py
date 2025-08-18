#!/usr/bin/env python3
"""
OMTX-Hub Test Runner
Comprehensive test execution with different test suites and environments
"""

import argparse
import os
import sys
import subprocess
import time
from typing import List, Dict, Any
from pathlib import Path

# Test suite configurations
TEST_SUITES = {
    "smoke": {
        "description": "Quick smoke tests (health checks, basic API)",
        "markers": "smoke",
        "timeout": 60,
        "parallel": True
    },
    "unit": {
        "description": "Unit tests for individual components",
        "markers": "unit",
        "timeout": 120,
        "parallel": True
    },
    "integration": {
        "description": "Integration tests (API, database, services)",
        "markers": "integration and not slow",
        "timeout": 300,
        "parallel": False
    },
    "e2e": {
        "description": "End-to-end workflow tests",
        "markers": "e2e",
        "timeout": 600,
        "parallel": False
    },
    "modal": {
        "description": "Modal integration tests",
        "markers": "modal",
        "timeout": 900,
        "parallel": False
    },
    "infrastructure": {
        "description": "Infrastructure and Kubernetes tests",
        "markers": "infrastructure",
        "timeout": 300,
        "parallel": False
    },
    "security": {
        "description": "Security and vulnerability tests",
        "markers": "security",
        "timeout": 180,
        "parallel": True
    },
    "performance": {
        "description": "Performance and load tests",
        "markers": "performance",
        "timeout": 600,
        "parallel": False
    },
    "all": {
        "description": "All tests (full test suite)",
        "markers": "",
        "timeout": 1800,
        "parallel": False
    }
}

# Environment configurations
ENVIRONMENTS = {
    "local": {
        "base_url": "http://localhost:8000",
        "modal_mode": "mock",
        "k8s_namespace": "default",
        "timeout_multiplier": 1.0
    },
    "staging": {
        "base_url": "https://api-staging.omtx-hub.com", 
        "modal_mode": "real",
        "k8s_namespace": "omtx-hub-staging",
        "timeout_multiplier": 1.5
    },
    "production": {
        "base_url": "https://api.omtx-hub.com",
        "modal_mode": "real", 
        "k8s_namespace": "omtx-hub",
        "timeout_multiplier": 2.0
    }
}

class TestRunner:
    """Main test runner class"""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent
        
        # Set environment variables
        self._setup_environment()
    
    def _setup_environment(self):
        """Setup environment variables for testing"""
        
        env_config = ENVIRONMENTS.get(self.args.environment, ENVIRONMENTS["local"])
        
        # Core test configuration
        os.environ["TEST_BASE_URL"] = env_config["base_url"]
        os.environ["MODAL_TEST_MODE"] = env_config["modal_mode"]
        os.environ["K8S_NAMESPACE"] = env_config["k8s_namespace"]
        
        # Timeout adjustments
        suite_config = TEST_SUITES.get(self.args.suite, TEST_SUITES["integration"])
        base_timeout = suite_config["timeout"]
        adjusted_timeout = int(base_timeout * env_config["timeout_multiplier"])
        os.environ["TEST_TIMEOUT"] = str(adjusted_timeout)
        
        # Optional environment variables
        if self.args.gcp_project:
            os.environ["GCP_PROJECT_ID"] = self.args.gcp_project
        
        if self.args.webhook_secret:
            os.environ["MODAL_WEBHOOK_SECRET"] = self.args.webhook_secret
        
        # Coverage configuration
        if self.args.coverage:
            os.environ["COVERAGE_CORE"] = "sysmon"
        
        print(f"🔧 Test Environment: {self.args.environment}")
        print(f"🎯 Target URL: {env_config['base_url']}")
        print(f"⏱️ Test Timeout: {adjusted_timeout}s")
        print(f"🧪 Modal Mode: {env_config['modal_mode']}")
    
    def run_tests(self) -> int:
        """Run the specified test suite"""
        
        suite_config = TEST_SUITES.get(self.args.suite, TEST_SUITES["integration"])
        
        print(f"\n🚀 Running {self.args.suite} tests")
        print(f"📝 Description: {suite_config['description']}")
        
        # Build pytest command
        cmd = self._build_pytest_command(suite_config)
        
        print(f"🔧 Command: {' '.join(cmd)}")
        print("=" * 80)
        
        # Run tests
        start_time = time.time()
        result = subprocess.run(cmd, cwd=self.project_root)
        duration = time.time() - start_time
        
        # Print results
        self._print_results(result.returncode, duration)
        
        return result.returncode
    
    def _build_pytest_command(self, suite_config: Dict[str, Any]) -> List[str]:
        """Build the pytest command with appropriate flags"""
        
        cmd = ["python", "-m", "pytest"]
        
        # Test directory
        cmd.append(str(self.test_dir))
        
        # Markers
        if suite_config["markers"]:
            cmd.extend(["-m", suite_config["markers"]])
        
        # Verbosity
        if self.args.verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        # Parallel execution
        if suite_config["parallel"] and not self.args.no_parallel:
            cmd.extend(["-n", str(self.args.workers)])
        
        # Coverage
        if self.args.coverage:
            cmd.extend([
                "--cov=backend",
                "--cov-report=term-missing",
                "--cov-report=html:tests/coverage_html",
                "--cov-report=xml:tests/coverage.xml"
            ])
        
        # Output formats
        if self.args.junit:
            cmd.extend(["--junitxml", "tests/test-results.xml"])
        
        if self.args.html_report:
            cmd.extend(["--html", "tests/report.html", "--self-contained-html"])
        
        # Fail fast
        if self.args.fail_fast:
            cmd.extend(["-x"])
        
        # Timeout
        timeout = int(os.environ.get("TEST_TIMEOUT", "300"))
        cmd.extend(["--timeout", str(timeout)])
        
        # Additional pytest args
        if self.args.pytest_args:
            cmd.extend(self.args.pytest_args.split())
        
        return cmd
    
    def _print_results(self, return_code: int, duration: float):
        """Print test results summary"""
        
        print("=" * 80)
        
        if return_code == 0:
            print("✅ Tests PASSED")
        else:
            print("❌ Tests FAILED")
        
        print(f"⏱️ Duration: {duration:.2f} seconds")
        
        # Check if coverage report was generated
        coverage_file = self.test_dir / "coverage.xml"
        if coverage_file.exists():
            print(f"📊 Coverage report: {coverage_file}")
        
        # Check if HTML report was generated
        html_report = self.test_dir / "report.html"
        if html_report.exists():
            print(f"📋 HTML report: {html_report}")
    
    def list_tests(self):
        """List available tests without running them"""
        
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "--collect-only",
            "-q"
        ]
        
        if self.args.suite != "all":
            suite_config = TEST_SUITES[self.args.suite]
            if suite_config["markers"]:
                cmd.extend(["-m", suite_config["markers"]])
        
        subprocess.run(cmd, cwd=self.project_root)
    
    def setup_test_environment(self):
        """Setup test environment (install dependencies, etc.)"""
        
        print("🔧 Setting up test environment...")
        
        # Install test dependencies
        requirements_file = self.test_dir / "requirements.txt"
        if requirements_file.exists():
            cmd = [
                sys.executable, "-m", "pip", "install", 
                "-r", str(requirements_file)
            ]
            result = subprocess.run(cmd)
            if result.returncode != 0:
                print("❌ Failed to install test dependencies")
                return False
        
        # Create coverage directory
        coverage_dir = self.test_dir / "coverage_html"
        coverage_dir.mkdir(exist_ok=True)
        
        print("✅ Test environment setup complete")
        return True

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(description="OMTX-Hub Test Runner")
    
    # Test suite selection
    parser.add_argument(
        "suite",
        choices=list(TEST_SUITES.keys()),
        default="integration",
        nargs="?",
        help="Test suite to run"
    )
    
    # Environment selection
    parser.add_argument(
        "--environment", "-e",
        choices=list(ENVIRONMENTS.keys()),
        default="local",
        help="Test environment"
    )
    
    # Test configuration
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel test execution"
    )
    
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel workers"
    )
    
    parser.add_argument(
        "--fail-fast", "-x",
        action="store_true",
        help="Stop on first failure"
    )
    
    # Output formats
    parser.add_argument(
        "--junit",
        action="store_true",
        help="Generate JUnit XML report"
    )
    
    parser.add_argument(
        "--html-report",
        action="store_true",
        help="Generate HTML report"
    )
    
    # Environment configuration
    parser.add_argument(
        "--gcp-project",
        help="GCP project ID for testing"
    )
    
    parser.add_argument(
        "--webhook-secret",
        help="Modal webhook secret for testing"
    )
    
    # Actions
    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List available tests without running"
    )
    
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Setup test environment"
    )
    
    # Pass-through pytest args
    parser.add_argument(
        "--pytest-args",
        help="Additional pytest arguments"
    )
    
    args = parser.parse_args()
    
    # Print available test suites if no suite specified
    if len(sys.argv) == 1:
        print("Available test suites:")
        for suite, config in TEST_SUITES.items():
            print(f"  {suite:12} - {config['description']}")
        print("\nUsage: python run_tests.py <suite> [options]")
        sys.exit(0)
    
    runner = TestRunner(args)
    
    # Handle special actions
    if args.setup:
        success = runner.setup_test_environment()
        sys.exit(0 if success else 1)
    
    if args.list_tests:
        runner.list_tests()
        sys.exit(0)
    
    # Run tests
    exit_code = runner.run_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()