"""
Configuration management for the Adaptive Testing Framework.

This module provides configuration classes and utilities for managing
testing framework settings, thresholds, and behavioral parameters.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum


class TestingMode(Enum):
    """Testing operation modes."""
    DEVELOPMENT = "development"
    CI_CD = "ci_cd"
    PRODUCTION_MONITORING = "production_monitoring"
    AUDIT = "audit"


class RiskTolerance(Enum):
    """Risk tolerance levels."""
    STRICT = "strict"          # Fail on any medium+ risk
    MODERATE = "moderate"      # Fail on high+ risk
    PERMISSIVE = "permissive"  # Fail only on critical risk


@dataclass
class QualityThresholds:
    """Quality gate thresholds."""
    test_coverage_percentage: float = 70.0
    risk_score_max: float = 0.7
    compliance_score_min: float = 0.8
    complexity_score_max: float = 8.0
    bug_density_max: float = 0.1
    performance_degradation_max: float = 0.2


@dataclass
class TestGenerationConfig:
    """Test generation configuration."""
    max_tests_per_file: int = 15
    max_test_depth: int = 3
    enable_performance_tests: bool = True
    enable_integration_tests: bool = True
    enable_compliance_tests: bool = True
    enable_security_tests: bool = True
    parallel_generation: bool = True
    generation_timeout_seconds: int = 300


@dataclass
class RiskAnalysisConfig:
    """Risk analysis configuration."""
    security_weight: float = 0.4
    complexity_weight: float = 0.2
    business_impact_weight: float = 0.4
    enable_static_analysis: bool = True
    enable_dependency_scanning: bool = True
    enable_secrets_detection: bool = True
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE


@dataclass
class ComplianceConfig:
    """Compliance checking configuration."""
    enabled_categories: List[str] = field(default_factory=lambda: [
        "DATA_PRIVACY",
        "API_SECURITY", 
        "FINANCIAL_REGULATIONS",
        "GRANTS_COMPLIANCE",
        "AUDIT_REQUIREMENTS"
    ])
    strict_mode: bool = True
    auto_fix_enabled: bool = False
    regulatory_frameworks: List[str] = field(default_factory=lambda: [
        "GDPR", "CCPA", "SOX", "HIPAA", "PCI_DSS"
    ])


@dataclass
class MonitoringConfig:
    """Continuous monitoring configuration."""
    monitoring_interval_seconds: int = 30
    file_watch_enabled: bool = True
    real_time_analysis: bool = True
    alert_on_high_risk: bool = True
    alert_on_compliance_violation: bool = True
    metrics_retention_days: int = 90


@dataclass
class AuditConfig:
    """Audit and reporting configuration."""
    enable_audit_trail: bool = True
    detailed_logging: bool = True
    export_format: str = "json"
    retention_period_days: int = 365
    compliance_evidence_collection: bool = True
    performance_metrics_tracking: bool = True


@dataclass
class NotificationConfig:
    """Notification and alerting configuration."""
    slack_webhook_url: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)
    github_comments_enabled: bool = True
    severity_threshold: str = "medium"  # minimum severity to trigger notifications


@dataclass
class AdaptiveTestingConfig:
    """Main configuration class for the Adaptive Testing Framework."""
    
    # Core settings
    project_root: Path = field(default_factory=lambda: Path.cwd())
    testing_mode: TestingMode = TestingMode.DEVELOPMENT
    log_level: str = "INFO"
    
    # Component configurations
    quality_thresholds: QualityThresholds = field(default_factory=QualityThresholds)
    test_generation: TestGenerationConfig = field(default_factory=TestGenerationConfig)
    risk_analysis: RiskAnalysisConfig = field(default_factory=RiskAnalysisConfig)
    compliance: ComplianceConfig = field(default_factory=ComplianceConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    
    # Advanced settings
    parallel_execution: bool = True
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    max_concurrent_jobs: int = 4
    
    # Environment-specific overrides
    environment_overrides: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation and environment loading."""
        self.project_root = Path(self.project_root).resolve()
        self._load_environment_variables()
        self._validate_configuration()
    
    def _load_environment_variables(self):
        """Load configuration from environment variables."""
        env_mappings = {
            'ADAPTIVE_TESTING_MODE': ('testing_mode', lambda x: TestingMode(x.lower())),
            'ADAPTIVE_LOG_LEVEL': ('log_level', str),
            'ADAPTIVE_PARALLEL_EXECUTION': ('parallel_execution', lambda x: x.lower() == 'true'),
            'ADAPTIVE_MAX_TESTS_PER_FILE': ('test_generation.max_tests_per_file', int),
            'ADAPTIVE_RISK_TOLERANCE': ('risk_analysis.risk_tolerance', lambda x: RiskTolerance(x.lower())),
            'ADAPTIVE_COVERAGE_THRESHOLD': ('quality_thresholds.test_coverage_percentage', float),
            'ADAPTIVE_RISK_THRESHOLD': ('quality_thresholds.risk_score_max', float),
            'SLACK_WEBHOOK_URL': ('notifications.slack_webhook_url', str),
            'ADAPTIVE_CACHE_ENABLED': ('cache_enabled', lambda x: x.lower() == 'true'),
        }
        
        for env_var, (config_path, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    converted_value = converter(value)
                    self._set_nested_attribute(config_path, converted_value)
                except (ValueError, TypeError) as e:
                    print(f"Warning: Invalid value for {env_var}: {value} ({e})")
    
    def _set_nested_attribute(self, path: str, value: Any):
        """Set nested attribute using dot notation."""
        parts = path.split('.')
        obj = self
        
        for part in parts[:-1]:
            obj = getattr(obj, part)
        
        setattr(obj, parts[-1], value)
    
    def _validate_configuration(self):
        """Validate configuration values."""
        # Validate thresholds
        if not 0 <= self.quality_thresholds.test_coverage_percentage <= 100:
            raise ValueError("Coverage threshold must be between 0 and 100")
        
        if not 0 <= self.quality_thresholds.risk_score_max <= 1:
            raise ValueError("Risk score threshold must be between 0 and 1")
        
        if not 0 <= self.quality_thresholds.compliance_score_min <= 1:
            raise ValueError("Compliance score threshold must be between 0 and 1")
        
        # Validate paths
        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {self.project_root}")
        
        # Validate test generation limits
        if self.test_generation.max_tests_per_file < 1:
            raise ValueError("Max tests per file must be at least 1")
        
        if self.test_generation.generation_timeout_seconds < 10:
            raise ValueError("Generation timeout must be at least 10 seconds")
    
    def get_grants_specific_config(self) -> Dict[str, Any]:
        """Get grants-specific configuration overrides."""
        return {
            'business_critical_patterns': [
                'calculate.*amount', 'validate.*eligibility', 'process.*grant',
                'award.*calculation', 'compliance.*check', 'audit.*log'
            ],
            'financial_validation_rules': [
                'precision_requirements', 'rounding_rules', 'currency_handling'
            ],
            'regulatory_compliance': [
                'CFR_200', 'OMB_Guidelines', 'Grant_Regulations'
            ],
            'data_privacy_requirements': [
                'PII_protection', 'financial_data_encryption', 'audit_trails'
            ],
            'api_security_standards': [
                'authentication_required', 'rate_limiting', 'input_validation'
            ]
        }
    
    def to_orchestrator_config(self) -> Dict[str, Any]:
        """Convert to orchestrator configuration format."""
        return {
            "monitoring_interval": self.monitoring.monitoring_interval_seconds,
            "risk_config": {
                "security_weight": self.risk_analysis.security_weight,
                "complexity_weight": self.risk_analysis.complexity_weight,
                "business_impact_weight": self.risk_analysis.business_impact_weight
            },
            "compliance_config": {
                "enabled_categories": self.compliance.enabled_categories,
                "strict_mode": self.compliance.strict_mode,
                "regulatory_frameworks": self.compliance.regulatory_frameworks
            },
            "generation_config": {
                "max_tests_per_file": self.test_generation.max_tests_per_file,
                "test_timeout": self.test_generation.generation_timeout_seconds,
                "parallel_generation": self.test_generation.parallel_generation
            }
        }
    
    def export_config(self, file_path: Path) -> None:
        """Export configuration to file."""
        import json
        
        config_dict = {
            "testing_mode": self.testing_mode.value,
            "log_level": self.log_level,
            "parallel_execution": self.parallel_execution,
            "cache_enabled": self.cache_enabled,
            "quality_thresholds": {
                "test_coverage_percentage": self.quality_thresholds.test_coverage_percentage,
                "risk_score_max": self.quality_thresholds.risk_score_max,
                "compliance_score_min": self.quality_thresholds.compliance_score_min,
                "complexity_score_max": self.quality_thresholds.complexity_score_max,
            },
            "test_generation": {
                "max_tests_per_file": self.test_generation.max_tests_per_file,
                "parallel_generation": self.test_generation.parallel_generation,
                "generation_timeout_seconds": self.test_generation.generation_timeout_seconds,
            },
            "risk_analysis": {
                "security_weight": self.risk_analysis.security_weight,
                "complexity_weight": self.risk_analysis.complexity_weight,
                "business_impact_weight": self.risk_analysis.business_impact_weight,
                "risk_tolerance": self.risk_analysis.risk_tolerance.value,
            },
            "compliance": {
                "enabled_categories": self.compliance.enabled_categories,
                "strict_mode": self.compliance.strict_mode,
                "regulatory_frameworks": self.compliance.regulatory_frameworks,
            },
            "monitoring": {
                "monitoring_interval_seconds": self.monitoring.monitoring_interval_seconds,
                "file_watch_enabled": self.monitoring.file_watch_enabled,
                "real_time_analysis": self.monitoring.real_time_analysis,
            }
        }
        
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: Path) -> 'AdaptiveTestingConfig':
        """Load configuration from file."""
        import json
        
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        
        # Create config with defaults
        config = cls()
        
        # Override with loaded values
        if 'testing_mode' in config_dict:
            config.testing_mode = TestingMode(config_dict['testing_mode'])
        
        if 'log_level' in config_dict:
            config.log_level = config_dict['log_level']
        
        if 'quality_thresholds' in config_dict:
            qt = config_dict['quality_thresholds']
            config.quality_thresholds.test_coverage_percentage = qt.get(
                'test_coverage_percentage', config.quality_thresholds.test_coverage_percentage
            )
            config.quality_thresholds.risk_score_max = qt.get(
                'risk_score_max', config.quality_thresholds.risk_score_max
            )
        
        # Continue for other config sections...
        
        return config


