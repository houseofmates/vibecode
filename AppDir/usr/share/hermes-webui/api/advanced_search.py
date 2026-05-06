"""
Hermes Web UI -- Advanced search with full-text indexing.
Provides intelligent search across sessions, messages, files, and wiki content.
"""
import json
import logging
import re
import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict
import sqlite3
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Search result with relevance scoring."""
    id: str
    type: str  # session, message, file, wiki
    title: str
    content: str
    score: float
    metadata: Dict[str, Any]
    highlights: List[str]
    created_at: float
    updated_at: float

@dataclass
class SearchQuery:
    """Search query with filters and options."""
    query: str
    filters: Dict[str, Any]
    limit: int = 50
    offset: int = 0
    sort_by: str = "relevance"  # relevance, date, title
    order: str = "desc"  # asc, desc
    include_highlights: bool = True

class FullTextIndex:
    """Full-text search index with SQLite FTS5."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize full-text search database."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable FTS5
            conn.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                    id UNINDEXED,
                    type UNINDEXED,
                    title,
                    content,
                    metadata UNINDEXED,
                    created_at UNINDEXED,
                    updated_at UNINDEXED,
                    tokenize='porter unicode61'
                )
            ''')
            
            # Create regular tables for metadata
            conn.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    metadata TEXT,
                    created_at REAL,
                    updated_at REAL,
                    indexed_at REAL DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_updated ON documents(updated_at)')
            
            conn.commit()
    
    def add_document(self, doc_id: str, doc_type: str, title: str, 
                   content: str, metadata: Dict[str, Any], 
                   created_at: float = None, updated_at: float = None) -> None:
        """Add document to search index."""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    now = time.time()
                    
                    # Insert into documents table
                    conn.execute('''
                        INSERT OR REPLACE INTO documents 
                        (id, type, title, content, metadata, created_at, updated_at, indexed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        doc_id, doc_type, title, content,
                        json.dumps(metadata), created_at or now, updated_at or now, now
                    ))
                    
                    # Insert into FTS index
                    conn.execute('''
                        INSERT OR REPLACE INTO search_index 
                        (id, type, title, content, metadata, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        doc_id, doc_type, title, content,
                        json.dumps(metadata), created_at or now, updated_at or now
                    ))
                    
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"Error indexing document {doc_id}: {e}")
    
    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> None:
        """Update existing document in index."""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Build update query dynamically
                    set_clauses = []
                    values = []
                    
                    for field, value in updates.items():
                        if field in ['title', 'content']:
                            set_clauses.append(f"{field} = ?")
                            values.append(value)
                        elif field == 'metadata':
                            set_clauses.append("metadata = ?")
                            values.append(json.dumps(value))
                        elif field in ['created_at', 'updated_at']:
                            set_clauses.append(f"{field} = ?")
                            values.append(value)
                    
                    if set_clauses:
                        set_clauses.append("indexed_at = ?")
                        values.append(time.time())
                        values.append(doc_id)
                        
                        conn.execute(f'''
                            UPDATE documents SET {', '.join(set_clauses)}
                            WHERE id = ?
                        ''', values)
                        
                        # Update FTS index as well
                        fts_updates = {k: v for k, v in updates.items() if k in ['title', 'content']}
                        if fts_updates:
                            fts_clauses = []
                            fts_values = []
                            
                            for field, value in fts_updates.items():
                                fts_clauses.append(f"{field} = ?")
                                fts_values.append(value)
                            
                            fts_values.append(doc_id)
                            
                            conn.execute(f'''
                                UPDATE search_index SET {', '.join(fts_clauses)}
                                WHERE id = ?
                            ''', fts_values)
                        
                        conn.commit()
                        
            except Exception as e:
                logger.error(f"Error updating document {doc_id}: {e}")
    
    def delete_document(self, doc_id: str) -> None:
        """Delete document from index."""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
                    conn.execute('DELETE FROM search_index WHERE id = ?', (doc_id,))
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"Error deleting document {doc_id}: {e}")
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform full-text search with ranking."""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Build FTS query
                    fts_query = self._build_fts_query(query)
                    
                    # Execute search with ranking
                    cursor = conn.execute(f'''
                        SELECT 
                            si.id,
                            si.type,
                            si.title,
                            snippet(search_index.content, 1, '<mark>', '</mark>', '...', 32) as content_snippet,
                            snippet(search_index.title, 2, '<mark>', '</mark>', '...', 64) as title_snippet,
                            bm25(search_index) as relevance_score,
                            si.metadata,
                            si.created_at,
                            si.updated_at
                        FROM search_index si
                        WHERE search_index MATCH ?
                        {self._build_filter_clause(query.filters)}
                        {self._build_sort_clause(query.sort_by, query.order)}
                        LIMIT ? OFFSET ?
                    ''', (fts_query, query.limit, query.offset))
                    
                    results = []
                    for row in cursor:
                        metadata = json.loads(row['metadata']) if row['metadata'] else {}
                        
                        # Generate highlights
                        highlights = []
                        if query.include_highlights:
                            highlights = self._generate_highlights(
                                query.query, 
                                row['title'], 
                                row['content_snippet']
                            )
                        
                        result = SearchResult(
                            id=row['id'],
                            type=row['type'],
                            title=row['title'],
                            content=row['content_snippet'],
                            score=row['relevance_score'],
                            metadata=metadata,
                            highlights=highlights,
                            created_at=row['created_at'],
                            updated_at=row['updated_at']
                        )
                        results.append(result)
                    
                    return results
                    
            except Exception as e:
                logger.error(f"Search error: {e}")
                return []
    
    def _build_fts_query(self, query: SearchQuery) -> str:
        """Build FTS query from search terms."""
        # Clean and tokenize query
        terms = re.findall(r'\w+', query.query.lower())
        
        if not terms:
            return '*'
        
        # Build query with AND/OR logic
        query_parts = []
        for term in terms:
            if len(term) > 2:
                # Use NEAR for phrases and partial matching
                query_parts.append(f'{term}*')
            else:
                query_parts.append(f'"{term}"')
        
        return ' OR '.join(query_parts)
    
    def _build_filter_clause(self, filters: Dict[str, Any]) -> str:
        """Build SQL filter clause."""
        if not filters:
            return ''
        
        conditions = []
        
        if 'type' in filters:
            types = filters['type'] if isinstance(filters['type'], list) else [filters['type']]
            placeholders = ','.join(['?' for _ in types])
            conditions.append(f'si.type IN ({placeholders})')
        
        if 'date_from' in filters:
            conditions.append('si.created_at >= ?')
        
        if 'date_to' in filters:
            conditions.append('si.created_at <= ?')
        
        if 'session_id' in filters:
            conditions.append('JSON_EXTRACT(si.metadata, "$.session_id") = ?')
        
        return f' AND {" AND ".join(conditions)}' if conditions else ''
    
    def _build_sort_clause(self, sort_by: str, order: str) -> str:
        """Build SQL sort clause."""
        valid_sort_fields = ['relevance', 'date', 'title']
        if sort_by not in valid_sort_fields:
            sort_by = 'relevance'
        
        valid_orders = ['asc', 'desc']
        if order not in valid_orders:
            order = 'desc'
        
        if sort_by == 'relevance':
            return f'ORDER BY relevance_score {order.upper()}'
        elif sort_by == 'date':
            return f'ORDER BY si.updated_at {order.upper()}'
        elif sort_by == 'title':
            return f'ORDER BY si.title {order.upper()}'
        
        return 'ORDER BY relevance_score DESC'
    
    def _generate_highlights(self, query: str, title: str, content: str) -> List[str]:
        """Generate search highlights."""
        highlights = []
        terms = re.findall(r'\w+', query.lower())
        
        for term in terms:
            if len(term) > 2:
                # Highlight in title
                title_matches = re.findall(
                    rf'(.{{0,30}}{re.escape(term)}(.{{0,30}})', 
                    title, 
                    re.IGNORECASE
                )
                for match in title_matches:
                    highlights.append(f"Title: ...{match[0]}{match[1]}...")
                
                # Highlight in content
                content_matches = re.findall(
                    rf'(.{{0,50}}{re.escape(term)}(.{{0,50}})', 
                    content, 
                    re.IGNORECASE
                )
                for match in content_matches[:2]:  # Limit content highlights
                    highlights.append(f"Content: ...{match[0]}{match[1]}...")
        
        return highlights[:5]  # Limit total highlights
    
    def get_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query."""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('''
                        SELECT DISTINCT title
                        FROM search_index
                        WHERE title MATCH ? || '*'
                        LIMIT ?
                    ''', (query, limit))
                    
                    return [row[0] for row in cursor]
                    
            except Exception as e:
                logger.error(f"Suggestion error: {e}")
                return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search index statistics."""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('''
                        SELECT 
                            type,
                            COUNT(*) as count,
                            AVG(LENGTH(content)) as avg_content_length
                        FROM documents
                        GROUP BY type
                    ''')
                    
                    type_stats = {}
                    total_docs = 0
                    
                    for row in cursor:
                        type_stats[row['type']] = {
                            'count': row['count'],
                            'avg_content_length': row['avg_content_length']
                        }
                        total_docs += row['count']
                    
                    # Get database size
                    cursor = conn.execute('PRAGMA page_size')
                    page_size = cursor.fetchone()[0]
                    
                    cursor = conn.execute('PRAGMA page_count')
                    page_count = cursor.fetchone()[0]
                    
                    db_size = page_size * page_count
                    
                    return {
                        'total_documents': total_docs,
                        'type_breakdown': type_stats,
                        'database_size_bytes': db_size,
                        'database_size_mb': round(db_size / (1024 * 1024), 2)
                    }
                    
            except Exception as e:
                logger.error(f"Stats error: {e}")
                return {}

class AdvancedSearchEngine:
    """Advanced search engine with multiple data sources."""
    
    def __init__(self, index_path: str):
        self.index = FullTextIndex(index_path)
        self.session_dir = Path.home() / '.hermes-webui' / 'sessions'
        self.wiki_dir = Path.home() / '.hermes-webui' / 'wiki'
        self.workspace_dir = Path.cwd()
    
    def index_all_content(self) -> None:
        """Index all available content."""
        logger.info("Starting full content indexing...")
        
        # Index sessions
        self._index_sessions()
        
        # Index wiki content
        self._index_wiki_content()
        
        # Index workspace files
        self._index_workspace_files()
        
        logger.info("Content indexing completed")
    
    def _index_sessions(self) -> None:
        """Index session data."""
        if not self.session_dir.exists():
            return
        
        for session_file in self.session_dir.glob('*.json'):
            try:
                data = json.loads(session_file.read_text())
                
                # Index session metadata
                self.index.add_document(
                    doc_id=f"session_{data['session_id']}",
                    doc_type='session',
                    title=data.get('title', 'Untitled'),
                    content=data.get('title', '') + ' ' + ' '.join(
                        msg.get('content', '') for msg in data.get('messages', [])[:10]
                    ),
                    metadata={
                        'session_id': data['session_id'],
                        'workspace': data.get('workspace'),
                        'model': data.get('model'),
                        'message_count': len(data.get('messages', [])),
                        'file_path': str(session_file)
                    },
                    created_at=data.get('created_at'),
                    updated_at=data.get('updated_at')
                )
                
                # Index individual messages
                for i, message in enumerate(data.get('messages', [])):
                    if message.get('content'):
                        self.index.add_document(
                            doc_id=f"message_{data['session_id']}_{i}",
                            doc_type='message',
                            title=f"Message from {message.get('role', 'unknown')}",
                            content=message['content'],
                            metadata={
                                'session_id': data['session_id'],
                                'role': message.get('role'),
                                'message_index': i,
                                'file_path': str(session_file)
                            },
                            created_at=message.get('timestamp', data.get('created_at')),
                            updated_at=message.get('timestamp', data.get('updated_at'))
                        )
                        
            except Exception as e:
                logger.error(f"Error indexing session {session_file}: {e}")
    
    def _index_wiki_content(self) -> None:
        """Index wiki content."""
        if not self.wiki_dir.exists():
            return
        
        for wiki_file in self.wiki_dir.rglob('*.md'):
            try:
                content = wiki_file.read_text()
                title = self._extract_title_from_markdown(content)
                
                self.index.add_document(
                    doc_id=f"wiki_{wiki_file.stem}",
                    doc_type='wiki',
                    title=title or wiki_file.stem,
                    content=content,
                    metadata={
                        'file_path': str(wiki_file),
                        'file_size': len(content),
                        'last_modified': wiki_file.stat().st_mtime
                    }
                )
                
            except Exception as e:
                logger.error(f"Error indexing wiki file {wiki_file}: {e}")
    
    def _index_workspace_files(self) -> None:
        """Index workspace files."""
        if not self.workspace_dir.exists():
            return
        
        # Index common file types
        file_extensions = ['.py', '.js', '.md', '.txt', '.json', '.yaml', '.yml']
        
        for file_path in self.workspace_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix in file_extensions:
                try:
                    if file_path.stat().st_size > 1024 * 1024:  # Skip files > 1MB
                        continue
                    
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    
                    self.index.add_document(
                        doc_id=f"file_{hashlib.md5(str(file_path).encode()).hexdigest()}",
                        doc_type='file',
                        title=file_path.name,
                        content=content,
                        metadata={
                            'file_path': str(file_path),
                            'file_size': file_path.stat().st_size,
                            'file_extension': file_path.suffix,
                            'relative_path': str(file_path.relative_to(self.workspace_dir))
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Error indexing file {file_path}: {e}")
    
    def _extract_title_from_markdown(self, content: str) -> Optional[str]:
        """Extract title from markdown content."""
        # Look for # heading
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # Look for first non-empty line
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                return line[:100]  # First 100 chars
        
        return None
    
    def search(self, query: SearchQuery) -> Dict[str, Any]:
        """Perform advanced search."""
        # Main FTS search
        results = self.index.search(query)
        
        # Add suggestions
        suggestions = self.index.get_suggestions(query.query)
        
        # Group results by type
        grouped_results = defaultdict(list)
        for result in results:
            grouped_results[result.type].append(asdict(result))
        
        return {
            'query': asdict(query),
            'results': [asdict(r) for r in results],
            'grouped_results': dict(grouped_results),
            'total_count': len(results),
            'suggestions': suggestions,
            'search_time': time.time()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        index_stats = self.index.get_stats()
        
        return {
            'index_stats': index_stats,
            'search_engine': {
                'version': '1.0',
                'features': [
                    'Full-text search (FTS5)',
                    'BM25 ranking',
                    'Search suggestions',
                    'Result highlighting',
                    'Multi-source indexing'
                ]
            }
        }

# Global search engine
ADVANCED_SEARCH = None

def get_advanced_search_engine(index_path: str = None) -> AdvancedSearchEngine:
    """Get global advanced search engine instance."""
    global ADVANCED_SEARCH
    if ADVANCED_SEARCH is None:
        if index_path is None:
            index_path = Path.home() / '.hermes-webui' / 'search_index.db'
        ADVANCED_SEARCH = AdvancedSearchEngine(str(index_path))
    return ADVANCED_SEARCH

def init_advanced_search() -> None:
    """Initialize advanced search engine."""
    engine = get_advanced_search_engine()
    
    # Index content in background
    def index_worker():
        try:
            engine.index_all_content()
        except Exception as e:
            logger.error(f"Background indexing error: {e}")
    
    import threading
    thread = threading.Thread(target=index_worker, daemon=True)
    thread.start()
    
    logger.info("Advanced search engine initialized")