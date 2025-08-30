#!/usr/bin/env python3
"""
Command Line Interface for the Adaptive Testing Framework.

Provides commands for running adaptive testing, generating reports,
and managing the testing system.
"""

import asyncio
import click
import json
import logging
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta

from testing.agents.orchestrator import AdaptiveTestingOrchestrator
from testing.config import (
    AdaptiveTestingConfig,
    get_default_config,
    get_ci_config,
    get_grants_domain_config
)
from testing.audit.trail_manager import AuditTrailManager


@click.group()
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
@click.option('--log-level', default='INFO', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Logging level')
@click.option('--project-root', type=click.Path(exists=True),
              help='Project root directory')
@click.pass_context
def cli(ctx, config: Optional[str], log_level: str, project_root: Optional[str]):
    """Adaptive Testing Framework CLI"""
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    if config:
        config_obj = AdaptiveTestingConfig.load_from_file(Path(config))
    else:
        config_obj = get_default_config()
    
    if project_root:
        config_obj.project_root = Path(project_root).resolve()
    
    # Store in context
    ctx.ensure_object(dict)
    ctx.obj['config'] = config_obj


@cli.command()
@click.option('--continuous', '-c', is_flag=True, 
              help='Run in continuous monitoring mode')
@click.option('--risk-threshold', '-r', type=float, default=0.5,
              help='Risk threshold for test generation (0.0-1.0)')
@click.option('--force-full-analysis', '-f', is_flag=True,
              help='Force full codebase analysis')
@click.pass_context
def run(ctx, continuous: bool, risk_threshold: float, force_full_analysis: bool):
    """Run adaptive testing analysis"""
    
    config = ctx.obj['config']
    
    click.echo("🤖 Starting Adaptive Testing Framework")
    click.echo(f"   Project: {config.project_root}")
    click.echo(f"   Mode: {'Continuous' if continuous else 'One-time'}")
    click.echo(f"   Risk threshold: {risk_threshold}")
    
    async def run_analysis():
        orchestrator = AdaptiveTestingOrchestrator(
            project_root=config.project_root,
            config=config.to_orchestrator_config()
        )
        
        if continuous:
            click.echo("\n📡 Starting continuous monitoring...")
            await orchestrator.start_continuous_monitoring()
        else:
            click.echo("\n🔍 Running single analysis cycle...")
            # Simulate a one-time analysis
            changes = await orchestrator._detect_code_changes()
            
            if changes:
                session = await orchestrator._start_testing_session(changes)
                await orchestrator._execute_testing_pipeline(session)
                
                click.echo(f"\n✅ Analysis complete!")
                click.echo(f"   Session ID: {session.session_id}")
                click.echo(f"   Changes processed: {len(changes)}")
                click.echo(f"   Tests generated: {len(session.generated_tests)}")
                
                # Show summary
                status = await orchestrator.get_status()
                click.echo(f"\n📊 System Status:")
                for key, value in status['performance_metrics'].items():
                    if value['count'] > 0:
                        click.echo(f"   {key}: avg {value['avg']:.2f}s")
            else:
                click.echo("   No changes detected.")
    
    try:
        asyncio.run(run_analysis())
    except KeyboardInterrupt:
        click.echo("\n🛑 Analysis stopped by user")
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--output', '-o', type=click.Path(), default='test-report.html',
              help='Output file for the report')
@click.option('--format', '-f', type=click.Choice(['html', 'json', 'markdown']),
              default='html', help='Report format')
@click.option('--days', '-d', type=int, default=30,
              help='Number of days to include in the report')
