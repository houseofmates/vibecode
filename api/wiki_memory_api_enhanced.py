# -*- coding: utf-8 -*-
"""
Wiki/Memory/SP Browser API Routes for Vibecode
Connects to remote host for memster, wiki, and Simply Plural data via SSH
Full CRUD operations for memories, wiki pages, and SP data
"""
import json
import subprocess
import os
from datetime import datetime

# add importance calc import
try:
 from .importance_calc import calculate_importance
except ImportError:
 import sys
 sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 from importance_calc import calculate_importance

def ssh_json_command(host, user, command, timeout=30):
    """Execute a command on remote host via SSH and return JSON output."""
    ssh_cmd = ['ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
               '-o', 'IdentityFile=~/.ssh/id_ed25519',
               f'{user}@{host}', command]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return {'error': result.stderr.strip() or 'SSH failed', 'output': ''}
        return {'output': result.stdout, 'error': None}
    except subprocess.TimeoutExpired:
        return {'error': 'SSH timeout', 'output': ''}
    except Exception as e:
        return {'error': str(e), 'output': ''}

def ssh_command_raw(host, user, command, timeout=30):
    """Execute a command and return raw output (for updates/inserts)."""
    ssh_cmd = ['ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
               '-o', 'IdentityFile=~/.ssh/id_ed25519',
               f'{user}@{host}', command]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        return {'output': result.stdout, 'error': result.stderr if result.returncode != 0 else None, 
                'returncode': result.returncode}
    except subprocess.TimeoutExpired:
        return {'error': 'SSH timeout', 'output': '', 'returncode': -1}
    except Exception as e:
        return {'error': str(e), 'output': '', 'returncode': -1}

_HOME = os.path.expanduser('~')
MEMSTER_HOST = os.environ.get('MEMSTER_HOST_LEGACY', os.environ.get('POPOS_IP', '127.0.0.1'))
MEMSTER_USER = os.environ.get('MEMSTER_USER', os.environ.get('USER', ''))
MEMSTER_DB = os.environ.get('MEMSTER_DB', f"{os.environ.get('DEFAULT_HOME', _HOME)}/.memster/memster_core.db")
WIKI_DB = os.environ.get('WIKI_DB', f"{os.environ.get('DEFAULT_HOME', _HOME)}/.hermes/wiki/wiki.db")

# ============ MEMORIES - FULL CRUD ============

def list_memster_memories(category=None, tier=None, limit=50, offset=0, search=None):
    """List memories from memster on .233 with filtering."""
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
    cmd = f"sqlite3 '{MEMSTER_DB}' '{query}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    if result.get('error'):
        return {'error': result['error'], 'memories': []}
    try:
        data = json.loads(result.get('output', '[]'))
        return {'memories': data if isinstance(data, list) else []}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {'memories': [], 'error': 'Invalid JSON from database'}

def get_memster_categories():
    """Get distinct categories from memories."""
    sql = "SELECT json_group_array(DISTINCT category) FROM memories WHERE category IS NOT NULL"
    cmd = f"sqlite3 '{MEMSTER_DB}' '{sql}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    try:
        data = json.loads(result.get('output', '[]'))
        return {'categories': data if isinstance(data, list) else []}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {'categories': ['world', 'experience', 'opinion', 'observation']}

def get_memster_tags():
    """Get all tags from memories."""
    # No memory_tags table in memster - tags are embedded in content
    return {'tags': []}

def search_memster_memories(query_text, limit=20):
    """Search memster memories using LIKE search."""
    search_escaped = query_text.replace("'", "''")
    sql = "SELECT json_group_array(json_object("
    sql += "'id', id, 'content', content, 'category', category, 'importance', importance, 'created_at', t_recorded, "
    sql += "'type', COALESCE(memory_type, 'observation'))) "
    sql += f"FROM memories WHERE content LIKE '%{search_escaped}%' "
    sql += f"ORDER BY importance DESC, t_recorded DESC LIMIT {limit}"
    cmd = f"sqlite3 '{MEMSTER_DB}' '{sql}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    try:
        data = json.loads(result.get('output', '[]'))
        return {'memories': data if isinstance(data, list) else []}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {'memories': []}

