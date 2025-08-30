#!/usr/bin/env python3
"""
Setup script for the Adaptive Testing Framework.

This script initializes the adaptive testing system, creates necessary
directories, sets up configuration, and provides guided setup.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


def print_banner():
    """Print setup banner."""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                  Adaptive Testing Framework                  ║
    ║                         Setup Wizard                        ║
    ╚══════════════════════════════════════════════════════════════╝
    
    🤖 Setting up intelligent test generation and quality assurance
    """)


def check_requirements():
    """Check if Python version and basic requirements are met."""
    print("🔍 Checking system requirements...")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check if git is available
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
        print("✅ Git is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Git not found - some features may be limited")
    
    # Check if this is a git repository
    if Path('.git').exists():
        print("✅ Git repository detected")
    else:
        print("⚠️  Not a git repository - initializing git is recommended")


def install_dependencies():
    """Install required dependencies."""
    print("\n📦 Installing dependencies...")
    
    try:
        # Install main dependencies
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], check=True)
        
        # Install development dependencies
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements-dev.txt'
        ], check=True)
        
        print("✅ Dependencies installed successfully")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("   Please run manually:")
        print("   pip install -r requirements.txt")
        print("   pip install -r requirements-dev.txt")
        return False
    
    return True


def create_directory_structure():
    """Create necessary directory structure."""
    print("\n📁 Creating directory structure...")
    
    directories = [
        'testing/audit',
        'testing/generated',
        'tests/generated/unit',
        'tests/generated/integration', 
        'tests/generated/compliance',
        'tests/generated/performance',
        'tests/generated/contract',
        'tests/generated/security',
        'reports/adaptive-testing',
        'logs/adaptive-testing',
        '.github/monitoring'
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"   Created: {directory}")
    
    print("✅ Directory structure created")