@click.pass_context
def report(ctx, output: str, format: str, days: int):
    """Generate comprehensive testing report"""
    
    config = ctx.obj['config']
    output_path = Path(output)
    
    click.echo(f"📋 Generating {format.upper()} report...")
    click.echo(f"   Period: Last {days} days")
    click.echo(f"   Output: {output_path}")
    
    async def generate_report():
        audit_manager = AuditTrailManager(config.project_root / "testing" / "audit")
        
        # Gather data
        sessions = await audit_manager.get_session_history(limit=100)
        violations = await audit_manager.get_compliance_violations()
        trends = await audit_manager.get_quality_trends(days=days)
        compliance_report = await audit_manager.generate_compliance_report()
        
        # Generate report based on format
        if format == 'json':
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'period_days': days,
                'sessions': sessions,
                'compliance_violations': violations,
                'quality_trends': trends,
                'compliance_summary': compliance_report
            }
            
            with open(output_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
        
        elif format == 'html':
            await generate_html_report(output_path, sessions, violations, trends, compliance_report, days)
        
        elif format == 'markdown':
            await generate_markdown_report(output_path, sessions, violations, trends, compliance_report, days)
        
        click.echo(f"✅ Report generated: {output_path}")
    
    try:
        asyncio.run(generate_report())
    except Exception as e:
        click.echo(f"❌ Error generating report: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--export-path', '-o', type=click.Path(), required=True,
              help='Export file path')
@click.option('--format', '-f', type=click.Choice(['json', 'csv']), 
              default='json', help='Export format')
@click.pass_context
def export(ctx, export_path: str, format: str):
    """Export audit data for external analysis"""
    
    config = ctx.obj['config']
    export_file = Path(export_path)
    
    click.echo(f"📤 Exporting audit data...")
    click.echo(f"   Format: {format.upper()}")
    click.echo(f"   Output: {export_file}")
    
    async def export_data():
        audit_manager = AuditTrailManager(config.project_root / "testing" / "audit")
        await audit_manager.export_audit_data(export_file, format=format)
        
        click.echo(f"✅ Data exported successfully")
        click.echo(f"   File size: {export_file.stat().st_size:,} bytes")
    
    try:
        asyncio.run(export_data())
    except Exception as e:
        click.echo(f"❌ Export failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('source_files', nargs=-1, required=True)
@click.option('--test-type', '-t', multiple=True,
              type=click.Choice(['unit', 'integration', 'compliance', 'performance']),
              help='Types of tests to generate')
@click.option('--output-dir', '-o', type=click.Path(),
              help='Output directory for generated tests')
@click.pass_context
def generate_tests(ctx, source_files: List[str], test_type: List[str], output_dir: Optional[str]):
    """Generate tests for specific source files"""
    
    config = ctx.obj['config']
    
    if not test_type:
        test_type = ['unit']
    
    click.echo(f"🔧 Generating tests...")
    click.echo(f"   Source files: {len(source_files)}")
    click.echo(f"   Test types: {', '.join(test_type)}")
    
    async def generate():
        from testing.generators.test_generator import TestCaseGenerator, TestGenerationRequest
        
        generator = TestCaseGenerator(
            project_root=config.project_root,
            config=config.test_generation.__dict__
        )
        
        all_generated = []
        
        for source_file in source_files:
            source_path = Path(source_file)
            if not source_path.exists():
                click.echo(f"   ⚠️ File not found: {source_file}")
                continue
            
            for ttype in test_type:
                request = TestGenerationRequest(
                    source_file=str(source_path),
                    test_category=ttype,
                    priority=7,
                    complexity_metrics={'risk': 0.5},
                    dependencies=[],
                    business_context='general'
                )
                
                try:
                    generated_files = await generator.generate_tests(request)
                    all_generated.extend(generated_files)
                    click.echo(f"   ✅ {source_file} ({ttype}): {len(generated_files)} tests")
                except Exception as e:
                    click.echo(f"   ❌ {source_file} ({ttype}): {e}")
        
        click.echo(f"\n📊 Generation Summary:")
        click.echo(f"   Total tests generated: {len(all_generated)}")
        
        if all_generated:
            click.echo(f"\n📁 Generated Files:")
            for test_file in all_generated:
                click.echo(f"   • {test_file}")
    
    try:
        asyncio.run(generate())
    except Exception as e:
        click.echo(f"❌ Generation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show current system status"""
    
    config = ctx.obj['config']
    
    click.echo("📊 Adaptive Testing System Status")
    click.echo("=" * 40)
    
    async def show_status():
        try:
            orchestrator = AdaptiveTestingOrchestrator(
                project_root=config.project_root,
                config=config.to_orchestrator_config()
            )
            
            status_info = await orchestrator.get_status()
            
            click.echo(f"Monitoring Active: {'🟢 Yes' if status_info['monitoring_active'] else '🔴 No'}")
            click.echo(f"Monitored Files: {status_info['monitored_files']:,}")
            click.echo(f"Sessions Completed: {status_info['sessions_completed']}")
            
            if status_info['current_session']:
                click.echo(f"Current Session: {status_info['current_session']}")
            
            click.echo(f"\nPerformance Metrics:")
            for metric, data in status_info['performance_metrics'].items():
                if data['count'] > 0:
                    click.echo(f"  {metric.replace('_', ' ').title()}: {data['avg']:.2f}s avg (max: {data['max']:.2f}s)")
            
            # Check audit trail
            audit_manager = AuditTrailManager(config.project_root / "testing" / "audit")
            recent_sessions = await audit_manager.get_session_history(limit=5)
            
            if recent_sessions:
                click.echo(f"\nRecent Sessions:")
                for session in recent_sessions[:3]:
                    click.echo(f"  • {session['session_id']} - {session['start_time']}")
            
        except Exception as e:
            click.echo(f"❌ Error getting status: {e}", err=True)
    
    try:
        asyncio.run(show_status())
    except Exception as e:
        click.echo(f"❌ Status check failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--profile', type=click.Choice(['default', 'ci', 'grants']),
              default='default', help='Configuration profile')
@click.option('--output', '-o', type=click.Path(), 
              default='adaptive-testing-config.json',
              help='Configuration file output path')
def init_config(profile: str, output: str):
    """Initialize configuration file"""
    
    click.echo(f"🔧 Creating configuration file...")
    click.echo(f"   Profile: {profile}")
    click.echo(f"   Output: {output}")
    
    # Select configuration based on profile
    if profile == 'ci':
        config = get_ci_config()
    elif profile == 'grants':
        config = get_grants_domain_config()
    else:
        config = get_default_config()
    
    # Export configuration
    config.export_config(Path(output))
    
    click.echo(f"✅ Configuration created: {output}")
    click.echo(f"\nNext steps:")
    click.echo(f"1. Review and customize the configuration")
    click.echo(f"2. Run: adaptive-testing -c {output} run")
    click.echo(f"3. Or run continuous monitoring: adaptive-testing -c {output} run --continuous")


async def generate_html_report(output_path: Path, sessions, violations, trends, compliance_report, days):
    """Generate HTML report."""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Adaptive Testing Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #2e86de; color: white; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f1f2f6; border-radius: 3px; }}
        .violation {{ color: #e74c3c; }}
        .success {{ color: #27ae60; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Adaptive Testing Report</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Period: Last {days} days</p>
    </div>
    
    <div class="section">
        <h2>Summary</h2>
        <div class="metric">Sessions: {len(sessions)}</div>
        <div class="metric">Violations: {len(violations)}</div>
        <div class="metric">Compliance Score: {compliance_report.get('average_compliance_score', 0):.2f}</div>
    </div>
    
    <div class="section">
        <h2>Recent Sessions</h2>
        <table>
            <tr><th>Session ID</th><th>Start Time</th><th>Tests Generated</th><th>Risk Score</th></tr>
            {''.join(f'<tr><td>{s["session_id"]}</td><td>{s["start_time"]}</td><td>{s["tests_generated"]}</td><td>{s["overall_risk_score"]:.2f}</td></tr>' for s in sessions[:10])}
        </table>
    </div>
    
    <div class="section">
        <h2>Compliance Violations</h2>
        <table>
            <tr><th>File</th><th>Category</th><th>Level</th><th>Description</th></tr>
            {''.join(f'<tr><td>{v["file_path"]}</td><td>{v["category"]}</td><td class="violation">{v["level"]}</td><td>{v["description"]}</td></tr>' for v in violations[:20])}
        </table>
    </div>
</body>
</html>"""
    
    with open(output_path, 'w') as f:
        f.write(html_content)


async def generate_markdown_report(output_path: Path, sessions, violations, trends, compliance_report, days):
    """Generate Markdown report."""
    md_content = f"""# Adaptive Testing Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Period:** Last {days} days

## Summary

- **Sessions Completed:** {len(sessions)}
- **Active Violations:** {len(violations)}
- **Average Compliance Score:** {compliance_report.get('average_compliance_score', 0):.2f}

## Recent Testing Sessions

| Session ID | Start Time | Tests Generated | Risk Score |
|------------|------------|-----------------|------------|
{''.join(f'| {s["session_id"]} | {s["start_time"]} | {s["tests_generated"]} | {s["overall_risk_score"]:.2f} |\n' for s in sessions[:10])}

## Compliance Violations

| File | Category | Level | Description |
|------|----------|-------|-------------|
{''.join(f'| {v["file_path"]} | {v["category"]} | {v["level"]} | {v["description"]} |\n' for v in violations[:20])}

## Quality Trends

- **Test Coverage:** Recent trend analysis
- **Security Score:** Risk assessment trends  
- **Compliance:** Regulatory compliance tracking

---
*Report generated by Adaptive Testing Framework*
"""
    
    with open(output_path, 'w') as f:
        f.write(md_content)


if __name__ == '__main__':
    cli()