def run_memster_hybrid_search(query_text, limit=10):
    """Hybrid search - uses text search for now."""
    return search_memster_memories(query_text, limit)

def get_memster_briefing():
    """Get recent activity briefing from memster."""
    # Get now memory (recently accessed)
    now_sql = "SELECT json_object('id', id, 'content', content, 'category', category, 'timestamp', t_recorded) "
    now_sql += "FROM memories ORDER BY t_event DESC LIMIT 1"
    now_cmd = f"sqlite3 '{MEMSTER_DB}' '{now_sql}'"
    now_result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, now_cmd)
    
    # Get contextual memories
    ctx_sql = "SELECT json_group_array(json_object("
    ctx_sql += "'id', id, 'content', content, 'category', category, 'tier', tier, 'importance', importance, "
    ctx_sql += "'timestamp', t_recorded)) FROM (SELECT * FROM memories ORDER BY t_event DESC LIMIT 30)"
    ctx_cmd = f"sqlite3 '{MEMSTER_DB}' '{ctx_sql}'"
    ctx_result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, ctx_cmd)
    
    # Get recent memories (last 24h)
    recent_sql = "SELECT count(*) FROM memories WHERE t_recorded > datetime('now', '-1 day')"
    recent_cmd = f"sqlite3 '{MEMSTER_DB}' '{recent_sql}'"
    recent_result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, recent_cmd)
    
    try:
        now = json.loads(now_result.get('output') or '{}')
    except (json.JSONDecodeError, TypeError, ValueError):
        now = None
    try:
        ctx = json.loads(ctx_result.get('output', '[]'))
    except (json.JSONDecodeError, TypeError, ValueError):
        ctx = []
    try:
        recent_count = int(recent_result.get('output', '0').strip() or '0')
    except (ValueError, AttributeError):
        recent_count = 0
    
    return {'now': now, 'briefing': {'contextual': ctx}, 'recent_count': recent_count}

def get_memster_memory_by_id(mem_id):
    """Get a single memory by ID."""
    mid = int(mem_id)
    sql = "SELECT json_group_array(json_object("
    sql += "'id', id, 'content', content, 'category', category, 'tier', tier, "
    sql += "'importance', importance, 'created_at', t_recorded, 'accessed_at', t_event, "
    sql += "'type', COALESCE(memory_type, 'observation'))) "
    sql += f"FROM memories WHERE id = {mid}"
    cmd = f"sqlite3 '{MEMSTER_DB}' '{sql}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    try:
        data = json.loads(result.get('output', '[]'))
        return data[0] if isinstance(data, list) and len(data) > 0 else None
    except (json.JSONDecodeError, TypeError, ValueError, IndexError):
        return None

def create_memster_memory(content, category='observation', tier='L2', tags=None):
    """Create a new memory."""
    content_escaped = content.replace("'", "''")
    cat_escaped = (category or 'observation').replace("'", "''")
    tier_escaped = (tier or 'L2').replace("'", "''")

    # Calculate importance based on content
    calculated_importance = calculate_importance(content, category)

    sql = f"INSERT INTO memories (content, category, tier, importance, t_recorded, t_event) VALUES ('{content_escaped}', '{cat_escaped}', '{tier_escaped}', {calculated_importance}, datetime('now'), datetime('now'))"
    cmd = f"sqlite3 '{MEMSTER_DB}' '{sql}'"
    result = ssh_command_raw(MEMSTER_HOST, MEMSTER_USER, cmd)

    if result.get('error'):
        return {'error': result['error']}

    # Get the ID of the inserted row
    id_sql = "SELECT last_insert_rowid()"
    id_cmd = f"sqlite3 '{MEMSTER_DB}' '{id_sql}'"
    id_result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, id_cmd)

    try:
        mem_id = int(id_result.get('output', '0').strip() or '0')
    except (ValueError, AttributeError):
        mem_id = None

    return {'id': mem_id, 'created': True}

