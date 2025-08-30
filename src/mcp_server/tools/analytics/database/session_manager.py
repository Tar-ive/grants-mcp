"""SQLite session management for analytics data persistence."""

import sqlite3
import logging
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager
import threading

logger = logging.getLogger(__name__)


class AsyncSQLiteManager:
    """
    Async-compatible SQLite manager for analytics data.
    
    Handles session persistence, score caching, and historical analytics.
    Uses threading to make SQLite operations async-compatible.
    """
    
    def __init__(self, db_path: str = "grants_analytics.db"):
        """Initialize the SQLite manager."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._local = threading.local()
        self._initialized = False
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
            
        return self._local.connection
    
    async def initialize(self):
        """Initialize database schema."""
        if self._initialized:
            return
            
        def _create_tables():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Grant scores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grant_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_id TEXT NOT NULL,
                    opportunity_title TEXT,
                    overall_score REAL NOT NULL,
                    technical_fit_score REAL,
                    competition_index REAL,
                    roi_score REAL,
                    timing_score REAL,
                    success_probability REAL,
                    score_breakdown TEXT,  -- JSON
                    recommendation TEXT,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    calculation_version TEXT DEFAULT '3.0.0',
                    UNIQUE(opportunity_id, calculation_version)
                )
            """)
            
            # Hidden opportunities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hidden_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_id TEXT NOT NULL,
                    opportunity_title TEXT,
                    hidden_score REAL NOT NULL,
                    visibility_index REAL,
                    undersubscription_score REAL,
                    cross_category_score REAL,
                    opportunity_type TEXT,
                    discovery_reason TEXT,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(opportunity_id)
                )
            """)
            
            # Search sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    search_query TEXT,
                    filters_json TEXT,
                    total_opportunities INTEGER,
                    scored_opportunities INTEGER,
                    hidden_opportunities INTEGER,
                    avg_score REAL,
                    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_end TIMESTAMP,
                    user_profile_json TEXT
                )
            """)
            
            # Strategic recommendations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategic_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    reach_grants_json TEXT,
                    match_grants_json TEXT,
                    safety_grants_json TEXT,
                    portfolio_diversity_score REAL,
                    expected_success_rate REAL,
                    risk_assessment TEXT,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES search_sessions(session_id)
                )
            """)
            
            # Analytics cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics_cache (
                    cache_key TEXT PRIMARY KEY,
                    cache_value TEXT,  -- JSON
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_grant_scores_opportunity 
                ON grant_scores(opportunity_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_grant_scores_calculated 
                ON grant_scores(calculated_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hidden_opportunities_score 
                ON hidden_opportunities(hidden_score DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_analytics_cache_expires 
                ON analytics_cache(expires_at)
            """)
            
            conn.commit()
            logger.info("Database schema initialized successfully")
        
        # Run in thread executor to make it async
        await asyncio.get_event_loop().run_in_executor(None, _create_tables)
        self._initialized = True
    
    async def store_grant_score(
        self,
        opportunity_id: str,
        opportunity_title: str,
        overall_score: float,
        score_components: Dict[str, float],
        score_breakdown: Dict[str, Any],
        recommendation: str,
        calculation_version: str = "3.0.0"
    ) -> bool:
        """Store grant score in database."""
        
        def _store():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO grant_scores (
                        opportunity_id, opportunity_title, overall_score,
                        technical_fit_score, competition_index, roi_score,
                        timing_score, success_probability,
                        score_breakdown, recommendation, calculation_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    opportunity_id, opportunity_title, overall_score,
                    score_components.get('technical_fit', 0),
                    score_components.get('competition_index', 0),
                    score_components.get('roi_score', 0),
                    score_components.get('timing_score', 0),
                    score_components.get('success_probability', 0),
                    json.dumps(score_breakdown),
                    recommendation, calculation_version
                ))
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error storing grant score: {e}")
                conn.rollback()
                return False
        
        return await asyncio.get_event_loop().run_in_executor(None, _store)
    
    async def get_grant_score(
        self, 
        opportunity_id: str,
        max_age_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """Retrieve grant score from database."""
        
        def _get():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            cursor.execute("""
                SELECT * FROM grant_scores 
                WHERE opportunity_id = ? AND calculated_at > ?
                ORDER BY calculated_at DESC LIMIT 1
            """, (opportunity_id, cutoff_time))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)
    
    async def store_hidden_opportunity(
        self,
        opportunity_id: str,
        opportunity_title: str,
        hidden_score: float,
        score_components: Dict[str, float],
        opportunity_type: str,
        discovery_reason: str
    ) -> bool:
        """Store hidden opportunity analysis."""
        
        def _store():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO hidden_opportunities (
                        opportunity_id, opportunity_title, hidden_score,
                        visibility_index, undersubscription_score, cross_category_score,
                        opportunity_type, discovery_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    opportunity_id, opportunity_title, hidden_score,
                    score_components.get('visibility_index', 0),
                    score_components.get('undersubscription_score', 0),
                    score_components.get('cross_category_score', 0),
                    opportunity_type, discovery_reason
                ))
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error storing hidden opportunity: {e}")
                conn.rollback()
                return False
        
        return await asyncio.get_event_loop().run_in_executor(None, _store)
    
    async def create_search_session(
        self,
        session_id: str,
        search_query: str,
        filters: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create a new search session."""
        
        def _create():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO search_sessions (
                        session_id, search_query, filters_json, user_profile_json
                    ) VALUES (?, ?, ?, ?)
                """, (
                    session_id, search_query, 
                    json.dumps(filters), 
                    json.dumps(user_profile) if user_profile else None
                ))
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error creating search session: {e}")
                conn.rollback()
                return False
        
        return await asyncio.get_event_loop().run_in_executor(None, _create)
    
    async def update_session_results(
        self,
        session_id: str,
        total_opportunities: int,
        scored_opportunities: int,
        hidden_opportunities: int,
        avg_score: float
    ) -> bool:
        """Update search session with results."""
        
        def _update():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    UPDATE search_sessions SET
                        total_opportunities = ?,
                        scored_opportunities = ?,
                        hidden_opportunities = ?,
                        avg_score = ?,
                        session_end = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                """, (
                    total_opportunities, scored_opportunities,
                    hidden_opportunities, avg_score, session_id
                ))
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error updating session results: {e}")
                conn.rollback()
                return False
        
        return await asyncio.get_event_loop().run_in_executor(None, _update)
    
    async def get_analytics_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieve value from analytics cache."""
        
        def _get():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Clean expired entries first
            cursor.execute("DELETE FROM analytics_cache WHERE expires_at < CURRENT_TIMESTAMP")
            
            # Get cached value
            cursor.execute("""
                SELECT cache_value, hit_count FROM analytics_cache 
                WHERE cache_key = ? AND expires_at > CURRENT_TIMESTAMP
            """, (cache_key,))
            
            row = cursor.fetchone()
            if row:
                # Increment hit count
                cursor.execute("""
                    UPDATE analytics_cache SET hit_count = hit_count + 1 
                    WHERE cache_key = ?
                """, (cache_key,))
                conn.commit()
                
                try:
                    return json.loads(row['cache_value'])
                except json.JSONDecodeError:
                    return None
            return None
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)
    
    async def set_analytics_cache(
        self, 
        cache_key: str, 
        cache_value: Any, 
        ttl_seconds: int = 3600
    ) -> bool:
        """Store value in analytics cache."""
        
        def _set():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO analytics_cache (
                        cache_key, cache_value, expires_at
                    ) VALUES (?, ?, ?)
                """, (
                    cache_key,
                    json.dumps(cache_value, default=str),
                    expires_at
                ))
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error setting analytics cache: {e}")
                conn.rollback()
                return False
        
        return await asyncio.get_event_loop().run_in_executor(None, _set)
    
    async def get_top_hidden_opportunities(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top hidden opportunities by score."""
        
        def _get():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM hidden_opportunities 
                ORDER BY hidden_score DESC 
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)
    
    async def get_analytics_stats(self) -> Dict[str, Any]:
        """Get database analytics statistics."""
        
        def _get():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            stats = {}
            
            # Count records in each table
            for table in ['grant_scores', 'hidden_opportunities', 'search_sessions']:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()['count']
            
            # Cache statistics
            cursor.execute("""
                SELECT COUNT(*) as total, SUM(hit_count) as total_hits 
                FROM analytics_cache
            """)
            cache_row = cursor.fetchone()
            stats['cache_entries'] = cache_row['total']
            stats['cache_total_hits'] = cache_row['total_hits'] or 0
            
            # Recent activity
            cursor.execute("""
                SELECT COUNT(*) as recent_scores 
                FROM grant_scores 
                WHERE calculated_at > datetime('now', '-24 hours')
            """)
            stats['recent_scores_24h'] = cursor.fetchone()['recent_scores']
            
            return stats
        
        return await asyncio.get_event_loop().run_in_executor(None, _get)
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, int]:
        """Clean up old data from database."""
        
        def _cleanup():
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            deleted_counts = {}
            
            # Clean old scores (keep recent ones)
            cursor.execute("""
                DELETE FROM grant_scores 
                WHERE calculated_at < ?
            """, (cutoff_date,))
            deleted_counts['grant_scores'] = cursor.rowcount
            
            # Clean old sessions
            cursor.execute("""
                DELETE FROM search_sessions 
                WHERE session_start < ?
            """, (cutoff_date,))
            deleted_counts['search_sessions'] = cursor.rowcount
            
            # Clean expired cache entries
            cursor.execute("DELETE FROM analytics_cache WHERE expires_at < CURRENT_TIMESTAMP")
            deleted_counts['cache_entries'] = cursor.rowcount
            
            conn.commit()
            return deleted_counts
        
        return await asyncio.get_event_loop().run_in_executor(None, _cleanup)
    
    async def close(self):
        """Close database connections."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')