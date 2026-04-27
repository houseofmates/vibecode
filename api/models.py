"""
Hermes Web UI -- Session model and in-memory session store.
"""
import collections
import json
import logging
import time
import uuid
from pathlib import Path

import api.config as _cfg
from api.config import (
    SESSION_DIR, SESSION_INDEX_FILE, SESSIONS, SESSIONS_MAX,
    LOCK, DEFAULT_WORKSPACE, DEFAULT_MODEL, PROJECTS_FILE, HOME,
    REMOTE_SESSIONS_CACHE_FILE
)
from api.workspace import get_last_workspace

logger = logging.getLogger(__name__)

_index_cache = {}
_INDEX_CACHE_LOADED = False

# Session list cache with TTL for fast API responses
_SESSIONS_LIST_CACHE = None
_SESSIONS_LIST_CACHE_TIME = 0
_SESSIONS_LIST_CACHE_TTL = 30  # Cache for 30 seconds

def _load_index_map():
    """Load the on-disk index into an in-memory dict. Returns a dict keyed by session_id."""
    global _index_cache, _INDEX_CACHE_LOADED
    if _INDEX_CACHE_LOADED:
        return _index_cache
    _index_cache = {}
    if SESSION_INDEX_FILE.exists():
        try:
            for entry in json.loads(SESSION_INDEX_FILE.read_text(encoding='utf-8')):
                _index_cache[entry['session_id']] = entry
        except Exception:
            pass
    _INDEX_CACHE_LOADED = True
    return _index_cache

def invalidate_sessions_list_cache():
    """Invalidate the sessions list cache. Call this when sessions are modified."""
    global _SESSIONS_LIST_CACHE, _SESSIONS_LIST_CACHE_TIME
    _SESSIONS_LIST_CACHE = None
    _SESSIONS_LIST_CACHE_TIME = 0

def _rebuild_session_index():
    """Full rebuild of the session index. Called once at startup or when the index is stale."""
    entries = []
    for p in SESSION_DIR.glob('*.json'):
        if p.name.startswith('_'): continue
        try:
            # Try loading by filename stem, but also try stripping 'session_' prefix
            s = Session.load(p.stem)
            if not s and p.stem.startswith('session_'):
                # Try loading by the ID inside the filename (without session_ prefix)
                s = Session.load(p.stem[8:])  # Remove 'session_' prefix
            if s: entries.append(s.compact())
        except Exception:
            logger.debug("Failed to load session from %s", p)
    with LOCK:
        for s in SESSIONS.values():
            if not any(e['session_id'] == s.session_id for e in entries):
                entries.append(s.compact())
    entries.sort(key=lambda s: s['updated_at'], reverse=True)
    SESSION_INDEX_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
    global _index_cache, _INDEX_CACHE_LOADED
    _index_cache = {e['session_id']: e for e in entries}
    _INDEX_CACHE_LOADED = True

def _upsert_session_index(session_compact):
    """Incrementally update the index with a single session. No full scan needed."""
    idx = _load_index_map()
    sid = session_compact['session_id']
    idx[sid] = session_compact
    # Write full index (acceptable since index is small -- only metadata, no messages)
    try:
        entries = sorted(idx.values(), key=lambda s: s['updated_at'], reverse=True)
        SESSION_INDEX_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

def _remove_session_from_index(session_id: str):
    """Remove a session from the index without deleting the entire file."""
    idx = _load_index_map()
    if session_id in idx:
        del idx[session_id]
        # Write updated index
        try:
            entries = sorted(idx.values(), key=lambda s: s['updated_at'], reverse=True)
            SESSION_INDEX_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
    # Invalidate cache
    global _index_cache, _INDEX_CACHE_LOADED
    _index_cache = idx
    _INDEX_CACHE_LOADED = True