def update_memster_memory(mem_id, content=None, category=None, tier=None, tags=None):
    """Update an existing memory."""
    mid = int(mem_id)
    updates = []
    
    if content is not None:
        content_escaped = content.replace("'", "''")
        updates.append(f"content = '{content_escaped}'")
    if category is not None:
        cat_escaped = category.replace("'", "''")
        updates.append(f"category = '{cat_escaped}'")
    if tier is not None:
        tier_escaped = tier.replace("'", "''")
        updates.append(f"tier = '{tier_escaped}'")
    
    updates.append("t_event = datetime('now')")
    
    if updates:
        sql = f"UPDATE memories SET {', '.join(updates)} WHERE id = {mid}"
        cmd = f"sqlite3 '{MEMSTER_DB}' '{sql}'"
        result = ssh_command_raw(MEMSTER_HOST, MEMSTER_USER, cmd)
        if result.get('error'):
            return {'error': result['error']}
    
    # Tags not supported in memster yet
    if tags is not None:
        pass
    
    return {'id': mid, 'updated': True}

def delete_memster_memory(mem_id):
    """Delete a memory."""
    mid = int(mem_id)
    
    # Delete related edges first
    edge_sql = f"DELETE FROM memory_edges WHERE source_memory_id = {mid} OR target_memory_id = {mid}"
    edge_cmd = f"sqlite3 '{MEMSTER_DB}' '{edge_sql}'"
    ssh_command_raw(MEMSTER_HOST, MEMSTER_USER, edge_cmd)
    
    # Delete memory
    sql = f"DELETE FROM memories WHERE id = {mid}"
    cmd = f"sqlite3 '{MEMSTER_DB}' '{sql}'"
    result = ssh_command_raw(MEMSTER_HOST, MEMSTER_USER, cmd)
    
    if result.get('error'):
        return {'error': result['error']}
    return {'id': mid, 'deleted': True}

def add_memory_tag(mem_id, tag):
    """Add a tag to a memory - not supported in memster."""
    return {'id': mem_id, 'tag': tag, 'added': False, 'reason': 'tags not supported'}

def remove_memory_tag(mem_id, tag):
    """Remove a tag from a memory - not supported."""
    return {'id': mem_id, 'tag': tag, 'removed': False, 'reason': 'tags not supported'}

def get_related_memories(mem_id, limit=10):
    """Get memories from same entity or tag."""
    mid = int(mem_id)
    
    # Get tags for this memory
    tag_sql = f"SELECT json_group_array(tag) FROM memory_tags WHERE memory_id = {mid}"
    tag_cmd = f"sqlite3 '{MEMSTER_DB}' '{tag_sql}'"
    tag_result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, tag_cmd)
    
    try:
        tags = json.loads(tag_result.get('output', '[]'))
        if not isinstance(tags, list):
            tags = []
    except:
        tags = []
    
    # Get entities for this memory  
    ent_sql = f"SELECT json_group_array(name) FROM entities WHERE memory_id = {mid}"
    ent_cmd = f"sqlite3 '{MEMSTER_DB}' '{ent_sql}'"
    ent_result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, ent_cmd)
    
    try:
        entities = json.loads(ent_result.get('output', '[]'))
        if not isinstance(entities, list):
            entities = []
    except:
        entities = []
    
    if not tags and not entities:
        return {'memories': []}
    
    # Build query for related memories
    conditions = [f"m.id != {mid}"]
    
    if tags:
        escaped_tags = ",".join([f"'{t.replace(chr(39), chr(39)+chr(39))}'" for t in tags[:5]])
        conditions.append(f"EXISTS (SELECT 1 FROM memory_tags mt WHERE mt.memory_id = m.id AND mt.tag IN ({escaped_tags}))")
    
    if entities:
        escaped_ents = ",".join([f"'{e.replace(chr(39), chr(39)+chr(39))}'" for e in entities[:3]])
        conditions.append(f"EXISTS (SELECT 1 FROM entities e WHERE e.memory_id = m.id AND e.name IN ({escaped_ents}))")
    
    sql = "SELECT json_group_array(json_object("
    sql += "'id', m.id, 'content', m.content, 'category', m.category, 'importance', m.importance, "
    sql += "'created_at', m.t_recorded)) FROM memories m WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY m.importance DESC, m.t_recorded DESC LIMIT {limit}"
    cmd = f"sqlite3 '{MEMSTER_DB}' '{sql}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    
    try:
        data = json.loads(result.get('output', '[]'))
        return {'memories': data if isinstance(data, list) else []}
    except:
        return {'memories': []}

