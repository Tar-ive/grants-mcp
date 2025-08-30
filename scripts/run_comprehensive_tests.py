#!/usr/bin/env python3
"""
Comprehensive test execution script for the Grants MCP Server.
This script simulates the GitHub Actions pipeline locally.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class TestRunner:
    """Main test execution orchestrator."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = {}
        self.start_time = time.time()
        
    def print_header(self, title: str):
        """Print a formatted header."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}{Colors.RESET}\n")
        
    def print_step(self, step: str):
        """Print a test step."""
        print(f"{Colors.CYAN}▶ {step}...{Colors.RESET}")
        
    def print_success(self, message: str):
        """Print a success message."""
        print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")
        
    def print_warning(self, message: str):
        """Print a warning message."""
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")
        
    def print_error(self, message: str):
        """Print an error message."""
        print(f"{Colors.RED}❌ {message}{Colors.RESET}")
        
    def run_command(self, cmd: List[str], description: str, timeout: int = 300) -> Tuple[bool, str, str]:
        """Run a shell command and return success status and output."""
        self.print_step(f"{description}")
        
        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )
            
            duration = time.time() - start
            
            if result.returncode == 0:
                self.print_success(f"{description} completed in {duration:.1f}s")
                return True, result.stdout, result.stderr
            else:
                self.print_error(f"{description} failed (exit code {result.returncode})")
                print(f"{Colors.RED}STDOUT: {result.stdout}{Colors.RESET}")
                print(f"{Colors.RED}STDERR: {result.stderr}{Colors.RESET}")
                return False, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            self.print_error(f"{description} timed out after {timeout}s")
            return False, "", "Timeout expired"
        except Exception as e:
            self.print_error(f"{description} failed with exception: {e}")
            return False, "", str(e)
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        self.print_header("Checking Dependencies")
        
        dependencies = [
            (["python3", "--version"], "Python 3"),
            (["pip", "--version"], "pip"),
            (["node", "--version"], "Node.js"),
            (["npm", "--version"], "npm"),
            (["docker", "--version"], "Docker"),
        ]
        
        all_ok = True
        for cmd, name in dependencies:
            success, stdout, stderr = self.run_command(cmd, f"Checking {name}")
            if success:
                version = stdout.strip().split('\n')[0]
                print(f"  {name}: {version}")
            else:
                all_ok = False
                
        return all_ok
    
    def install_dependencies(self) -> bool:
        """Install Python and Node.js dependencies."""
        self.print_header("Installing Dependencies")
        
        # Install Python dependencies
        python_success, _, _ = self.run_command(
            ["python3", "-m", "pip", "install", "-r", "requirements.txt", "-r", "requirements-dev.txt"],
            "Installing Python dependencies",
            timeout=300
        )
        
        # Install Node.js dependencies
        node_success, _, _ = self.run_command(
            ["npm", "ci"],
            "Installing Node.js dependencies",
            timeout=180
        )
        
        return python_success and node_success
    
    def run_linting(self) -> bool:
        """Run code linting and type checking."""
        self.print_header("Code Quality Checks")
        
        # Python linting
        flake8_success, _, _ = self.run_command(
            ["flake8", "src/", "tests/", "--max-line-length=100", "--extend-ignore=E203,W503"],
            "Running flake8 linting"
        )
        
        # Type checking
        mypy_success, _, _ = self.run_command(
            ["mypy", "src/", "--ignore-missing-imports"],
            "Running mypy type checking"
        )
        
        # TypeScript build (also checks TypeScript syntax)
        ts_success, _, _ = self.run_command(
            ["npm", "run", "build"],
            "Building TypeScript"
        )
        
        return flake8_success and mypy_success and ts_success
    
    def run_security_scans(self) -> bool:
        """Run security scanning tools."""
        self.print_header("Security Scans")
        
        # Bandit security scan
        bandit_success, _, _ = self.run_command(
            ["bandit", "-r", "src/", "-f", "json", "-o", "security-report.json"],
            "Running Bandit security scan"
        )
        
        # Safety dependency check
        safety_success, _, _ = self.run_command(
            ["safety", "check", "--json", "--output", "security-deps.json"],
            "Running Safety dependency check"
        )
        
        # Note: These tools might not be critical failures
        if not bandit_success:
            self.print_warning("Bandit security scan had issues (non-critical)")
        if not safety_success:
            self.print_warning("Safety dependency check had issues (non-critical)")
            
        return True  # Don't fail the entire pipeline on security warnings
    
    def run_unit_tests(self) -> bool:
        """Run unit tests."""
        self.print_header("Unit Tests")
        
        success, stdout, stderr = self.run_command(
            ["pytest", "tests/unit/", "-v", "-m", "unit", "--junit-xml=junit-unit.xml"],
            "Running unit tests"
        )
        
        self.results['unit_tests'] = {
            'success': success,
            'output': stdout,
            'errors': stderr
        }
        
        return success
    
    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        self.print_header("Integration Tests")
        
        success, stdout, stderr = self.run_command(
            ["pytest", "tests/integration/", "-v", "-m", "integration", "--junit-xml=junit-integration.xml"],
            "Running integration tests"
        )
        
        self.results['integration_tests'] = {
            'success': success,
            'output': stdout,
            'errors': stderr
        }
        
        return success
    
    def run_contract_tests(self) -> bool:
        """Run contract tests."""
        self.print_header("Contract Tests")
        
        success, stdout, stderr = self.run_command(
            ["pytest", "tests/contract/", "-v", "-m", "contract", "--junit-xml=junit-contract.xml"],
            "Running contract tests"
        )
        
        self.results['contract_tests'] = {
            'success': success,
            'output': stdout,
            'errors': stderr
        }
        
        return success
    
    def run_edge_case_tests(self) -> bool:
        """Run edge case tests."""
        self.print_header("Edge Case Tests")
        
        success, stdout, stderr = self.run_command(
            ["pytest", "tests/edge_cases/", "-v", "-m", "edge_case", "--junit-xml=junit-edge.xml"],
            "Running edge case tests"
        )
        
        self.results['edge_case_tests'] = {
            'success': success,
            'output': stdout,
            'errors': stderr
        }
        
        return success
    
    def run_performance_tests(self) -> bool:
        """Run performance tests."""
        self.print_header("Performance Tests")
        
        success, stdout, stderr = self.run_command(
            ["pytest", "tests/performance/", "-v", "-m", "performance", "--benchmark-only", "--benchmark-json=benchmark-results.json"],
            "Running performance tests",
            timeout=600  # Longer timeout for performance tests
        )
        
        self.results['performance_tests'] = {
            'success': success,
            'output': stdout,
            'errors': stderr
        }
        
        return success
    
    def run_typescript_tests(self) -> bool:
        """Run TypeScript tests."""
        self.print_header("TypeScript Tests")
        
        success, stdout, stderr = self.run_command(
            ["npm", "test"],
            "Running TypeScript tests"
        )
        
        self.results['typescript_tests'] = {
            'success': success,
            'output': stdout,
            'errors': stderr
        }
        
        return success
    
    def run_live_api_tests(self, api_key: Optional[str] = None) -> bool:
        """Run live API tests if API key is provided."""
        if not api_key:
            self.print_warning("Skipping live API tests (no API key provided)")
            return True
            
        self.print_header("Live API Tests")
        
        env = os.environ.copy()
        env['USE_REAL_API'] = 'true'
        env['API_KEY'] = api_key
        
        process = subprocess.run(
            ["pytest", "tests/live/", "-v", "-m", "real_api", "--junit-xml=junit-live.xml"],
            capture_output=True,
            text=True,
            timeout=900,  # 15 minutes for live API tests
            cwd=self.project_root,
            env=env
        )
        
        success = process.returncode == 0
        
        if success:
            self.print_success("Live API tests completed")
        else:
            self.print_error("Live API tests failed")
            print(f"{Colors.RED}STDOUT: {process.stdout}{Colors.RESET}")
            print(f"{Colors.RED}STDERR: {process.stderr}{Colors.RESET}")
            
        self.results['live_api_tests'] = {
            'success': success,
            'output': process.stdout,
            'errors': process.stderr
        }
        
        return success
    
    def run_docker_tests(self) -> bool:
        """Run Docker deployment tests."""
        self.print_header("Docker Tests")
        
        # Build Docker image
        build_success, _, _ = self.run_command(
            ["docker", "build", "-t", "grants-mcp:test", "."],
            "Building Docker image",
            timeout=600
        )
        
        if not build_success:
            return False
        
        # Start container
        start_success, _, _ = self.run_command(
            ["docker", "run", "-d", "--name", "grants-mcp-test", "-p", "8080:8080", 
             "-e", "SIMPLER_GRANTS_API_KEY=test_key", "grants-mcp:test"],
            "Starting Docker container"
        )
        
        if not start_success:
            return False
        
        try:
            # Wait for container to be ready
            self.print_step("Waiting for container to be ready")
            time.sleep(15)
            
            # Test health endpoint
            health_success, _, _ = self.run_command(
                ["curl", "-f", "http://localhost:8080/health"],
                "Testing health endpoint"
            )
            
            # Test MCP endpoint
            mcp_success, _, _ = self.run_command(
                ["curl", "-X", "POST", "http://localhost:8080/mcp",
                 "-H", "Content-Type: application/json",
                 "-d", '{"jsonrpc":"2.0","method":"tools/list","id":1}'],
                "Testing MCP endpoint"
            )
            
            return health_success and mcp_success
            
        finally:
            # Cleanup container
            self.run_command(
                ["docker", "stop", "grants-mcp-test"],
                "Stopping Docker container"
            )
            self.run_command(
                ["docker", "rm", "grants-mcp-test"],
                "Removing Docker container"
            )
    
    def run_coverage_tests(self) -> bool:
        """Run tests with coverage reporting."""
        self.print_header("Coverage Tests")
        
        success, stdout, stderr = self.run_command(
            ["pytest", "tests/unit/", "tests/integration/", "tests/contract/",
             "--cov=src", "--cov-branch", "--cov-report=term-missing",
             "--cov-report=html:htmlcov", "--cov-report=xml:coverage.xml"],
            "Running tests with coverage"
        )
        
        if success:
            self.print_success("Coverage report generated in htmlcov/index.html")
        
        return success
    
    def generate_report(self):
        """Generate a final test report."""
        self.print_header("Test Results Summary")
        
        total_duration = time.time() - self.start_time
        
        print(f"Total execution time: {total_duration:.1f} seconds\n")
        
        # Count results
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result.get('success', False))
        failed_tests = total_tests - passed_tests
        
        print(f"Test Categories: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "N/A")
        
        print("\nDetailed Results:")
        for test_name, result in self.results.items():
            status = "✅ PASS" if result.get('success', False) else "❌ FAIL"
            print(f"  {test_name}: {status}")
        
        # Save results to JSON
        report_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_seconds': total_duration,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests/total_tests)*100 if total_tests > 0 else 0,
            'results': self.results
        }
        
        with open(self.project_root / 'test-report.json', 'w') as f:
            json.dump(report_data, f, indent=2)
            
        self.print_success("Test report saved to test-report.json")
        
        return failed_tests == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run comprehensive tests for Grants MCP Server')
    parser.add_argument('--api-key', help='API key for live tests')
    parser.add_argument('--skip-docker', action='store_true', help='Skip Docker tests')
    parser.add_argument('--skip-performance', action='store_true', help='Skip performance tests')
    parser.add_argument('--skip-live', action='store_true', help='Skip live API tests')
    parser.add_argument('--quick', action='store_true', help='Run only unit and integration tests')
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Initialize test runner
    runner = TestRunner(project_root)
    
    print(f"{Colors.BOLD}{Colors.MAGENTA}")
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║          Grants MCP Server - Comprehensive Test Suite        ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")
    
    # Track overall success
    overall_success = True
    
    # Phase 1: Setup and Dependencies
    if not runner.check_dependencies():
        runner.print_error("Dependency check failed")
        sys.exit(1)
        
    if not runner.install_dependencies():
        runner.print_error("Failed to install dependencies")
        sys.exit(1)
    
    # Phase 2: Code Quality
    if not runner.run_linting():
        runner.print_error("Code quality checks failed")
        overall_success = False
    
    runner.run_security_scans()  # Non-critical
    
    # Phase 3: Core Tests
    if not runner.run_unit_tests():
        overall_success = False
        
    if not runner.run_integration_tests():
        overall_success = False
        
    if not runner.run_contract_tests():
        overall_success = False
        
    if not runner.run_edge_case_tests():
        overall_success = False
        
    if not runner.run_typescript_tests():
        overall_success = False
    
    # Phase 4: Extended Tests (if not quick mode)
    if not args.quick:
        if not args.skip_performance and not runner.run_performance_tests():
            overall_success = False
            
        if not args.skip_docker and not runner.run_docker_tests():
            overall_success = False
            
        if not args.skip_live and not runner.run_live_api_tests(args.api_key):
            overall_success = False
    
    # Phase 5: Coverage Report
    if not runner.run_coverage_tests():
        overall_success = False
    
    # Generate final report
    report_success = runner.generate_report()
    
    # Final status
    if overall_success and report_success:
        runner.print_success("All tests completed successfully! 🎉")
        sys.exit(0)
    else:
        runner.print_error("Some tests failed. Check the report for details.")
        sys.exit(1)


if __name__ == '__main__':
    main()