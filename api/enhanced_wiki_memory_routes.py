# -*- coding: utf-8 -*-
"""
Enhanced Wiki/Memory/SP API routes for vibecode v2.0
Rich browser with full CRUD, search, and real-time data from memster/.250
"""
import json
import os
import paramiko
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

_HOME = os.path.expanduser('~')

MEMSTER_HOST = os.environ.get('MEMSTER_HOST', os.environ.get('UBUNTU_IP', '127.0.0.1'))
MEMSTER_HOST_LEGACY = os.environ.get('MEMSTER_HOST_LEGACY', os.environ.get('POPOS_IP', '127.0.0.1'))
MEMSTER_USER = os.environ.get('MEMSTER_USER', os.environ.get('USER', ''))
MEMSTER_DB = os.environ.get('MEMSTER_DB', f"{os.environ.get('DEFAULT_HOME', _HOME)}/.memster/memster.db")
WIKI_DB = os.environ.get('WIKI_DB', f"{os.environ.get('DEFAULT_HOME', _HOME)}/.hermes/wiki/wiki.db")
SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH', f"{_HOME}/.ssh/id_ed25519")
REMOTE_SESSIONS_DIR = os.environ.get('REMOTE_SESSIONS_DIR', f"{os.environ.get('DEFAULT_HOME', _HOME)}/.hermes/sessions")