# ============ WIKI - FULL CRUD ============

def list_wiki_pages(category=None, limit=50):
    """List wiki pages from .250."""
    query = "SELECT json_group_array(json_object("
    query += "'slug', slug, 'title', title, 'category', category, 'word_count', word_count, "
    query += "'updated_at', updated_at, 'links_in', (SELECT COUNT(*) FROM backlinks WHERE target_slug = pages.slug), "
    query += "'links_out', (SELECT COUNT(*) FROM backlinks WHERE source_slug = pages.slug))) FROM pages"
    if category and category != 'all':
        category_escaped = category.replace("'", "''")
        query += f" WHERE category = '{category_escaped}'"
    query += f" ORDER BY title LIMIT {limit}"
    cmd = f"sqlite3 '{WIKI_DB}' '{query}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    try:
        data = json.loads(result.get('output', '[]'))
        return {'pages': data if isinstance(data, list) else []}
    except:
        return {'pages': []}

def get_wiki_categories():
    """Get distinct wiki categories."""
    sql = "SELECT json_group_array(DISTINCT category) FROM pages WHERE category IS NOT NULL"
    cmd = f"sqlite3 '{WIKI_DB}' '{sql}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    try:
        data = json.loads(result.get('output', '[]'))
        return {'categories': data if isinstance(data, list) else []}
    except:
        return {'categories': ['infrastructure', 'projects', 'preferences', 'system', 'apps', 'people', 'notes']}

def get_wiki_tags():
    """Get all wiki tags (from tags column JSON)."""
    sql = "SELECT json_group_array(DISTINCT json_each.value) FROM pages, json_each(pages.tags)"
    cmd = f"sqlite3 '{WIKI_DB}' '{sql}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    try:
        data = json.loads(result.get('output', '[]'))
        return {'tags': data if isinstance(data, list) else []}
    except:
        return {'tags': []}

def get_wiki_page(slug):
    """Get a wiki page by slug."""
    slug_escaped = slug.replace("'", "''")
    sql = "SELECT json_object("
    sql += "'slug', slug, 'title', title, 'content', content, 'category', category, "
    sql += "'tags', COALESCE(tags, '[]'), 'sources', COALESCE(sources, '[]'), 'word_count', word_count, 'updated_at', updated_at) "
    sql += f"FROM pages WHERE slug = '{slug_escaped}'"
    cmd = f"sqlite3 '{WIKI_DB}' '{sql}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    try:
        page = json.loads(result.get('output', '{}'))
        if page.get('slug') is None:
            return {'error': 'Page not found'}
        
        # Get wikilinks (outgoing)
        out_sql = "SELECT json_group_array(distinct json_object('slug', target_slug, 'title', COALESCE((SELECT title FROM pages WHERE slug = target_slug), target_slug))) "
        out_sql += f"FROM backlinks WHERE source_slug = '{slug_escaped}'"
        out_cmd = f"sqlite3 '{WIKI_DB}' '{out_sql}'"
        out_result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, out_cmd)
        
        # Get backlinks (incoming)
        in_sql = "SELECT json_group_array(distinct json_object('slug', source_slug, 'title', COALESCE((SELECT title FROM pages WHERE slug = source_slug), source_slug))) "
        in_sql += f"FROM backlinks WHERE target_slug = '{slug_escaped}'"
        in_cmd = f"sqlite3 '{WIKI_DB}' '{in_sql}'"
        in_result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, in_cmd)
        
        try:
            page['wikilinks'] = json.loads(out_result.get('output', '[]')) or []
        except:
            page['wikilinks'] = []
        try:
            page['backlinks'] = json.loads(in_result.get('output', '[]')) or []
        except:
            page['backlinks'] = []
        
        # Parse tags
        try:
            if page.get('tags') and isinstance(page['tags'], str):
                page['tags'] = json.loads(page['tags'])
        except:
            page['tags'] = []
            
        # Parse sources
        try:
            if page.get('sources') and isinstance(page['sources'], str):
                page['sources'] = json.loads(page['sources'])
        except:
            page['sources'] = []
        
        return page
    except Exception as e:
        return {'error': str(e)}

