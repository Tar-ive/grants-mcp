"""
Audit Trail Manager for Adaptive Testing

This module manages comprehensive audit logging for test case generation,
risk assessments, compliance checks, and quality metrics tracking.
"""

import json
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import asyncio
import aiosqlite
from enum import Enum

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    CODE_CHANGE_DETECTED = "code_change_detected"
    RISK_ASSESSMENT = "risk_assessment"
    COMPLIANCE_CHECK = "compliance_check"
    TEST_GENERATION = "test_generation"
    TEST_EXECUTION = "test_execution"
    ERROR_OCCURRED = "error_occurred"
    OPTIMIZATION_COMPLETE = "optimization_complete"
    HIGH_RISK_CHANGE = "high_risk_change"
    COMPLIANCE_VIOLATION = "compliance_violation"
    PERFORMANCE_METRICS = "performance_metrics"
    QUALITY_GATE_CHECK = "quality_gate_check"


@dataclass
class AuditEvent:
    """Individual audit event record."""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    session_id: Optional[str]
    file_path: Optional[str]
    user_id: Optional[str]
    event_data: Dict[str, Any]
    severity: str
    tags: List[str]
    correlation_id: Optional[str]


@dataclass
class QualityMetrics:
    """Quality metrics for audit tracking."""
    test_coverage_percentage: float
    code_complexity_score: float
    security_score: float
    compliance_score: float
    performance_score: float
    bug_density: float
    technical_debt_minutes: int
    maintainability_index: float
    timestamp: datetime


@dataclass
class ComplianceEvidence:
    """Evidence for compliance audit."""
    regulation: str
    requirement: str
    evidence_type: str
    file_path: str
    implementation_details: str
    verification_status: str
    last_verified: datetime
    next_review_date: datetime