class MemsterClient:
    """Client for SSH-based memster/wiki queries on .250"""
    
    _ssh_cache = None
    _ssh_cache_legacy = None
    
    @classmethod
    def _get_ssh(cls, host=None):
        """Get cached SSH connection or create new one"""
        target_host = host or MEMSTER_HOST
        cache_key = '_ssh_cache' if target_host == MEMSTER_HOST else '_ssh_cache_legacy'
        
        if getattr(cls, cache_key) is None:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Check if SSH key exists
            key_exists = os.path.exists(SSH_KEY_PATH)
            
            try:
                if key_exists:
                    ssh.connect(target_host, username=MEMSTER_USER, key_filename=SSH_KEY_PATH, timeout=10)
                else:
                    ssh.connect(target_host, username=MEMSTER_USER, timeout=10)
            except paramiko.AuthenticationException as e:
                # Clear the cached connection so we can retry
                error_msg = f"SSH authentication failed to {target_host}. "
                if key_exists:
                    error_msg += f"Check that SSH key {SSH_KEY_PATH} is authorized on {target_host}. "
                    error_msg += f"Try: ssh-copy-id -i {SSH_KEY_PATH} {MEMSTER_USER}@{target_host}"
                else:
                    error_msg += f"No SSH key found at {SSH_KEY_PATH}. "
                    error_msg += f"Generate one with: ssh-keygen -t ed25519 -f {SSH_KEY_PATH}"
                raise Exception(error_msg) from e
            except paramiko.SSHException as e:
                error_msg = f"SSH connection failed to {target_host}: {str(e)}. "
                error_msg += f"Ensure {target_host} is reachable and SSH is enabled."
                raise Exception(error_msg) from e
            except Exception as e:
                error_msg = f"Failed to connect to {target_host}: {str(e)}"
                raise Exception(error_msg) from e
            
            setattr(cls, cache_key, ssh)
        return getattr(cls, cache_key)
    
    @classmethod
    def query(cls, sql: str, db: str) -> str:
        """Execute SQL query, return raw output"""
        try:
            ssh = cls._get_ssh()
            escaped = sql.replace('"', '\\"')
            cmd = f'sqlite3 {db} "{escaped}"'
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            if err:
                return None
            return out
        except Exception as e:
            return None
    
    @classmethod
    def query_json(cls, sql: str, db: str) -> Any:
        """Execute SQL query, return parsed JSON"""
        result = cls.query(sql, db)
        if not result:
            return []
        try:
            return json.loads(result)
        except:
            return []
    
    @classmethod
    def close(cls):
        if cls._ssh_cache:
            cls._ssh_cache.close()
            cls._ssh_cache = None
        if cls._ssh_cache_legacy:
            cls._ssh_cache_legacy.close()
            cls._ssh_cache_legacy = None

    @classmethod
    def list_remote_sessions(cls, sessions_dir: str = REMOTE_SESSIONS_DIR) -> List[Dict[str, Any]]:
        """List session files from remote .250 machine via SSH, with .233 as fallback"""
        all_sessions = {}
        
        # Primary: .250
        try:
            ssh = cls._get_ssh(MEMSTER_HOST)
            cmd = f'ls -la {sessions_dir}/ 2>/dev/null | grep -E "\\.(json|jsonl)$" || echo ""'
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode().strip()
            
            if out:
                for line in out.split('\n'):
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) < 9:
                        continue
                    filename = parts[-1]
                    if filename.startswith('.') or not (filename.endswith('.json') or filename.endswith('.jsonl')):
                        continue
                    
                    session_id = filename.replace('.json', '').replace('.jsonl', '')
                    session_data = {"session_id": session_id, "filename": filename, "title": session_id, "source": MEMSTER_HOST}
                    try:
                        cmd2 = f'cat {sessions_dir}/{filename} 2>/dev/null | head -c 10000'
                        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2)
                        content = stdout2.read().decode().strip()
                        if content:
                            data = json.loads(content)
                            if isinstance(data, list) and len(data) > 0:
                                data = data[0]
                            if isinstance(data, dict):
                                if 'title' in data:
                                    session_data['title'] = data['title']
                                elif 'session_title' in data:
                                    session_data['title'] = data['session_title']
                                if 'created_at' in data:
                                    session_data['created_at'] = data['created_at']
                                if 'updated_at' in data:
                                    session_data['updated_at'] = data['updated_at']
                    except:
                        pass
                    
                    all_sessions[session_id] = session_data
        except:
            pass
        
        # Legacy: .233 (add sessions that don't exist in .250)
        try:
            ssh = cls._get_ssh(MEMSTER_HOST_LEGACY)
            cmd = f'ls -la {sessions_dir}/ 2>/dev/null | grep -E "\\.(json|jsonl)$" || echo ""'
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode().strip()
            
            if out:
                for line in out.split('\n'):
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) < 9:
                        continue
                    filename = parts[-1]
                    if filename.startswith('.') or not (filename.endswith('.json') or filename.endswith('.jsonl')):
                        continue
                    
                    session_id = filename.replace('.json', '').replace('.jsonl', '')
                    
                    session_data = {"session_id": session_id, "filename": filename, "title": session_id, "source": MEMSTER_HOST_LEGACY}
                    try:
                        cmd2 = f'cat {sessions_dir}/{filename} 2>/dev/null | head -c 10000'
                        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2)
                        content = stdout2.read().decode().strip()
                        if content:
                            data = json.loads(content)
                            if isinstance(data, list) and len(data) > 0:
                                data = data[0]
                            if isinstance(data, dict):
                                if 'title' in data:
                                    session_data['title'] = data['title']
                                elif 'session_title' in data:
                                    session_data['title'] = data['session_title']
                                if 'created_at' in data:
                                    session_data['created_at'] = data['created_at']
                                if 'updated_at' in data:
                                    session_data['updated_at'] = data['updated_at']
                    except:
                        pass
                    
                    all_sessions[session_id] = session_data
        except:
            pass
        
        sessions = list(all_sessions.values())
        sessions.sort(key=lambda x: x.get('filename', ''), reverse=True)
        return sessions[:100]

    @classmethod
    def get_remote_session(cls, session_id: str, sessions_dir: str = REMOTE_SESSIONS_DIR) -> Optional[Dict[str, Any]]:
        """Get a specific session from remote machine"""
        
        # Try .250 first
        try:
            ssh = cls._get_ssh(MEMSTER_HOST)
            for ext in ['.json', '.jsonl']:
                filepath = f"{sessions_dir}/{session_id}{ext}"
                cmd = f'cat {filepath} 2>/dev/null || echo ""'
                stdin, stdout, stderr = ssh.exec_command(cmd)
                content = stdout.read().decode().strip()
                
                if content:
                    data = json.loads(content)
                    if isinstance(data, list):
                        return {"session_id": session_id, "messages": data, "title": session_id, "_remote_source": f"{MEMSTER_HOST}:{filepath}"}
                    elif isinstance(data, dict):
                        data["_remote_source"] = f"{MEMSTER_HOST}:{filepath}"
                        if "session_id" not in data:
                            data["session_id"] = session_id
                        return data
        except:
            pass
        
        # Try .233 if not found on .250
        try:
            ssh = cls._get_ssh(MEMSTER_HOST_LEGACY)
            for ext in ['.json', '.jsonl']:
                filepath = f"{sessions_dir}/{session_id}{ext}"
                cmd = f'cat {filepath} 2>/dev/null || echo ""'
                stdin, stdout, stderr = ssh.exec_command(cmd)
                content = stdout.read().decode().strip()
                
                if content:
                    data = json.loads(content)
                    if isinstance(data, list):
                        return {"session_id": session_id, "messages": data, "title": session_id, "_remote_source": f"{MEMSTER_HOST_LEGACY}:{filepath}"}
                    elif isinstance(data, dict):
                        data["_remote_source"] = f"{MEMSTER_HOST_LEGACY}:{filepath}"
                        if "session_id" not in data:
                            data["session_id"] = session_id
                        return data
        except:
            pass
        
        return None