def create_wiki_page(slug, title, category, content, tags=None, sources=None):
    """Create a new wiki page."""
    slug_escaped = slug.replace("'", "''")
    title_escaped = title.replace("'", "''")
    cat_escaped = category.replace("'", "''")
    content_escaped = content.replace("'", "''")
    tags_json = json.dumps(tags or [])
    tags_escaped = tags_json.replace("'", "''")
    sources_json = json.dumps(sources or [])
    sources_escaped = sources_json.replace("'", "''")
    
    # Count words
    word_count = len(content.split())
    
    sql = f"INSERT INTO pages (slug, title, category, content, tags, sources, word_count, updated_at) "
    sql += f"VALUES ('{slug_escaped}', '{title_escaped}', '{cat_escaped}', '{content_escaped}', '{tags_escaped}', '{sources_escaped}', {word_count}, datetime('now'))"
    cmd = f"sqlite3 '{WIKI_DB}' '{sql}'"
    result = ssh_command_raw(MEMSTER_HOST, MEMSTER_USER, cmd)
    
    if result.get('error'):
        return {'error': result['error']}
    
    return {'slug': slug, 'created': True}

def update_wiki_page(slug, title=None, category=None, content=None, tags=None, sources=None):
    """Update an existing wiki page."""
    slug_escaped = slug.replace("'", "''")
    
    # Check if page exists
    check_sql = f"SELECT COUNT(*) FROM pages WHERE slug = '{slug_escaped}'"
    check_cmd = f"sqlite3 '{WIKI_DB}' '{check_sql}'"
    check_result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, check_cmd)
    
    try:
        exists = int(check_result.get('output', '0').strip() or '0') > 0
        if not exists:
            return {'error': 'Page not found'}
    except:
        return {'error': 'Failed to check page existence'}
    
    updates = ["updated_at = datetime('now')"]
    
    if title is not None:
        title_escaped = title.replace("'", "''")
        updates.append(f"title = '{title_escaped}'")
    if category is not None:
        cat_escaped = category.replace("'", "''")
        updates.append(f"category = '{cat_escaped}'")
    if content is not None:
        content_escaped = content.replace("'", "''")
        updates.append(f"content = '{content_escaped}'")
        # Recalculate word count
        word_count = len(content.split())
        updates.append(f"word_count = {word_count}")
    if tags is not None:
        tags_json = json.dumps(tags)
        tags_escaped = tags_json.replace("'", "''")
        updates.append(f"tags = '{tags_escaped}'")
    if sources is not None:
        sources_json = json.dumps(sources)
        sources_escaped = sources_json.replace("'", "''")
        updates.append(f"sources = '{sources_escaped}'")
    
    sql = f"UPDATE pages SET {', '.join(updates)} WHERE slug = '{slug_escaped}'"
    cmd = f"sqlite3 '{WIKI_DB}' '{sql}'"
    result = ssh_command_raw(MEMSTER_HOST, MEMSTER_USER, cmd)
    
    if result.get('error'):
        return {'error': result['error']}
    
    return {'slug': slug, 'updated': True}

def delete_wiki_page(slug):
    """Delete a wiki page and its backlinks."""
    slug_escaped = slug.replace("'", "''")
    
    # Delete backlinks first
    del_links = f"DELETE FROM backlinks WHERE source_slug = '{slug_escaped}' OR target_slug = '{slug_escaped}'"
    del_cmd = f"sqlite3 '{WIKI_DB}' '{del_links}'"
    ssh_command_raw(MEMSTER_HOST, MEMSTER_USER, del_cmd)
    
    # Delete page
    sql = f"DELETE FROM pages WHERE slug = '{slug_escaped}'"
    cmd = f"sqlite3 '{WIKI_DB}' '{sql}'"
    result = ssh_command_raw(MEMSTER_HOST, MEMSTER_USER, cmd)
    
    if result.get('error'):
        return {'error': result['error']}
    
    return {'slug': slug, 'deleted': True}

