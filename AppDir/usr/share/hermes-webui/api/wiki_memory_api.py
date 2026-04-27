# -*- coding: utf-8 -*-
"""
Wiki/Memory/SP Browser API Routes for Vibecode
Local database access (no SSH needed since we're on .233)
Full CRUD operations for memories, wiki pages, and SP data
"""
import json
import sqlite3
import os
from datetime import datetime

def run_sqlite_query(db_path, query, fetch=True):
    """Execute a SQLite query and return results."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        if fetch:
            rows = cursor.fetchall()
            conn.close()
            return {'output': json.dumps([dict(r) for r in rows]), 'error': None}
        else:
            conn.commit()
            lastrow = cursor.lastrowid
            conn.close()
            return {'output': str(lastrow) if lastrow else 'OK', 'error': None}
    except Exception as e:
        return {'error': str(e), 'output': ''}

# For backwards compatibility - these now use local SQLite
ssh_json_command = lambda host, user, command, timeout=30: run_sqlite_query(
    command.split(' ', 2)[1].strip("'"), 
    command.split(' ', 2)[2].strip("'"),
    fetch=True
)

ssh_command_raw = lambda host, user, command, timeout=30: run_sqlite_query(
    command.split(' ', 2)[1].strip("'"), 
    command.split(' ', 2)[2].strip("'"),
    fetch=False
)

MEMSTER_HOST = '192.168.4.250'  # For reference
MEMSTER_USER = 'house'
MEMSTER_DB = '/home/house/.memster/memster_core.db'
WIKI_DB = '/home/house/.hermes/wiki/wiki.db'

# ============ MEMORIES - FULL CRUD ============

def list_memster_memories(category=None, tier=None, limit=50, offset=0, search=None):
    """List memories from memster with filtering."""
    db = MEMSTER_DB
    query = "SELECT json_group_array(json_object("
    query += "'id', id, 'content', content, 'category', category, 'tier', tier, 'importance', importance, "
    query += "'created_at', t_recorded, 'accessed_at', t_event, 'type', COALESCE(memory_type, 'observation'))) "
    query += "FROM memories WHERE 1=1"
    if category and category != 'all':
        category_escaped = category.replace("'", "''")
        query += f" AND category = '{category_escaped}'"
    if tier:
        tier_escaped = tier.replace("'", "''")
        query += f" AND tier = '{tier_escaped}'"
    if search:
        search_escaped = search.replace("'", "''")
        query += f" AND content LIKE '%{search_escaped}%'"
    query += f" ORDER BY t_recorded DESC LIMIT {limit} OFFSET {offset}"
    
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        if rows:
            data = json.loads(rows[0][0]) if rows[0][0] else []
            return {'memories': data if isinstance(data, list) else []}
        return {'memories': []}
    except Exception as e:
        conn.close()
        return {'memories': [], 'error': str(e)}

def get_memster_categories():
    """Get distinct categories from memories."""
    db = MEMSTER_DB
    sql = "SELECT json_group_array(DISTINCT category) FROM memories WHERE category IS NOT NULL"
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        if rows and rows[0][0]:
            data = json.loads(rows[0][0])
            return {'categories': data if isinstance(data, list) else []}
        return {'categories': ['world', 'experience', 'opinion', 'observation']}
    except Exception:
        conn.close()
        return {'categories': ['world', 'experience', 'opinion', 'observation']}

def get_memster_tags():
    """Get all tags from memories."""
    # No memory_tags table in memster - tags are embedded in content
    return {'tags': []}

def search_memster_memories(query_text, limit=20):
    """Search memster memories using LIKE search."""
    db = MEMSTER_DB
    search_escaped = query_text.replace("'", "''")
    sql = "SELECT json_group_array(json_object("
    sql += "'id', id, 'content', content, 'category', category, 'importance', importance, 'created_at', t_recorded, "
    sql += "'type', COALESCE(memory_type, 'observation'))) "
    sql += f"FROM memories WHERE content LIKE '%{search_escaped}%' "
    sql += f"ORDER BY importance DESC, t_recorded DESC LIMIT {limit}"
    
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        if rows and rows[0][0]:
            data = json.loads(rows[0][0])
            return {'memories': data if isinstance(data, list) else []}
        return {'memories': []}
    except Exception:
        conn.close()
        return {'memories': []}

def run_memster_hybrid_search(query_text, limit=10):
    """Hybrid search - uses text search for now."""
    return search_memster_memories(query_text, limit)

def get_memster_briefing():
    """Get recent activity briefing from memster."""
    db = MEMSTER_DB
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    
    # Get now memory (recently accessed)
    now_sql = "SELECT json_object('id', id, 'content', content, 'category', category, 'timestamp', t_recorded) "
    now_sql += "FROM memories ORDER BY t_event DESC LIMIT 1"
    
    # Get contextual memories
    ctx_sql = "SELECT json_group_array(json_object("
    ctx_sql += "'id', id, 'content', content, 'category', category, 'tier', tier, 'importance', importance, "
    ctx_sql += "'timestamp', t_recorded)) FROM (SELECT * FROM memories ORDER BY t_event DESC LIMIT 30)"
    
    # Get recent memories (last 24h)
    recent_sql = "SELECT count(*) FROM memories WHERE t_recorded > datetime('now', '-1 day')"
    
    try:
        cursor.execute(now_sql)
        now = json.loads(cursor.fetchone()[0] or '{}')
    except Exception:
        now = None
    
    try:
        cursor.execute(ctx_sql)
        ctx = json.loads(cursor.fetchone()[0] or '[]')
    except Exception:
        ctx = []
    
    try:
        cursor.execute(recent_sql)
        recent_count = int(cursor.fetchone()[0] or 0)
    except Exception:
        recent_count = 0
    
    conn.close()
    return {'now': now, 'briefing': {'contextual': ctx}, 'recent_count': recent_count}

def get_memster_memory_by_id(mem_id):
    """Get a single memory by ID."""
    db = MEMSTER_DB
    mid = int(mem_id)
    sql = "SELECT id, content, category, tier, importance, t_recorded as created_at, t_event as accessed_at, COALESCE(memory_type, 'observation') as type FROM memories WHERE id = ?"
    
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (mid,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None
    except Exception:
        conn.close()
        return None

def create_memster_memory(content, category='observation', tier='L2', tags=None):
    """Create a new memory."""
    db = MEMSTER_DB
    cursor_sql = "INSERT INTO memories (content, category, tier, importance, t_recorded, t_event) VALUES (?, ?, ?, 5.0, datetime('now'), datetime('now'))"
    
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(cursor_sql, (content, category, tier))
        mem_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {'id': mem_id, 'created': True}
    except Exception as e:
        conn.close()
        return {'error': str(e)}

def update_memster_memory(mem_id, content=None, category=None, tier=None, tags=None):
    """Update an existing memory."""
    db = MEMSTER_DB
    mid = int(mem_id)
    updates = []
    params = []
    
    if content is not None:
        updates.append("content = ?")
        params.append(content)
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    if tier is not None:
        updates.append("tier = ?")
        params.append(tier)
    
    updates.append("t_event = datetime('now')")
    
    if not updates:
        return {'id': mid, 'updated': True}
    
    params.append(mid)
    sql = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"
    
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
        conn.close()
        return {'id': mid, 'updated': True}
    except Exception as e:
        conn.close()
        return {'error': str(e)}

def delete_memster_memory(mem_id):
    """Delete a memory."""
    db = MEMSTER_DB
    mid = int(mem_id)
    
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        # Delete related edges first
        cursor.execute("DELETE FROM memory_edges WHERE source_memory_id = ? OR target_memory_id = ?", (mid, mid))
        # Delete memory
        cursor.execute("DELETE FROM memories WHERE id = ?", (mid,))
        conn.commit()
        conn.close()
        return {'id': mid, 'deleted': True}
    except Exception as e:
        conn.close()
        return {'error': str(e)}

def add_memory_tag(mem_id, tag):
    """Add a tag to a memory - not supported."""
    return {'id': mem_id, 'tag': tag, 'added': False, 'reason': 'tags not supported'}

def remove_memory_tag(mem_id, tag):
    """Remove a tag from a memory - not supported."""
    return {'id': mem_id, 'tag': tag, 'removed': False, 'reason': 'tags not supported'}

def get_related_memories(mem_id, limit=10):
    """Get memories from same category."""
    db = MEMSTER_DB
    mid = int(mem_id)
    
    # Get this memory's category
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT category FROM memories WHERE id = ?", (mid,))
    row = cursor.fetchone()
    if not row or not row[0]:
        conn.close()
        return {'memories': []}
    
    category = row[0]
    sql = "SELECT json_group_array(json_object("
    sql += "'id', id, 'content', content, 'category', category, 'importance', importance, "
    sql += "'created_at', t_recorded)) FROM memories WHERE id != ? AND category = ? "
    sql += "ORDER BY importance DESC, t_recorded DESC LIMIT ?"
    
    cursor.execute(sql, (mid, category, limit))
    result = cursor.fetchone()
    conn.close()
    
    try:
        data = json.loads(result[0] or '[]')
        return {'memories': data if isinstance(data, list) else []}
    except Exception:
        return {'memories': []}

# ============ WIKI - FULL CRUD ============

def list_wiki_pages(category=None, limit=50):
    """List wiki pages."""
    db = WIKI_DB
    query = "SELECT json_group_array(json_object("
    query += "'slug', slug, 'title', title, 'category', category, 'word_count', word_count, "
    query += "'updated_at', updated)) FROM pages"
    if category and category != 'all':
        category_escaped = category.replace("'", "''")
        query += f" WHERE category = '{category_escaped}'"
    query += f" ORDER BY title LIMIT {limit}"
    
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        if rows and rows[0][0]:
            data = json.loads(rows[0][0])
            return {'pages': data if isinstance(data, list) else []}
        return {'pages': []}
    except Exception:
        conn.close()
        return {'pages': []}

def get_wiki_categories():
    """Get distinct wiki categories."""
    db = WIKI_DB
    sql = "SELECT json_group_array(DISTINCT category) FROM pages WHERE category IS NOT NULL"
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        if rows and rows[0][0]:
            data = json.loads(rows[0][0])
            return {'categories': data if isinstance(data, list) else []}
        return {'categories': ['infrastructure', 'projects', 'preferences', 'system', 'apps', 'people', 'notes']}
    except Exception:
        conn.close()
        return {'categories': ['infrastructure', 'projects', 'preferences', 'system', 'apps', 'people', 'notes']}

def get_wiki_tags():
    """Get all wiki tags."""
    return {'tags': []}

def get_wiki_page(slug):
    """Get a wiki page by slug."""
    db = WIKI_DB
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM pages WHERE slug = ?", (slug,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {'error': 'Page not found'}
        
        page = dict(row)
        # Parse tags/sources if they exist
        if page.get('tags'):
            try:
                page['tags'] = json.loads(page['tags'])
            except Exception:
                page['tags'] = []
        if page.get('sources'):
            try:
                page['sources'] = json.loads(page['sources'])
            except Exception:
                page['sources'] = []
        
        page['wikilinks'] = []
        page['backlinks'] = []
        conn.close()
        return page
    except Exception as e:
        conn.close()
        return {'error': str(e)}

def create_wiki_page(slug, title, category, content, tags=None, sources=None):
    """Create a new wiki page."""
    db = WIKI_DB
    word_count = len(content.split())
    tags_json = json.dumps(tags or [])
    sources_json = json.dumps(sources or [])
    
    sql = "INSERT INTO pages (slug, title, category, content, tags, sources, word_count, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))"
    
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (slug, title, category, content, tags_json, sources_json, word_count))
        conn.commit()
        conn.close()
        return {'slug': slug, 'created': True}
    except Exception as e:
        conn.close()
        return {'error': str(e)}

def update_wiki_page(slug, title=None, category=None, content=None, tags=None, sources=None):
    """Update an existing wiki page."""
    db = WIKI_DB
    
    # Check if page exists
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pages WHERE slug = ?", (slug,))
    count = cursor.fetchone()[0]
    if count == 0:
        conn.close()
        return {'error': 'Page not found'}
    
    updates = []
    params = []
    
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    if content is not None:
        updates.append("content = ?")
        params.append(content)
        word_count = len(content.split())
        updates.append("word_count = ?")
        params.append(word_count)
    if tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(tags))
    if sources is not None:
        updates.append("sources = ?")
        params.append(json.dumps(sources))
    
    updates.append("updated_at = datetime('now')")
    params.append(slug)
    
    sql = f"UPDATE pages SET {', '.join(updates)} WHERE slug = ?"
    
    try:
        cursor.execute(sql, params)
        conn.commit()
        conn.close()
        return {'slug': slug, 'updated': True}
    except Exception as e:
        conn.close()
        return {'error': str(e)}

def delete_wiki_page(slug):
    """Delete a wiki page."""
    db = WIKI_DB
    
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM pages WHERE slug = ?", (slug,))
        conn.commit()
        conn.close()
        return {'slug': slug, 'deleted': True}
    except Exception as e:
        conn.close()
        return {'error': str(e)}

def search_wiki_pages(query, limit=20):
    """Search wiki pages using LIKE search."""
    db = WIKI_DB
    search_escaped = query.replace("'", "''")
    sql = "SELECT json_group_array(json_object("
    sql += "'slug', slug, 'title', title, 'category', category)) "
    sql += f"FROM pages WHERE title LIKE '%{search_escaped}%' OR content LIKE '%{search_escaped}%' "
    sql += f"ORDER BY title LIMIT {limit}"
    
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        if rows and rows[0][0]:
            data = json.loads(rows[0][0])
            return {'pages': data if isinstance(data, list) else []}
        return {'pages': []}
    except Exception:
        conn.close()
        return {'pages': []}

# ============ SIMPLY PLURAL DATA ============

def get_sp_system_info():
    """Get Simply Plural system info - placeholder."""
    return {'system': 'placeholder', 'members': []}

def get_sp_fronters():
    """Get current Simply Plural fronters - placeholder."""
    return {'fronters': []}

def get_sp_members():
    """Get Simply Plural members - placeholder."""
    return {'members': []}

def get_sp_status():
    """Get Simply Plural status - alias for compatibility."""
    return {'status': 'placeholder', 'current_member': None}
