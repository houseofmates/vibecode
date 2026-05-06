"""
Hermes Web UI -- Database and session management optimizations.
Provides query optimization, connection pooling, and efficient session operations.
"""
import json
import logging
import sqlite3
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Connection pool for SQLite databases
class ConnectionPool:
    """Thread-safe SQLite connection pool."""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self.pool = []
        self.lock = threading.Lock()
        self.created_connections = 0
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database with optimized schema."""
        with self.get_connection() as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool."""
        conn = None
        try:
            with self.lock:
                if self.pool:
                    conn = self.pool.pop()
                elif self.created_connections < self.max_connections:
                    conn = sqlite3.connect(self.db_path, check_same_thread=False)
                    conn.row_factory = sqlite3.Row
                    self.created_connections += 1
                else:
                    # Wait for a connection to become available
                    while not self.pool:
                        time.sleep(0.1)
                    conn = self.pool.pop()
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                with self.lock:
                    self.pool.append(conn)

# Query cache for frequently accessed data
class QueryCache:
    """Thread-safe query result cache with TTL."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def get(self, query_hash: str) -> Optional[Any]:
        """Get cached query result."""
        with self.lock:
            if query_hash in self.cache:
                result, timestamp = self.cache[query_hash]
                if time.time() - timestamp < self.ttl:
                    self.access_times[query_hash] = time.time()
                    return result
                else:
                    # Expired
                    del self.cache[query_hash]
                    del self.access_times[query_hash]
            return None
    
    def set(self, query_hash: str, result: Any) -> None:
        """Cache query result."""
        with self.lock:
            # Remove oldest if at capacity
            if len(self.cache) >= self.max_size:
                oldest = min(self.access_times.items(), key=lambda x: x[1])
                del self.cache[oldest[0]]
                del self.access_times[oldest[0]]
            
            self.cache[query_hash] = (result, time.time())
            self.access_times[query_hash] = time.time()
    
    def invalidate(self, pattern: str = None) -> None:
        """Invalidate cache entries matching pattern."""
        with self.lock:
            if pattern is None:
                self.cache.clear()
                self.access_times.clear()
            else:
                to_remove = [k for k in self.cache.keys() if pattern in k]
                for k in to_remove:
                    del self.cache[k]
                    del self.access_times[k]

# Session batch operations
class SessionBatchProcessor:
    """Efficient batch processing of session operations."""
    
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self.pending_operations = []
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def add_operation(self, operation: str, session_id: str, data: Dict[str, Any] = None) -> None:
        """Add operation to batch queue."""
        with self.lock:
            self.pending_operations.append({
                'operation': operation,
                'session_id': session_id,
                'data': data or {},
                'timestamp': time.time()
            })
            
            if len(self.pending_operations) >= self.batch_size:
                self._process_batch()
    
    def _process_batch(self) -> None:
        """Process pending operations in batch."""
        if not self.pending_operations:
            return
        
        operations = self.pending_operations.copy()
        self.pending_operations.clear()
        
        # Submit batch processing to thread pool
        self.executor.submit(self._execute_batch, operations)
    
    def _execute_batch(self, operations: List[Dict[str, Any]]) -> None:
        """Execute batch of operations."""
        try:
            # Group operations by type
            groups = defaultdict(list)
            for op in operations:
                groups[op['operation']].append(op)
            
            # Process each group
            for operation_type, ops in groups.items():
                if operation_type == 'save':
                    self._batch_save(ops)
                elif operation_type == 'delete':
                    self._batch_delete(ops)
                elif operation_type == 'update_index':
                    self._batch_update_index(ops)
                    
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
    
    def _batch_save(self, operations: List[Dict[str, Any]]) -> None:
        """Batch save sessions."""
        # Implementation would depend on specific storage backend
        for op in operations:
            try:
                # Save individual session
                pass
            except Exception as e:
                logger.error(f"Batch save error for {op['session_id']}: {e}")
    
    def _batch_delete(self, operations: List[Dict[str, Any]]) -> None:
        """Batch delete sessions."""
        for op in operations:
            try:
                # Delete individual session
                pass
            except Exception as e:
                logger.error(f"Batch delete error for {op['session_id']}: {e}")
    
    def _batch_update_index(self, operations: List[Dict[str, Any]]) -> None:
        """Batch update session index."""
        try:
            # Update index in bulk
            pass
        except Exception as e:
            logger.error(f"Batch index update error: {e}")
    
    def flush(self) -> None:
        """Process any remaining operations."""
        with self.lock:
            if self.pending_operations:
                self._process_batch()

# Optimized session queries
class OptimizedSessionQueries:
    """Optimized queries for session operations."""
    
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.query_cache = QueryCache()
        self.connection_pool = None
        
        # Try to create SQLite database for indexing
        self.db_path = session_dir / 'sessions.db'
        try:
            self.connection_pool = ConnectionPool(str(self.db_path))
            self._create_indexes()
        except Exception as e:
            logger.warning(f"Could not create session database: {e}")
    
    def _create_indexes(self) -> None:
        """Create database indexes for performance."""
        if not self.connection_pool:
            return
            
        with self.connection_pool.get_connection() as conn:
            # Create sessions table if not exists
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT,
                    workspace TEXT,
                    model TEXT,
                    created_at REAL,
                    updated_at REAL,
                    message_count INTEGER,
                    pinned INTEGER DEFAULT 0,
                    archived INTEGER DEFAULT 0,
                    project_id TEXT,
                    profile TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    estimated_cost REAL DEFAULT 0.0,
                    personality TEXT,
                    machine_id TEXT,
                    machine_hostname TEXT
                )
            ''')
            
            # Create indexes for common queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON sessions(workspace)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_model ON sessions(model)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_pinned ON sessions(pinned)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_archived ON sessions(archived)')
            conn.commit()
    
    def get_sessions_batch(self, session_ids: List[str]) -> Dict[str, Any]:
        """Get multiple sessions efficiently."""
        query_hash = f"batch_get_{hash(tuple(session_ids))}"
        cached = self.query_cache.get(query_hash)
        if cached:
            return cached
        
        result = {}
        
        if self.connection_pool:
            # Use database query
            placeholders = ','.join(['?'] * len(session_ids))
            with self.connection_pool.get_connection() as conn:
                cursor = conn.execute(
                    f'SELECT * FROM sessions WHERE session_id IN ({placeholders})',
                    session_ids
                )
                for row in cursor:
                    result[row['session_id']] = dict(row)
        else:
            # Fall back to file system
            for session_id in session_ids:
                try:
                    session_file = self.session_dir / f'{session_id}.json'
                    if session_file.exists():
                        result[session_id] = json.loads(session_file.read_text())
                except Exception as e:
                    logger.error(f"Error loading session {session_id}: {e}")
        
        self.query_cache.set(query_hash, result)
        return result
    
    def search_sessions(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search sessions efficiently."""
        query_hash = f"search_{query}_{limit}"
        cached = self.query_cache.get(query_hash)
        if cached:
            return cached
        
        result = []
        
        if self.connection_pool:
            # Use database FTS if available
            with self.connection_pool.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM sessions 
                    WHERE title LIKE ? OR workspace LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', limit))
                result = [dict(row) for row in cursor]
        else:
            # Fall back to file system search
            for session_file in self.session_dir.glob('*.json'):
                if len(result) >= limit:
                    break
                    
                try:
                    data = json.loads(session_file.read_text())
                    if query.lower() in data.get('title', '').lower() or \
                       query.lower() in data.get('workspace', '').lower():
                        result.append(data)
                except Exception:
                    continue
        
            result.sort(key=lambda x: x.get('updated_at', 0), reverse=True)
            result = result[:limit]
        
        self.query_cache.set(query_hash, result)
        return result
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics efficiently."""
        query_hash = "session_stats"
        cached = self.query_cache.get(query_hash)
        if cached:
            return cached
        
        stats = {
            'total_sessions': 0,
            'active_sessions': 0,
            'pinned_sessions': 0,
            'archived_sessions': 0,
            'total_messages': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'avg_session_duration': 0.0
        }
        
        if self.connection_pool:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN archived = 0 THEN 1 ELSE 0 END) as active,
                        SUM(pinned) as pinned,
                        SUM(archived) as archived,
                        SUM(message_count) as total_messages,
                        SUM(input_tokens + output_tokens) as total_tokens,
                        SUM(estimated_cost) as total_cost
                    FROM sessions
                ''')
                row = cursor.fetchone()
                if row:
                    stats.update({
                        'total_sessions': row['total'],
                        'active_sessions': row['active'],
                        'pinned_sessions': row['pinned'],
                        'archived_sessions': row['archived'],
                        'total_messages': row['total_messages'],
                        'total_tokens': row['total_tokens'],
                        'total_cost': row['total_cost']
                    })
        
        self.query_cache.set(query_hash, stats)
        return stats
    
    def invalidate_cache(self, pattern: str = None) -> None:
        """Invalidate query cache."""
        self.query_cache.invalidate(pattern)

# Global optimizer instance
_SESSION_OPTIMIZER = None

def get_session_optimizer() -> OptimizedSessionQueries:
    """Get global session optimizer instance."""
    global _SESSION_OPTIMIZER
    if _SESSION_OPTIMIZER is None:
        from api.config import SESSION_DIR
        _SESSION_OPTIMIZER = OptimizedSessionQueries(SESSION_DIR)
    return _SESSION_OPTIMIZER

def optimize_session_operations() -> None:
    """Initialize session operation optimizations."""
    optimizer = get_session_optimizer()
    logger.info("Session optimization initialized")

# Background optimization tasks
def start_optimization_tasks(interval: int = 300) -> None:
    """Start background optimization tasks."""
    def optimization_loop():
        while True:
            try:
                optimizer = get_session_optimizer()
                
                # Clean up expired cache entries
                optimizer.invalidate_cache()
                
                # Update database statistics
                if optimizer.connection_pool:
                    with optimizer.connection_pool.get_connection() as conn:
                        conn.execute('ANALYZE')
                        conn.commit()
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Optimization task error: {e}")
                time.sleep(60)
    
    thread = threading.Thread(target=optimization_loop, daemon=True)
    thread.start()
    logger.info("Optimization tasks started")