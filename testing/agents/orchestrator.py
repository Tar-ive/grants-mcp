"""
Adaptive Testing Agent Orchestrator

This module implements the main orchestration system for the adaptive testing agent
that continuously evolves with the codebase. It coordinates all testing agents,
monitors code changes, and manages the testing lifecycle.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import ast

from testing.risk.risk_analyzer import RiskAnalyzer, RiskLevel
from testing.compliance.checker import ComplianceChecker
from testing.audit.trail_manager import AuditTrailManager
from testing.generators.test_generator import TestCaseGenerator

logger = logging.getLogger(__name__)


class TestingPhase(Enum):
    """Testing phases in the adaptive pipeline."""
    DISCOVERY = "discovery"
    GENERATION = "generation"
    EXECUTION = "execution"
    ANALYSIS = "analysis"
    OPTIMIZATION = "optimization"


@dataclass
class CodeChangeEvent:
    """Represents a code change event that triggers adaptive testing."""
    file_path: str
    change_type: str  # added, modified, deleted
    timestamp: datetime
    file_hash: str
    complexity_score: float
    affected_modules: List[str]
    test_requirements: List[str]


@dataclass
class TestGenerationRequest:
    """Request for test case generation."""
    source_file: str
    test_category: str
    priority: int
    complexity_metrics: Dict[str, float]
    dependencies: List[str]
    business_context: str


@dataclass
class AdaptiveTestSession:
    """Represents a complete adaptive testing session."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    phase: TestingPhase
    code_changes: List[CodeChangeEvent]
    generated_tests: List[str]
    execution_results: Dict[str, Any]
    risk_scores: Dict[str, float]
    compliance_status: Dict[str, bool]