class AuditTrailManager:
    """
    Manages comprehensive audit trails for the adaptive testing system.
    
    Provides persistent storage, querying, and reporting capabilities
    for all testing activities, compliance checks, and quality metrics.
    """
    
    def __init__(self, audit_dir: Path):
        """Initialize the audit trail manager."""
        self.audit_dir = audit_dir
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Database paths
        self.db_path = audit_dir / "audit_trail.db"
        self.compliance_db_path = audit_dir / "compliance_evidence.db"
        self.metrics_db_path = audit_dir / "quality_metrics.db"
        
        # JSON log files for backup
        self.json_log_path = audit_dir / "audit_log.jsonl"
        self.session_log_path = audit_dir / "sessions.json"
        
        # Initialize databases
        asyncio.create_task(self._initialize_databases())
        
        logger.info(f"Initialized Audit Trail Manager at {audit_dir}")
    
    async def _initialize_databases(self):
        """Initialize SQLite databases for audit storage."""
        await self._create_audit_tables()
        await self._create_compliance_tables()
        await self._create_metrics_tables()
    
    async def _create_audit_tables(self):
        """Create audit trail tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    file_path TEXT,
                    user_id TEXT,
                    event_data TEXT,
                    severity TEXT,
                    tags TEXT,
                    correlation_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS test_sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    phase TEXT,
                    code_changes_count INTEGER,
                    tests_generated INTEGER,
                    tests_passed INTEGER,
                    tests_failed INTEGER,
                    overall_risk_score REAL,
                    compliance_score REAL,
                    session_data TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS risk_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    file_path TEXT,
                    risk_score REAL,
                    risk_level TEXT,
                    security_score REAL,
                    complexity_score REAL,
                    business_impact_score REAL,
                    findings_count INTEGER,
                    assessment_data TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (session_id) REFERENCES test_sessions (session_id)
                )
            """)
            
            # Create indexes for performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON audit_events(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON audit_events(session_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON audit_events(event_type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_risk_session ON risk_assessments(session_id)")
            
            await db.commit()
    
    async def _create_compliance_tables(self):
        """Create compliance tracking tables."""
        async with aiosqlite.connect(self.compliance_db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS compliance_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    regulation TEXT NOT NULL,
                    requirement TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    file_path TEXT,
                    implementation_details TEXT,
                    verification_status TEXT,
                    last_verified TEXT,
                    next_review_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS compliance_violations (
                    violation_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    file_path TEXT,
                    category TEXT,
                    level TEXT,
                    rule_id TEXT,
                    description TEXT,
                    remediation TEXT,
                    status TEXT DEFAULT 'open',
                    detected_at TEXT,
                    resolved_at TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS compliance_reports (
                    report_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    file_path TEXT,
                    overall_score REAL,
                    is_compliant BOOLEAN,
                    violations_count INTEGER,
                    categories_checked TEXT,
                    report_data TEXT,
                    generated_at TEXT
                )
            """)
            
            await db.commit()
    
    async def _create_metrics_tables(self):
        """Create quality metrics tables."""
        async with aiosqlite.connect(self.metrics_db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    metric_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    test_coverage_percentage REAL,
                    code_complexity_score REAL,
                    security_score REAL,
                    compliance_score REAL,
                    performance_score REAL,
                    bug_density REAL,
                    technical_debt_minutes INTEGER,
                    maintainability_index REAL,
                    timestamp TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS performance_trends (
                    trend_id TEXT PRIMARY KEY,
                    metric_name TEXT,
                    metric_value REAL,
                    session_id TEXT,
                    file_path TEXT,
                    measurement_timestamp TEXT,
                    trend_direction TEXT,
                    baseline_value REAL
                )
            """)
            
            await db.commit()
    
    async def log_event(
        self, 
        event_type: AuditEventType, 
        event_data: Dict[str, Any],
        session_id: Optional[str] = None,
        file_path: Optional[str] = None,
        severity: str = "info",
        tags: Optional[List[str]] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log an audit event."""
        
        event_id = f"{event_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        timestamp = datetime.now(timezone.utc)
        
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            session_id=session_id,
            file_path=file_path,
            user_id=None,  # Could be extracted from environment
            event_data=event_data,
            severity=severity,
            tags=tags or [],
            correlation_id=correlation_id
        )
        
        # Store in database
        await self._store_event(event)
        
        # Also log to JSON file for backup
        await self._append_to_json_log(event)
        
        logger.debug(f"Logged audit event: {event_id} ({event_type.value})")
        return event_id
    
    async def _store_event(self, event: AuditEvent):
        """Store event in SQLite database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO audit_events 
                (event_id, event_type, timestamp, session_id, file_path, user_id, 
                 event_data, severity, tags, correlation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.event_type.value,
                event.timestamp.isoformat(),
                event.session_id,
                event.file_path,
                event.user_id,
                json.dumps(event.event_data, default=str),
                event.severity,
                json.dumps(event.tags),
                event.correlation_id
            ))
            await db.commit()
    
    async def _append_to_json_log(self, event: AuditEvent):
        """Append event to JSON log file."""
        try:
            with open(self.json_log_path, 'a', encoding='utf-8') as f:
                event_dict = asdict(event)
                event_dict['timestamp'] = event.timestamp.isoformat()
                event_dict['event_type'] = event.event_type.value
                f.write(json.dumps(event_dict, default=str) + '\n')
        except Exception as e:
            logger.error(f"Error writing to JSON log: {e}")
    
    async def log_session(self, session) -> None:
        """Log a complete testing session."""
        session_data = {
            "session_id": session.session_id,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "phase": session.phase.value,
            "code_changes": [asdict(change) for change in session.code_changes],
            "generated_tests": session.generated_tests,
            "execution_results": session.execution_results,
            "risk_scores": session.risk_scores,
            "compliance_status": session.compliance_status
        }
        
        # Store session in database
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO test_sessions
                (session_id, start_time, end_time, phase, code_changes_count, 
                 tests_generated, tests_passed, tests_failed, overall_risk_score, 
                 compliance_score, session_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.start_time.isoformat(),
                session.end_time.isoformat() if session.end_time else None,
                session.phase.value,
                len(session.code_changes),
                len(session.generated_tests),
                session.execution_results.get('tests_passed', 0),
                session.execution_results.get('tests_failed', 0),
                sum(session.risk_scores.values()) / len(session.risk_scores) if session.risk_scores else 0.0,
                sum(session.compliance_status.values()) / len(session.compliance_status) if session.compliance_status else 1.0,
                json.dumps(session_data, default=str)
            ))
            await db.commit()
        
        # Log session end event
        await self.log_event(
            AuditEventType.SESSION_END,
            session_data,
            session_id=session.session_id,
            severity="info"
        )
    
    async def log_risk_assessment(self, assessment, session_id: str) -> None:
        """Log a risk assessment."""
        assessment_id = f"risk_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Store in database
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO risk_assessments
                (assessment_id, session_id, file_path, risk_score, risk_level,
                 security_score, complexity_score, business_impact_score, 
                 findings_count, assessment_data, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assessment_id,
                session_id,
                assessment.file_path,
                assessment.overall_score,
                assessment.level.value,
                assessment.security_score,
                assessment.complexity_score,
                assessment.business_impact_score,
                len(assessment.findings),
                json.dumps(asdict(assessment), default=str),
                assessment.timestamp.isoformat()
            ))
            await db.commit()
        
        # Log audit event
        await self.log_event(
            AuditEventType.RISK_ASSESSMENT,
            {
                "assessment_id": assessment_id,
                "file_path": assessment.file_path,
                "risk_score": assessment.overall_score,
                "risk_level": assessment.level.value,
                "findings_count": len(assessment.findings)
            },
            session_id=session_id,
            file_path=assessment.file_path,
            severity="info" if assessment.level.value in ["low", "medium"] else "warning"
        )
    
    async def log_high_risk_change(self, change, risk_assessment) -> None:
        """Log a high-risk code change."""
        await self.log_event(
            AuditEventType.HIGH_RISK_CHANGE,
            {
                "file_path": change.file_path,
                "change_type": change.change_type,
                "complexity_score": change.complexity_score,
                "risk_score": risk_assessment.overall_score,
                "risk_level": risk_assessment.level.value,
                "findings_count": len(risk_assessment.findings),
                "critical_findings": [
                    f.description for f in risk_assessment.findings 
                    if f.level.value in ["critical", "high"]
                ]
            },
            file_path=change.file_path,
            severity="warning",
            tags=["high_risk", "security", "compliance"]
        )
    
    async def log_compliance_report(self, report, session_id: str) -> None:
        """Log a compliance report."""
        report_id = f"compliance_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Store compliance report
        async with aiosqlite.connect(self.compliance_db_path) as db:
            await db.execute("""
                INSERT INTO compliance_reports
                (report_id, session_id, file_path, overall_score, is_compliant,
                 violations_count, categories_checked, report_data, generated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_id,
                session_id,
                report.file_path,
                report.overall_score,
                report.is_compliant,
                len(report.violations),
                json.dumps([cat.value for cat in report.categories_checked]),
                json.dumps(asdict(report), default=str),
                report.timestamp.isoformat()
            ))
            
            # Store individual violations
            for violation in report.violations:
                violation_id = f"viol_{report_id}_{violation.rule_id}_{datetime.now().strftime('%f')}"
                await db.execute("""
                    INSERT INTO compliance_violations
                    (violation_id, session_id, file_path, category, level, 
                     rule_id, description, remediation, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    violation_id,
                    session_id,
                    report.file_path,
                    violation.category.value,
                    violation.level.value,
                    violation.rule_id,
                    violation.description,
                    violation.remediation,
                    datetime.now().isoformat()
                ))
            
            await db.commit()
        
        # Log audit event
        await self.log_event(
            AuditEventType.COMPLIANCE_CHECK,
            {
                "report_id": report_id,
                "file_path": report.file_path,
                "overall_score": report.overall_score,
                "is_compliant": report.is_compliant,
                "violations_count": len(report.violations),
                "critical_violations": [
                    v.description for v in report.violations 
                    if v.level.value == "critical"
                ]
            },
            session_id=session_id,
            file_path=report.file_path,
            severity="error" if not report.is_compliant else "info"
        )
    
    async def log_error(self, error_message: str, session_id: Optional[str] = None) -> None:
        """Log an error event."""
        await self.log_event(
            AuditEventType.ERROR_OCCURRED,
            {
                "error_message": error_message,
                "timestamp": datetime.now().isoformat()
            },
            session_id=session_id,
            severity="error",
            tags=["error", "system"]
        )
    
    async def log_optimization_results(self, optimization_data: Dict[str, Any]) -> None:
        """Log optimization phase results."""
        await self.log_event(
            AuditEventType.OPTIMIZATION_COMPLETE,
            optimization_data,
            session_id=optimization_data.get("session_id"),
            severity="info",
            tags=["optimization", "performance", "metrics"]
        )
    
    async def log_quality_metrics(self, metrics: QualityMetrics, session_id: str) -> None:
        """Log quality metrics."""
        metric_id = f"metrics_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Store in database
        async with aiosqlite.connect(self.metrics_db_path) as db:
            await db.execute("""
                INSERT INTO quality_metrics
                (metric_id, session_id, test_coverage_percentage, code_complexity_score,
                 security_score, compliance_score, performance_score, bug_density,
                 technical_debt_minutes, maintainability_index, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric_id,
                session_id,
                metrics.test_coverage_percentage,
                metrics.code_complexity_score,
                metrics.security_score,
                metrics.compliance_score,
                metrics.performance_score,
                metrics.bug_density,
                metrics.technical_debt_minutes,
                metrics.maintainability_index,
                metrics.timestamp.isoformat()
            ))
            await db.commit()
        
        # Log audit event
        await self.log_event(
            AuditEventType.PERFORMANCE_METRICS,
            asdict(metrics),
            session_id=session_id,
            severity="info",
            tags=["metrics", "quality", "performance"]
        )
    
    async def get_session_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent session history."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT * FROM test_sessions 
                ORDER BY start_time DESC 
                LIMIT ?
            """, (limit,)) as cursor:
                sessions = []
                async for row in cursor:
                    sessions.append({
                        "session_id": row[0],
                        "start_time": row[1],
                        "end_time": row[2],
                        "phase": row[3],
                        "code_changes_count": row[4],
                        "tests_generated": row[5],
                        "tests_passed": row[6],
                        "tests_failed": row[7],
                        "overall_risk_score": row[8],
                        "compliance_score": row[9]
                    })
                return sessions
    
    async def get_compliance_violations(
        self, 
        status: str = "open", 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get compliance violations."""
        async with aiosqlite.connect(self.compliance_db_path) as db:
            query = """
                SELECT * FROM compliance_violations 
                WHERE status = ? 
                ORDER BY detected_at DESC 
                LIMIT ?
            """
            async with db.execute(query, (status, limit)) as cursor:
                violations = []
                async for row in cursor:
                    violations.append({
                        "violation_id": row[0],
                        "session_id": row[1],
                        "file_path": row[2],
                        "category": row[3],
                        "level": row[4],
                        "rule_id": row[5],
                        "description": row[6],
                        "remediation": row[7],
                        "status": row[8],
                        "detected_at": row[9],
                        "resolved_at": row[10]
                    })
                return violations
    
    async def get_quality_trends(self, days: int = 30) -> Dict[str, List[float]]:
        """Get quality metric trends over time."""
        since_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        since_date = since_date.replace(day=since_date.day - days)
        
        async with aiosqlite.connect(self.metrics_db_path) as db:
            query = """
                SELECT test_coverage_percentage, code_complexity_score, 
                       security_score, compliance_score, performance_score,
                       timestamp
                FROM quality_metrics 
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """
            async with db.execute(query, (since_date.isoformat(),)) as cursor:
                trends = {
                    "test_coverage": [],
                    "complexity": [],
                    "security": [],
                    "compliance": [],
                    "performance": [],
                    "timestamps": []
                }
                
                async for row in cursor:
                    trends["test_coverage"].append(row[0])
                    trends["complexity"].append(row[1])
                    trends["security"].append(row[2])
                    trends["compliance"].append(row[3])
                    trends["performance"].append(row[4])
                    trends["timestamps"].append(row[5])
                
                return trends
    
    async def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report."""
        async with aiosqlite.connect(self.compliance_db_path) as db:
            # Get violation summary
            async with db.execute("""
                SELECT category, level, COUNT(*) as count
                FROM compliance_violations
                WHERE status = 'open'
                GROUP BY category, level
            """) as cursor:
                violation_summary = {}
                async for row in cursor:
                    category = row[0]
                    level = row[1]
                    count = row[2]
                    
                    if category not in violation_summary:
                        violation_summary[category] = {}
                    violation_summary[category][level] = count
            
            # Get compliance scores
            async with db.execute("""
                SELECT AVG(overall_score) as avg_score,
                       COUNT(*) as total_reports
                FROM compliance_reports
                WHERE generated_at >= datetime('now', '-7 days')
            """) as cursor:
                row = await cursor.fetchone()
                avg_score = row[0] if row[0] else 0.0
                total_reports = row[1] if row[1] else 0
            
            return {
                "report_date": datetime.now().isoformat(),
                "average_compliance_score": avg_score,
                "total_reports_last_7_days": total_reports,
                "violation_summary": violation_summary,
                "overall_status": "compliant" if avg_score >= 0.8 else "non_compliant"
            }
    
    async def export_audit_data(self, output_path: Path, format: str = "json") -> None:
        """Export audit data for external analysis."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            audit_data = {
                "export_timestamp": datetime.now().isoformat(),
                "sessions": await self.get_session_history(limit=1000),
                "violations": await self.get_compliance_violations(limit=1000),
                "quality_trends": await self.get_quality_trends(days=90),
                "compliance_report": await self.generate_compliance_report()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(audit_data, f, indent=2, default=str)
        
        logger.info(f"Exported audit data to {output_path}")