def get_default_config() -> AdaptiveTestingConfig:
    """Get default configuration for the adaptive testing framework."""
    return AdaptiveTestingConfig()


def get_ci_config() -> AdaptiveTestingConfig:
    """Get CI/CD optimized configuration."""
    config = AdaptiveTestingConfig()
    config.testing_mode = TestingMode.CI_CD
    config.test_generation.max_tests_per_file = 10  # Reduced for faster CI
    config.test_generation.generation_timeout_seconds = 180  # Reduced timeout
    config.monitoring.real_time_analysis = False  # Disabled for CI
    config.notifications.github_comments_enabled = True
    return config


def get_production_monitoring_config() -> AdaptiveTestingConfig:
    """Get production monitoring configuration."""
    config = AdaptiveTestingConfig()
    config.testing_mode = TestingMode.PRODUCTION_MONITORING
    config.monitoring.monitoring_interval_seconds = 300  # 5 minutes
    config.risk_analysis.risk_tolerance = RiskTolerance.STRICT
    config.audit.detailed_logging = True
    config.notifications.severity_threshold = "low"
    return config


def get_grants_domain_config() -> AdaptiveTestingConfig:
    """Get grants domain-specific configuration."""
    config = AdaptiveTestingConfig()
    
    # Enhanced compliance for grants domain
    config.compliance.enabled_categories.extend([
        "FINANCIAL_ACCURACY",
        "AUDIT_TRAIL_COMPLETENESS", 
        "GRANTS_REGULATORY_COMPLIANCE"
    ])
    config.compliance.strict_mode = True
    
    # Lower risk tolerance for financial systems
    config.risk_analysis.risk_tolerance = RiskTolerance.STRICT
    config.risk_analysis.business_impact_weight = 0.5  # Higher business impact weight
    
    # Higher quality thresholds
    config.quality_thresholds.test_coverage_percentage = 85.0
    config.quality_thresholds.risk_score_max = 0.5
    config.quality_thresholds.compliance_score_min = 0.9
    
    # Enhanced test generation
    config.test_generation.enable_compliance_tests = True
    config.test_generation.enable_security_tests = True
    config.test_generation.max_tests_per_file = 20  # More thorough testing
    
    return config