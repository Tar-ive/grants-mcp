"""
Risk Assessment Engine for Adaptive Testing

This module analyzes code changes to identify security vulnerabilities,
complexity risks, and business impact to prioritize testing efforts.
"""

import ast
import re
import logging
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    """Risk category types."""
    SECURITY = "security"
    COMPLIANCE = "compliance"
    BUSINESS_LOGIC = "business_logic"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"
    DATA_INTEGRITY = "data_integrity"


@dataclass
class RiskFinding:
    """Individual risk finding."""
    category: RiskCategory
    level: RiskLevel
    description: str
    location: str
    line_number: Optional[int]
    mitigation: str
    score: float


@dataclass
class RiskAssessment:
    """Complete risk assessment for a code change."""
    file_path: str
    overall_score: float
    level: RiskLevel
    findings: List[RiskFinding]
    business_impact_score: float
    security_score: float
    complexity_score: float
    grants_specific_score: float
    timestamp: datetime
    recommendations: List[str]


class SecurityPatternDetector:
    """Detects security-related patterns in code."""
    
    def __init__(self):
        # Security vulnerability patterns
        self.sql_injection_patterns = [
            r'\.execute\s*\(\s*["\'].*%.*["\']',  # SQL string formatting
            r'f["\']\s*SELECT.*\{.*\}',  # F-string in SQL
            r'\.format\s*\(\s*\).*SELECT',  # .format() in SQL
        ]
        
        self.xss_patterns = [
            r'\.innerHTML\s*=',  # Direct innerHTML assignment
            r'document\.write\s*\(',  # document.write usage
            r'eval\s*\(',  # eval() usage
        ]
        
        self.path_traversal_patterns = [
            r'\.\./|\.\.\/',  # Path traversal sequences
            r'os\.path\.join.*\.\.',  # Unsafe path joining
        ]
        
        self.hardcoded_secrets_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',  # Hardcoded passwords
            r'api_key\s*=\s*["\'][^"\']+["\']',   # Hardcoded API keys
            r'secret\s*=\s*["\'][^"\']+["\']',    # Hardcoded secrets
            r'token\s*=\s*["\'][^"\']+["\']',     # Hardcoded tokens
        ]
    
    def scan_content(self, content: str, file_path: str) -> List[RiskFinding]:
        """Scan content for security vulnerabilities."""
        findings = []
        
        # SQL Injection detection
        findings.extend(self._detect_sql_injection(content, file_path))
        
        # XSS detection
        findings.extend(self._detect_xss(content, file_path))
        
        # Path traversal detection
        findings.extend(self._detect_path_traversal(content, file_path))
        
        # Hardcoded secrets detection
        findings.extend(self._detect_hardcoded_secrets(content, file_path))
        
        # Grants-specific security checks
        findings.extend(self._detect_grants_security_issues(content, file_path))
        
        return findings
    
    def _detect_sql_injection(self, content: str, file_path: str) -> List[RiskFinding]:
        """Detect potential SQL injection vulnerabilities."""
        findings = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in self.sql_injection_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(RiskFinding(
                        category=RiskCategory.SECURITY,
                        level=RiskLevel.HIGH,
                        description="Potential SQL injection vulnerability",
                        location=f"{file_path}:{i}",
                        line_number=i,
                        mitigation="Use parameterized queries or ORM methods",
                        score=0.8
                    ))
        
        return findings
    
    def _detect_xss(self, content: str, file_path: str) -> List[RiskFinding]:
        """Detect potential XSS vulnerabilities."""
        findings = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in self.xss_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(RiskFinding(
                        category=RiskCategory.SECURITY,
                        level=RiskLevel.MEDIUM,
                        description="Potential XSS vulnerability",
                        location=f"{file_path}:{i}",
                        line_number=i,
                        mitigation="Sanitize user input and use safe DOM manipulation",
                        score=0.6
                    ))
        
        return findings
    
    def _detect_path_traversal(self, content: str, file_path: str) -> List[RiskFinding]:
        """Detect potential path traversal vulnerabilities."""
        findings = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in self.path_traversal_patterns:
                if re.search(pattern, line):
                    findings.append(RiskFinding(
                        category=RiskCategory.SECURITY,
                        level=RiskLevel.MEDIUM,
                        description="Potential path traversal vulnerability",
                        location=f"{file_path}:{i}",
                        line_number=i,
                        mitigation="Validate and sanitize file paths",
                        score=0.7
                    ))
        
        return findings
    
    def _detect_hardcoded_secrets(self, content: str, file_path: str) -> List[RiskFinding]:
        """Detect hardcoded secrets and credentials."""
        findings = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in self.hardcoded_secrets_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(RiskFinding(
                        category=RiskCategory.SECURITY,
                        level=RiskLevel.HIGH,
                        description="Hardcoded credentials detected",
                        location=f"{file_path}:{i}",
                        line_number=i,
                        mitigation="Use environment variables or secure key management",
                        score=0.9
                    ))
        
        return findings
    
    def _detect_grants_security_issues(self, content: str, file_path: str) -> List[RiskFinding]:
        """Detect grants-specific security issues."""
        findings = []
        lines = content.split('\n')
        
        # Check for unencrypted financial data
        financial_patterns = [
            r'amount\s*=\s*["\']?\d+',  # Direct amount assignment
            r'ssn\s*=',  # SSN handling
            r'tax_id\s*=',  # Tax ID handling
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in financial_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(RiskFinding(
                        category=RiskCategory.DATA_INTEGRITY,
                        level=RiskLevel.HIGH,
                        description="Potential financial data security issue",
                        location=f"{file_path}:{i}",
                        line_number=i,
                        mitigation="Encrypt sensitive financial data",
                        score=0.8
                    ))
        
        return findings


class ComplexityAnalyzer:
    """Analyzes code complexity to identify risk factors."""
    
    def analyze_python_complexity(self, content: str, file_path: str) -> List[RiskFinding]:
        """Analyze Python code complexity."""
        findings = []
        
        try:
            tree = ast.parse(content)
            complexity_metrics = self._calculate_complexity_metrics(tree)
            
            # High cyclomatic complexity
            if complexity_metrics['cyclomatic'] > 10:
                findings.append(RiskFinding(
                    category=RiskCategory.BUSINESS_LOGIC,
                    level=RiskLevel.MEDIUM,
                    description=f"High cyclomatic complexity: {complexity_metrics['cyclomatic']}",
                    location=file_path,
                    line_number=None,
                    mitigation="Refactor complex functions into smaller, testable units",
                    score=min(complexity_metrics['cyclomatic'] / 20, 1.0)
                ))
            
            # Deep nesting
            if complexity_metrics['max_nesting'] > 4:
                findings.append(RiskFinding(
                    category=RiskCategory.BUSINESS_LOGIC,
                    level=RiskLevel.MEDIUM,
                    description=f"Deep nesting level: {complexity_metrics['max_nesting']}",
                    location=file_path,
                    line_number=None,
                    mitigation="Reduce nesting with early returns and guard clauses",
                    score=min(complexity_metrics['max_nesting'] / 8, 1.0)
                ))
            
            # Too many functions/classes
            if complexity_metrics['function_count'] > 20:
                findings.append(RiskFinding(
                    category=RiskCategory.BUSINESS_LOGIC,
                    level=RiskLevel.LOW,
                    description=f"High function count: {complexity_metrics['function_count']}",
                    location=file_path,
                    line_number=None,
                    mitigation="Consider splitting into multiple modules",
                    score=0.3
                ))
                
        except SyntaxError as e:
            findings.append(RiskFinding(
                category=RiskCategory.BUSINESS_LOGIC,
                level=RiskLevel.CRITICAL,
                description=f"Syntax error in code: {e}",
                location=file_path,
                line_number=getattr(e, 'lineno', None),
                mitigation="Fix syntax errors",
                score=1.0
            ))
        
        return findings
    
    def _calculate_complexity_metrics(self, tree: ast.AST) -> Dict[str, int]:
        """Calculate various complexity metrics from AST."""
        metrics = {
            'cyclomatic': 1,  # Base complexity
            'max_nesting': 0,
            'function_count': 0,
            'class_count': 0,
            'async_function_count': 0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try)):
                metrics['cyclomatic'] += 1
            elif isinstance(node, ast.FunctionDef):
                metrics['function_count'] += 1
            elif isinstance(node, ast.AsyncFunctionDef):
                metrics['async_function_count'] += 1
            elif isinstance(node, ast.ClassDef):
                metrics['class_count'] += 1
        
        # Calculate nesting (simplified)
        metrics['max_nesting'] = self._calculate_max_nesting(tree)
        
        return metrics
    
    def _calculate_max_nesting(self, tree: ast.AST) -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0
        
        def calculate_depth(node: ast.AST, current_depth: int = 0) -> int:
            nonlocal max_depth
            max_depth = max(max_depth, current_depth)
            
            depth_increasing_nodes = (ast.If, ast.While, ast.For, ast.Try, ast.With,
                                    ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            
            for child in ast.iter_child_nodes(node):
                if isinstance(child, depth_increasing_nodes):
                    calculate_depth(child, current_depth + 1)
                else:
                    calculate_depth(child, current_depth)
            
            return max_depth
        
        return calculate_depth(tree)


class BusinessImpactAnalyzer:
    """Analyzes business impact of code changes."""
    
    def __init__(self):
        self.critical_modules = {
            'financial_calculations',
            'grant_matching',
            'eligibility_checking',
            'payment_processing',
            'audit_logging',
            'compliance_reporting'
        }
        
        self.high_impact_patterns = [
            r'calculate.*amount',
            r'process.*payment',
            r'validate.*eligibility',
            r'grant.*matching',
            r'audit.*log',
            r'compliance.*check'
        ]
    
    def analyze_business_impact(self, content: str, file_path: str) -> List[RiskFinding]:
        """Analyze business impact of code changes."""
        findings = []
        
        # Check if file is in critical module
        file_path_lower = file_path.lower()
        for critical_module in self.critical_modules:
            if critical_module.replace('_', '') in file_path_lower.replace('_', '').replace('/', ''):
                findings.append(RiskFinding(
                    category=RiskCategory.BUSINESS_LOGIC,
                    level=RiskLevel.HIGH,
                    description=f"Changes in critical business module: {critical_module}",
                    location=file_path,
                    line_number=None,
                    mitigation="Require additional testing and code review",
                    score=0.8
                ))
                break
        
        # Check for high-impact patterns
        content_lower = content.lower()
        for pattern in self.high_impact_patterns:
            if re.search(pattern, content_lower):
                findings.append(RiskFinding(
                    category=RiskCategory.BUSINESS_LOGIC,
                    level=RiskLevel.MEDIUM,
                    description=f"High-impact business logic pattern detected",
                    location=file_path,
                    line_number=None,
                    mitigation="Ensure comprehensive test coverage",
                    score=0.6
                ))
        
        # Grants-specific business logic checks
        findings.extend(self._analyze_grants_business_logic(content, file_path))
        
        return findings
    
    def _analyze_grants_business_logic(self, content: str, file_path: str) -> List[RiskFinding]:
        """Analyze grants-specific business logic risks."""
        findings = []
        
        # Check for calculation logic
        calculation_patterns = [
            r'award_amount\s*[=+\-*/%]',
            r'eligibility\s*=\s*.*calculate',
            r'score\s*[=+\-*/%]',
            r'match\s*=\s*.*calculate'
        ]
        
        for pattern in calculation_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                findings.append(RiskFinding(
                    category=RiskCategory.BUSINESS_LOGIC,
                    level=RiskLevel.HIGH,
                    description="Critical grants calculation logic detected",
                    location=file_path,
                    line_number=None,
                    mitigation="Implement comprehensive calculation tests and validation",
                    score=0.9
                ))
        
        return findings


class RiskAnalyzer:
    """Main risk analysis engine."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.security_detector = SecurityPatternDetector()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.business_analyzer = BusinessImpactAnalyzer()
        
        # Risk scoring weights
        self.weights = {
            'security': config.get('security_weight', 0.4),
            'complexity': config.get('complexity_weight', 0.2),
            'business_impact': config.get('business_impact_weight', 0.4)
        }
    
    async def analyze_change(self, change_event) -> RiskAssessment:
        """Analyze a code change event for risk factors."""
        logger.info(f"Analyzing risk for {change_event.file_path}")
        
        file_path = Path(change_event.file_path)
        
        # Read file content
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return self._create_error_assessment(change_event, str(e))
        
        # Collect all findings
        all_findings = []
        
        # Security analysis
        security_findings = self.security_detector.scan_content(content, str(file_path))
        all_findings.extend(security_findings)
        
        # Complexity analysis
        if file_path.suffix == '.py':
            complexity_findings = self.complexity_analyzer.analyze_python_complexity(content, str(file_path))
            all_findings.extend(complexity_findings)
        
        # Business impact analysis
        business_findings = self.business_analyzer.analyze_business_impact(content, str(file_path))
        all_findings.extend(business_findings)
        
        # Calculate scores
        security_score = self._calculate_category_score(security_findings, RiskCategory.SECURITY)
        complexity_score = change_event.complexity_score / 10  # Normalize to 0-1
        business_score = self._calculate_category_score(business_findings, RiskCategory.BUSINESS_LOGIC)
        grants_specific_score = self._calculate_grants_specific_score(all_findings)
        
        # Overall risk score
        overall_score = (
            security_score * self.weights['security'] +
            complexity_score * self.weights['complexity'] +
            business_score * self.weights['business_impact']
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_findings, risk_level)
        
        return RiskAssessment(
            file_path=str(file_path),
            overall_score=overall_score,
            level=risk_level,
            findings=all_findings,
            business_impact_score=business_score,
            security_score=security_score,
            complexity_score=complexity_score,
            grants_specific_score=grants_specific_score,
            timestamp=datetime.now(),
            recommendations=recommendations
        )
    
    def _calculate_category_score(self, findings: List[RiskFinding], category: RiskCategory) -> float:
        """Calculate risk score for a specific category."""
        category_findings = [f for f in findings if f.category == category]
        
        if not category_findings:
            return 0.0
        
        # Weight findings by severity
        weighted_scores = []
        for finding in category_findings:
            weight = 1.0
            if finding.level == RiskLevel.CRITICAL:
                weight = 4.0
            elif finding.level == RiskLevel.HIGH:
                weight = 3.0
            elif finding.level == RiskLevel.MEDIUM:
                weight = 2.0
            elif finding.level == RiskLevel.LOW:
                weight = 1.0
            
            weighted_scores.append(finding.score * weight)
        
        # Average weighted score, capped at 1.0
        return min(sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.0, 1.0)
    
    def _calculate_grants_specific_score(self, findings: List[RiskFinding]) -> float:
        """Calculate grants-specific risk score."""
        grants_findings = [
            f for f in findings 
            if any(keyword in f.description.lower() 
                  for keyword in ['grant', 'financial', 'calculation', 'eligibility'])
        ]
        
        if not grants_findings:
            return 0.0
        
        return min(sum(f.score for f in grants_findings) / len(grants_findings), 1.0)
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level based on overall score."""
        if score >= 0.8:
            return RiskLevel.CRITICAL
        elif score >= 0.6:
            return RiskLevel.HIGH
        elif score >= 0.4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_recommendations(self, findings: List[RiskFinding], risk_level: RiskLevel) -> List[str]:
        """Generate recommendations based on findings."""
        recommendations = []
        
        # General recommendations based on risk level
        if risk_level == RiskLevel.CRITICAL:
            recommendations.append("URGENT: Manual code review required before deployment")
            recommendations.append("Implement comprehensive integration tests")
            recommendations.append("Consider security audit")
        elif risk_level == RiskLevel.HIGH:
            recommendations.append("Require peer review and additional testing")
            recommendations.append("Run full test suite before merging")
        
        # Specific recommendations based on findings
        security_findings = [f for f in findings if f.category == RiskCategory.SECURITY]
        if security_findings:
            recommendations.append("Address security vulnerabilities immediately")
            recommendations.append("Run security scanning tools")
        
        complexity_findings = [f for f in findings if f.category == RiskCategory.BUSINESS_LOGIC]
        if len(complexity_findings) > 3:
            recommendations.append("Consider refactoring to reduce complexity")
        
        # Grants-specific recommendations
        grants_findings = [
            f for f in findings 
            if 'grant' in f.description.lower() or 'financial' in f.description.lower()
        ]
        if grants_findings:
            recommendations.append("Validate all financial calculations")
            recommendations.append("Ensure compliance with grants regulations")
            recommendations.append("Test edge cases for grant eligibility")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _create_error_assessment(self, change_event, error_msg: str) -> RiskAssessment:
        """Create an error assessment when file analysis fails."""
        return RiskAssessment(
            file_path=change_event.file_path,
            overall_score=0.5,  # Medium risk for errors
            level=RiskLevel.MEDIUM,
            findings=[RiskFinding(
                category=RiskCategory.BUSINESS_LOGIC,
                level=RiskLevel.MEDIUM,
                description=f"Analysis error: {error_msg}",
                location=change_event.file_path,
                line_number=None,
                mitigation="Manual review required",
                score=0.5
            )],
            business_impact_score=0.5,
            security_score=0.0,
            complexity_score=0.5,
            grants_specific_score=0.0,
            timestamp=datetime.now(),
            recommendations=["Manual code review required due to analysis error"]
        )