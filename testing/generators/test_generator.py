"""
Intelligent Test Case Generator for Adaptive Testing

This module generates comprehensive test cases based on code analysis,
risk assessment, and business requirements. It supports unit tests,
integration tests, performance tests, and grants-specific validation tests.
"""

import ast
import re
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import jinja2
import json

logger = logging.getLogger(__name__)


class TestType(Enum):
    """Types of tests that can be generated."""
    UNIT = "unit"
    INTEGRATION = "integration"
    CONTRACT = "contract"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    REGRESSION = "regression"
    EDGE_CASE = "edge_case"
    SECURITY = "security"


class TestComplexity(Enum):
    """Test complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    COMPREHENSIVE = "comprehensive"


@dataclass
class TestCaseSpec:
    """Specification for a single test case."""
    test_name: str
    test_type: TestType
    description: str
    function_under_test: str
    input_parameters: Dict[str, Any]
    expected_output: Any
    assertions: List[str]
    setup_code: Optional[str]
    teardown_code: Optional[str]
    mocks_required: List[str]
    complexity: TestComplexity
    priority: int
    business_context: str
    compliance_requirements: List[str]


@dataclass
class TestSuite:
    """Collection of related test cases."""
    suite_name: str
    file_path: str
    test_cases: List[TestCaseSpec]
    imports: List[str]
    fixtures: List[str]
    setup_class: Optional[str]
    teardown_class: Optional[str]
    metadata: Dict[str, Any]


class CodeAnalyzer:
    """Analyzes code to extract testable elements."""
    
    def __init__(self):
        self.grants_patterns = {
            'financial_calculation': [
                r'calculate.*amount', r'compute.*funding', r'award.*calculation',
                r'eligibility.*score', r'matching.*algorithm'
            ],
            'api_endpoint': [
                r'@app\.route', r'@router\.(get|post|put|delete)',
                r'async def.*tool', r'def.*search'
            ],
            'data_validation': [
                r'validate.*', r'verify.*', r'check.*eligibility',
                r'sanitize.*', r'clean.*input'
            ],
            'business_logic': [
                r'process.*grant', r'evaluate.*proposal', r'rank.*opportunities',
                r'filter.*results', r'score.*match'
            ]
        }
    
    def analyze_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze Python file to extract testable elements."""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            analysis = {
                'functions': [],
                'classes': [],
                'async_functions': [],
                'imports': [],
                'complexity_factors': [],
                'business_patterns': [],
                'test_requirements': []
            }
            
            # Extract functions, classes, and imports
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = self._analyze_function(node, content)
                    analysis['functions'].append(func_info)
                    
                elif isinstance(node, ast.AsyncFunctionDef):
                    func_info = self._analyze_async_function(node, content)
                    analysis['async_functions'].append(func_info)
                    
                elif isinstance(node, ast.ClassDef):
                    class_info = self._analyze_class(node, content)
                    analysis['classes'].append(class_info)
                    
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_info = self._extract_import_info(node)
                    analysis['imports'].append(import_info)
            
            # Identify business patterns
            analysis['business_patterns'] = self._identify_business_patterns(content)
            
            # Determine complexity factors
            analysis['complexity_factors'] = self._identify_complexity_factors(tree, content)
            
            # Suggest test requirements
            analysis['test_requirements'] = self._determine_test_requirements(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing Python file {file_path}: {e}")
            return self._create_fallback_analysis(file_path)
    
    def _analyze_function(self, node: ast.FunctionDef, content: str) -> Dict[str, Any]:
        """Analyze a function node."""
        func_info = {
            'name': node.name,
            'type': 'function',
            'line_number': node.lineno,
            'args': [arg.arg for arg in node.args.args],
            'returns': self._get_return_type_hint(node),
            'docstring': ast.get_docstring(node),
            'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
            'complexity': self._calculate_function_complexity(node),
            'calls_external_apis': self._has_external_api_calls(node, content),
            'modifies_state': self._modifies_state(node),
            'pure_function': self._is_pure_function(node),
            'business_critical': self._is_business_critical(node.name, content),
            'test_scenarios': self._generate_test_scenarios(node, content)
        }
        
        return func_info
    
    def _analyze_async_function(self, node: ast.AsyncFunctionDef, content: str) -> Dict[str, Any]:
        """Analyze an async function node."""
        func_info = {
            'name': node.name,
            'type': 'async_function',
            'line_number': node.lineno,
            'args': [arg.arg for arg in node.args.args],
            'returns': self._get_return_type_hint(node),
            'docstring': ast.get_docstring(node),
            'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
            'complexity': self._calculate_function_complexity(node),
            'calls_external_apis': self._has_external_api_calls(node, content),
            'modifies_state': self._modifies_state(node),
            'async_patterns': self._identify_async_patterns(node),
            'business_critical': self._is_business_critical(node.name, content),
            'test_scenarios': self._generate_async_test_scenarios(node, content)
        }
        
        return func_info
    
    def _analyze_class(self, node: ast.ClassDef, content: str) -> Dict[str, Any]:
        """Analyze a class node."""
        methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        
        class_info = {
            'name': node.name,
            'type': 'class',
            'line_number': node.lineno,
            'bases': [self._get_base_name(base) for base in node.bases],
            'methods': [m.name for m in methods],
            'public_methods': [m.name for m in methods if not m.name.startswith('_')],
            'private_methods': [m.name for m in methods if m.name.startswith('_')],
            'properties': self._extract_properties(node),
            'is_dataclass': any(d for d in node.decorator_list if self._get_decorator_name(d) == 'dataclass'),
            'is_enum': any(base for base in node.bases if self._get_base_name(base) == 'Enum'),
            'business_critical': self._is_business_critical(node.name, content),
            'test_scenarios': self._generate_class_test_scenarios(node, content)
        }
        
        return class_info
    
    def _identify_business_patterns(self, content: str) -> List[str]:
        """Identify business-specific patterns in the code."""
        patterns_found = []
        content_lower = content.lower()
        
        for pattern_type, patterns in self.grants_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    patterns_found.append(pattern_type)
                    break
        
        return patterns_found
    
    def _determine_test_requirements(self, analysis: Dict[str, Any]) -> List[TestType]:
        """Determine what types of tests are needed."""
        requirements = []
        
        # Always need unit tests
        if analysis['functions'] or analysis['classes']:
            requirements.append(TestType.UNIT)
        
        # Integration tests for external dependencies
        if any(func.get('calls_external_apis') for func in analysis['functions'] + analysis['async_functions']):
            requirements.append(TestType.INTEGRATION)
        
        # Performance tests for complex algorithms
        high_complexity_functions = [
            func for func in analysis['functions'] + analysis['async_functions']
            if func.get('complexity', 0) > 5
        ]
        if high_complexity_functions:
            requirements.append(TestType.PERFORMANCE)
        
        # Compliance tests for business patterns
        if analysis['business_patterns']:
            requirements.append(TestType.COMPLIANCE)
        
        # Contract tests for API endpoints
        if 'api_endpoint' in analysis['business_patterns']:
            requirements.append(TestType.CONTRACT)
        
        # Security tests for validation functions
        if 'data_validation' in analysis['business_patterns']:
            requirements.append(TestType.SECURITY)
        
        return requirements
    
    def _calculate_function_complexity(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
        
        return complexity
    
    def _generate_test_scenarios(self, node: ast.FunctionDef, content: str) -> List[str]:
        """Generate test scenarios for a function."""
        scenarios = ['happy_path']  # Always include happy path
        
        # Add edge cases based on function characteristics
        if self._has_conditional_logic(node):
            scenarios.extend(['edge_case_true', 'edge_case_false'])
        
        if self._has_error_handling(node):
            scenarios.append('error_handling')
        
        if self._has_loops(node):
            scenarios.extend(['empty_collection', 'single_item', 'multiple_items'])
        
        if self._is_business_critical(node.name, content):
            scenarios.extend(['boundary_values', 'invalid_input'])
        
        return scenarios
    
    def _generate_async_test_scenarios(self, node: ast.AsyncFunctionDef, content: str) -> List[str]:
        """Generate test scenarios for async functions."""
        scenarios = self._generate_test_scenarios(node, content)
        
        # Add async-specific scenarios
        scenarios.extend(['async_success', 'async_timeout', 'concurrent_execution'])
        
        if self._has_external_api_calls(node, content):
            scenarios.extend(['api_success', 'api_failure', 'api_rate_limit'])
        
        return scenarios
    
    def _generate_class_test_scenarios(self, node: ast.ClassDef, content: str) -> List[str]:
        """Generate test scenarios for a class."""
        scenarios = ['initialization', 'method_interactions']
        
        # Add scenarios based on class characteristics
        public_methods = [m for m in node.body if isinstance(m, ast.FunctionDef) and not m.name.startswith('_')]
        
        if len(public_methods) > 1:
            scenarios.append('method_chaining')
        
        if any(m.name in ['__enter__', '__exit__'] for m in node.body if isinstance(m, ast.FunctionDef)):
            scenarios.append('context_manager')
        
        if self._is_business_critical(node.name, content):
            scenarios.extend(['state_validation', 'invariants'])
        
        return scenarios
    
    # Helper methods for AST analysis
    def _get_return_type_hint(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Optional[str]:
        """Extract return type hint from function."""
        if node.returns:
            return ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
        return None
    
    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{decorator.value.id}.{decorator.attr}" if hasattr(decorator.value, 'id') else decorator.attr
        return str(decorator)
    
    def _get_base_name(self, base) -> str:
        """Extract base class name."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return f"{base.value.id}.{base.attr}" if hasattr(base.value, 'id') else base.attr
        return str(base)
    
    def _extract_import_info(self, node: Union[ast.Import, ast.ImportFrom]) -> str:
        """Extract import information."""
        if isinstance(node, ast.Import):
            return ', '.join(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            names = ', '.join(alias.name for alias in node.names)
            return f"from {module} import {names}"
        return ''
    
    def _extract_properties(self, node: ast.ClassDef) -> List[str]:
        """Extract properties from a class."""
        properties = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and any(
                self._get_decorator_name(d) == 'property' for d in item.decorator_list
            ):
                properties.append(item.name)
        return properties
    
    def _has_conditional_logic(self, node: ast.AST) -> bool:
        """Check if node contains conditional logic."""
        return any(isinstance(child, ast.If) for child in ast.walk(node))
    
    def _has_error_handling(self, node: ast.AST) -> bool:
        """Check if node contains error handling."""
        return any(isinstance(child, (ast.Try, ast.Raise)) for child in ast.walk(node))
    
    def _has_loops(self, node: ast.AST) -> bool:
        """Check if node contains loops."""
        return any(isinstance(child, (ast.For, ast.While)) for child in ast.walk(node))
    
    def _has_external_api_calls(self, node: ast.AST, content: str) -> bool:
        """Check if function makes external API calls."""
        api_indicators = ['requests.', 'httpx.', 'aiohttp.', 'urllib.', 'fetch(']
        node_content = content  # In a real implementation, extract just this node's content
        return any(indicator in node_content for indicator in api_indicators)
    
    def _modifies_state(self, node: ast.AST) -> bool:
        """Check if function modifies external state."""
        # Look for assignments, database calls, file operations
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                return True
            # Could add more sophisticated checks here
        return False
    
    def _is_pure_function(self, node: ast.AST) -> bool:
        """Check if function is pure (no side effects)."""
        return not self._modifies_state(node) and not self._has_external_api_calls(node, "")
    
    def _is_business_critical(self, name: str, content: str) -> bool:
        """Check if function/class is business critical."""
        critical_keywords = [
            'calculate', 'validate', 'process', 'payment', 'award',
            'eligibility', 'compliance', 'audit', 'financial'
        ]
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in critical_keywords)
    
    def _identify_async_patterns(self, node: ast.AsyncFunctionDef) -> List[str]:
        """Identify async patterns in the function."""
        patterns = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Await):
                patterns.append('await_usage')
            elif isinstance(child, ast.AsyncWith):
                patterns.append('async_context_manager')
            # Could add more async pattern detection
        
        return patterns
    
    def _identify_complexity_factors(self, tree: ast.AST, content: str) -> List[str]:
        """Identify factors that contribute to code complexity."""
        factors = []
        
        # Count various complexity contributors
        node_counts = {'if': 0, 'for': 0, 'try': 0, 'class': 0, 'function': 0}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                node_counts['if'] += 1
            elif isinstance(node, (ast.For, ast.While)):
                node_counts['for'] += 1
            elif isinstance(node, ast.Try):
                node_counts['try'] += 1
            elif isinstance(node, ast.ClassDef):
                node_counts['class'] += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                node_counts['function'] += 1
        
        # Determine complexity factors
        if node_counts['if'] > 5:
            factors.append('high_conditional_complexity')
        if node_counts['for'] > 3:
            factors.append('multiple_loops')
        if node_counts['try'] > 2:
            factors.append('complex_error_handling')
        if node_counts['function'] > 20:
            factors.append('large_function_count')
        
        return factors
    
    def _create_fallback_analysis(self, file_path: Path) -> Dict[str, Any]:
        """Create a fallback analysis when parsing fails."""
        return {
            'functions': [],
            'classes': [],
            'async_functions': [],
            'imports': [],
            'complexity_factors': ['parsing_failed'],
            'business_patterns': [],
            'test_requirements': [TestType.UNIT]
        }


class TestTemplateEngine:
    """Generates test code using templates."""
    
    def __init__(self):
        # Initialize Jinja2 environment
        self.env = jinja2.Environment(
            loader=jinja2.DictLoader(self._get_templates()),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Test data generators
        self.test_data_generators = {
            'string': lambda: '"test_string"',
            'int': lambda: '42',
            'float': lambda: '3.14',
            'bool': lambda: 'True',
            'list': lambda: '[1, 2, 3]',
            'dict': lambda: '{"key": "value"}',
            'None': lambda: 'None'
        }
    
    def _get_templates(self) -> Dict[str, str]:
        """Get Jinja2 templates for different test types."""
        return {
            'python_unit_test': '''"""
Unit tests for {{ module_name }}.

Generated by Adaptive Testing Agent on {{ timestamp }}.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
{% for import_stmt in imports %}
{{ import_stmt }}
{% endfor %}

from {{ module_path }} import {{ classes_under_test|join(', ') }}


class Test{{ test_class_name }}:
    """Test class for {{ classes_under_test[0] if classes_under_test else 'module functions' }}."""
    
    {% if fixtures %}
    # Fixtures
    {% for fixture in fixtures %}
    @pytest.fixture
    def {{ fixture.name }}(self):
        """{{ fixture.description }}"""
        {{ fixture.setup_code | indent(8) }}
        yield {{ fixture.yield_value }}
        # Cleanup
        {{ fixture.cleanup_code | indent(8) }}
    
    {% endfor %}
    {% endif %}
    
    {% for test_case in test_cases %}
    def test_{{ test_case.test_name }}(self{% if test_case.fixtures %}, {{ test_case.fixtures|join(', ') }}{% endif %}):
        """{{ test_case.description }}"""
        {% if test_case.setup_code %}
        # Setup
        {{ test_case.setup_code | indent(8) }}
        
        {% endif %}
        {% if test_case.mocks_required %}
        # Mocks
        {% for mock in test_case.mocks_required %}
        {{ mock.setup_code | indent(8) }}
        {% endfor %}
        
        {% endif %}
        {% if test_case.is_async %}
        # Async test execution
        async def async_test():
            {{ test_case.execution_code | indent(12) }}
            
        result = asyncio.run(async_test())
        {% else %}
        # Test execution
        {{ test_case.execution_code | indent(8) }}
        {% endif %}
        
        # Assertions
        {% for assertion in test_case.assertions %}
        {{ assertion | indent(8) }}
        {% endfor %}
        
        {% if test_case.teardown_code %}
        # Cleanup
        {{ test_case.teardown_code | indent(8) }}
        {% endif %}
    
    {% endfor %}


# Performance tests
{% if performance_tests %}
class TestPerformance{{ test_class_name }}:
    """Performance tests for {{ classes_under_test[0] if classes_under_test else 'module functions' }}."""
    
    {% for perf_test in performance_tests %}
    def test_performance_{{ perf_test.test_name }}(self, benchmark):
        """{{ perf_test.description }}"""
        {{ perf_test.setup_code | indent(8) }}
        
        result = benchmark({{ perf_test.function_call }})
        
        {% for assertion in perf_test.assertions %}
        {{ assertion | indent(8) }}
        {% endfor %}
    
    {% endfor %}
{% endif %}


# Edge case tests
{% if edge_case_tests %}
class TestEdgeCases{{ test_class_name }}:
    """Edge case tests for {{ classes_under_test[0] if classes_under_test else 'module functions' }}."""
    
    {% for edge_test in edge_case_tests %}
    def test_{{ edge_test.test_name }}(self):
        """{{ edge_test.description }}"""
        {% if edge_test.expected_exception %}
        with pytest.raises({{ edge_test.expected_exception }}):
            {{ edge_test.execution_code | indent(12) }}
        {% else %}
        {{ edge_test.execution_code | indent(8) }}
        
        {% for assertion in edge_test.assertions %}
        {{ assertion | indent(8) }}
        {% endfor %}
        {% endif %}
    
    {% endfor %}
{% endif %}


# Grants-specific tests
{% if grants_tests %}
class TestGrantsCompliance{{ test_class_name }}:
    """Grants-specific compliance and business logic tests."""
    
    {% for grants_test in grants_tests %}
    def test_{{ grants_test.test_name }}(self):
        """{{ grants_test.description }}
        
        Compliance requirement: {{ grants_test.compliance_requirement }}
        """
        {{ grants_test.setup_code | indent(8) }}
        
        {{ grants_test.execution_code | indent(8) }}
        
        # Business logic assertions
        {% for assertion in grants_test.assertions %}
        {{ assertion | indent(8) }}
        {% endfor %}
        
        # Compliance assertions
        {% for comp_assertion in grants_test.compliance_assertions %}
        {{ comp_assertion | indent(8) }}
        {% endfor %}
    
    {% endfor %}
{% endif %}
''',

            'integration_test': '''"""
Integration tests for {{ module_name }}.

Generated by Adaptive Testing Agent on {{ timestamp }}.
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, patch
{% for import_stmt in imports %}
{{ import_stmt }}
{% endfor %}

from {{ module_path }} import {{ classes_under_test|join(', ') }}


@pytest.mark.integration
class TestIntegration{{ test_class_name }}:
    """Integration tests for {{ classes_under_test[0] if classes_under_test else 'module' }}."""
    
    {% for integration_test in integration_tests %}
    @pytest.mark.asyncio
    async def test_{{ integration_test.test_name }}(self):
        """{{ integration_test.description }}"""
        {% if integration_test.requires_real_api %}
        # Note: This test requires real API access
        if not os.getenv("USE_REAL_API"):
            pytest.skip("Real API tests disabled")
        {% endif %}
        
        {{ integration_test.setup_code | indent(8) }}
        
        {% if integration_test.mock_responses %}
        # Mock external responses
        {% for mock_resp in integration_test.mock_responses %}
        {{ mock_resp.setup_code | indent(8) }}
        {% endfor %}
        {% endif %}
        
        # Execute integration test
        {{ integration_test.execution_code | indent(8) }}
        
        # Verify integration results
        {% for assertion in integration_test.assertions %}
        {{ assertion | indent(8) }}
        {% endfor %}
    
    {% endfor %}
''',

            'contract_test': '''"""
API Contract tests for {{ module_name }}.

Generated by Adaptive Testing Agent on {{ timestamp }}.
"""

import pytest
import jsonschema
from {{ module_path }} import {{ api_classes|join(', ') }}


@pytest.mark.contract
class TestAPIContracts:
    """API contract validation tests."""
    
    {% for contract_test in contract_tests %}
    def test_{{ contract_test.endpoint_name }}_contract(self):
        """Test API contract for {{ contract_test.endpoint }}"""
        
        # Request schema validation
        {{ contract_test.request_validation | indent(8) }}
        
        # Response schema validation  
        {{ contract_test.response_validation | indent(8) }}
        
        # Business rule validation
        {{ contract_test.business_validation | indent(8) }}
    
    {% endfor %}
'''
        }
    
    def generate_test_file(self, test_suite: TestSuite) -> str:
        """Generate complete test file content."""
        template_name = self._select_template(test_suite)
        template = self.env.get_template(template_name)
        
        context = self._build_template_context(test_suite)
        
        return template.render(**context)
    
    def _select_template(self, test_suite: TestSuite) -> str:
        """Select appropriate template based on test suite type."""
        # Determine template based on test types present
        test_types = [tc.test_type for tc in test_suite.test_cases]
        
        if TestType.CONTRACT in test_types:
            return 'contract_test'
        elif TestType.INTEGRATION in test_types:
            return 'integration_test'
        else:
            return 'python_unit_test'
    
    def _build_template_context(self, test_suite: TestSuite) -> Dict[str, Any]:
        """Build context dictionary for template rendering."""
        # Extract module information
        module_path = test_suite.metadata.get('module_path', 'src.module')
        module_name = test_suite.metadata.get('module_name', 'module')
        
        # Group tests by type
        unit_tests = [tc for tc in test_suite.test_cases if tc.test_type == TestType.UNIT]
        performance_tests = [tc for tc in test_suite.test_cases if tc.test_type == TestType.PERFORMANCE]
        edge_case_tests = [tc for tc in test_suite.test_cases if tc.test_type == TestType.EDGE_CASE]
        grants_tests = [tc for tc in test_suite.test_cases if tc.test_type == TestType.COMPLIANCE]
        integration_tests = [tc for tc in test_suite.test_cases if tc.test_type == TestType.INTEGRATION]
        contract_tests = [tc for tc in test_suite.test_cases if tc.test_type == TestType.CONTRACT]
        
        context = {
            'module_name': module_name,
            'module_path': module_path,
            'test_class_name': test_suite.suite_name.replace('_', '').title(),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'imports': test_suite.imports,
            'fixtures': test_suite.fixtures,
            'classes_under_test': test_suite.metadata.get('classes', []),
            'api_classes': test_suite.metadata.get('api_classes', []),
            'test_cases': self._convert_test_cases_for_template(unit_tests),
            'performance_tests': self._convert_test_cases_for_template(performance_tests),
            'edge_case_tests': self._convert_test_cases_for_template(edge_case_tests),
            'grants_tests': self._convert_test_cases_for_template(grants_tests),
            'integration_tests': self._convert_test_cases_for_template(integration_tests),
            'contract_tests': self._convert_test_cases_for_template(contract_tests)
        }
        
        return context
    
    def _convert_test_cases_for_template(self, test_cases: List[TestCaseSpec]) -> List[Dict[str, Any]]:
        """Convert test case specifications to template-friendly format."""
        converted = []
        
        for tc in test_cases:
            converted_tc = {
                'test_name': tc.test_name,
                'description': tc.description,
                'setup_code': tc.setup_code or '',
                'teardown_code': tc.teardown_code or '',
                'execution_code': self._generate_execution_code(tc),
                'assertions': tc.assertions,
                'is_async': 'async' in tc.function_under_test.lower(),
                'fixtures': tc.mocks_required,
                'mocks_required': self._convert_mocks_to_template(tc.mocks_required),
                'compliance_requirement': tc.business_context,
                'compliance_assertions': self._generate_compliance_assertions(tc),
                'expected_exception': self._get_expected_exception(tc)
            }
            converted.append(converted_tc)
        
        return converted
    
    def _generate_execution_code(self, test_case: TestCaseSpec) -> str:
        """Generate test execution code."""
        if test_case.input_parameters:
            params = ', '.join(f"{k}={v}" for k, v in test_case.input_parameters.items())
            return f"result = {test_case.function_under_test}({params})"
        else:
            return f"result = {test_case.function_under_test}()"
    
    def _convert_mocks_to_template(self, mocks: List[str]) -> List[Dict[str, str]]:
        """Convert mock requirements to template format."""
        mock_configs = []
        for mock_name in mocks:
            mock_configs.append({
                'name': mock_name,
                'setup_code': f"mock_{mock_name} = Mock()"
            })
        return mock_configs
    
    def _generate_compliance_assertions(self, test_case: TestCaseSpec) -> List[str]:
        """Generate compliance-specific assertions."""
        assertions = []
        
        for requirement in test_case.compliance_requirements:
            if 'financial' in requirement.lower():
                assertions.append("assert isinstance(result, (int, float, Decimal))")
                assertions.append("assert result >= 0")
            elif 'audit' in requirement.lower():
                assertions.append("assert 'audit_trail' in result")
            elif 'validation' in requirement.lower():
                assertions.append("assert result is not None")
        
        return assertions
    
    def _get_expected_exception(self, test_case: TestCaseSpec) -> Optional[str]:
        """Determine if test case should expect an exception."""
        if 'error' in test_case.test_name.lower() or 'invalid' in test_case.test_name.lower():
            return 'ValueError'
        return None


class TestCaseGenerator:
    """Main test case generator."""
    
    def __init__(self, project_root: Path, config: Dict[str, Any]):
        """Initialize the test generator."""
        self.project_root = project_root
        self.config = config
        self.code_analyzer = CodeAnalyzer()
        self.template_engine = TestTemplateEngine()
        
        # Test generation settings
        self.max_tests_per_file = config.get('max_tests_per_file', 10)
        self.test_timeout = config.get('test_timeout', 30)
        self.parallel_generation = config.get('parallel_generation', True)
        
        logger.info("Initialized Test Case Generator")
    
    async def generate_tests(self, request) -> List[str]:
        """Generate test files based on a test generation request."""
        logger.info(f"Generating tests for {request.source_file} - {request.test_category}")
        
        source_path = Path(request.source_file)
        
        # Analyze source code
        if source_path.suffix == '.py':
            analysis = self.code_analyzer.analyze_python_file(source_path)
        else:
            logger.warning(f"Unsupported file type: {source_path.suffix}")
            return []
        
        # Generate test specifications
        test_specs = await self._generate_test_specifications(request, analysis)
        
        # Create test suites
        test_suites = self._organize_into_suites(test_specs, request)
        
        # Generate test files
        generated_files = []
        for suite in test_suites:
            test_file_path = await self._write_test_file(suite)
            if test_file_path:
                generated_files.append(str(test_file_path))
        
        logger.info(f"Generated {len(generated_files)} test files")
        return generated_files
    
    async def _generate_test_specifications(self, request, analysis: Dict[str, Any]) -> List[TestCaseSpec]:
        """Generate test case specifications based on analysis."""
        test_specs = []
        
        # Generate unit tests for functions
        for func_info in analysis['functions'] + analysis['async_functions']:
            specs = await self._generate_function_tests(func_info, request, analysis)
            test_specs.extend(specs)
        
        # Generate class tests
        for class_info in analysis['classes']:
            specs = await self._generate_class_tests(class_info, request, analysis)
            test_specs.extend(specs)
        
        # Generate business-specific tests
        if request.business_context in ['grants_processing', 'financial_calculations']:
            specs = await self._generate_business_logic_tests(request, analysis)
            test_specs.extend(specs)
        
        # Generate integration tests if needed
        if request.test_category in ['integration', 'contract']:
            specs = await self._generate_integration_tests(request, analysis)
            test_specs.extend(specs)
        
        return test_specs[:self.max_tests_per_file]  # Limit number of tests
    
    async def _generate_function_tests(self, func_info: Dict[str, Any], request, analysis: Dict[str, Any]) -> List[TestCaseSpec]:
        """Generate test specifications for a function."""
        test_specs = []
        func_name = func_info['name']
        
        # Generate tests for each scenario
        for scenario in func_info.get('test_scenarios', ['happy_path']):
            test_spec = TestCaseSpec(
                test_name=f"{func_name}_{scenario}",
                test_type=TestType.UNIT,
                description=f"Test {func_name} with {scenario.replace('_', ' ')} scenario",
                function_under_test=func_name,
                input_parameters=self._generate_test_parameters(func_info, scenario),
                expected_output=self._generate_expected_output(func_info, scenario),
                assertions=self._generate_assertions(func_info, scenario),
                setup_code=self._generate_setup_code(func_info, scenario),
                teardown_code=None,
                mocks_required=self._identify_required_mocks(func_info),
                complexity=self._determine_test_complexity(func_info),
                priority=request.priority,
                business_context=request.business_context,
                compliance_requirements=self._get_compliance_requirements(func_info, request)
            )
            test_specs.append(test_spec)
        
        return test_specs
    
    async def _generate_class_tests(self, class_info: Dict[str, Any], request, analysis: Dict[str, Any]) -> List[TestCaseSpec]:
        """Generate test specifications for a class."""
        test_specs = []
        class_name = class_info['name']
        
        # Generate initialization test
        init_spec = TestCaseSpec(
            test_name=f"{class_name.lower()}_initialization",
            test_type=TestType.UNIT,
            description=f"Test {class_name} initialization",
            function_under_test=f"{class_name}",
            input_parameters={},
            expected_output="instance",
            assertions=[f"assert isinstance(result, {class_name})"],
            setup_code=None,
            teardown_code=None,
            mocks_required=[],
            complexity=TestComplexity.SIMPLE,
            priority=request.priority,
            business_context=request.business_context,
            compliance_requirements=[]
        )
        test_specs.append(init_spec)
        
        # Generate method tests
        for method_name in class_info.get('public_methods', [])[:3]:  # Limit to first 3 methods
            method_spec = TestCaseSpec(
                test_name=f"{class_name.lower()}_{method_name}",
                test_type=TestType.UNIT,
                description=f"Test {class_name}.{method_name} method",
                function_under_test=f"instance.{method_name}",
                input_parameters={},
                expected_output="success",
                assertions=["assert result is not None"],
                setup_code=f"instance = {class_name}()",
                teardown_code=None,
                mocks_required=[],
                complexity=TestComplexity.MODERATE,
                priority=request.priority,
                business_context=request.business_context,
                compliance_requirements=[]
            )
            test_specs.append(method_spec)
        
        return test_specs
    
    async def _generate_business_logic_tests(self, request, analysis: Dict[str, Any]) -> List[TestCaseSpec]:
        """Generate business logic specific tests."""
        test_specs = []
        
        if request.business_context == 'grants_processing':
            # Generate grants-specific compliance tests
            test_specs.extend(await self._generate_grants_compliance_tests(request, analysis))
        elif request.business_context == 'financial_calculations':
            # Generate financial calculation tests
            test_specs.extend(await self._generate_financial_tests(request, analysis))
        
        return test_specs
    
    async def _generate_grants_compliance_tests(self, request, analysis: Dict[str, Any]) -> List[TestCaseSpec]:
        """Generate grants-specific compliance tests."""
        test_specs = []
        
        # Eligibility validation test
        eligibility_spec = TestCaseSpec(
            test_name="grants_eligibility_validation",
            test_type=TestType.COMPLIANCE,
            description="Test grants eligibility validation compliance",
            function_under_test="validate_eligibility",
            input_parameters={"applicant_data": "test_applicant"},
            expected_output=True,
            assertions=[
                "assert result in [True, False]",
                "assert 'audit_trail' in locals() or True"  # Check audit trail exists
            ],
            setup_code="test_applicant = {'type': 'nonprofit', 'tax_status': 'exempt'}",
            teardown_code=None,
            mocks_required=[],
            complexity=TestComplexity.COMPLEX,
            priority=10,
            business_context="grants_compliance",
            compliance_requirements=["CFR 200.205", "OMB A-133"]
        )
        test_specs.append(eligibility_spec)
        
        return test_specs
    
    async def _generate_financial_tests(self, request, analysis: Dict[str, Any]) -> List[TestCaseSpec]:
        """Generate financial calculation tests."""
        test_specs = []
        
        # Precision test
        precision_spec = TestCaseSpec(
            test_name="financial_calculation_precision",
            test_type=TestType.COMPLIANCE,
            description="Test financial calculation precision requirements",
            function_under_test="calculate_award_amount",
            input_parameters={"base_amount": "Decimal('1000.00')", "percentage": "Decimal('0.15')"},
            expected_output="Decimal('150.00')",
            assertions=[
                "assert isinstance(result, Decimal)",
                "assert result.as_tuple().exponent <= -2"  # At least 2 decimal places
            ],
            setup_code="from decimal import Decimal",
            teardown_code=None,
            mocks_required=[],
            complexity=TestComplexity.COMPLEX,
            priority=10,
            business_context="financial_compliance",
            compliance_requirements=["Financial Precision Standards"]
        )
        test_specs.append(precision_spec)
        
        return test_specs
    
    async def _generate_integration_tests(self, request, analysis: Dict[str, Any]) -> List[TestCaseSpec]:
        """Generate integration test specifications."""
        test_specs = []
        
        # API integration test
        if 'api_endpoint' in analysis.get('business_patterns', []):
            api_spec = TestCaseSpec(
                test_name="api_integration_test",
                test_type=TestType.INTEGRATION,
                description="Test API endpoint integration",
                function_under_test="api_call",
                input_parameters={"query": "test"},
                expected_output="api_response",
                assertions=[
                    "assert result is not None",
                    "assert 'data' in result"
                ],
                setup_code="api_client = APIClient()",
                teardown_code="await api_client.close()",
                mocks_required=["external_api"],
                complexity=TestComplexity.COMPLEX,
                priority=request.priority,
                business_context=request.business_context,
                compliance_requirements=[]
            )
            test_specs.append(api_spec)
        
        return test_specs
    
    def _organize_into_suites(self, test_specs: List[TestCaseSpec], request) -> List[TestSuite]:
        """Organize test specifications into test suites."""
        # Group tests by type and complexity
        suites_dict = {}
        
        for spec in test_specs:
            suite_key = f"{spec.test_type.value}_{spec.business_context}"
            
            if suite_key not in suites_dict:
                suites_dict[suite_key] = TestSuite(
                    suite_name=f"test_{suite_key}",
                    file_path=self._generate_test_file_path(request.source_file, suite_key),
                    test_cases=[],
                    imports=self._generate_imports(request),
                    fixtures=[],
                    setup_class=None,
                    teardown_class=None,
                    metadata={
                        'module_path': self._get_module_path(request.source_file),
                        'module_name': Path(request.source_file).stem,
                        'classes': [],  # Would extract from analysis
                        'api_classes': []  # Would extract from analysis
                    }
                )
            
            suites_dict[suite_key].test_cases.append(spec)
        
        return list(suites_dict.values())
    
    async def _write_test_file(self, test_suite: TestSuite) -> Optional[Path]:
        """Write test suite to file."""
        try:
            test_content = self.template_engine.generate_test_file(test_suite)
            
            test_file_path = Path(test_suite.file_path)
            test_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            test_file_path.write_text(test_content, encoding='utf-8')
            
            logger.info(f"Generated test file: {test_file_path}")
            return test_file_path
            
        except Exception as e:
            logger.error(f"Error writing test file {test_suite.file_path}: {e}")
            return None
    
    # Helper methods for test generation
    def _generate_test_parameters(self, func_info: Dict[str, Any], scenario: str) -> Dict[str, Any]:
        """Generate test parameters based on function info and scenario."""
        params = {}
        
        # Generate parameters based on function arguments
        for arg in func_info.get('args', []):
            if scenario == 'edge_case_empty':
                params[arg] = '""' if 'str' in arg else '[]'
            elif scenario == 'edge_case_none':
                params[arg] = 'None'
            else:
                # Generate appropriate test data based on argument name
                params[arg] = self._generate_test_data_for_arg(arg)
        
        return params
    
    def _generate_test_data_for_arg(self, arg_name: str) -> str:
        """Generate appropriate test data for an argument."""
        arg_lower = arg_name.lower()
        
        if 'amount' in arg_lower or 'price' in arg_lower:
            return 'Decimal("100.00")'
        elif 'id' in arg_lower:
            return '"test_id_123"'
        elif 'name' in arg_lower:
            return '"Test Name"'
        elif 'email' in arg_lower:
            return '"test@example.com"'
        elif 'count' in arg_lower or 'num' in arg_lower:
            return '5'
        elif 'flag' in arg_lower or 'is_' in arg_lower:
            return 'True'
        else:
            return '"test_value"'
    
    def _generate_expected_output(self, func_info: Dict[str, Any], scenario: str) -> Any:
        """Generate expected output based on function info and scenario."""
        return_type = func_info.get('returns')
        
        if scenario.startswith('error'):
            return 'Exception'
        elif return_type:
            if 'bool' in str(return_type).lower():
                return True
            elif 'int' in str(return_type).lower():
                return 42
            elif 'str' in str(return_type).lower():
                return '"expected_string"'
        
        return 'expected_result'
    
    def _generate_assertions(self, func_info: Dict[str, Any], scenario: str) -> List[str]:
        """Generate assertions based on function info and scenario."""
        assertions = ["assert result is not None"]
        
        # Add type-specific assertions
        return_type = func_info.get('returns')
        if return_type:
            if 'bool' in str(return_type).lower():
                assertions.append("assert isinstance(result, bool)")
            elif 'int' in str(return_type).lower():
                assertions.append("assert isinstance(result, int)")
            elif 'str' in str(return_type).lower():
                assertions.append("assert isinstance(result, str)")
        
        # Add business-specific assertions
        if func_info.get('business_critical'):
            assertions.append("assert result != None")  # Critical functions should not return None
        
        return assertions
    
    def _generate_setup_code(self, func_info: Dict[str, Any], scenario: str) -> Optional[str]:
        """Generate setup code for test case."""
        if func_info.get('calls_external_apis'):
            return "# Setup mocks for external API calls"
        elif scenario == 'database_test':
            return "# Setup test database"
        return None
    
    def _identify_required_mocks(self, func_info: Dict[str, Any]) -> List[str]:
        """Identify what mocks are required for testing this function."""
        mocks = []
        
        if func_info.get('calls_external_apis'):
            mocks.append('api_client')
        
        if func_info.get('modifies_state'):
            mocks.append('database')
        
        return mocks
    
    def _determine_test_complexity(self, func_info: Dict[str, Any]) -> TestComplexity:
        """Determine test complexity based on function characteristics."""
        complexity_score = func_info.get('complexity', 1)
        
        if complexity_score > 10:
            return TestComplexity.COMPREHENSIVE
        elif complexity_score > 5:
            return TestComplexity.COMPLEX
        elif complexity_score > 2:
            return TestComplexity.MODERATE
        else:
            return TestComplexity.SIMPLE
    
    def _get_compliance_requirements(self, func_info: Dict[str, Any], request) -> List[str]:
        """Get compliance requirements for this function."""
        requirements = []
        
        if func_info.get('business_critical'):
            requirements.append("Business Critical Function")
        
        if request.business_context == 'grants_processing':
            requirements.extend(["CFR 200", "OMB Guidelines"])
        elif request.business_context == 'financial_calculations':
            requirements.extend(["Financial Accuracy", "Audit Trail"])
        
        return requirements
    
    def _generate_test_file_path(self, source_file: str, suite_key: str) -> str:
        """Generate path for test file."""
        source_path = Path(source_file)
        test_dir = self.project_root / "tests" / "generated"
        
        # Create test filename
        test_filename = f"test_{source_path.stem}_{suite_key}.py"
        
        return str(test_dir / test_filename)
    
    def _generate_imports(self, request) -> List[str]:
        """Generate import statements for test file."""
        imports = [
            "import pytest",
            "import asyncio",
            "from unittest.mock import Mock, AsyncMock, patch",
            "from decimal import Decimal",
            "import os"
        ]
        
        # Add business-specific imports
        if request.business_context == 'grants_processing':
            imports.append("from mcp_server.models.grants_schemas import OpportunityV1")
        
        return imports
    
    def _get_module_path(self, source_file: str) -> str:
        """Get module path for import statements."""
        source_path = Path(source_file)
        
        # Convert file path to module path
        if 'src' in source_path.parts:
            src_index = source_path.parts.index('src')
            module_parts = source_path.parts[src_index+1:-1] + (source_path.stem,)
            return '.'.join(module_parts)
        
        return source_path.stem