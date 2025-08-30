#!/usr/bin/env python3
"""
Deployment validation script for Grants MCP Cloud Run deployment.

This script validates the deployment configuration before pushing to production.
"""

import json
import os
import sys
import yaml
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def validate_github_workflow() -> Tuple[bool, List[str]]:
    """Validate GitHub Actions workflow file."""
    errors = []
    workflow_path = Path(".github/workflows/deploy.yml")
    
    if not workflow_path.exists():
        errors.append("GitHub workflow file not found at .github/workflows/deploy.yml")
        return False, errors
    
    try:
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)
        
        # Check required fields - 'on' might be parsed differently by YAML
        required_fields = ['name', 'env', 'jobs']
        for field in required_fields:
            if field not in workflow:
                errors.append(f"Missing required field '{field}' in workflow")
        
        # Check for 'on' field specifically (can be True in YAML)
        if 'on' not in workflow and True not in workflow:
            errors.append("Missing required field 'on' in workflow")
        
        # Check environment variables
        env = workflow.get('env', {})
        expected_env = {
            'PROJECT_ID': 'grants-mcp',
            'REGION': 'us-central1',
            'SERVICE': 'grants-mcp'
        }
        
        for key, expected_value in expected_env.items():
            if env.get(key) != expected_value:
                errors.append(f"Environment variable {key} should be '{expected_value}', got '{env.get(key)}'")
        
        # Check for required secrets usage
        workflow_str = str(workflow)
        required_secrets = ['GCP_SA_KEY', 'SIMPLER_GRANTS_API_KEY']
        for secret in required_secrets:
            if f"secrets.{secret}" not in workflow_str:
                errors.append(f"Required secret '{secret}' not found in workflow")
        
        print("✅ GitHub workflow validation passed")
        
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML syntax in workflow file: {e}")
    except Exception as e:
        errors.append(f"Error validating workflow: {e}")
    
    return len(errors) == 0, errors

def validate_dockerfile() -> Tuple[bool, List[str]]:
    """Validate Dockerfile configuration."""
    errors = []
    dockerfile_path = Path("Dockerfile")
    
    if not dockerfile_path.exists():
        errors.append("Dockerfile not found")
        return False, errors
    
    try:
        with open(dockerfile_path, 'r') as f:
            content = f.read()
        
        # Check for multi-stage build
        if "FROM python:3.11-slim as builder" not in content:
            errors.append("Multi-stage build not properly configured")
        
        # Check for non-root user
        if "RUN groupadd -r appuser && useradd -r -g appuser appuser" not in content:
            errors.append("Non-root user not configured")
        
        # Check for health check
        if "HEALTHCHECK" not in content:
            errors.append("Health check not configured")
        
        # Check for required environment variables
        required_env_vars = ['PYTHONUNBUFFERED=1', 'MCP_TRANSPORT=http', 'PORT=8080']
        for env_var in required_env_vars:
            if env_var not in content:
                errors.append(f"Missing environment variable: {env_var}")
        
        # Check for security best practices
        if "USER appuser" not in content:
            errors.append("Container should switch to non-root user")
        
        print("✅ Dockerfile validation passed")
        
    except Exception as e:
        errors.append(f"Error validating Dockerfile: {e}")
    
    return len(errors) == 0, errors

def validate_server_health_endpoint() -> Tuple[bool, List[str]]:
    """Validate server has health endpoint."""
    errors = []
    server_path = Path("src/mcp_server/server.py")
    
    if not server_path.exists():
        errors.append("Server file not found")
        return False, errors
    
    try:
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for health endpoint
        if '@self.mcp.get("/health")' not in content:
            errors.append("Health endpoint not found in server")
        
        # Check for health check function
        if 'async def health_check():' not in content:
            errors.append("Health check function not implemented")
        
        # Check for required health response fields
        required_fields = ['"status"', '"service"', '"version"', '"timestamp"', '"transport"']
        for field in required_fields:
            if field not in content:
                errors.append(f"Health endpoint missing required field: {field}")
        
        print("✅ Server health endpoint validation passed")
        
    except Exception as e:
        errors.append(f"Error validating server: {e}")
    
    return len(errors) == 0, errors

def validate_requirements() -> Tuple[bool, List[str]]:
    """Validate requirements.txt exists and has required dependencies."""
    errors = []
    req_path = Path("requirements.txt")
    
    if not req_path.exists():
        errors.append("requirements.txt not found")
        return False, errors
    
    try:
        with open(req_path, 'r') as f:
            content = f.read().lower()
        
        required_deps = ['fastmcp', 'httpx', 'pydantic', 'uvicorn']
        for dep in required_deps:
            if dep not in content:
                errors.append(f"Missing required dependency: {dep}")
        
        print("✅ Requirements validation passed")
        
    except Exception as e:
        errors.append(f"Error validating requirements: {e}")
    
    return len(errors) == 0, errors