class Session:
    def __init__(self, session_id: str=None, title: str='Untitled',
                 workspace=str(DEFAULT_WORKSPACE), model=DEFAULT_MODEL,
                 messages=None, created_at=None, updated_at=None,
                 tool_calls=None, pinned: bool=False, archived: bool=False,
                 project_id: str=None, profile=None,
                 input_tokens: int=0, output_tokens: int=0, estimated_cost=None,
                 personality=None,
                 active_stream_id: str=None,
                 pending_user_message: str=None,
                 pending_attachments=None,
                 pending_started_at=None,
                 **kwargs):
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.title = title
        self.workspace = str(Path(workspace).expanduser().resolve())
        self.model = model
        self.messages = messages or []
        self.tool_calls = tool_calls or []
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()
        self.pinned = bool(pinned)
        self.archived = bool(archived)
        self.project_id = project_id or None
        self.profile = profile
        self.input_tokens = input_tokens or 0
        self.output_tokens = output_tokens or 0
        self.estimated_cost = estimated_cost
        self.personality = personality
        self.active_stream_id = active_stream_id
        self.pending_user_message = pending_user_message
        self.pending_attachments = pending_attachments or []
        self.pending_started_at = pending_started_at

    @property
    def path(self):
        return SESSION_DIR / f'{self.session_id}.json'

    def save(self, touch_updated_at: bool = True) -> None:
        if touch_updated_at:
            self.updated_at = time.time()
        self.path.write_text(
            json.dumps(self.__dict__, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        _upsert_session_index(self.compact())
        invalidate_sessions_list_cache()

    @classmethod
    def load(cls, sid):
        # Validate session ID format to prevent path traversal
        # Allow hyphens for CLI sessions (UUID format), but no other special chars
        if not sid or not all(c in '0123456789abcdefghijklmnopqrstuvwxyz_-' for c in sid):
            return None
        # Try both naming conventions: {sid}.json and session_{sid}.json
        p = SESSION_DIR / f'{sid}.json'
        if not p.exists():
            p = SESSION_DIR / f'session_{sid}.json'
        if not p.exists():
            return None
        return cls(**json.loads(p.read_text(encoding='utf-8')))

    def compact(self) -> dict:
        return {
            'session_id': self.session_id,
            'title': self.title,
            'workspace': self.workspace,
            'model': self.model,
            'message_count': len(self.messages),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'pinned': self.pinned,
            'archived': self.archived,
            'project_id': self.project_id,
            'profile': self.profile,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'estimated_cost': self.estimated_cost,
            'personality': self.personality,
        }

def get_session(sid):
    with LOCK:
        if sid in SESSIONS:
            SESSIONS.move_to_end(sid)  # LRU: mark as recently used
            return SESSIONS[sid]
    s = Session.load(sid)
    if s:
        with LOCK:
            SESSIONS[sid] = s
            SESSIONS.move_to_end(sid)
            while len(SESSIONS) > SESSIONS_MAX:
                SESSIONS.popitem(last=False)  # evict least recently used
        return s
    raise KeyError(sid)

def new_session(workspace=None, model=None):
    # Use _cfg.DEFAULT_MODEL (not the import-time snapshot) so save_settings() changes take effect
    try:
        from api.profiles import get_active_profile_name
        _profile = get_active_profile_name()
    except ImportError:
        _profile = None
    s = Session(workspace=workspace or get_last_workspace(), model=model or _cfg.DEFAULT_MODEL, profile=_profile)
    with LOCK:
        SESSIONS[s.session_id] = s
        SESSIONS.move_to_end(s.session_id)
        while len(SESSIONS) > SESSIONS_MAX:
            SESSIONS.popitem(last=False)
    s.save()
    return s

def all_sessions(limit=500):
    global _SESSIONS_LIST_CACHE, _SESSIONS_LIST_CACHE_TIME
    now = time.time()
    
    # Return cached result if fresh (avoid expensive file I/O)
    if _SESSIONS_LIST_CACHE is not None and (now - _SESSIONS_LIST_CACHE_TIME) < _SESSIONS_LIST_CACHE_TTL:
        return _SESSIONS_LIST_CACHE[:limit]
    
    # Phase C: try index first for O(1) read; fall back to full scan
    result = []
    if SESSION_INDEX_FILE.exists():
        try:
            index = json.loads(SESSION_INDEX_FILE.read_text(encoding='utf-8'))
            # Trust the index - skip expensive file.exists() checks
            # Only filter out entries without a session_id
            valid_entries = [s for s in index if s.get('session_id')]
            
            # Overlay any in-memory sessions that may be newer than the index
            index_map = {s['session_id']: s for s in valid_entries}
            with LOCK:
                for s in SESSIONS.values():
                    index_map[s.session_id] = s.compact()
            result = sorted(index_map.values(), key=lambda s: (s.get('pinned', False), s['updated_at']), reverse=True)
            # Hide empty Untitled sessions from the UI (created by tests, page refreshes, etc.)
            result = [s for s in result if not (s.get('title','Untitled')=='Untitled' and s.get('message_count',0)==0)]
            # Backfill: sessions created before Sprint 22 have no profile tag.
            # Attribute them to 'default' so the client profile filter works correctly.
            for s in result:
                if not s.get('profile'):
                    s['profile'] = 'default'
            
            # Update cache
            _SESSIONS_LIST_CACHE = result
            _SESSIONS_LIST_CACHE_TIME = now
            return result[:limit]
        except Exception:
            logger.debug("Failed to load session index, falling back to full scan")
    # Full scan fallback - optimized: pre-sort by mtime, only load recent files
    out = []
    # Get all json files with their mtimes, sort by mtime desc, take 2x limit as buffer
    files_with_mtime = []
    for p in SESSION_DIR.glob('*.json'):
        if p.name.startswith('_'): continue
        try:
            files_with_mtime.append((p, p.stat().st_mtime))
        except Exception:
            pass
    # Sort by mtime descending (most recent first) and only load top N
    files_with_mtime.sort(key=lambda x: x[1], reverse=True)
    files_to_load = files_with_mtime[:limit * 2]  # 2x buffer for filtering
    for p, _ in files_to_load:
        try:
            s = Session.load(p.stem)
            if s: out.append(s)
        except Exception:
            logger.debug("Failed to load session from %s", p)
    for s in SESSIONS.values():
        if all(s.session_id != x.session_id for x in out): out.append(s)
    out.sort(key=lambda s: (getattr(s, 'pinned', False), s.updated_at), reverse=True)
    result = [s.compact() for s in out if not (s.title=='Untitled' and len(s.messages)==0)]
    for s in result:
        if not s.get('profile'):
            s['profile'] = 'default'
    
    # Update cache even for fallback case
    _SESSIONS_LIST_CACHE = result
    _SESSIONS_LIST_CACHE_TIME = now
    return result[:limit]


def title_from(messages, fallback: str='Untitled'):
    """Derive a session title from the first user message."""
    for m in messages:
        if m.get('role') == 'user':
            c = m.get('content', '')
            if isinstance(c, list):
                c = ' '.join(p.get('text', '') for p in c if isinstance(p, dict) and p.get('type') == 'text')
            text = str(c).strip()
            if text:
                return text[:64]
    return fallback


# ── Project helpers ──────────────────────────────────────────────────────────

def load_projects() -> list:
    """Load project list from disk. Returns list of project dicts."""
    if not PROJECTS_FILE.exists():
        return []
    try:
        return json.loads(PROJECTS_FILE.read_text(encoding='utf-8'))
    except Exception:
        return []

def save_projects(projects) -> None:
    """Write project list to disk."""
    PROJECTS_FILE.write_text(json.dumps(projects, ensure_ascii=False, indent=2), encoding='utf-8')


def import_cli_session(
    session_id: str,
    title: str,
    messages,
    model: str='unknown',
    profile=None,
    created_at=None,
    updated_at=None,
):
    """Create a new WebUI session populated with CLI messages.
    Returns the Session object.
    """
    s = Session(
        session_id=session_id,
        title=title,
        workspace=get_last_workspace(),
        model=model,
        messages=messages,
        profile=profile,
        created_at=created_at,
        updated_at=updated_at,
    )
    s.save(touch_updated_at=False)
    return s


# ── CLI session bridge ──────────────────────────────────────────────────────

def get_cli_sessions() -> list:
    """Read CLI sessions from the agent's SQLite store and return them as
    dicts in a format the WebUI sidebar can render alongside local sessions.

    Returns empty list if the SQLite DB is missing, the sqlite3 module is
    unavailable, or any error occurs -- the bridge is purely additive and never
    crashes the WebUI.
    """
    import os
    cli_sessions = []
    try:
        import sqlite3
    except ImportError:
        return cli_sessions

    # Use the active WebUI profile's HERMES_HOME to find state.db.
    # The active profile is determined by what the user has selected in the UI
    # (stored in the server's runtime config). This means:
    #   - default profile  -> ~/.hermes/state.db
    #   - named profile X  -> ~/.hermes/profiles/X/state.db
    # We resolve the active profile's home directory rather than just using
    # HERMES_HOME (which is the server's launch profile, not necessarily the
    # active one after a profile switch).
    try:
        from api.profiles import get_active_hermes_home
        hermes_home = Path(get_active_hermes_home()).expanduser().resolve()
    except Exception:
        hermes_home = Path(os.getenv('HERMES_HOME', str(HOME / '.hermes'))).expanduser().resolve()

    db_path = hermes_home / 'state.db'
    if not db_path.exists():
        return cli_sessions

    # Try to resolve the active CLI profile so imported sessions integrate
    # with the WebUI profile filter (available since Sprint 22).
    try:
        from api.profiles import get_active_profile_name
        _cli_profile = get_active_profile_name()
    except ImportError:
        _cli_profile = None  # older agent -- fall back to no profile

    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT s.id, s.title, s.model, s.message_count,
                       s.started_at, s.source,
                       MAX(m.timestamp) AS last_activity
                FROM sessions s
                LEFT JOIN messages m ON m.session_id = s.id
                WHERE s.source IS NOT NULL AND s.source != 'webui'
                GROUP BY s.id
                ORDER BY COALESCE(MAX(m.timestamp), s.started_at) DESC
                LIMIT 200
            """)
            for row in cur.fetchall():
                sid = row['id']
                raw_ts = row['last_activity'] or row['started_at']
                # Prefer the CLI session's own profile from the DB; fall back to
                # the active CLI profile so sidebar filtering works either way.
                profile = _cli_profile  # CLI DB has no profile column; use active profile

                _source = row['source'] or 'cli'
                _display_title = row['title'] or f'{_source.title()} Session'
                cli_sessions.append({
                    'session_id': sid,
                    'title': _display_title,
                    'workspace': str(get_last_workspace()),
                    'model': row['model'] or None,
                    'message_count': row['message_count'] or 0,
                    'created_at': row['started_at'],
                    'updated_at': raw_ts,
                    'pinned': False,
                    'archived': False,
                    'project_id': None,
                    'profile': profile,
                    'source_tag': _source,
                    'is_cli_session': True,
                })
    except Exception:
        # DB schema changed, locked, or corrupted -- silently degrade
        return []

    return cli_sessions


def get_cli_session_messages(sid) -> list:
    """Read messages for a single CLI session from the SQLite store.
    Returns a list of {role, content, timestamp} dicts.
    Returns empty list on any error.
    """
    import os
    try:
        import sqlite3
    except ImportError:
        return []

    try:
        from api.profiles import get_active_hermes_home
        hermes_home = Path(get_active_hermes_home()).expanduser().resolve()
    except Exception:
        hermes_home = Path(os.getenv('HERMES_HOME', str(HOME / '.hermes'))).expanduser().resolve()
    db_path = hermes_home / 'state.db'
    if not db_path.exists():
        return []

    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT role, content, timestamp
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (sid,))
            msgs = []
            for row in cur.fetchall():
                msgs.append({
                    'role': row['role'],
                    'content': row['content'],
                    'timestamp': row['timestamp'],
                })
    except Exception:
        return []
    return msgs


def delete_cli_session(sid) -> bool:
    """Delete a CLI session from state.db (messages + session row).
    Returns True if deleted, False if not found or error.
    """
    import os
    try:
        import sqlite3
    except ImportError:
        return False

    try:
        from api.profiles import get_active_hermes_home
        hermes_home = Path(get_active_hermes_home()).expanduser().resolve()
    except Exception:
        hermes_home = Path(os.getenv('HERMES_HOME', str(HOME / '.hermes'))).expanduser().resolve()
    db_path = hermes_home / 'state.db'
    if not db_path.exists():
        return False

    try:
        with sqlite3.connect(str(db_path)) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
            cur.execute("DELETE FROM sessions WHERE id = ?", (sid,))
            conn.commit()
            return cur.rowcount > 0
    except Exception:
        return False