def setup_configuration():
    """Set up initial configuration."""
    print("\n⚙️  Setting up configuration...")
    
    # Determine project type
    is_grants_project = any(
        'grant' in str(p).lower() 
        for p in Path('.').glob('**/*.py')
        if 'node_modules' not in str(p) and '.git' not in str(p)
    )
    
    if is_grants_project:
        print("   Detected grants-related project - using enhanced configuration")
        config_profile = 'grants'
    else:
        config_profile = 'default'
    
    # Create configuration
    config = create_adaptive_config(config_profile)
    
    # Write configuration file
    config_path = Path('adaptive-testing-config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration created: {config_path}")
    return config


def create_adaptive_config(profile: str = 'default') -> Dict[str, Any]:
    """Create adaptive testing configuration."""
    
    base_config = {
        "testing_mode": "development",
        "log_level": "INFO",
        "parallel_execution": True,
        "cache_enabled": True,
        "quality_thresholds": {
            "test_coverage_percentage": 70.0,
            "risk_score_max": 0.7,
            "compliance_score_min": 0.8,
            "complexity_score_max": 8.0
        },
        "test_generation": {
            "max_tests_per_file": 15,
            "parallel_generation": True,
            "generation_timeout_seconds": 300,
            "enable_performance_tests": True,
            "enable_integration_tests": True,
            "enable_compliance_tests": True,
            "enable_security_tests": True
        },
        "risk_analysis": {
            "security_weight": 0.4,
            "complexity_weight": 0.2,
            "business_impact_weight": 0.4,
            "risk_tolerance": "moderate",
            "enable_static_analysis": True,
            "enable_dependency_scanning": True,
            "enable_secrets_detection": True
        },
        "compliance": {
            "enabled_categories": [
                "DATA_PRIVACY",
                "API_SECURITY", 
                "FINANCIAL_REGULATIONS",
                "GRANTS_COMPLIANCE",
                "AUDIT_REQUIREMENTS"
            ],
            "strict_mode": False,
            "regulatory_frameworks": ["GDPR", "CCPA", "SOX"]
        },
        "monitoring": {
            "monitoring_interval_seconds": 30,
            "file_watch_enabled": True,
            "real_time_analysis": True,
            "alert_on_high_risk": True,
            "alert_on_compliance_violation": True
        }
    }
    
    if profile == 'grants':
        # Enhanced configuration for grants projects
        base_config["quality_thresholds"]["test_coverage_percentage"] = 85.0
        base_config["quality_thresholds"]["risk_score_max"] = 0.5
        base_config["quality_thresholds"]["compliance_score_min"] = 0.9
        base_config["risk_analysis"]["risk_tolerance"] = "strict"
        base_config["risk_analysis"]["business_impact_weight"] = 0.5
        base_config["compliance"]["strict_mode"] = True
        base_config["compliance"]["enabled_categories"].extend([
            "FINANCIAL_ACCURACY",
            "AUDIT_TRAIL_COMPLETENESS",
            "GRANTS_REGULATORY_COMPLIANCE"
        ])
        base_config["test_generation"]["max_tests_per_file"] = 20
        base_config["compliance"]["regulatory_frameworks"].extend([
            "CFR_200", "OMB_Guidelines"
        ])
    
    return base_config


def setup_github_actions():
    """Set up GitHub Actions integration."""
    print("\n🔗 Setting up GitHub Actions integration...")
    
    # Check if .github/workflows exists
    workflows_dir = Path('.github/workflows')
    if not workflows_dir.exists():
        workflows_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if adaptive-qa.yml already exists
    adaptive_workflow = workflows_dir / 'adaptive-qa.yml'
    if adaptive_workflow.exists():
        print("   ✅ Adaptive QA workflow already exists")
    else:
        print("   ⚠️  Adaptive QA workflow not found")
        print("      The workflow should have been created during setup.")
        print("      Check .github/workflows/adaptive-qa.yml")
    
    # Create monitoring configuration
    monitoring_config = {
        "monitoring_enabled": True,
        "quality_thresholds": {
            "test_coverage": 70.0,
            "risk_threshold": 0.7,
            "compliance_score": 0.8
        },
        "alert_conditions": {
            "critical_risk_detected": True,
            "compliance_violations": True,
            "quality_gates_failed": True,
            "deployment_blocked": True
        },
        "adaptive_settings": {
            "auto_test_generation": True,
            "risk_based_prioritization": True,
            "continuous_compliance_check": True
        }
    }
    
    monitoring_path = Path('.github/monitoring/adaptive-qa-config.json')
    monitoring_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(monitoring_path, 'w') as f:
        json.dump(monitoring_config, f, indent=2)
    
    print("✅ GitHub Actions integration configured")


def setup_pre_commit_hooks():
    """Set up pre-commit hooks for adaptive testing."""
    print("\n🪝 Setting up pre-commit hooks...")
    
    pre_commit_config = """
repos:
  - repo: local
    hooks:
      - id: adaptive-risk-check
        name: Adaptive Risk Assessment
        entry: python testing/cli.py run --risk-threshold 0.8
        language: system
        pass_filenames: false
        stages: [pre-commit]
        
      - id: adaptive-compliance-check
        name: Compliance Validation
        entry: python -c "
import sys
sys.path.append('testing')
from testing.compliance.checker import ComplianceChecker
from pathlib import Path
import asyncio

async def check():
    checker = ComplianceChecker({})
    files = [Path(f) for f in sys.argv[1:] if f.endswith('.py')]
    for f in files:
        if f.exists():
            report = await checker.check_file(f)
            if not report.is_compliant:
                print(f'❌ Compliance issues in {f}')
                sys.exit(1)
    print('✅ All files compliant')

asyncio.run(check())
        "
        language: system
        files: \\.py$
        stages: [pre-commit]
"""
    
    pre_commit_path = Path('.pre-commit-config.yaml')
    
    if not pre_commit_path.exists():
        with open(pre_commit_path, 'w') as f:
            f.write(pre_commit_config)
        print("✅ Pre-commit configuration created")
    else:
        print("⚠️  Pre-commit config already exists - skipping")


def create_makefile():
    """Create Makefile with common adaptive testing commands."""
    print("\n📜 Creating Makefile...")
    
    makefile_content = """# Adaptive Testing Framework Makefile

.PHONY: install test test-adaptive run-adaptive status report clean help

# Default Python interpreter
PYTHON := python3

# Configuration file
CONFIG := adaptive-testing-config.json

help: ## Show this help message
	@echo "Adaptive Testing Framework Commands:"
	@echo "===================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \\033[36m%-20s\\033[0m %s\\n", $$1, $$2}'

install: ## Install all dependencies
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -r requirements-dev.txt

test: ## Run standard test suite
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

test-adaptive: ## Run adaptive testing analysis
	$(PYTHON) testing/cli.py -c $(CONFIG) run

test-continuous: ## Start continuous adaptive monitoring
	$(PYTHON) testing/cli.py -c $(CONFIG) run --continuous

test-generate: ## Generate tests for specific files
	$(PYTHON) testing/cli.py -c $(CONFIG) generate-tests src/**/*.py --test-type unit integration

run-adaptive: ## Run one-time adaptive analysis
	$(PYTHON) testing/cli.py -c $(CONFIG) run --force-full-analysis

status: ## Check adaptive testing system status
	$(PYTHON) testing/cli.py -c $(CONFIG) status

report: ## Generate comprehensive testing report
	$(PYTHON) testing/cli.py -c $(CONFIG) report --format html --output reports/adaptive-testing-report.html

report-json: ## Generate JSON testing report
	$(PYTHON) testing/cli.py -c $(CONFIG) report --format json --output reports/adaptive-testing-report.json

export-audit: ## Export audit trail data
	$(PYTHON) testing/cli.py -c $(CONFIG) export --export-path reports/audit-export.json

risk-analysis: ## Run risk analysis on changed files
	$(PYTHON) -c "
import sys
sys.path.append('testing')
from testing.risk.risk_analyzer import RiskAnalyzer
from testing.agents.orchestrator import CodeChangeEvent
from datetime import datetime
import asyncio
from pathlib import Path

async def analyze():
    analyzer = RiskAnalyzer({})
    src_files = list(Path('src').rglob('*.py'))
    for f in src_files[:5]:  # Limit for demo
        change = CodeChangeEvent(
            file_path=str(f),
            change_type='modified',
            timestamp=datetime.now(),
            file_hash='demo',
            complexity_score=3.0,
            affected_modules=[],
            test_requirements=['unit']
        )
        assessment = await analyzer.analyze_change(change)
        print(f'{f}: Risk {assessment.overall_score:.2f} ({assessment.level.value})')

asyncio.run(analyze())
	"

compliance-check: ## Run compliance validation
	$(PYTHON) -c "
import sys
sys.path.append('testing')
from testing.compliance.checker import ComplianceChecker
from pathlib import Path
import asyncio

async def check():
    checker = ComplianceChecker({})
    src_files = list(Path('src').rglob('*.py'))
    for f in src_files[:5]:  # Limit for demo
        report = await checker.check_file(f)
        status = '✅' if report.is_compliant else '❌'
        print(f'{status} {f}: Score {report.overall_score:.2f}')

asyncio.run(check())
	"

# Quality gates
quality-gates: ## Check quality gates before deployment
	@echo "🚪 Checking quality gates..."
	@$(PYTHON) testing/cli.py -c $(CONFIG) run --risk-threshold 0.5
	@pytest tests/ --cov=src --cov-fail-under=70
	@echo "✅ Quality gates passed"

# GitHub Actions testing
test-ci: ## Run CI-style testing locally
	$(PYTHON) testing/cli.py -c $(CONFIG) run --risk-threshold 0.7
	pytest tests/ --cov=src --cov-report=xml --junit-xml=junit.xml --maxfail=5

# Development helpers
dev-setup: install ## Set up development environment
	pre-commit install || echo "Pre-commit not available"
	$(PYTHON) setup_adaptive_testing.py

clean: ## Clean up generated files and caches
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf tests/generated/

clean-audit: ## Clean audit trail (WARNING: removes all audit data)
	@echo "⚠️  This will remove all audit trail data. Continue? [y/N]" && read ans && [ $${ans:-N} = y ]
	rm -rf testing/audit/*.db
	rm -rf testing/audit/*.jsonl
	rm -rf testing/audit/*.json
	echo "🗑️  Audit trail cleaned"

# Monitoring and alerts
monitor: ## Start monitoring dashboard (if available)
	@echo "📊 Starting monitoring (requires additional setup)..."
	@echo "   Monitoring dashboard not implemented in this version"
	@echo "   Check reports/adaptive-testing-report.html for current status"

# Security and compliance
security-scan: ## Run security scanning
	bandit -r src/ -f json -o reports/security-scan.json || true
	safety check --json --output reports/safety-check.json || true
	@echo "🔒 Security scan completed - check reports/"

# Performance testing
perf-test: ## Run performance tests
	pytest tests/performance/ --benchmark-only --benchmark-json=reports/benchmark.json || true
	@echo "⚡ Performance tests completed"

# Documentation
docs: ## Generate documentation (placeholder)
	@echo "📚 Documentation generation not implemented"
	@echo "   Check testing/ directory for module documentation"

# Version and info
version: ## Show version information
	@echo "Adaptive Testing Framework v1.0.0"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Project: $$(pwd)"
	@echo "Config: $(CONFIG)"

# All-in-one commands
full-test: test test-adaptive quality-gates ## Run complete testing suite
	@echo "🎯 Full testing suite completed!"

daily-check: status risk-analysis compliance-check ## Daily health check
	@echo "📅 Daily check completed!"
"""
    
    makefile_path = Path('Makefile')
    
    with open(makefile_path, 'w') as f:
        f.write(makefile_content)
    
    print("✅ Makefile created with adaptive testing commands")


def setup_example_tests():
    """Create example test files to demonstrate the system."""
    print("\n📝 Creating example test files...")
    
    # Example unit test
    unit_test_example = '''"""
Example unit tests generated by the Adaptive Testing Framework.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from decimal import Decimal

# Example of grants-specific financial calculation test
def test_award_amount_calculation_precision():
    """Test financial calculation precision requirements."""
    from decimal import Decimal
    
    # Test data
    base_amount = Decimal('1000.00')
    percentage = Decimal('0.15')
    
    # Mock calculation function
    def calculate_award_amount(base: Decimal, rate: Decimal) -> Decimal:
        return (base * rate).quantize(Decimal('0.01'))
    
    # Test execution
    result = calculate_award_amount(base_amount, percentage)
    
    # Assertions
    assert isinstance(result, Decimal)
    assert result == Decimal('150.00')
    assert result.as_tuple().exponent <= -2  # At least 2 decimal places


@pytest.mark.asyncio
async def test_api_client_error_handling():
    """Test API client error handling and resilience."""
    
    # Mock API client
    class MockAPIClient:
        async def search_opportunities(self, query: str):
            if query == "error_test":
                raise Exception("API Error")
            return {"data": [{"title": f"Grant for {query}"}]}
    
    client = MockAPIClient()
    
    # Test successful case
    result = await client.search_opportunities("technology")
    assert "data" in result
    assert len(result["data"]) > 0
    
    # Test error case
    with pytest.raises(Exception, match="API Error"):
        await client.search_opportunities("error_test")


def test_compliance_validation():
    """Test compliance requirements for grants processing."""
    
    def validate_applicant_eligibility(applicant_data: dict) -> bool:
        """Mock eligibility validation function."""
        required_fields = ['organization_type', 'tax_status', 'location']
        return all(field in applicant_data for field in required_fields)
    
    # Test compliant applicant
    compliant_applicant = {
        'organization_type': 'nonprofit',
        'tax_status': 'exempt',
        'location': 'US'
    }
    
    assert validate_applicant_eligibility(compliant_applicant) is True
    
    # Test non-compliant applicant
    non_compliant_applicant = {
        'organization_type': 'nonprofit'
        # Missing required fields
    }
    
    assert validate_applicant_eligibility(non_compliant_applicant) is False


class TestRiskScenarios:
    """Test various risk scenarios for grants processing."""
    
    def test_edge_case_empty_data(self):
        """Test handling of empty data inputs."""
        def process_grant_data(data):
            return data if data else {"status": "no_data"}
        
        result = process_grant_data([])
        assert result == {"status": "no_data"}
    
    def test_boundary_values_funding_amounts(self):
        """Test boundary values for funding amounts."""
        def validate_funding_amount(amount):
            return 0 <= amount <= 1000000
        
        # Test boundary conditions
        assert validate_funding_amount(0) is True
        assert validate_funding_amount(1000000) is True
        assert validate_funding_amount(-1) is False
        assert validate_funding_amount(1000001) is False
'''
    
    example_test_path = Path('tests/generated/unit/test_example_adaptive.py')
    example_test_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(example_test_path, 'w') as f:
        f.write(unit_test_example)
    
    print(f"✅ Example test created: {example_test_path}")


def print_next_steps():
    """Print next steps and usage instructions."""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                     Setup Complete! 🎉                     ║
    ╚══════════════════════════════════════════════════════════════╝
    
    🚀 Next Steps:
    
    1. Test the installation:
       make test-adaptive
    
    2. Run continuous monitoring:
       make test-continuous
    
    3. Generate a testing report:
       make report
    
    4. Check system status:
       make status
    
    5. View all available commands:
       make help
    
    📚 Key Files Created:
    • adaptive-testing-config.json  - Main configuration
    • Makefile                     - Command shortcuts
    • testing/                     - Framework modules
    • .github/workflows/adaptive-qa.yml - CI/CD pipeline
    
    🔗 Integration:
    • GitHub Actions workflow is ready for CI/CD
    • Pre-commit hooks available (run: pre-commit install)
    • Quality gates configured for deployment safety
    
    💡 Tips:
    • Customize adaptive-testing-config.json for your needs
    • The system learns and improves over time
    • Check reports/ directory for detailed analysis
    • Use 'make daily-check' for regular health checks
    
    📖 Documentation:
    • Framework modules have inline documentation
    • Use --help with CLI commands for details
    • Check tests/generated/ for example tests
    
    Happy Testing! 🧪✨
    """)


def main():
    """Main setup function."""
    try:
        print_banner()
        check_requirements()
        
        if not install_dependencies():
            print("❌ Setup failed - dependency installation failed")
            sys.exit(1)
        
        create_directory_structure()
        config = setup_configuration()
        setup_github_actions()
        setup_pre_commit_hooks()
        create_makefile()
        setup_example_tests()
        
        print_next_steps()
        
        print("✅ Adaptive Testing Framework setup completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure you have Python 3.9+ installed")
        print("2. Check that you have write permissions in this directory")
        print("3. Verify internet connection for package downloads")
        print("4. Try running individual components manually")
        sys.exit(1)


if __name__ == '__main__':
    main()