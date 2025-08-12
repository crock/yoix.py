"""
Database Manager for Yoix internal data storage.

Handles build information, caches, test results, site metrics, and other internal data.
Uses SQLite for lightweight, zero-configuration storage.
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from contextlib import contextmanager


class DatabaseManager:
    """Manages internal SQLite database for Yoix data storage."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the database manager.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default to .yoix/data.db in current directory
            db_path = Path.cwd() / '.yoix' / 'data.db'
            
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._init_schema()
        
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
                
    def _init_schema(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            # Build information table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS builds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    build_hash TEXT UNIQUE NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds REAL,
                    status TEXT NOT NULL DEFAULT 'running',
                    content_dir TEXT NOT NULL,
                    public_dir TEXT NOT NULL,
                    posts_count INTEGER DEFAULT 0,
                    pages_count INTEGER DEFAULT 0,
                    assets_count INTEGER DEFAULT 0,
                    plugins_loaded TEXT,
                    errors TEXT,
                    warnings TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Cache table for various cached data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at TEXT,
                    category TEXT DEFAULT 'general',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Site metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    build_hash TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metric_unit TEXT,
                    category TEXT DEFAULT 'general',
                    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (build_hash) REFERENCES builds (build_hash)
                )
            """)
            
            # Test results table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    build_hash TEXT,
                    test_name TEXT NOT NULL,
                    test_category TEXT DEFAULT 'general',
                    status TEXT NOT NULL,
                    duration_seconds REAL,
                    error_message TEXT,
                    details TEXT,
                    run_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (build_hash) REFERENCES builds (build_hash)
                )
            """)
            
            # Plugin data table for plugins to store persistent data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plugin_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_name TEXT NOT NULL,
                    data_key TEXT NOT NULL,
                    data_value TEXT NOT NULL,
                    expires_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(plugin_name, data_key)
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_builds_hash ON builds (build_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_builds_start_time ON builds (start_time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache (expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_build ON metrics (build_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tests_build ON test_results (build_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_plugin_data_plugin ON plugin_data (plugin_name)")
            
            conn.commit()
            
    # Build Management
    def start_build(self, content_dir: Path, public_dir: Path) -> str:
        """Start a new build and return build hash.
        
        Args:
            content_dir: Content directory path
            public_dir: Public output directory path
            
        Returns:
            Build hash identifier
        """
        # Generate unique build hash based on timestamp and paths
        timestamp = datetime.now().isoformat()
        hash_input = f"{timestamp}:{content_dir}:{public_dir}"
        build_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO builds (
                    build_hash, start_time, content_dir, public_dir, status
                ) VALUES (?, ?, ?, ?, 'running')
            """, (build_hash, timestamp, str(content_dir), str(public_dir)))
            conn.commit()
            
        return build_hash
        
    def complete_build(self, build_hash: str, posts_count: int = 0, pages_count: int = 0, 
                      assets_count: int = 0, plugins_loaded: List[str] = None,
                      errors: List[str] = None, warnings: List[str] = None):
        """Mark build as completed and update statistics.
        
        Args:
            build_hash: Build identifier
            posts_count: Number of posts processed
            pages_count: Number of pages processed
            assets_count: Number of assets processed
            plugins_loaded: List of loaded plugin names
            errors: List of error messages
            warnings: List of warning messages
        """
        end_time = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            # Get start time to calculate duration
            result = conn.execute(
                "SELECT start_time FROM builds WHERE build_hash = ?",
                (build_hash,)
            ).fetchone()
            
            if result:
                start_time = datetime.fromisoformat(result['start_time'])
                duration = (datetime.now() - start_time).total_seconds()
                
                conn.execute("""
                    UPDATE builds SET 
                        end_time = ?, duration_seconds = ?, status = 'completed',
                        posts_count = ?, pages_count = ?, assets_count = ?,
                        plugins_loaded = ?, errors = ?, warnings = ?
                    WHERE build_hash = ?
                """, (
                    end_time, duration, posts_count, pages_count, assets_count,
                    json.dumps(plugins_loaded or []),
                    json.dumps(errors or []),
                    json.dumps(warnings or []),
                    build_hash
                ))
                conn.commit()
                
    def fail_build(self, build_hash: str, error_message: str):
        """Mark build as failed.
        
        Args:
            build_hash: Build identifier
            error_message: Error that caused failure
        """
        end_time = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE builds SET 
                    end_time = ?, status = 'failed', errors = ?
                WHERE build_hash = ?
            """, (end_time, json.dumps([error_message]), build_hash))
            conn.commit()
            
    def get_build_info(self, build_hash: str) -> Optional[Dict[str, Any]]:
        """Get build information by hash.
        
        Args:
            build_hash: Build identifier
            
        Returns:
            Build information dictionary or None if not found
        """
        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT * FROM builds WHERE build_hash = ?",
                (build_hash,)
            ).fetchone()
            
            if result:
                build_info = dict(result)
                # Parse JSON fields
                build_info['plugins_loaded'] = json.loads(build_info['plugins_loaded'] or '[]')
                build_info['errors'] = json.loads(build_info['errors'] or '[]')
                build_info['warnings'] = json.loads(build_info['warnings'] or '[]')
                return build_info
                
        return None
        
    def get_recent_builds(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent builds ordered by start time.
        
        Args:
            limit: Maximum number of builds to return
            
        Returns:
            List of build information dictionaries
        """
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT * FROM builds 
                ORDER BY start_time DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            builds = []
            for result in results:
                build_info = dict(result)
                build_info['plugins_loaded'] = json.loads(build_info['plugins_loaded'] or '[]')
                build_info['errors'] = json.loads(build_info['errors'] or '[]')
                build_info['warnings'] = json.loads(build_info['warnings'] or '[]')
                builds.append(build_info)
                
            return builds
            
    # Cache Management
    def cache_set(self, key: str, value: Any, expires_in_seconds: Optional[int] = None, category: str = 'general'):
        """Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            expires_in_seconds: Optional expiration time in seconds
            category: Cache category for organization
        """
        expires_at = None
        if expires_in_seconds:
            expires_at = (datetime.now() + timedelta(seconds=expires_in_seconds)).isoformat()
            
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache (key, value, expires_at, category, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (key, json.dumps(value), expires_at, category))
            conn.commit()
            
    def cache_get(self, key: str) -> Any:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._get_connection() as conn:
            result = conn.execute("""
                SELECT value, expires_at FROM cache 
                WHERE key = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """, (key,)).fetchone()
            
            if result:
                return json.loads(result['value'])
                
        return None
        
    def cache_delete(self, key: str):
        """Delete cache entry.
        
        Args:
            key: Cache key to delete
        """
        with self._get_connection() as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
            
    def cache_clear_category(self, category: str):
        """Clear all cache entries in a category.
        
        Args:
            category: Category to clear
        """
        with self._get_connection() as conn:
            conn.execute("DELETE FROM cache WHERE category = ?", (category,))
            conn.commit()
            
    def cache_cleanup_expired(self):
        """Remove expired cache entries."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP")
            conn.commit()
            
    def cache_list_by_category(self, category: str) -> List[str]:
        """List all cache keys in a category.
        
        Args:
            category: Category to list
            
        Returns:
            List of cache keys in the category
        """
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT key FROM cache 
                WHERE category = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """, (category,)).fetchall()
            
            return [result['key'] for result in results]
            
    # Metrics Management
    def record_metric(self, build_hash: str, metric_name: str, value: float, 
                     unit: str = None, category: str = 'general'):
        """Record a metric for a build.
        
        Args:
            build_hash: Build identifier
            metric_name: Name of the metric
            value: Metric value
            unit: Optional unit (e.g., 'seconds', 'bytes', 'count')
            category: Metric category
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO metrics (build_hash, metric_name, metric_value, metric_unit, category)
                VALUES (?, ?, ?, ?, ?)
            """, (build_hash, metric_name, value, unit, category))
            conn.commit()
            
    def get_build_metrics(self, build_hash: str) -> List[Dict[str, Any]]:
        """Get all metrics for a build.
        
        Args:
            build_hash: Build identifier
            
        Returns:
            List of metric dictionaries
        """
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT * FROM metrics WHERE build_hash = ?
                ORDER BY recorded_at
            """, (build_hash,)).fetchall()
            
            return [dict(result) for result in results]
            
    def get_metric_history(self, metric_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get history of a specific metric across builds.
        
        Args:
            metric_name: Name of the metric
            limit: Maximum number of entries to return
            
        Returns:
            List of metric entries with build information
        """
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT m.*, b.start_time, b.status 
                FROM metrics m
                JOIN builds b ON m.build_hash = b.build_hash
                WHERE m.metric_name = ?
                ORDER BY m.recorded_at DESC
                LIMIT ?
            """, (metric_name, limit)).fetchall()
            
            return [dict(result) for result in results]
            
    # Test Results Management
    def record_test_result(self, test_name: str, status: str, build_hash: str = None,
                          category: str = 'general', duration: float = None, 
                          error_message: str = None, details: str = None):
        """Record a test result.
        
        Args:
            test_name: Name of the test
            status: Test status ('passed', 'failed', 'skipped')
            build_hash: Optional build identifier
            category: Test category
            duration: Test duration in seconds
            error_message: Error message if test failed
            details: Additional test details
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO test_results 
                (build_hash, test_name, test_category, status, duration_seconds, error_message, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (build_hash, test_name, category, status, duration, error_message, details))
            conn.commit()
            
    def get_test_results(self, build_hash: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get test results.
        
        Args:
            build_hash: Optional build identifier to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of test result dictionaries
        """
        with self._get_connection() as conn:
            if build_hash:
                results = conn.execute("""
                    SELECT * FROM test_results 
                    WHERE build_hash = ?
                    ORDER BY run_at DESC
                    LIMIT ?
                """, (build_hash, limit)).fetchall()
            else:
                results = conn.execute("""
                    SELECT * FROM test_results 
                    ORDER BY run_at DESC
                    LIMIT ?
                """, (limit,)).fetchall()
                
            return [dict(result) for result in results]
            
    # Plugin Data Management
    def plugin_set_data(self, plugin_name: str, key: str, value: Any, expires_in_seconds: Optional[int] = None):
        """Store data for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            key: Data key
            value: Value to store (will be JSON serialized)
            expires_in_seconds: Optional expiration time
        """
        expires_at = None
        if expires_in_seconds:
            expires_at = (datetime.now() + timedelta(seconds=expires_in_seconds)).isoformat()
            
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO plugin_data (plugin_name, data_key, data_value, expires_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (plugin_name, key, json.dumps(value), expires_at))
            conn.commit()
            
    def plugin_get_data(self, plugin_name: str, key: str) -> Any:
        """Get data for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            key: Data key
            
        Returns:
            Stored value or None if not found/expired
        """
        with self._get_connection() as conn:
            result = conn.execute("""
                SELECT data_value FROM plugin_data 
                WHERE plugin_name = ? AND data_key = ? 
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """, (plugin_name, key)).fetchone()
            
            if result:
                return json.loads(result['data_value'])
                
        return None
        
    def plugin_delete_data(self, plugin_name: str, key: str = None):
        """Delete plugin data.
        
        Args:
            plugin_name: Name of the plugin
            key: Optional specific key to delete. If None, deletes all data for plugin.
        """
        with self._get_connection() as conn:
            if key:
                conn.execute("DELETE FROM plugin_data WHERE plugin_name = ? AND data_key = ?", 
                           (plugin_name, key))
            else:
                conn.execute("DELETE FROM plugin_data WHERE plugin_name = ?", (plugin_name,))
            conn.commit()
            
    # Database Maintenance
    def cleanup_old_builds(self, keep_days: int = 30):
        """Clean up old build data.
        
        Args:
            keep_days: Number of days of build history to keep
        """
        cutoff_date = (datetime.now() - timedelta(days=keep_days)).isoformat()
        
        with self._get_connection() as conn:
            # Get build hashes to delete
            old_builds = conn.execute("""
                SELECT build_hash FROM builds WHERE start_time < ?
            """, (cutoff_date,)).fetchall()
            
            build_hashes = [row['build_hash'] for row in old_builds]
            
            if build_hashes:
                placeholders = ','.join('?' * len(build_hashes))
                
                # Delete related data
                conn.execute(f"DELETE FROM metrics WHERE build_hash IN ({placeholders})", build_hashes)
                conn.execute(f"DELETE FROM test_results WHERE build_hash IN ({placeholders})", build_hashes)
                conn.execute(f"DELETE FROM builds WHERE build_hash IN ({placeholders})", build_hashes)
                
            conn.commit()
            
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        with self._get_connection() as conn:
            stats = {}
            
            # Table counts
            for table in ['builds', 'cache', 'metrics', 'test_results', 'plugin_data']:
                result = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
                stats[f'{table}_count'] = result['count']
                
            # Database file size
            stats['db_size_bytes'] = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            # Recent activity
            recent_builds = conn.execute("""
                SELECT COUNT(*) as count FROM builds 
                WHERE start_time > datetime('now', '-7 days')
            """).fetchone()
            stats['recent_builds_7days'] = recent_builds['count']
            
            return stats