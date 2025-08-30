"""
Compliance Checker Framework for Grants MCP

This module implements comprehensive compliance checking for data protection,
API security, financial regulations, and grants-specific requirements.
"""

import re
import ast
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ComplianceCategory(Enum):
    """Compliance category types."""
    DATA_PRIVACY = "data_privacy"
    API_SECURITY = "api_security"
    FINANCIAL_REGULATIONS = "financial_regulations"
    GRANTS_COMPLIANCE = "grants_compliance"
    AUDIT_REQUIREMENTS = "audit_requirements"
    ACCESSIBILITY = "accessibility"


class ComplianceLevel(Enum):
    """Compliance violation severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ComplianceViolation:
    """Individual compliance violation."""
    category: ComplianceCategory
    level: ComplianceLevel
    rule_id: str
    description: str
    location: str
    line_number: Optional[int]
    remediation: str
    regulation_reference: Optional[str]
    automated_fix_available: bool


@dataclass
class ComplianceReport:
    """Complete compliance report for a file or change."""
    file_path: str
    is_compliant: bool
    overall_score: float
    violations: List[ComplianceViolation]
    categories_checked: List[ComplianceCategory]
    timestamp: datetime
    recommendations: List[str]
    compliance_summary: Dict[ComplianceCategory, bool]


class DataPrivacyChecker:
    """Checks for data privacy and PII handling compliance."""
    
    def __init__(self):
        # PII patterns
        self.pii_patterns = {
            'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}-?\d{3}-?\d{4}\b',
            'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            'bank_account': r'\b\d{8,17}\b'
        }
        
        # PII handling keywords
        self.pii_keywords = {
            'personal_info', 'social_security', 'taxpayer_id', 'bank_account',
            'credit_card', 'passport', 'driver_license', 'birth_date',
            'full_name', 'home_address', 'phone_number', 'email_address'
        }
        
        # Required encryption patterns
        self.encryption_patterns = [
            r'encrypt\s*\(',
            r'cipher\.',
            r'hash\s*\(',
            r'bcrypt\.',
            r'scrypt\.',
            r'pbkdf2\.'
        ]
    
    def check_compliance(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check data privacy compliance."""
        violations = []
        
        # Check for PII exposure
        violations.extend(self._check_pii_exposure(content, file_path))
        
        # Check for proper encryption
        violations.extend(self._check_encryption_usage(content, file_path))
        
        # Check for GDPR compliance patterns
        violations.extend(self._check_gdpr_compliance(content, file_path))
        
        # Check for data retention policies
        violations.extend(self._check_data_retention(content, file_path))
        
        return violations
    
    def _check_pii_exposure(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check for PII exposure in code."""
        violations = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('#') or line.strip().startswith('//'):
                continue
            
            # Check for PII patterns in strings
            for pii_type, pattern in self.pii_patterns.items():
                if re.search(pattern, line):
                    violations.append(ComplianceViolation(
                        category=ComplianceCategory.DATA_PRIVACY,
                        level=ComplianceLevel.CRITICAL,
                        rule_id="PII-001",
                        description=f"Potential {pii_type.upper()} exposed in code",
                        location=f"{file_path}:{i}",
                        line_number=i,
                        remediation="Remove PII from code and use proper data handling",
                        regulation_reference="GDPR Art. 5, CCPA Sec. 1798.100",
                        automated_fix_available=False
                    ))
            
            # Check for PII keywords without proper handling
            line_lower = line.lower()
            for keyword in self.pii_keywords:
                if keyword in line_lower and not any(enc in line_lower for enc in ['encrypt', 'hash', 'mask']):
                    violations.append(ComplianceViolation(
                        category=ComplianceCategory.DATA_PRIVACY,
                        level=ComplianceLevel.HIGH,
                        rule_id="PII-002",
                        description=f"PII keyword '{keyword}' without proper protection",
                        location=f"{file_path}:{i}",
                        line_number=i,
                        remediation="Implement encryption or masking for PII data",
                        regulation_reference="GDPR Art. 32",
                        automated_fix_available=False
                    ))
        
        return violations
    
    def _check_encryption_usage(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check for proper encryption usage."""
        violations = []
        lines = content.split('\n')
        
        has_sensitive_data = any(keyword in content.lower() for keyword in self.pii_keywords)
        has_encryption = any(re.search(pattern, content, re.IGNORECASE) for pattern in self.encryption_patterns)
        
        if has_sensitive_data and not has_encryption:
            violations.append(ComplianceViolation(
                category=ComplianceCategory.DATA_PRIVACY,
                level=ComplianceLevel.HIGH,
                rule_id="ENC-001",
                description="Sensitive data handling without encryption",
                location=file_path,
                line_number=None,
                remediation="Implement encryption for sensitive data storage and transmission",
                regulation_reference="GDPR Art. 32, CCPA Sec. 1798.81.5",
                automated_fix_available=False
            ))
        
        # Check for weak encryption
        weak_patterns = [r'md5\s*\(', r'sha1\s*\(', r'base64\s*\.']
        for i, line in enumerate(lines, 1):
            for pattern in weak_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(ComplianceViolation(
                        category=ComplianceCategory.DATA_PRIVACY,
                        level=ComplianceLevel.MEDIUM,
                        rule_id="ENC-002",
                        description="Weak encryption algorithm detected",
                        location=f"{file_path}:{i}",
                        line_number=i,
                        remediation="Use strong encryption algorithms (AES-256, SHA-256+)",
                        regulation_reference="NIST SP 800-57",
                        automated_fix_available=True
                    ))
        
        return violations
    
    def _check_gdpr_compliance(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check for GDPR compliance patterns."""
        violations = []
        
        # Check for data processing without consent mechanisms
        has_data_processing = any(term in content.lower() for term in 
                                ['user_data', 'personal_info', 'process_data', 'store_data'])
        has_consent_check = any(term in content.lower() for term in 
                              ['consent', 'opt_in', 'permission', 'agree'])
        
        if has_data_processing and not has_consent_check:
            violations.append(ComplianceViolation(
                category=ComplianceCategory.DATA_PRIVACY,
                level=ComplianceLevel.HIGH,
                rule_id="GDPR-001",
                description="Data processing without consent mechanisms",
                location=file_path,
                line_number=None,
                remediation="Implement consent collection and validation",
                regulation_reference="GDPR Art. 6, Art. 7",
                automated_fix_available=False
            ))
        
        return violations
    
    def _check_data_retention(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check for data retention policy implementation."""
        violations = []
        
        # Check for data deletion mechanisms
        has_data_storage = any(term in content.lower() for term in 
                             ['save_data', 'store_data', 'persist', 'database'])
        has_deletion = any(term in content.lower() for term in 
                         ['delete', 'remove', 'purge', 'cleanup'])
        
        if has_data_storage and not has_deletion:
            violations.append(ComplianceViolation(
                category=ComplianceCategory.DATA_PRIVACY,
                level=ComplianceLevel.MEDIUM,
                rule_id="RET-001",
                description="Data storage without retention/deletion policy",
                location=file_path,
                line_number=None,
                remediation="Implement data retention and deletion mechanisms",
                regulation_reference="GDPR Art. 17 (Right to erasure)",
                automated_fix_available=False
            ))
        
        return violations


class APISecurityChecker:
    """Checks for API security compliance."""
    
    def __init__(self):
        self.security_headers = {
            'authorization', 'x-api-key', 'x-auth-token', 'bearer',
            'x-csrf-token', 'x-requested-with'
        }
        
        self.rate_limiting_patterns = [
            r'rate_limit', r'throttle', r'limit_per', r'requests_per'
        ]
        
        self.input_validation_patterns = [
            r'validate\s*\(', r'sanitize\s*\(', r'clean\s*\(',
            r'check_input', r'verify_input'
        ]
    
    def check_compliance(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check API security compliance."""
        violations = []
        
        # Check for authentication
        violations.extend(self._check_authentication(content, file_path))
        
        # Check for rate limiting
        violations.extend(self._check_rate_limiting(content, file_path))
        
        # Check for input validation
        violations.extend(self._check_input_validation(content, file_path))
        
        # Check for CORS configuration
        violations.extend(self._check_cors_config(content, file_path))
        
        return violations
    
    def _check_authentication(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check for proper API authentication."""
        violations = []
        
        # Check if this looks like an API endpoint
        is_api_file = any(term in content.lower() for term in 
                         ['@app.route', 'fastapi', 'request', 'response', 'endpoint'])
        
        if is_api_file:
            has_auth = any(header in content.lower() for header in self.security_headers)
            
            if not has_auth:
                violations.append(ComplianceViolation(
                    category=ComplianceCategory.API_SECURITY,
                    level=ComplianceLevel.HIGH,
                    rule_id="AUTH-001",
                    description="API endpoint without authentication mechanism",
                    location=file_path,
                    line_number=None,
                    remediation="Implement API authentication (API key, JWT, OAuth)",
                    regulation_reference="OWASP API Security Top 10 - A2",
                    automated_fix_available=False
                ))
        
        return violations
    
    def _check_rate_limiting(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check for rate limiting implementation."""
        violations = []
        
        is_api_file = any(term in content.lower() for term in 
                         ['@app.route', 'fastapi', 'request', 'response'])
        
        if is_api_file:
            has_rate_limiting = any(re.search(pattern, content, re.IGNORECASE) 
                                  for pattern in self.rate_limiting_patterns)
            
            if not has_rate_limiting:
                violations.append(ComplianceViolation(
                    category=ComplianceCategory.API_SECURITY,
                    level=ComplianceLevel.MEDIUM,
                    rule_id="RATE-001",
                    description="API endpoint without rate limiting",
                    location=file_path,
                    line_number=None,
                    remediation="Implement rate limiting to prevent abuse",
                    regulation_reference="OWASP API Security Top 10 - A4",
                    automated_fix_available=False
                ))
        
        return violations
    
    def _check_input_validation(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check for input validation."""
        violations = []
        
        has_user_input = any(term in content.lower() for term in 
                           ['request.', 'input', 'form_data', 'json_data'])
        has_validation = any(re.search(pattern, content, re.IGNORECASE) 
                           for pattern in self.input_validation_patterns)
        
        if has_user_input and not has_validation:
            violations.append(ComplianceViolation(
                category=ComplianceCategory.API_SECURITY,
                level=ComplianceLevel.HIGH,
                rule_id="VAL-001",
                description="User input without validation",
                location=file_path,
                line_number=None,
                remediation="Implement input validation and sanitization",
                regulation_reference="OWASP API Security Top 10 - A3",
                automated_fix_available=False
            ))
        
        return violations
    
    def _check_cors_config(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check for CORS configuration."""
        violations = []
        
        has_cors_wildcard = '*' in content and 'cors' in content.lower()
        
        if has_cors_wildcard:
            violations.append(ComplianceViolation(
                category=ComplianceCategory.API_SECURITY,
                level=ComplianceLevel.MEDIUM,
                rule_id="CORS-001",
                description="Overly permissive CORS configuration",
                location=file_path,
                line_number=None,
                remediation="Configure CORS with specific allowed origins",
                regulation_reference="OWASP CORS Security Cheat Sheet",
                automated_fix_available=False
            ))
        
        return violations


class GrantsComplianceChecker:
    """Checks for grants-specific compliance requirements."""
    
    def __init__(self):
        self.financial_keywords = {
            'award_amount', 'grant_amount', 'funding_amount', 'payment',
            'disbursement', 'allocation', 'budget', 'expenditure'
        }
        
        self.audit_keywords = {
            'audit_log', 'transaction_log', 'activity_log', 'change_log',
            'access_log', 'modification_history'
        }
        
        self.eligibility_keywords = {
            'eligibility', 'qualification', 'criteria', 'requirements',
            'eligible_applicant', 'qualified_entity'
        }
    
    def check_compliance(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check grants-specific compliance."""
        violations = []
        
        # Check for financial calculation accuracy
        violations.extend(self._check_financial_calculations(content, file_path))
        
        # Check for audit trail requirements
        violations.extend(self._check_audit_trail(content, file_path))
        
        # Check for eligibility verification
        violations.extend(self._check_eligibility_verification(content, file_path))
        
        # Check for transparency requirements
        violations.extend(self._check_transparency_requirements(content, file_path))
        
        return violations
    
    def _check_financial_calculations(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check financial calculation compliance."""
        violations = []
        
        has_financial_calc = any(keyword in content.lower() for keyword in self.financial_keywords)
        
        if has_financial_calc:
            # Check for rounding precision
            has_rounding = any(term in content.lower() for term in ['round(', 'decimal', 'precision'])
            if not has_rounding:
                violations.append(ComplianceViolation(
                    category=ComplianceCategory.FINANCIAL_REGULATIONS,
                    level=ComplianceLevel.HIGH,
                    rule_id="FIN-001",
                    description="Financial calculations without precision handling",
                    location=file_path,
                    line_number=None,
                    remediation="Use Decimal type or specify rounding precision",
                    regulation_reference="OMB Circular A-133",
                    automated_fix_available=True
                ))
            
            # Check for validation
            has_validation = any(term in content.lower() for term in ['validate', 'verify', 'check'])
            if not has_validation:
                violations.append(ComplianceViolation(
                    category=ComplianceCategory.FINANCIAL_REGULATIONS,
                    level=ComplianceLevel.MEDIUM,
                    rule_id="FIN-002",
                    description="Financial calculations without validation",
                    location=file_path,
                    line_number=None,
                    remediation="Add validation for financial calculation results",
                    regulation_reference="CFR Title 2",
                    automated_fix_available=False
                ))
        
        return violations
    
    def _check_audit_trail(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check audit trail requirements."""
        violations = []
        
        # Check if this file modifies data
        has_data_modification = any(term in content.lower() for term in 
                                  ['insert', 'update', 'delete', 'modify', 'save', 'create'])
        
        if has_data_modification:
            has_logging = any(keyword in content.lower() for keyword in self.audit_keywords)
            has_log_calls = any(term in content.lower() for term in ['log.', 'logger.', 'audit('])
            
            if not (has_logging or has_log_calls):
                violations.append(ComplianceViolation(
                    category=ComplianceCategory.AUDIT_REQUIREMENTS,
                    level=ComplianceLevel.HIGH,
                    rule_id="AUD-001",
                    description="Data modification without audit logging",
                    location=file_path,
                    line_number=None,
                    remediation="Implement comprehensive audit logging",
                    regulation_reference="OMB A-123, CFR 200.303",
                    automated_fix_available=False
                ))
        
        return violations
    
    def _check_eligibility_verification(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check eligibility verification compliance."""
        violations = []
        
        has_eligibility = any(keyword in content.lower() for keyword in self.eligibility_keywords)
        
        if has_eligibility:
            # Check for proper verification steps
            has_verification = any(term in content.lower() for term in 
                                 ['verify', 'validate', 'confirm', 'check'])
            
            if not has_verification:
                violations.append(ComplianceViolation(
                    category=ComplianceCategory.GRANTS_COMPLIANCE,
                    level=ComplianceLevel.HIGH,
                    rule_id="ELIG-001",
                    description="Eligibility determination without verification",
                    location=file_path,
                    line_number=None,
                    remediation="Implement eligibility verification process",
                    regulation_reference="CFR 200.205",
                    automated_fix_available=False
                ))
        
        return violations
    
    def _check_transparency_requirements(self, content: str, file_path: str) -> List[ComplianceViolation]:
        """Check transparency and reporting requirements."""
        violations = []
        
        # Check for public data handling
        has_public_data = any(term in content.lower() for term in 
                            ['public', 'transparency', 'disclosure', 'report'])
        
        if has_public_data:
            # Should have data sanitization
            has_sanitization = any(term in content.lower() for term in 
                                 ['sanitize', 'clean', 'redact', 'anonymize'])
            
            if not has_sanitization:
                violations.append(ComplianceViolation(
                    category=ComplianceCategory.GRANTS_COMPLIANCE,
                    level=ComplianceLevel.MEDIUM,
                    rule_id="TRANS-001",
                    description="Public data handling without sanitization",
                    location=file_path,
                    line_number=None,
                    remediation="Implement data sanitization for public disclosure",
                    regulation_reference="FOIA, Sunshine Act",
                    automated_fix_available=False
                ))
        
        return violations


class ComplianceChecker:
    """Main compliance checker orchestrator."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize checkers
        self.data_privacy_checker = DataPrivacyChecker()
        self.api_security_checker = APISecurityChecker()
        self.grants_checker = GrantsComplianceChecker()
        
        # Enabled checks
        self.enabled_categories = set(config.get('enabled_categories', [
            ComplianceCategory.DATA_PRIVACY,
            ComplianceCategory.API_SECURITY,
            ComplianceCategory.FINANCIAL_REGULATIONS,
            ComplianceCategory.GRANTS_COMPLIANCE,
            ComplianceCategory.AUDIT_REQUIREMENTS
        ]))
    
    async def check_file(self, file_path: Path) -> ComplianceReport:
        """Check compliance for a single file."""
        logger.info(f"Checking compliance for {file_path}")
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return self._create_error_report(file_path, str(e))
        
        all_violations = []
        categories_checked = []
        
        # Data privacy checks
        if ComplianceCategory.DATA_PRIVACY in self.enabled_categories:
            privacy_violations = self.data_privacy_checker.check_compliance(content, str(file_path))
            all_violations.extend(privacy_violations)
            categories_checked.append(ComplianceCategory.DATA_PRIVACY)
        
        # API security checks
        if ComplianceCategory.API_SECURITY in self.enabled_categories:
            api_violations = self.api_security_checker.check_compliance(content, str(file_path))
            all_violations.extend(api_violations)
            categories_checked.append(ComplianceCategory.API_SECURITY)
        
        # Grants-specific checks
        if any(cat in self.enabled_categories for cat in [
            ComplianceCategory.FINANCIAL_REGULATIONS,
            ComplianceCategory.GRANTS_COMPLIANCE,
            ComplianceCategory.AUDIT_REQUIREMENTS
        ]):
            grants_violations = self.grants_checker.check_compliance(content, str(file_path))
            all_violations.extend(grants_violations)
            categories_checked.extend([
                ComplianceCategory.FINANCIAL_REGULATIONS,
                ComplianceCategory.GRANTS_COMPLIANCE,
                ComplianceCategory.AUDIT_REQUIREMENTS
            ])
        
        # Calculate compliance score
        overall_score = self._calculate_compliance_score(all_violations)
        is_compliant = overall_score >= 0.8 and not any(
            v.level == ComplianceLevel.CRITICAL for v in all_violations
        )
        
        # Generate compliance summary
        compliance_summary = self._generate_compliance_summary(all_violations, categories_checked)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_violations)
        
        return ComplianceReport(
            file_path=str(file_path),
            is_compliant=is_compliant,
            overall_score=overall_score,
            violations=all_violations,
            categories_checked=categories_checked,
            timestamp=datetime.now(),
            recommendations=recommendations,
            compliance_summary=compliance_summary
        )
    
    def _calculate_compliance_score(self, violations: List[ComplianceViolation]) -> float:
        """Calculate overall compliance score (0-1)."""
        if not violations:
            return 1.0
        
        # Penalty weights by severity
        penalties = {
            ComplianceLevel.CRITICAL: 0.4,
            ComplianceLevel.HIGH: 0.2,
            ComplianceLevel.MEDIUM: 0.1,
            ComplianceLevel.LOW: 0.05,
            ComplianceLevel.INFO: 0.01
        }
        
        total_penalty = sum(penalties.get(v.level, 0.1) for v in violations)
        
        # Score is 1.0 minus penalties, with minimum of 0.0
        return max(0.0, 1.0 - min(total_penalty, 1.0))
    
    def _generate_compliance_summary(
        self, 
        violations: List[ComplianceViolation], 
        categories: List[ComplianceCategory]
    ) -> Dict[ComplianceCategory, bool]:
        """Generate per-category compliance status."""
        summary = {}
        
        for category in categories:
            category_violations = [v for v in violations if v.category == category]
            critical_violations = [v for v in category_violations if v.level == ComplianceLevel.CRITICAL]
            
            # Category is compliant if no critical violations
            summary[category] = len(critical_violations) == 0
        
        return summary
    
    def _generate_recommendations(self, violations: List[ComplianceViolation]) -> List[str]:
        """Generate compliance recommendations."""
        recommendations = []
        
        # Priority recommendations for critical violations
        critical_violations = [v for v in violations if v.level == ComplianceLevel.CRITICAL]
        if critical_violations:
            recommendations.append("URGENT: Address critical compliance violations immediately")
            recommendations.append("Consider blocking deployment until critical issues are resolved")
        
        # Category-specific recommendations
        categories_with_violations = set(v.category for v in violations)
        
        if ComplianceCategory.DATA_PRIVACY in categories_with_violations:
            recommendations.append("Review data privacy practices and PII handling")
            recommendations.append("Conduct privacy impact assessment")
        
        if ComplianceCategory.API_SECURITY in categories_with_violations:
            recommendations.append("Enhance API security measures")
            recommendations.append("Review authentication and authorization mechanisms")
        
        if ComplianceCategory.FINANCIAL_REGULATIONS in categories_with_violations:
            recommendations.append("Validate financial calculation accuracy")
            recommendations.append("Implement financial controls and audit trails")
        
        if ComplianceCategory.GRANTS_COMPLIANCE in categories_with_violations:
            recommendations.append("Review grants-specific compliance requirements")
            recommendations.append("Ensure proper eligibility verification processes")
        
        # Automated fix recommendations
        auto_fixable = [v for v in violations if v.automated_fix_available]
        if auto_fixable:
            recommendations.append(f"{len(auto_fixable)} violations can be automatically fixed")
        
        return recommendations
    
    def _create_error_report(self, file_path: Path, error_msg: str) -> ComplianceReport:
        """Create error report when file analysis fails."""
        return ComplianceReport(
            file_path=str(file_path),
            is_compliant=False,
            overall_score=0.0,
            violations=[ComplianceViolation(
                category=ComplianceCategory.DATA_PRIVACY,
                level=ComplianceLevel.HIGH,
                rule_id="ERR-001",
                description=f"Compliance check failed: {error_msg}",
                location=str(file_path),
                line_number=None,
                remediation="Manual compliance review required",
                regulation_reference=None,
                automated_fix_available=False
            )],
            categories_checked=[],
            timestamp=datetime.now(),
            recommendations=["Manual compliance review required due to analysis error"],
            compliance_summary={}
        )