def register_enhanced_wiki_memory_routes(app):
    """Register all enhanced wiki/memory/SP routes on the Flask app"""
    
    # ============================================
    # MEMORIES API
    # ============================================
    
    @app.route('/api/memories', methods=['GET'])
    def api_memories_list():
        """List memories with optional filtering"""
        limit = min(int(request.args.get('limit', 100)), 500)
        category = request.args.get('category', '')
        search = request.args.get('search', '')
        
        query = """SELECT json_group_array(json_object(
            'id', id, 'content', content, 'category', category, 
            'tier', tier, 'importance', importance,
            'tags', COALESCE(tags, '[]'), 'created_at', created_at,
            'updated_at', updated_at
        )) FROM memories WHERE 1=1"""
        
        if category and category != 'all':
            query += f" AND category='{category.replace(chr(39), chr(39)+chr(39))}'"
        if search:
            safe = search.replace("'", "''")
            query += f" AND content LIKE '%{safe}%'"
        
        query += f" ORDER BY importance DESC, updated_at DESC LIMIT {limit}"
        
        memories = MemsterClient.query_json(query, MEMSTER_DB)
        
        return jsonify({
            'ok': True,
            'memories': memories or [],
            'count': len(memories) if memories else 0
        })
    
    @app.route('/api/memories/search', methods=['GET'])
    def api_memories_search():
        """Hybrid search memories (content + tags)"""
        q = request.args.get('q', '')
        limit = min(int(request.args.get('limit', 20)), 100)
        
        safe_q = q.replace("'", "''")
        query = f"""SELECT json_group_array(json_object(
            'id', id, 'content', content, 'category', category,
            'tier', tier, 'importance', importance,
            'tags', COALESCE(tags, '[]'), 'created_at', created_at
        )) FROM memories 
        WHERE content LIKE '%{safe_q}%'
        ORDER BY importance DESC LIMIT {limit}"""
        
        memories = MemsterClient.query_json(query, MEMSTER_DB)
        
        return jsonify({
            'ok': True,
            'memories': memories or [],
            'query': q,
            'count': len(memories) if memories else 0
        })
    
    @app.route('/api/memories/<int:mem_id>', methods=['GET'])
    def api_memory_get(mem_id):
        """Get single memory by ID"""
        query = f"""SELECT json_object(
            'id', id, 'content', content, 'category', category,
            'tier', tier, 'importance', importance,
            'tags', COALESCE(tags, '[]'), 'source', source,
            'created_at', created_at, 'updated_at', updated_at,
            'access_count', access_count
        ) FROM memories WHERE id = {mem_id} LIMIT 1"""
        
        result = MemsterClient.query_json(query, MEMSTER_DB)
        
        if not result:
            return jsonify({'ok': False, 'error': 'Memory not found'}), 404
        
        # Get related memories via graph edges
        related_query = f"""SELECT json_group_array(json_object(
            'id', m.id, 'content', substr(m.content, 1, 100),
            'link_type', e.link_type
        )) FROM memory_edges e
        JOIN memories m ON e.target_id = m.id
        WHERE e.source_id = {mem_id}
        UNION ALL
        SELECT json_group_array(json_object(
            'id', m.id, 'content', substr(m.content, 1, 100),
            'link_type', e.link_type
        )) FROM memory_edges e
        JOIN memories m ON e.source_id = m.id  
        WHERE e.target_id = {mem_id}"""
        
        related = MemsterClient.query_json(related_query, MEMSTER_DB)
        
        return jsonify({
            'ok': True,
            'memory': result[0] if isinstance(result, list) else result,
            'related': related or []
        })
    
    @app.route('/api/memories', methods=['POST'])
    def api_memory_create():
        """Create new memory (store-only, requires SSH to .250)"""
        data = request.get_json() or {}
        
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'ok': False, 'error': 'Content required'}), 400
        
        category = data.get('category', 'observation')
        tags = json.dumps(data.get('tags', []))
        
        # Escape for SQL
        safe_content = content.replace("'", "''")
        safe_tags = tags.replace("'", "''")
        
        query = f"""INSERT INTO memories (content, category, tags, created_at, updated_at, importance)
        VALUES ('{safe_content}', '{category}', '{safe_tags}', datetime('now'), datetime('now'), {data.get('importance', 50)})
        RETURNING id"""
        
        result = MemsterClient.query_json(query, MEMSTER_DB)
        
        return jsonify({
            'ok': True,
            'id': result[0]['id'] if result else None,
            'message': 'Memory created'
        })
    
    @app.route('/api/memories/<int:mem_id>', methods=['PUT'])
    def api_memory_update(mem_id):
        """Update existing memory"""
        data = request.get_json() or {}
        
        if data.get('content'):
            safe_content = data['content'].replace("'", "''")
            query = f"""UPDATE memories 
            SET content = '{safe_content}', 
                updated_at = datetime('now')
            WHERE id = {mem_id}
            RETURNING id"""
            
            MemsterClient.query_json(query, MEMSTER_DB)
        
        return jsonify({'ok': True, 'id': mem_id, 'message': 'Memory updated'})
    
    @app.route('/api/memories/<int:mem_id>', methods=['DELETE'])
    def api_memory_delete(mem_id):
        """Delete a memory"""
        query = f"DELETE FROM memories WHERE id = {mem_id} RETURNING id"
        MemsterClient.query_json(query, MEMSTER_DB)
        
        return jsonify({'ok': True, 'id': mem_id, 'message': 'Memory deleted'})
    
    # ============================================
    # WIKI API
    # ============================================
    
    @app.route('/api/wiki/pages', methods=['GET'])
    def api_wiki_pages():
        """List all wiki pages"""
        query = """SELECT json_group_array(json_object(
            'slug', slug, 'title', title, 'category', category,
            'word_count', word_count, 'link_count_out', link_count_out,
            'link_count_in', link_count_in, 'updated_at', updated_at,
            'snippet', substr(content, 1, 120)
        )) FROM pages ORDER BY category, title"""
        
        pages = MemsterClient.query_json(query, WIKI_DB)
        
        # Group by category
        by_cat = {}
        for p in (pages or []):
            cat = p.get('category', 'notes')
            by_cat.setdefault(cat, []).append(p)
        
        return jsonify({
            'ok': True,
            'pages': pages or [],
            'by_category': by_cat,
            'count': len(pages) if pages else 0
        })
    
    @app.route('/api/wiki/pages/<slug>', methods=['GET'])
    def api_wiki_page(slug):
        """Get single wiki page"""
        safe = slug.replace("'", "''")
        query = f"""SELECT json_object(
            'slug', slug, 'title', title, 'category', category,
            'content', content, 'tags', tags, 'sources', sources,
            'word_count', word_count, 'updated_at', updated_at
        ) FROM pages WHERE slug = '{safe}' LIMIT 1"""
        
        result = MemsterClient.query_json(query, WIKI_DB)
        
        if not result:
            return jsonify({'ok': False, 'error': 'Page not found'}), 404
        
        page = result[0] if isinstance(result, list) else result
        
        # Find backlinks
        back_query = f"""SELECT json_group_array(json_object(
            'slug', slug, 'title', title
        )) FROM pages WHERE content LIKE '%[[{safe}]]%'"""
        
        backlinks = MemsterClient.query_json(back_query, WIKI_DB)
        page['backlinks'] = backlinks or []
        
        # Parse outgoing links from content
        out_links = re.findall(r'\[\[([^\]|]+)', page.get('content', ''))
        page['outgoing_links'] = list(set(out_links))
        
        return jsonify({'ok': True, 'page': page})
    
    @app.route('/api/wiki/search', methods=['GET'])
    def api_wiki_search():
        """Search wiki pages"""
        q = request.args.get('q', '')
        limit = min(int(request.args.get('limit', 20)), 100)
        category = request.args.get('category', '')
        
        safe_q = q.replace("'", "''")
        
        query = f"""SELECT json_group_array(json_object(
            'slug', slug, 'title', title, 'category', category,
            'snippet', substr(content, 1, 200),
            'word_count', word_count
        )) FROM pages WHERE (title LIKE '%{safe_q}%' OR content LIKE '%{safe_q}%')"""
        
        if category and category != 'all':
            query += f" AND category = '{category.replace(chr(39), chr(39)+chr(39))}'"
        
        query += f" ORDER BY word_count DESC LIMIT {limit}"
        
        results = MemsterClient.query_json(query, WIKI_DB)
        
        return jsonify({
            'ok': True,
            'pages': results or [],
            'query': q,
            'count': len(results) if results else 0
        })
    
    # ============================================
    # SIMPLY PLURAL (SP) API
    # ============================================
    
    @app.route('/api/sp/members', methods=['GET'])
    def api_sp_members():
        """List all SP headmates"""
        query = """SELECT json_group_array(json_object(
            'uid', uid, 'name', name, 'color', color, 
            'color_name', custom_plurality, 'pronouns', pronouns,
            'description', description, 'is_archived', is_archived,
            'is_current', is_current, 'sort_order', sort_order
        )) FROM sp_members WHERE is_archived = 0 ORDER BY sort_order, name"""
        
        members = MemsterClient.query_json(query, MEMSTER_DB)
        
        return jsonify({
            'ok': True,
            'members': members or [],
            'count': len(members) if members else 0
        })
    
    @app.route('/api/sp/status', methods=['GET'])
    def api_sp_status():
        """Get current fronting status"""
        query = """SELECT json_object(
            'system_id', system_id,
            'system_name', system_name,
            'current_count', (SELECT COUNT(*) FROM sp_members WHERE is_current = 1),
            'total_members', (SELECT COUNT(*) FROM sp_members WHERE is_archived = 0),
            'current_member', (SELECT json_object('name', name, 'color', color, 'pronouns', pronouns)
                              FROM sp_members WHERE is_current = 1 LIMIT 1),
            'current_fronters', (SELECT json_group_array(json_object('name', name, 'color', color))
                                 FROM sp_members WHERE is_current = 1)
        ) FROM sp_status LIMIT 1"""
        
        result = MemsterClient.query_json(query, MEMSTER_DB)
        
        return jsonify({
            'ok': True,
            'status': result[0] if result else None
        })
    
    @app.route('/api/sp/history', methods=['GET'])
    def api_sp_history():
        """Get fronting history"""
        limit = min(int(request.args.get('limit', 50)), 200)
        
        query = f"""SELECT json_group_array(json_object(
            'id', h.id,
            'member_name', COALESCE(m.name, 'unknown'),
            'member_color', m.color,
            'started_at', h.started_at,
            'ended_at', h.ended_at,
            'duration_minutes', 
                CASE 
                    WHEN h.ended_at IS NOT NULL 
                    THEN (julianday(h.ended_at) - julianday(h.started_at)) * 24 * 60
                    ELSE (julianday('now') - julianday(h.started_at)) * 24 * 60
                END
        )) FROM sp_front_history h
        LEFT JOIN sp_members m ON h.member_id = m.uid
        ORDER BY h.started_at DESC LIMIT {limit}"""
        
        history = MemsterClient.query_json(query, MEMSTER_DB)
        
        return jsonify({
            'ok': True,
            'history': history or [],
            'count': len(history) if history else 0
        })
    
    @app.route('/api/sp/summary', methods=['GET'])
    def api_sp_summary():
        """Get time-based summary stats"""
        # Last 24 hours fronting distribution
        query = """SELECT json_group_array(json_object(
            'member_name', COALESCE(m.name, 'unknown'),
            'total_minutes', SUM(
                CASE 
                    WHEN h.ended_at IS NOT NULL 
                    THEN (julianday(h.ended_at) - julianday(h.started_at)) * 24 * 60
                    ELSE (julianday('now') - julianday(h.started_at)) * 24 * 60
                END
            )
        )) FROM sp_front_history h
        LEFT JOIN sp_members m ON h.member_id = m.uid
        WHERE datetime(h.started_at) > datetime('now', '-1 day')
        GROUP BY h.member_id
        ORDER BY total_minutes DESC"""
        
        last24h = MemsterClient.query_json(query, MEMSTER_DB)
        
        return jsonify({
            'ok': True,
            'last_24h': last24h or [],
            'generated_at': datetime.utcnow().isoformat()
        })
    
    # ============================================
    # BRIEFING API - Unified startup context
    # ============================================
    
    @app.route('/api/briefing', methods=['GET'])
    def api_briefing():
        """Get unified briefing - memories + wiki + SP status"""
        # Recent important memories
        mem_query = """SELECT json_group_array(json_object(
            'id', id, 'content', substr(content, 1, 100), 
            'category', category, 'importance', importance
        )) FROM memories 
        WHERE tier IN ('core', 'critical') OR importance > 80
        ORDER BY importance DESC, updated_at DESC LIMIT 10"""
        
        memories = MemsterClient.query_json(mem_query, MEMSTER_DB)
        
        # Current SP status
        sp_query = """SELECT json_object(
            'current_member', (SELECT json_object('name', name, 'color', color)
                              FROM sp_members WHERE is_current = 1 LIMIT 1)
        ) FROM sp_status LIMIT 1"""
        
        sp_status = MemsterClient.query_json(sp_query, MEMSTER_DB)
        
        # Recent wiki updates
        wiki_query = """SELECT json_group_array(json_object(
            'slug', slug, 'title', title
        )) FROM pages ORDER BY updated_at DESC LIMIT 5"""
        
        wiki = MemsterClient.query_json(wiki_query, WIKI_DB)
        
        return jsonify({
            'ok': True,
            'memories': memories or [],
            'sp_status': sp_status[0] if sp_status else None,
            'recent_wiki': wiki or [],
            'generated_at': datetime.utcnow().isoformat()
        })

from flask import Flask, request, jsonify
