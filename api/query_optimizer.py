"""
Advanced database query optimization with intelligent indexing and query analysis.
Optimizes database operations for better performance and reduced load.
"""
import sqlite3
import time
import logging
import threading
import re
from typing import Dict, List, Any, Optional, Tuple, Callable
from collections import defaultdict, deque
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class QueryStats:
    """Statistics for a query execution."""
    query: str
    execution_time: float
    rows_returned: int
    timestamp: float
    cache_hit: bool = False
    index_used: str = None

@dataclass
class IndexRecommendation:
    """Recommended index for optimization."""
    table: str
    columns: List[str]
    index_type: str
    estimated_improvement: float
    query_count: int

class QueryOptimizer:
    """Advanced database query optimizer."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
        self.lock = threading.Lock()
        
        # Query analysis
        self.query_history: deque = deque(maxlen=1000)
        self.query_patterns: Dict[str, List[QueryStats]] = defaultdict(list)
        self.slow_queries: List[QueryStats] = []
        self.index_recommendations: List[IndexRecommendation] = []
        
        # Optimization settings
        self.slow_query_threshold = 0.1  # 100ms
        self.max_history = 1000
        self.analysis_interval = 100  # Analyze every 100 queries
        
        # Query templates for common patterns
        self.query_templates = {
            'select_by_id': re.compile(r'SELECT\s+.*?\s+FROM\s+(\w+)\s+WHERE\s+(\w+)\s*=\s*?', re.IGNORECASE),
            'select_by_session': re.compile(r'SELECT\s+.*?\s+FROM\s+sessions\s+WHERE\s+session_id\s*=\s*?', re.IGNORECASE),
            'select_list': re.compile(r'SELECT\s+.*?\s+FROM\s+(\w+)(?:\s+WHERE\s+.*?)?(?:\s+ORDER\s+BY\s+.*?)?(?:\s+LIMIT\s+.*?)?$', re.IGNORECASE),
            'insert': re.compile(r'INSERT\s+INTO\s+(\w+)', re.IGNORECASE),
            'update': re.compile(r'UPDATE\s+(\w+)\s+SET', re.IGNORECASE),
            'delete': re.compile(r'DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+.*?)?$', re.IGNORECASE)
        }
        
        self._connect()
        self._analyze_existing_schema()
        logger.info(f"Query optimizer initialized for {db_path}")
    
    def _connect(self):
        """Establish database connection with optimizations."""
        self.connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0,
            isolation_level=None
        )
        
        # Enable optimizations
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('PRAGMA synchronous=NORMAL')
        self.connection.execute('PRAGMA cache_size=10000')
        self.connection.execute('PRAGMA temp_store=MEMORY')
        self.connection.execute('PRAGMA mmap_size=268435456')  # 256MB
        self.connection.execute('PRAGMA optimize')
    
    def _analyze_existing_schema(self):
        """Analyze existing database schema for optimization opportunities."""
        try:
            cursor = self.connection.cursor()
            
            # Get table info
            cursor.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            
            tables = cursor.fetchall()
            
            for table_name, create_sql in tables:
                self._analyze_table(table_name, create_sql)
            
            logger.info(f"Schema analysis completed for {len(tables)} tables")
            
        except Exception as e:
            logger.error(f"Schema analysis error: {e}")
    
    def _analyze_table(self, table_name: str, create_sql: str):
        """Analyze individual table for optimization opportunities."""
        try:
            cursor = self.connection.cursor()
            
            # Get table statistics
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Analyze common query patterns
            if table_name == 'sessions':
                self._recommend_sessions_indexes(table_name, row_count)
            elif table_name == 'messages':
                self._recommend_messages_indexes(table_name, row_count)
            elif table_name == 'workspaces':
                self._recommend_workspace_indexes(table_name, row_count)
            
        except Exception as e:
            logger.error(f"Table analysis error for {table_name}: {e}")
    
    def _recommend_sessions_indexes(self, table_name: str, row_count: int):
        """Recommend indexes for sessions table."""
        recommendations = [
            IndexRecommendation(
                table=table_name,
                columns=['session_id'],
                index_type='UNIQUE',
                estimated_improvement=0.8,
                query_count=self._count_queries_using_columns(['session_id'])
            ),
            IndexRecommendation(
                table=table_name,
                columns=['created_at'],
                index_type='INDEX',
                estimated_improvement=0.6,
                query_count=self._count_queries_using_columns(['created_at'])
            ),
            IndexRecommendation(
                table=table_name,
                columns=['workspace'],
                index_type='INDEX',
                estimated_improvement=0.5,
                query_count=self._count_queries_using_columns(['workspace'])
            )
        ]
        
        self.index_recommendations.extend(recommendations)
    
    def _recommend_messages_indexes(self, table_name: str, row_count: int):
        """Recommend indexes for messages table."""
        recommendations = [
            IndexRecommendation(
                table=table_name,
                columns=['session_id', 'timestamp'],
                index_type='INDEX',
                estimated_improvement=0.9,
                query_count=self._count_queries_using_columns(['session_id', 'timestamp'])
            ),
            IndexRecommendation(
                table=table_name,
                columns=['role'],
                index_type='INDEX',
                estimated_improvement=0.3,
                query_count=self._count_queries_using_columns(['role'])
            )
        ]
        
        self.index_recommendations.extend(recommendations)
    
    def _recommend_workspace_indexes(self, table_name: str, row_count: int):
        """Recommend indexes for workspace table."""
        recommendations = [
            IndexRecommendation(
                table=table_name,
                columns=['workspace_id'],
                index_type='UNIQUE',
                estimated_improvement=0.7,
                query_count=self._count_queries_using_columns(['workspace_id'])
            )
        ]
        
        self.index_recommendations.extend(recommendations)
    
    def _count_queries_using_columns(self, columns: List[str]) -> int:
        """Count queries that use specific columns."""
        count = 0
        for pattern_name, pattern in self.query_templates.items():
            if pattern_name.startswith('select'):
                for stats in self.query_patterns[pattern_name]:
                    if any(col in stats.query.lower() for col in columns):
                        count += 1
        return count
    
    def execute_query(self, query: str, params: Tuple = None, use_cache: bool = True) -> List[Dict]:
        """Execute query with optimization and monitoring."""
        start_time = time.time()
        cache_hit = False
        index_used = None
        
        try:
            with self.lock:
                cursor = self.connection.cursor()
                
                # Check query cache if enabled
                if use_cache:
                    cached_result = self._check_query_cache(query, params)
                    if cached_result is not None:
                        cache_hit = True
                        execution_time = time.time() - start_time
                        self._record_query_stats(query, execution_time, len(cached_result), cache_hit, index_used)
                        return cached_result
                
                # Analyze and optimize query
                optimized_query, index_suggestion = self._optimize_query(query)
                
                # Use EXPLAIN QUERY PLAN to check index usage
                if index_suggestion:
                    try:
                        explain_cursor = self.connection.cursor()
                        explain_cursor.execute(f"EXPLAIN QUERY PLAN {optimized_query}", params)
                        plan = explain_cursor.fetchone()
                        if plan:
                            index_used = plan[3] if len(plan) > 3 else None
                    except:
                        pass
                
                # Execute query
                cursor.execute(optimized_query, params or ())
                result = cursor.fetchall()
                
                # Convert to list of dictionaries
                columns = [desc[0] for desc in cursor.description]
                result_dict = [dict(zip(columns, row)) for row in result]
                
                execution_time = time.time() - start_time
                
                # Cache result if appropriate
                if use_cache and self._should_cache_query(query):
                    self._cache_query_result(query, params, result_dict)
                
                # Record statistics
                self._record_query_stats(query, execution_time, len(result_dict), cache_hit, index_used)
                
                return result_dict
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Query execution error: {e}")
            self._record_query_stats(query, execution_time, 0, cache_hit, index_used)
            raise
    
    def _optimize_query(self, query: str) -> Tuple[str, str]:
        """Optimize individual query."""
        optimized = query
        index_suggestion = None
        
        # Remove unnecessary whitespace
        optimized = re.sub(r'\s+', ' ', optimized.strip())
        
        # Add LIMIT to large result sets if not present
        if (optimized.upper().startswith('SELECT') and 
            'LIMIT' not in optimized.upper() and 
            'sessions' in optimized.lower()):
            # Add reasonable LIMIT for session queries
            if 'WHERE session_id' in optimized.lower():
                optimized += ' LIMIT 1000'
        
        # Suggest index for WHERE clauses
        where_match = re.search(r'WHERE\s+(\w+)\s*=\s*', optimized, re.IGNORECASE)
        if where_match:
            column = where_match.group(1)
            table_match = re.search(r'FROM\s+(\w+)', optimized, re.IGNORECASE)
            if table_match:
                table = table_match.group(1)
                index_suggestion = f"CREATE INDEX IF NOT EXISTS idx_{table}_{column} ON {table}({column})"
        
        return optimized, index_suggestion
    
    def _check_query_cache(self, query: str, params: Tuple) -> Optional[List[Dict]]:
        """Check if query result is cached."""
        # Simple in-memory cache for frequently used queries
        cache_key = self._get_cache_key(query, params)
        
        # This would integrate with the advanced_cache module
        try:
            from api.advanced_cache import get_cache_key, get_cache as get_from_cache
            cache_key_full = get_cache_key('query_result', cache_key)
            return get_from_cache(cache_key_full)
        except:
            return None
    
    def _cache_query_result(self, query: str, params: Tuple, result: List[Dict]):
        """Cache query result."""
        try:
            from api.advanced_cache import get_cache_key, set_cache as set_to_cache
            cache_key = self._get_cache_key(query, params)
            cache_key_full = get_cache_key('query_result', cache_key)
            set_to_cache(cache_key_full, result, ttl=300)  # 5 minutes
        except:
            pass
    
    def _get_cache_key(self, query: str, params: Tuple) -> str:
        """Generate cache key for query."""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:16]
        params_hash = hashlib.md5(str(params).encode()).hexdigest()[:16] if params else ''
        return f"{query_hash}:{params_hash}"
    
    def _should_cache_query(self, query: str) -> bool:
        """Determine if query should be cached."""
        query_upper = query.upper()
        
        # Cache SELECT queries but not DML
        if (query_upper.startswith('SELECT') and 
            not query_upper.startswith('SELECT COUNT') and
            'sessions' in query.upper()):
            return True
        
        return False
    
    def _record_query_stats(self, query: str, execution_time: float, 
                          rows_returned: int, cache_hit: bool, index_used: str):
        """Record query execution statistics."""
        stats = QueryStats(
            query=query,
            execution_time=execution_time,
            rows_returned=rows_returned,
            timestamp=time.time(),
            cache_hit=cache_hit,
            index_used=index_used
        )
        
        self.query_history.append(stats)
        
        # Track slow queries
        if execution_time > self.slow_query_threshold:
            self.slow_queries.append(stats)
            logger.warning(f"Slow query detected: {execution_time:.3f}s - {query[:100]}...")
        
        # Categorize query pattern
        for pattern_name, pattern in self.query_templates.items():
            if pattern.search(query):
                self.query_patterns[pattern_name].append(stats)
                break
        
        # Trigger analysis periodically
        if len(self.query_history) % self.analysis_interval == 0:
            self._analyze_performance()
    
    def _analyze_performance(self):
        """Analyze query performance and generate recommendations."""
        if len(self.query_history) < 50:
            return
        
        # Calculate statistics
        total_queries = len(self.query_history)
        total_time = sum(q.execution_time for q in self.query_history)
        avg_time = total_time / total_queries
        slow_count = len(self.slow_queries)
        slow_rate = slow_count / total_queries
        
        # Cache hit rate
        cache_hits = sum(1 for q in self.query_history if q.cache_hit)
        cache_hit_rate = cache_hits / total_queries
        
        logger.info(f"Query Performance Analysis:")
        logger.info(f"  Total queries: {total_queries}")
        logger.info(f"  Average time: {avg_time:.3f}s")
        logger.info(f"  Slow queries: {slow_count} ({slow_rate:.1%})")
        logger.info(f"  Cache hit rate: {cache_hit_rate:.1%}")
        
        # Generate optimization recommendations
        self._generate_optimization_recommendations()
    
    def _generate_optimization_recommendations(self):
        """Generate optimization recommendations based on analysis."""
        recommendations = []
        
        # Analyze slow queries
        if self.slow_queries:
            # Find common patterns in slow queries
            slow_patterns = defaultdict(int)
            for query in self.slow_queries:
                for pattern_name, pattern in self.query_templates.items():
                    if pattern.search(query.query):
                        slow_patterns[pattern_name] += 1
                        break
            
            # Recommend indexes for most common slow patterns
            for pattern, count in sorted(slow_patterns.items(), key=lambda x: x[1], reverse=True)[:3]:
                if pattern == 'select_by_session':
                    recommendations.append("Consider adding composite index on (session_id, timestamp)")
                elif pattern == 'select_by_id':
                    recommendations.append("Ensure primary key indexes are properly defined")
        
        # Add existing index recommendations
        recommendations.extend([
            f"Create index: {rec.table}({', '.join(rec.columns)})" 
            for rec in sorted(self.index_recommendations, key=lambda x: x.estimated_improvement, reverse=True)[:5]
        ])
        
        if recommendations:
            logger.info("Optimization Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                logger.info(f"  {i}. {rec}")
    
    def create_recommended_indexes(self):
        """Create recommended database indexes."""
        if not self.index_recommendations:
            logger.info("No index recommendations available")
            return
        
        created_count = 0
        for recommendation in self.index_recommendations:
            try:
                if recommendation.index_type == 'UNIQUE':
                    sql = f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{recommendation.table}_{'_'.join(recommendation.columns)} ON {recommendation.table}({', '.join(recommendation.columns)})"
                else:
                    sql = f"CREATE INDEX IF NOT EXISTS idx_{recommendation.table}_{'_'.join(recommendation.columns)} ON {recommendation.table}({', '.join(recommendation.columns)})"
                
                self.connection.execute(sql)
                self.connection.commit()
                created_count += 1
                logger.info(f"Created index: idx_{recommendation.table}_{'_'.join(recommendation.columns)}")
                
            except Exception as e:
                logger.error(f"Failed to create index {recommendation.table}: {e}")
        
        logger.info(f"Created {created_count} recommended indexes")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        if not self.query_history:
            return {'message': 'No query history available'}
        
        total_queries = len(self.query_history)
        total_time = sum(q.execution_time for q in self.query_history)
        avg_time = total_time / total_queries
        slow_count = len(self.slow_queries)
        
        # Cache statistics
        cache_hits = sum(1 for q in self.query_history if q.cache_hit)
        cache_hit_rate = cache_hits / total_queries
        
        # Index usage statistics
        index_usage = defaultdict(int)
        for q in self.query_history:
            if q.index_used:
                index_usage[q.index_used] += 1
        
        return {
            'total_queries': total_queries,
            'average_execution_time': avg_time,
            'slow_queries': slow_count,
            'slow_query_rate': slow_count / total_queries,
            'cache_hit_rate': cache_hit_rate,
            'index_recommendations': [
                {
                    'table': rec.table,
                    'columns': rec.columns,
                    'type': rec.index_type,
                    'estimated_improvement': rec.estimated_improvement,
                    'query_count': rec.query_count
                } for rec in self.index_recommendations
            ],
            'index_usage': dict(index_usage),
            'recent_slow_queries': [
                {
                    'query': q.query[:100] + '...' if len(q.query) > 100 else q.query,
                    'execution_time': q.execution_time,
                    'rows_returned': q.rows_returned,
                    'timestamp': q.timestamp
                } for q in self.slow_queries[-10:]
            ]
        }
    
    def optimize_database(self):
        """Run database optimization commands."""
        try:
            logger.info("Running database optimization...")
            
            # Analyze tables
            self.connection.execute("ANALYZE")
            
            # Vacuum to reclaim space
            self.connection.execute("VACUUM")
            
            # Rebuild indexes
            self.connection.execute("REINDEX")
            
            self.connection.commit()
            logger.info("Database optimization completed")
            
        except Exception as e:
            logger.error(f"Database optimization error: {e}")
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Query optimizer database connection closed")

# Global query optimizer
_query_optimizer: Optional[QueryOptimizer] = None

def initialize_query_optimizer(db_path: str):
    """Initialize global query optimizer."""
    global _query_optimizer
    _query_optimizer = QueryOptimizer(db_path)
    logger.info("Global query optimizer initialized")

def execute_optimized_query(query: str, params: Tuple = None, use_cache: bool = True) -> List[Dict]:
    """Execute query through global optimizer."""
    if not _query_optimizer:
        raise RuntimeError("Query optimizer not initialized")
    return _query_optimizer.execute_query(query, params, use_cache)

def get_query_performance_report() -> Dict[str, Any]:
    """Get query performance report."""
    if _query_optimizer:
        return _query_optimizer.get_performance_report()
    return {}

def optimize_database():
    """Optimize database through global optimizer."""
    if _query_optimizer:
        _query_optimizer.optimize_database()

def create_recommended_indexes():
    """Create recommended indexes."""
    if _query_optimizer:
        _query_optimizer.create_recommended_indexes()

def close_query_optimizer():
    """Close query optimizer."""
    if _query_optimizer:
        _query_optimizer.close()