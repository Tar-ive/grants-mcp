"""
Adaptive Testing Agents Package

This package contains intelligent agents for automated test generation,
risk assessment, and continuous quality assurance.
"""

from .orchestrator import AdaptiveTestingOrchestrator, create_orchestrator_config

__version__ = "1.0.0"
__all__ = ["AdaptiveTestingOrchestrator", "create_orchestrator_config"]