class AdaptiveTestingOrchestrator:
    """
    Main orchestrator for the adaptive testing agent system.
    
    Coordinates continuous monitoring, test generation, risk assessment,
    and compliance checking in response to code changes.
    """
    
    def __init__(self, project_root: Path, config: Dict[str, Any]):
        """Initialize the orchestrator."""
        self.project_root = project_root
        self.config = config
        
        # Initialize components
        self.risk_analyzer = RiskAnalyzer(config.get("risk_config", {}))
        self.compliance_checker = ComplianceChecker(config.get("compliance_config", {}))
        self.audit_manager = AuditTrailManager(project_root / "testing" / "audit")
        self.test_generator = TestCaseGenerator(project_root, config.get("generation_config", {}))
        
        # Session management
        self.current_session: Optional[AdaptiveTestSession] = None
        self.session_history: List[AdaptiveTestSession] = []
        
        # File monitoring
        self.monitored_files: Dict[str, str] = {}  # path -> hash
        self.file_dependencies: Dict[str, Set[str]] = {}
        self.test_cache: Dict[str, datetime] = {}
        
        # Performance tracking
        self.performance_metrics = {
            "test_generation_time": [],
            "execution_time": [],
            "risk_analysis_time": [],
            "compliance_check_time": []
        }
        
        logger.info("Initialized Adaptive Testing Orchestrator")
    
    async def start_continuous_monitoring(self) -> None:
        """Start continuous code monitoring and adaptive testing."""
        logger.info("Starting continuous monitoring for adaptive testing")
        
        # Initial code scan
        await self._perform_initial_scan()
        
        # Start monitoring loop
        while True:
            try:
                await self._monitoring_cycle()
                await asyncio.sleep(self.config.get("monitoring_interval", 30))
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _perform_initial_scan(self) -> None:
        """Perform initial scan of the codebase."""
        logger.info("Performing initial codebase scan")
        
        # Scan source files
        src_files = list(self.project_root.glob("src/**/*.py")) + list(self.project_root.glob("src/**/*.ts"))
        for file_path in src_files:
            await self._analyze_file(file_path, is_initial=True)
        
        # Build dependency graph
        await self._build_dependency_graph()
        
        logger.info(f"Initial scan complete: {len(src_files)} files analyzed")
    
    async def _monitoring_cycle(self) -> None:
        """Execute one monitoring cycle."""
        start_time = time.time()
        
        # Detect changes
        changes = await self._detect_code_changes()
        
        if changes:
            # Start new testing session
            session = await self._start_testing_session(changes)
            
            try:
                # Execute adaptive testing pipeline
                await self._execute_testing_pipeline(session)
                
                # Complete session
                session.end_time = datetime.now()
                session.phase = TestingPhase.ANALYSIS
                
                self.session_history.append(session)
                
                # Audit logging
                await self.audit_manager.log_session(session)
                
            except Exception as e:
                logger.error(f"Error in testing pipeline: {e}")
                session.phase = TestingPhase.ANALYSIS
                await self.audit_manager.log_error(str(e), session.session_id)
            
            finally:
                self.current_session = None
        
        cycle_time = time.time() - start_time
        logger.debug(f"Monitoring cycle completed in {cycle_time:.2f}s")
    
    async def _detect_code_changes(self) -> List[CodeChangeEvent]:
        """Detect changes in monitored files."""
        changes = []
        
        # Check existing files for modifications
        for file_path_str, old_hash in self.monitored_files.items():
            file_path = Path(file_path_str)
            
            if file_path.exists():
                new_hash = await self._calculate_file_hash(file_path)
                if new_hash != old_hash:
                    change = await self._create_change_event(file_path, "modified")
                    changes.append(change)
                    self.monitored_files[file_path_str] = new_hash
            else:
                # File was deleted
                change = CodeChangeEvent(
                    file_path=file_path_str,
                    change_type="deleted",
                    timestamp=datetime.now(),
                    file_hash="",
                    complexity_score=0.0,
                    affected_modules=[],
                    test_requirements=["cleanup"]
                )
                changes.append(change)
                del self.monitored_files[file_path_str]
        
        # Check for new files
        src_files = list(self.project_root.glob("src/**/*.py")) + list(self.project_root.glob("src/**/*.ts"))
        for file_path in src_files:
            file_path_str = str(file_path)
            if file_path_str not in self.monitored_files:
                change = await self._create_change_event(file_path, "added")
                changes.append(change)
                self.monitored_files[file_path_str] = await self._calculate_file_hash(file_path)
        
        return changes
    
    async def _create_change_event(self, file_path: Path, change_type: str) -> CodeChangeEvent:
        """Create a code change event from a file change."""
        file_hash = await self._calculate_file_hash(file_path)
        complexity_score = await self._calculate_complexity(file_path)
        affected_modules = await self._get_affected_modules(file_path)
        test_requirements = await self._determine_test_requirements(file_path, change_type)
        
        return CodeChangeEvent(
            file_path=str(file_path),
            change_type=change_type,
            timestamp=datetime.now(),
            file_hash=file_hash,
            complexity_score=complexity_score,
            affected_modules=affected_modules,
            test_requirements=test_requirements
        )
    
    async def _start_testing_session(self, changes: List[CodeChangeEvent]) -> AdaptiveTestSession:
        """Start a new adaptive testing session."""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = AdaptiveTestSession(
            session_id=session_id,
            start_time=datetime.now(),
            end_time=None,
            phase=TestingPhase.DISCOVERY,
            code_changes=changes,
            generated_tests=[],
            execution_results={},
            risk_scores={},
            compliance_status={}
        )
        
        self.current_session = session
        logger.info(f"Started testing session {session_id} with {len(changes)} changes")
        
        return session
    
    async def _execute_testing_pipeline(self, session: AdaptiveTestSession) -> None:
        """Execute the complete adaptive testing pipeline."""
        
        # Phase 1: Discovery and Risk Analysis
        session.phase = TestingPhase.DISCOVERY
        await self._discovery_phase(session)
        
        # Phase 2: Test Generation
        session.phase = TestingPhase.GENERATION
        await self._generation_phase(session)
        
        # Phase 3: Test Execution
        session.phase = TestingPhase.EXECUTION
        await self._execution_phase(session)
        
        # Phase 4: Analysis and Optimization
        session.phase = TestingPhase.OPTIMIZATION
        await self._optimization_phase(session)
    
    async def _discovery_phase(self, session: AdaptiveTestSession) -> None:
        """Execute discovery phase: risk analysis and compliance checking."""
        logger.info(f"Executing discovery phase for session {session.session_id}")
        
        start_time = time.time()
        
        for change in session.code_changes:
            # Risk analysis
            risk_score = await self.risk_analyzer.analyze_change(change)
            session.risk_scores[change.file_path] = risk_score.overall_score
            
            # Compliance checking
            compliance_results = await self.compliance_checker.check_file(Path(change.file_path))
            session.compliance_status[change.file_path] = compliance_results.is_compliant
            
            # Log critical issues
            if risk_score.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                await self.audit_manager.log_high_risk_change(change, risk_score)
        
        discovery_time = time.time() - start_time
        self.performance_metrics["risk_analysis_time"].append(discovery_time)
        logger.info(f"Discovery phase completed in {discovery_time:.2f}s")
    
    async def _generation_phase(self, session: AdaptiveTestSession) -> None:
        """Execute test generation phase."""
        logger.info(f"Executing generation phase for session {session.session_id}")
        
        start_time = time.time()
        
        # Generate test requests based on changes and risk scores
        test_requests = []
        for change in session.code_changes:
            risk_score = session.risk_scores.get(change.file_path, 0.5)
            priority = self._calculate_test_priority(risk_score, change.complexity_score)
            
            for requirement in change.test_requirements:
                request = TestGenerationRequest(
                    source_file=change.file_path,
                    test_category=requirement,
                    priority=priority,
                    complexity_metrics={"complexity": change.complexity_score, "risk": risk_score},
                    dependencies=list(change.affected_modules),
                    business_context=self._get_business_context(change.file_path)
                )
                test_requests.append(request)
        
        # Generate tests
        for request in sorted(test_requests, key=lambda x: x.priority, reverse=True):
            try:
                test_files = await self.test_generator.generate_tests(request)
                session.generated_tests.extend(test_files)
            except Exception as e:
                logger.error(f"Error generating tests for {request.source_file}: {e}")
        
        generation_time = time.time() - start_time
        self.performance_metrics["test_generation_time"].append(generation_time)
        logger.info(f"Generated {len(session.generated_tests)} test files in {generation_time:.2f}s")
    
    async def _execution_phase(self, session: AdaptiveTestSession) -> None:
        """Execute generated tests."""
        logger.info(f"Executing tests for session {session.session_id}")
        
        start_time = time.time()
        
        if not session.generated_tests:
            logger.warning("No tests generated for execution")
            return
        
        # Execute tests using pytest
        import subprocess
        
        try:
            # Run tests with parallel execution
            cmd = [
                "python", "-m", "pytest",
                "-v", "--tb=short",
                "--junit-xml=test-results/adaptive-session.xml",
                "--cov=src",
                "--cov-report=json:test-results/coverage-adaptive.json",
                "-n", "auto",  # parallel execution
                "--durations=10"
            ] + session.generated_tests
            
            result = subprocess.run(
                cmd, 
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            session.execution_results = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "test_count": len(session.generated_tests)
            }
            
        except subprocess.TimeoutExpired:
            session.execution_results = {
                "return_code": -1,
                "error": "Test execution timeout",
                "test_count": len(session.generated_tests)
            }
        
        execution_time = time.time() - start_time
        self.performance_metrics["execution_time"].append(execution_time)
        logger.info(f"Test execution completed in {execution_time:.2f}s")
    
    async def _optimization_phase(self, session: AdaptiveTestSession) -> None:
        """Execute optimization phase: analyze results and improve."""
        logger.info(f"Executing optimization phase for session {session.session_id}")
        
        # Analyze test results
        await self._analyze_test_results(session)
        
        # Update test cache and dependencies
        await self._update_test_metadata(session)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(session)
        
        # Store optimization data
        optimization_data = {
            "session_id": session.session_id,
            "recommendations": recommendations,
            "performance_metrics": self._get_session_metrics(session),
            "improvement_opportunities": await self._identify_improvements(session)
        }
        
        await self.audit_manager.log_optimization_results(optimization_data)
        logger.info("Optimization phase completed")
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate hash of file contents."""
        try:
            content = file_path.read_text(encoding='utf-8')
            return hashlib.md5(content.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""
    
    async def _calculate_complexity(self, file_path: Path) -> float:
        """Calculate complexity score for a file."""
        try:
            if file_path.suffix == ".py":
                return await self._calculate_python_complexity(file_path)
            elif file_path.suffix == ".ts":
                return await self._calculate_typescript_complexity(file_path)
            else:
                return 1.0  # Default complexity
        except Exception as e:
            logger.error(f"Error calculating complexity for {file_path}: {e}")
            return 1.0
    
    async def _calculate_python_complexity(self, file_path: Path) -> float:
        """Calculate complexity for Python files using AST analysis."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            complexity_score = 1.0  # Base complexity
            
            # Count various complexity factors
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                    complexity_score += 0.2
                elif isinstance(node, ast.FunctionDef):
                    complexity_score += 0.3
                elif isinstance(node, ast.ClassDef):
                    complexity_score += 0.5
                elif isinstance(node, ast.AsyncFunctionDef):
                    complexity_score += 0.4
            
            return min(complexity_score, 10.0)  # Cap at 10.0
            
        except Exception as e:
            logger.error(f"Error analyzing Python complexity: {e}")
            return 1.0
    
    async def _calculate_typescript_complexity(self, file_path: Path) -> float:
        """Calculate complexity for TypeScript files (simplified)."""
        try:
            content = file_path.read_text()
            
            complexity_score = 1.0
            
            # Simple heuristics for TypeScript
            complexity_score += content.count("function") * 0.3
            complexity_score += content.count("class") * 0.5
            complexity_score += content.count("if") * 0.2
            complexity_score += content.count("for") * 0.2
            complexity_score += content.count("while") * 0.2
            complexity_score += content.count("try") * 0.3
            complexity_score += content.count("async") * 0.2
            
            return min(complexity_score, 10.0)
            
        except Exception as e:
            logger.error(f"Error analyzing TypeScript complexity: {e}")
            return 1.0
    
    def _calculate_test_priority(self, risk_score: float, complexity_score: float) -> int:
        """Calculate test generation priority based on risk and complexity."""
        # Priority scale: 1 (lowest) to 10 (highest)
        base_priority = 5
        
        # Risk factor (0-5 points)
        risk_points = min(risk_score * 5, 5)
        
        # Complexity factor (0-3 points)
        complexity_points = min(complexity_score / 10 * 3, 3)
        
        # Business criticality (0-2 points)
        business_points = 2  # Default high priority for grants domain
        
        total_priority = base_priority + risk_points + complexity_points + business_points
        return min(int(total_priority), 10)
    
    def _get_business_context(self, file_path: str) -> str:
        """Determine business context for a file."""
        if "grants" in file_path.lower():
            return "grants_processing"
        elif "api" in file_path.lower():
            return "api_integration"
        elif "financial" in file_path.lower():
            return "financial_calculations"
        elif "search" in file_path.lower():
            return "search_functionality"
        else:
            return "general"
    
    async def _get_affected_modules(self, file_path: Path) -> List[str]:
        """Get modules that might be affected by changes to this file."""
        # This would use the dependency graph built during initialization
        file_str = str(file_path)
        return list(self.file_dependencies.get(file_str, set()))
    
    async def _determine_test_requirements(self, file_path: Path, change_type: str) -> List[str]:
        """Determine what types of tests are needed."""
        requirements = []
        
        if change_type == "added":
            requirements = ["unit", "integration"]
        elif change_type == "modified":
            requirements = ["unit", "regression"]
        elif change_type == "deleted":
            requirements = ["cleanup"]
        
        # Add domain-specific requirements
        file_str = str(file_path).lower()
        if "api" in file_str:
            requirements.append("contract")
        if "financial" in file_str or "grant" in file_str:
            requirements.append("compliance")
        if "performance" in file_str or "analytics" in file_str:
            requirements.append("performance")
        
        return requirements
    
    async def _build_dependency_graph(self) -> None:
        """Build dependency graph for the codebase."""
        logger.info("Building dependency graph")
        
        # This is a simplified implementation
        # In practice, you'd use AST analysis to build a proper dependency graph
        
        src_files = list(self.project_root.glob("src/**/*.py"))
        for file_path in src_files:
            try:
                content = file_path.read_text()
                file_str = str(file_path)
                dependencies = set()
                
                # Simple import analysis
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith(('import ', 'from ')):
                        # Extract import information
                        if 'mcp_server' in line:
                            dependencies.add(line.split()[1])
                
                self.file_dependencies[file_str] = dependencies
                
            except Exception as e:
                logger.error(f"Error analyzing dependencies for {file_path}: {e}")
    
    async def _analyze_file(self, file_path: Path, is_initial: bool = False) -> None:
        """Analyze a single file."""
        file_hash = await self._calculate_file_hash(file_path)
        self.monitored_files[str(file_path)] = file_hash
        
        if not is_initial:
            logger.debug(f"Analyzed file: {file_path}")
    
    async def _analyze_test_results(self, session: AdaptiveTestSession) -> None:
        """Analyze test execution results."""
        if "return_code" not in session.execution_results:
            return
        
        # Parse JUnit XML if available
        junit_file = self.project_root / "test-results" / "adaptive-session.xml"
        if junit_file.exists():
            # Parse test results (simplified)
            session.execution_results["junit_parsed"] = True
    
    async def _update_test_metadata(self, session: AdaptiveTestSession) -> None:
        """Update test cache and metadata."""
        for test_file in session.generated_tests:
            self.test_cache[test_file] = session.start_time
    
    async def _generate_recommendations(self, session: AdaptiveTestSession) -> List[str]:
        """Generate recommendations for improvement."""
        recommendations = []
        
        # Analyze execution results
        if session.execution_results.get("return_code", 0) != 0:
            recommendations.append("Review failed tests and fix implementation issues")
        
        # Analyze risk scores
        high_risk_files = [
            path for path, score in session.risk_scores.items() 
            if score > 0.7
        ]
        if high_risk_files:
            recommendations.append(f"Focus on high-risk files: {', '.join(high_risk_files[:3])}")
        
        # Analyze compliance
        non_compliant_files = [
            path for path, compliant in session.compliance_status.items() 
            if not compliant
        ]
        if non_compliant_files:
            recommendations.append(f"Address compliance issues in: {', '.join(non_compliant_files[:3])}")
        
        return recommendations
    
    def _get_session_metrics(self, session: AdaptiveTestSession) -> Dict[str, Any]:
        """Get performance metrics for the session."""
        return {
            "session_duration": (session.end_time - session.start_time).total_seconds() if session.end_time else 0,
            "changes_processed": len(session.code_changes),
            "tests_generated": len(session.generated_tests),
            "avg_risk_score": sum(session.risk_scores.values()) / len(session.risk_scores) if session.risk_scores else 0,
            "compliance_rate": sum(session.compliance_status.values()) / len(session.compliance_status) if session.compliance_status else 1.0
        }
    
    async def _identify_improvements(self, session: AdaptiveTestSession) -> List[str]:
        """Identify opportunities for improvement."""
        improvements = []
        
        # Performance improvements
        if self.performance_metrics["test_generation_time"]:
            avg_gen_time = sum(self.performance_metrics["test_generation_time"]) / len(self.performance_metrics["test_generation_time"])
            if avg_gen_time > 30:  # More than 30 seconds
                improvements.append("Optimize test generation performance")
        
        # Coverage improvements
        if len(session.generated_tests) == 0:
            improvements.append("Improve test generation coverage")
        
        return improvements
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current status of the orchestrator."""
        return {
            "monitoring_active": self.current_session is not None,
            "monitored_files": len(self.monitored_files),
            "sessions_completed": len(self.session_history),
            "current_session": self.current_session.session_id if self.current_session else None,
            "performance_metrics": {
                key: {
                    "count": len(values),
                    "avg": sum(values) / len(values) if values else 0,
                    "max": max(values) if values else 0
                }
                for key, values in self.performance_metrics.items()
            }
        }


# Configuration factory
def create_orchestrator_config() -> Dict[str, Any]:
    """Create default configuration for the orchestrator."""
    return {
        "monitoring_interval": 30,  # seconds
        "risk_config": {
            "security_weight": 0.3,
            "complexity_weight": 0.2,
            "business_impact_weight": 0.5
        },
        "compliance_config": {
            "data_privacy_rules": ["PII", "financial_data"],
            "api_security_rules": ["authentication", "rate_limiting"],
            "grants_specific_rules": ["calculation_accuracy", "audit_trail"]
        },
        "generation_config": {
            "max_tests_per_file": 10,
            "test_timeout": 30,
            "parallel_generation": True
        }
    }