"""
Audit Trail Management Module

Provides comprehensive audit logging and trail management for
testing activities, compliance checks, and quality metrics.
"""

from .trail_manager import AuditTrailManager, AuditEventType

__all__ = ["AuditTrailManager", "AuditEventType"]