def search_wiki_pages(query_text, limit=10):
    """Search wiki pages."""
    search_escaped = query_text.replace("'", "''")
    sql = "SELECT json_group_array(json_object("
    sql += "'slug', slug, 'title', title, 'snippet', substr(content, 1, 200), 'category', category)) "
    sql += f"FROM pages WHERE title LIKE '%{search_escaped}%' OR content LIKE '%{search_escaped}%'"
    sql += f" ORDER BY word_count DESC LIMIT {limit}"
    cmd = f"sqlite3 '{WIKI_DB}' '{sql}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    try:
        data = json.loads(result.get('output', '[]'))
        return {'pages': data if isinstance(data, list) else []}
    except:
        return {'pages': []}

# ============ SIMPLY PLURAL ============

def get_sp_members(include_archived=False):
    """Get SP headmates from memster DB on .250."""
    archived_filter = "" if include_archived else "WHERE is_archived = 0"
    sql = "SELECT json_group_array(json_object("
    sql += "'uid', uid, 'name', name, 'color', color, 'pronouns', pronouns, "
    sql += "'display_name', display_name, 'is_archived', is_archived, 'is_current', is_current)) "
    sql += f"FROM sp_members {archived_filter} ORDER BY sort_order, name"
    cmd = f"sqlite3 '{MEMSTER_DB}' '{sql}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    try:
        data = json.loads(result.get('output', '[]'))
        return {'members': data if isinstance(data, list) else []}
    except:
        return {'members': []}

def get_sp_status():
    """Get SP current status."""
    sql = "SELECT json_object("
    sql += "'current', COALESCE((SELECT json_object("
    sql += "'uid', uid, 'name', name, 'color', color, 'pronouns', pronouns, 'display_name', display_name) "
    sql += "FROM sp_members WHERE is_current = 1 LIMIT 1), null), "
    sql += "'total_active', (SELECT COUNT(*) FROM sp_members WHERE is_archived = 0), "
    sql += "'total_archived', (SELECT COUNT(*) FROM sp_members WHERE is_archived = 1), "
    sql += "'updated_at', (SELECT MAX(last_updated) FROM sp_members))"
    cmd = f"sqlite3 '{MEMSTER_DB}' '{sql}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    try:
        return json.loads(result.get('output', '{}'))
    except:
        return {'current': None, 'total_active': 0, 'total_archived': 0}

def get_sp_activity_timeline(hours=24):
    """Get SP front history timeline."""
    sql = "SELECT json_group_array(json_object("
    sql += "'id', id, 'uid', uid, 'name', COALESCE((SELECT display_name FROM sp_members WHERE uid = sp_front_history.uid), uid), "
    sql += "'color', COALESCE((SELECT color FROM sp_members WHERE uid = sp_front_history.uid), '#888888'), "
    sql += "'started_at', started_at, 'ended_at', ended_at)) "
    sql += f"FROM sp_front_history WHERE started_at > datetime('now', '-{hours} hours') ORDER BY started_at DESC"
    cmd = f"sqlite3 '{MEMSTER_DB}' '{sql}'"
    result = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, cmd)
    try:
        data = json.loads(result.get('output', '[]'))
        return {'timeline': data if isinstance(data, list) else []}
    except:
        return {'timeline': []}

# Aliases for compatibility
list_sp_headmates = get_sp_members

# ============ UTILITY ============

def get_health_stats():
    """Get health stats for all data sources."""
    mem_count = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, f"sqlite3 '{MEMSTER_DB}' 'SELECT COUNT(*) FROM memories'")
    wiki_count = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, f"sqlite3 '{WIKI_DB}' 'SELECT COUNT(*) FROM pages'")
    member_count = ssh_json_command(MEMSTER_HOST, MEMSTER_USER, f"sqlite3 '{MEMSTER_DB}' 'SELECT COUNT(*) FROM sp_members WHERE is_archived=0'")
    
    try:
        mem_n = int(mem_count.get('output', '0').strip() or '0')
    except:
        mem_n = 0
    try:
        wiki_n = int(wiki_count.get('output', '0').strip() or '0')
    except:
        wiki_n = 0
    try:
        member_n = int(member_count.get('output', '0').strip() or '0')
    except:
        member_n = 0
    
    return {
        'memories': {'count': mem_n, 'status': 'ok' if not mem_count.get('error') else 'error'},
        'wiki': {'count': wiki_n, 'status': 'ok' if not wiki_count.get('error') else 'error'},
        'sp_members': {'count': member_n, 'status': 'ok' if not member_count.get('error') else 'error'}
    }