def validate_documentation() -> Tuple[bool, List[str]]:
    """Validate required documentation exists."""
    errors = []
    
    required_docs = [
        "CLOUD_DEPLOYMENT.md",
        "USER_ONBOARDING.md",
        "README.md"
    ]
    
    for doc in required_docs:
        if not Path(doc).exists():
            errors.append(f"Missing documentation: {doc}")
    
    if len(errors) == 0:
        print("✅ Documentation validation passed")
    
    return len(errors) == 0, errors

def check_git_status() -> Tuple[bool, List[str]]:
    """Check git status and ensure we're on main branch."""
    errors = []
    
    try:
        # Check current branch
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, check=True)
        current_branch = result.stdout.strip()
        
        if current_branch != 'main':
            errors.append(f"Not on main branch (currently on: {current_branch})")
        
        # Check for uncommitted changes
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print("⚠️  Uncommitted changes detected - ensure all changes are committed before deployment")
        
        # Check if we can push (remote exists)
        result = subprocess.run(['git', 'remote', '-v'], 
                              capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            errors.append("No git remote configured - cannot deploy without remote repository")
        
        if len(errors) == 0:
            print("✅ Git status validation passed")
        
    except subprocess.CalledProcessError as e:
        errors.append(f"Git command failed: {e}")
    
    return len(errors) == 0, errors

def validate_environment_template() -> Tuple[bool, List[str]]:
    """Validate environment template exists."""
    errors = []
    
    env_example_path = Path(".env.example")
    if not env_example_path.exists():
        errors.append(".env.example file not found")
        return False, errors
    
    try:
        with open(env_example_path, 'r') as f:
            content = f.read()
        
        if "SIMPLER_GRANTS_API_KEY=" not in content:
            errors.append("SIMPLER_GRANTS_API_KEY not found in .env.example")
        
        print("✅ Environment template validation passed")
        
    except Exception as e:
        errors.append(f"Error validating environment template: {e}")
    
    return len(errors) == 0, errors

def print_deployment_checklist():
    """Print the deployment checklist for the user."""
    print("\n🚀 DEPLOYMENT CHECKLIST")
    print("=" * 50)
    print("\nBEFORE PUSHING TO MAIN BRANCH:")
    print("1. Add GitHub Repository Secrets:")
    print("   - Go to: https://github.com/Tar-ive/grants-mcp/settings/secrets/actions")
    print("   - Add 'GCP_SA_KEY' (entire contents of service account JSON)")
    print("   - Add 'SIMPLER_GRANTS_API_KEY' (your API key)")
    print("\n2. Ensure Google Cloud Project Setup:")
    print("   - Project ID: grants-mcp")
    print("   - Service account 'github-deployer' created with proper IAM roles")
    print("   - Service account 'grants-mcp-runner' created for runtime")
    print("   - APIs enabled: run.googleapis.com, artifactregistry.googleapis.com")
    print("\n3. Push to main branch:")
    print("   git push origin main")
    print("\n4. Monitor deployment:")
    print("   - Check GitHub Actions tab for workflow progress")
    print("   - Deployment will provide service URL upon completion")
    print("\n5. Test deployment:")
    print("   - Health check: curl <service-url>/health")
    print("   - MCP tools: curl -X POST <service-url>/mcp -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"tools/list\",\"id\":1}'")

def main():
    """Run all validation checks."""
    print("🔍 VALIDATING DEPLOYMENT CONFIGURATION")
    print("=" * 50)
    
    validators = [
        ("GitHub Workflow", validate_github_workflow),
        ("Dockerfile", validate_dockerfile),
        ("Server Health Endpoint", validate_server_health_endpoint),
        ("Requirements", validate_requirements),
        ("Documentation", validate_documentation),
        ("Git Status", check_git_status),
        ("Environment Template", validate_environment_template),
    ]
    
    all_passed = True
    all_errors = []
    
    for name, validator in validators:
        try:
            passed, errors = validator()
            if not passed:
                all_passed = False
                all_errors.extend([f"{name}: {error}" for error in errors])
        except Exception as e:
            all_passed = False
            all_errors.append(f"{name}: Validation failed with exception: {e}")
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("Configuration is ready for deployment.")
        print_deployment_checklist()
    else:
        print("❌ VALIDATION ERRORS FOUND:")
        for error in all_errors:
            print(f"  • {error}")
        print(f"\nPlease fix {len(all_errors)} error(s) before deployment.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())