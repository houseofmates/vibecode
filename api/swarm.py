"""
Hermes Web UI -- Swarm multi-agent orchestration backend.

Manages parallel worker agents spawned from a single user task.
Workers run as separate _run_agent_streaming threads with their own
stream_ids, all flowing through the existing multiplexed SSE pipeline.

Coordination model:
  SWARM_COORD[swarm_id] = [
    {worker_id, worker_name, role, content, timestamp, type},
    ...
  ]
  Workers append messages here throughout execution. The user sees
  these messages in the swarm's coordination chat in real time.

State model:
  SWARMS[swarm_id] = {
    id, session_id, task, mode, model, workspace,
    coord_session_id: str,   # parent session that owns the coordination chat
    workers: [{worker_id, stream_id, task, status, result, session_id, ...}],
    status: running|completed|cancelled|failed,
    created_at, completed_at, aggregated_result
  }

Worker lifecycle: pending -> running -> done|error
Swarm lifecycle: running -> completed|cancelled|failed
"""

import json
import logging
import queue
import threading
import time
import uuid
import traceback
import re

logger = logging.getLogger(__name__)

MAX_WORKER_TIMEOUT = 300  # 5 minutes

# ── In-memory swarm state ────────────────────────────────────────────────────
SWARMS = {}          # swarm_id -> swarm dict
SWARMS_LOCK = threading.Lock()

# Coordination messages per swarm
SWARM_COORD = {}     # swarm_id -> list of coord messages
SWARM_CONTEXT = {}   # swarm_id -> dict of shared findings between workers
CONTEXT_LOCK = threading.Lock()

STREAM_CHUNK_INTERCEPT = {}  # swarm_id -> callback for live coord chat streaming
COORD_LOCK = threading.Lock()

# Rainbow colors for swarm cards
SWARM_COLORS = [
    '#e94560',  # 0: red (accent)
    '#ff6b35',  # 1: orange
    '#f6b012',  # 2: amber (termisol accent)
    '#4ade80',  # 3: green
    '#22d3ee',  # 4: cyan
    '#6cb4ff',  # 5: blue
    '#a78bfa',  # 6: violet
    '#f472b6',  # 7: pink
]

# Reverse index: stream_id -> swarm_id
_STREAM_TO_SWARM = {}
_STREAM_TO_WORKER = {}
MAX_WORKERS_PER_SWARM = 8

# Stream hooks: stream_id -> callback for intercepting text chunks
SWARM_STREAM_HOOKS = {}
STREAM_HOOKS_LOCK = threading.Lock()

def register_stream_hook(stream_id, swarm_id, worker_id, worker_name):
    """Register a hook that will be called on each text chunk from this stream."""
    with STREAM_HOOKS_LOCK:
        SWARM_STREAM_HOOKS[stream_id] = (swarm_id, worker_id, worker_name)

def unregister_stream_hook(stream_id):
    """Remove a stream hook."""
    with STREAM_HOOKS_LOCK:
        SWARM_STREAM_HOOKS.pop(stream_id, None)

def on_stream_chunk(stream_id, text_chunk):
    """Called from streaming.py when a text chunk is produced.
    Posts to coordination chat so all agents see live output.
    """
    with STREAM_HOOKS_LOCK:
        hook = SWARM_STREAM_HOOKS.get(stream_id)
    if not hook:
        return
    swarm_id, worker_id, worker_name = hook
    if text_chunk and text_chunk.strip():
        _post_coord_message(swarm_id, worker_id, worker_name, 'agent',
            text_chunk, 'chunk')

WORKER_NAMES = [
    'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta'
]

# ── Coordination helpers ────────────────────────────────────────────────────

def _get_swarm_color(index):
    return SWARM_COLORS[index % len(SWARM_COLORS)]

def _post_coord_message(swarm_id, worker_id, worker_name, role, content, msg_type='text'):
    """Append a message to the swarm's coordination chat."""
    with COORD_LOCK:
        if swarm_id not in SWARM_COORD:
            SWARM_COORD[swarm_id] = []
        SWARM_COORD[swarm_id].append({
            'worker_id': worker_id,
            'worker_name': worker_name,
            'role': role,
            'content': content,
            'timestamp': time.time(),
            'type': msg_type,
        })

def _get_coord_messages(swarm_id, after_ts=None):
    """Get coordination messages for a swarm, optionally after a timestamp."""
    with COORD_LOCK:
        msgs = SWARM_COORD.get(swarm_id, [])
        if after_ts is not None:
            msgs = [m for m in msgs if m['timestamp'] > after_ts]
        return list(msgs)

def swarm_context_set(swarm_id, key, value):
    """Write a shared value to the swarm context pool."""
    with CONTEXT_LOCK:
        if swarm_id not in SWARM_CONTEXT:
            SWARM_CONTEXT[swarm_id] = {}
        SWARM_CONTEXT[swarm_id][key] = value

def swarm_context_get(swarm_id, key=None):
    """Read from the swarm context pool."""
    with CONTEXT_LOCK:
        ctx = SWARM_CONTEXT.get(swarm_id, {})
        if key is not None:
            return ctx.get(key)
        return dict(ctx)

def swarm_context_keys(swarm_id):
    """List all keys in the swarm context pool."""
    with CONTEXT_LOCK:
        return list(SWARM_CONTEXT.get(swarm_id, {}).keys())

def set_swarm_context(swarm_id, key, value):
    """Set a shared context entry accessible to all workers in the swarm."""
    with CONTEXT_LOCK:
        if swarm_id not in SWARM_CONTEXT:
            SWARM_CONTEXT[swarm_id] = {}
        SWARM_CONTEXT[swarm_id][key] = {
            'value': value,
            'timestamp': time.time(),
        }

def get_swarm_context(swarm_id):
    """Get all shared context entries for a swarm."""
    with CONTEXT_LOCK:
        return dict(SWARM_CONTEXT.get(swarm_id, {}))

def clear_swarm_context(swarm_id):
    """Clear shared context when swarm completes."""
    with CONTEXT_LOCK:
        SWARM_CONTEXT.pop(swarm_id, None)

def _stream_chunk_to_coord(swarm_id, stream_id, text_chunk):
    """Relay worker streaming text to coordination chat in real-time."""
    with SWARMS_LOCK:
        worker_id = _STREAM_TO_WORKER.get(stream_id)
        swarm = SWARMS.get(swarm_id)
        if not swarm or not worker_id:
            return
        worker = None
        for w in swarm['workers']:
            if w['worker_id'] == worker_id:
                worker = w
                break
        if not worker:
            return
        worker_idx = swarm['workers'].index(worker)
        worker_name = worker.get('name', WORKER_NAMES[worker_idx] if worker_idx < len(WORKER_NAMES) else worker_id[:6])

    # Append to coord messages
    _post_coord_message(swarm_id, worker_id, worker_name, 'agent', text_chunk, 'stream')

    # Fanout to SSE
    _fanout_swarm_event('swarm.stream_chunk', swarm_id, {
        'worker_id': worker_id,
        'worker_name': worker_name,
        'text': text_chunk,
    })


# ── SSE fanout ──────────────────────────────────────────────────────────────

def _fanout_swarm_event(event_type, swarm_id, data):
    try:
        from api.config import MULTIPLEX_QUEUES, MULTIPLEX_LOCK
        payload = {**data, 'swarm_id': swarm_id}
        with MULTIPLEX_LOCK:
            clients = list(MULTIPLEX_QUEUES.items())
            for _cid, mq in clients:
                try:
                    mq.put_nowait((event_type, payload))
                    mq._last_put = time.time()
                except Exception as e:
                    logger.debug(f"Failed to send swarm event to client {_cid}: {e}")
    except Exception as e:
        logger.debug(f"swarm fanout failed for {event_type}: {e}")

def register_stream_to_swarm(stream_id, swarm_id, worker_id):
    with SWARMS_LOCK:
        _STREAM_TO_SWARM[stream_id] = swarm_id
        _STREAM_TO_WORKER[stream_id] = worker_id

def unregister_stream_from_swarm(stream_id):
    with SWARMS_LOCK:
        _STREAM_TO_SWARM.pop(stream_id, None)
        _STREAM_TO_WORKER.pop(stream_id, None)

def get_swarm_for_stream(stream_id):
    with SWARMS_LOCK:
        return _STREAM_TO_SWARM.get(stream_id), _STREAM_TO_WORKER.get(stream_id)

# ── Stream hooks ────────────────────────────────────────────────────────────

def on_worker_stream_done(stream_id, result_text, usage=None):
    swarm_id, worker_id = get_swarm_for_stream(stream_id)
    if not swarm_id:
        return False

    with SWARMS_LOCK:
        swarm = SWARMS.get(swarm_id)
        if not swarm:
            return True

        worker = None
        for w in swarm['workers']:
            if w['worker_id'] == worker_id:
                worker = w
                break
        if not worker:
            return True

        worker['status'] = 'done'
        worker['result'] = result_text or ''
        worker['completed_at'] = time.time()
        if usage:
            worker['usage'] = usage

        # Post completion message to coordination chat
        worker_idx = swarm['workers'].index(worker)
        worker_name = worker.get('name', WORKER_NAMES[worker_idx] if worker_idx < len(WORKER_NAMES) else worker_id[:6])
        _post_coord_message(swarm_id, worker_id, worker_name, 'agent',
            f"✓ finished: {worker['task'][:80]}\n\n{result_text[:300] if result_text else '(no output)'}")

        _fanout_swarm_event('swarm.worker_completed', swarm_id, {
            'worker_id': worker_id,
            'stream_id': stream_id,
            'task': worker['task'],
            'status': 'done',
            'result': worker['result'][:500] if worker['result'] else '',
            'duration': round(worker['completed_at'] - (worker.get('started_at') or worker['completed_at']), 1),
        })

        all_done = all(w['status'] in ('done', 'error') for w in swarm['workers'])
        if all_done:
            swarm['status'] = 'completed'
            swarm['completed_at'] = time.time()
            results = {}
            for w in swarm['workers']:
                results[w['worker_id']] = {
                    'task': w['task'],
                    'status': w['status'],
                    'result': (w.get('result') or '')[:2000],
                    'duration': round(
                        (w.get('completed_at') or time.time()) - (w.get('started_at') or time.time()), 1
                    ) if w.get('started_at') else None,
                }
            swarm['aggregated_result'] = results
            
            # Attach swarm summary to parent session
            threading.Thread(target=attach_swarm_to_session, args=(swarm_id,), daemon=True).start()
            
            _fanout_swarm_event('swarm.completed', swarm_id, {
                'task': swarm['task'],
                'worker_count': len(swarm['workers']),
                'results': results,
                'duration': round(swarm['completed_at'] - swarm['created_at'], 1),
            })
            try:
                inject_results_into_session(swarm_id, swarm['session_id'])
            except Exception as e:
                logger.warning(f"Failed to inject swarm results into session: {e}")
            clear_swarm_context(swarm_id)

    clean_coord = None  # Keep only latest 200 msgs
    with COORD_LOCK:
        if swarm_id in SWARM_COORD and len(SWARM_COORD[swarm_id]) > 200:
            SWARM_COORD[swarm_id] = SWARM_COORD[swarm_id][-200:]

    unregister_stream_from_swarm(stream_id)
    return True

def on_worker_stream_error(stream_id, error_text):
    swarm_id, worker_id = get_swarm_for_stream(stream_id)
    if not swarm_id:
        return False

    with SWARMS_LOCK:
        swarm = SWARMS.get(swarm_id)
        if not swarm:
            return True

        worker = None
        for w in swarm['workers']:
            if w['worker_id'] == worker_id:
                worker = w
                break
        if not worker:
            return True

        worker['status'] = 'error'
        worker['result'] = error_text or 'unknown error'
        worker['completed_at'] = time.time()

        worker_idx = swarm['workers'].index(worker)
        worker_name = worker.get('name', WORKER_NAMES[worker_idx] if worker_idx < len(WORKER_NAMES) else worker_id[:6])
        _post_coord_message(swarm_id, worker_id, worker_name, 'agent',
            f"✗ failed: {worker['task'][:80]}\n\n{error_text[:300] if error_text else 'unknown error'}")

        _fanout_swarm_event('swarm.worker_error', swarm_id, {
            'worker_id': worker_id,
            'stream_id': stream_id,
            'task': worker['task'],
            'status': 'error',
            'error': error_text[:500] if error_text else '',
        })

        all_done = all(w['status'] in ('done', 'error') for w in swarm['workers'])
        if all_done:
            swarm['status'] = 'completed'
            swarm['completed_at'] = time.time()
            results = {}
            for w in swarm['workers']:
                results[w['worker_id']] = {
                    'task': w['task'],
                    'status': w['status'],
                    'result': (w.get('result') or '')[:2000],
                }
            swarm['aggregated_result'] = results
            _fanout_swarm_event('swarm.completed', swarm_id, {
                'task': swarm['task'],
                'worker_count': len(swarm['workers']),
                'results': results,
                'duration': round(swarm['completed_at'] - swarm['created_at'], 1),
            })
            try:
                inject_results_into_session(swarm_id, swarm['session_id'])
            except Exception as e:
                logger.warning(f"Failed to inject swarm results into session: {e}")
            clear_swarm_context(swarm_id)

    clean_coord = None  # Keep only latest 200 msgs
    with COORD_LOCK:
        if swarm_id in SWARM_COORD and len(SWARM_COORD[swarm_id]) > 200:
            SWARM_COORD[swarm_id] = SWARM_COORD[swarm_id][-200:]

    unregister_stream_from_swarm(stream_id)
    return True

# ── Session context inheritance ─────────────────────────────────────────────

def _get_session_context(session_id):
    """Get a context summary from a parent session for worker inheritance."""
    try:
        from api.models import get_session
        s = get_session(session_id)
        if not s:
            return ''
        ctx = []
        ctx.append(f"## swarm task context")
        ctx.append(f"workspace: {s.workspace or os.environ.get('DEFAULT_HOME', os.path.expanduser('~'))}")
        if hasattr(s, 'title') and s.title and s.title != 'Untitled':
            ctx.append(f"conversation: {s.title}")
        if hasattr(s, 'messages') and s.messages:
            # Include last 3 exchanges for context
            msgs = s.messages[-6:]
            ctx.append("\n## recent conversation:\n")
            for m in msgs:
                role = m.get('role', 'user')
                content = m.get('content', '')
                if isinstance(content, str) and content.strip():
                    snippet = content[:400]
                    if len(content) > 400:
                        snippet += '...'
                    ctx.append(f"[{role}]: {snippet}")
        return '\n'.join(ctx)
    except Exception:
        return ''

def _get_system_prompt(session_id):
    """Get system prompt from parent session if available."""
    try:
        from api.models import get_session
        s = get_session(session_id)
        if not s:
            return ''
        return getattr(s, 'system_prompt', '') or ''
    except Exception:
        return ''

# ── Swarm creation ───────────────────────────────────────────────────────────

def create_swarm(session_id, task, subtasks, model, workspace, mode='auto'):
    """Spawn a swarm of parallel agents that share a coordination chat."""
    if not subtasks:
        raise ValueError("swarm requires at least 1 subtask")
    if len(subtasks) > MAX_WORKERS_PER_SWARM:
        raise ValueError(f"max {MAX_WORKERS_PER_SWARM} workers per swarm, got {len(subtasks)}")

    swarm_id = uuid.uuid4().hex[:12]
    coord_session_id = f"swarm-{swarm_id}"  # virtual coordination session

    workers = []
    for i, sub in enumerate(subtasks):
        if isinstance(sub, str):
            sub = {'task': sub}
        worker_id = uuid.uuid4().hex[:12]
        stream_id = uuid.uuid4().hex
        workers.append({
            'worker_id': worker_id,
            'worker_name': WORKER_NAMES[i] if i < len(WORKER_NAMES) else f"worker-{i+1}",
            'stream_id': stream_id,
            'task': sub.get('task', f'worker {i+1}'),
            'context': sub.get('context', ''),
            'tools': sub.get('tools', []),
            'status': 'pending',
            'result': None,
            'usage': None,
            'started_at': None,
            'completed_at': None,
            'session_id': None,  # created per-worker in thread
        })

    # Get context from parent session
    parent_context = _get_session_context(session_id)
    system_prompt = _get_system_prompt(session_id)

    # Initialize coordination messages
    with COORD_LOCK:
        SWARM_COORD[swarm_id] = []

    # Build coordination system prompt (shared by all workers)
    coord_system = (system_prompt + '\n\n' if system_prompt else '') + f"""You are part of a collaborative swarm working on: "{task}"

Your role: {workers[0]['task']} (and others will handle other aspects)

## swarm rules:
- This swarm shares a coordination chat where all agents can see each other's progress
- Post updates, findings, and questions to the coordination chat as you work
- Read what other agents have posted to understand the full context
- Be concise but informative in your coordination messages
- Share data, code snippets, and findings — don't keep them to yourself
- When you find something another agent might need, flag it in your next message
- Mark your final result clearly with ✓ DONE

## coordination chat:
All messages you post go to the shared swarm coordination chat. Other agents and the user can see them.

Start by posting your plan to the coordination chat, then execute your task.
When done, post your final result with ✓ DONE prefix.
""" if not system_prompt else f"""You are part of a swarm working on: "{task}". {system_prompt}

Post your progress and findings to the coordination chat as you work.
Share relevant data with other agents. Be helpful and collaborative.
Mark your final result with ✓ DONE.
"""

    swarm = {
        'id': swarm_id,
        'session_id': session_id,
        'coord_session_id': coord_session_id,
        'task': task,
        'mode': mode,
        'model': model,
        'workspace': workspace,
        'system_prompt': coord_system,
        'parent_context': parent_context,
        'workers': workers,
        'status': 'running',
        'created_at': time.time(),
        'completed_at': None,
        'aggregated_result': None,
    }

    with SWARMS_LOCK:
        SWARMS[swarm_id] = swarm
        for w in workers:
            _STREAM_TO_SWARM[w['stream_id']] = swarm_id
            _STREAM_TO_WORKER[w['stream_id']] = w['worker_id']

    # Post swarm start to coordination chat
    _post_coord_message(swarm_id, '__system__', 'swarm',
        f"🐝 swarm started: {task}\n\n{len(workers)} agents: {', '.join(w['worker_name'] for w in workers)}", 'system')

    # Fan out started event
    _fanout_swarm_event('swarm.started', swarm_id, {
        'task': task,
        'worker_count': len(workers),
        'mode': mode,
        'coord_session_id': coord_session_id,
        'workers': [{'worker_id': w['worker_id'], 'worker_name': w['worker_name'], 'task': w['task'], 'color': _get_swarm_color(i)} for i, w in enumerate(workers)],
    })

    # Post each agent's intro to coordination chat
    for i, w in enumerate(workers):
        _post_coord_message(swarm_id, w['worker_id'], w['worker_name'], 'agent',
            f"👋 {w['worker_name']} taking on: {w['task']}", 'join')

    # Spawn workers
    from api.config import STREAMS, STREAMS_LOCK, CANCEL_FLAGS
    from api.models import new_session
    from api.streaming import _run_agent_streaming

    for i, w in enumerate(workers):
        q = queue.Queue()
        with STREAMS_LOCK:
            STREAMS[w['stream_id']] = q
        cancel_event = threading.Event()
        CANCEL_FLAGS[w['stream_id']] = cancel_event

        # Create a session for this worker with hashtag prefix
        worker_session = new_session(workspace=workspace, model=model)
        w['session_id'] = worker_session.session_id
        # Tag session title so sidebar can filter it
        worker_session.title = f"#{swarm_id[:6]} {w['worker_name']}: {w['task'][:40]}"
        worker_session.save()
        w['status'] = 'running'
        w['started_at'] = time.time()

        # Build worker prompt with context
        worker_context = parent_context
        if w.get('context'):
            worker_context = (worker_context + '\n\n' if worker_context else '') + f"## your specific context:\n{w['context']}"

        worker_prompt = f"""{coord_system}

{worker_context}

---

## YOUR TASK:
{w['task']}

Begin working now. Post your plan first, then execute. Share findings in the coordination chat.
"""

        _fanout_swarm_event('swarm.worker_started', swarm_id, {
            'worker_id': w['worker_id'],
            'worker_name': w['worker_name'],
            'stream_id': w['stream_id'],
            'task': w['task'],
            'status': 'running',
        })

        thr = threading.Thread(
            target=_run_swarm_worker,
            args=(swarm_id, w, worker_prompt, model, workspace, session_id, i),
            daemon=True,
        )
        thr.start()

    return swarm_id, [{'worker_id': w['worker_id'], 'worker_name': w['worker_name'], 'stream_id': w['stream_id'], 'task': w['task']} for w in workers]

# ── Worker thread ────────────────────────────────────────────────────────────

def _run_swarm_worker(swarm_id, worker, worker_prompt, model, workspace, session_id, worker_index):
    stream_id = worker['stream_id']
    worker_id = worker['worker_id']
    worker_name = worker.get('name', WORKER_NAMES[worker_index] if worker_index < len(WORKER_NAMES) else worker_id[:6])

    with SWARMS_LOCK:
        _STREAM_TO_SWARM[stream_id] = swarm_id
        _STREAM_TO_WORKER[stream_id] = worker_id

    # Post that we're starting
    _post_coord_message(swarm_id, worker_id, worker_name, 'agent',
        f"{worker_name} is thinking...", 'thinking')

    try:
        from api.streaming import _run_agent_streaming

        # Note: SSE event routing is handled by STREAM_CHUNK_HOOKS below
        # The coordination chat receives live updates via _chunk_hook function

        # Hook: intercept SSE text chunks for live coord chat
        from api.streaming import STREAM_CHUNK_HOOKS
        stream_id_local = stream_id
        swarm_id_local = swarm_id
        def _chunk_hook(chunk_text):
            _stream_chunk_to_coord(swarm_id_local, stream_id_local, chunk_text)
        STREAM_CHUNK_HOOKS[stream_id_local] = _chunk_hook

        try:
            _run_agent_streaming(
                session_id=worker['session_id'],
                msg_text=worker_prompt,
                model=model,
                workspace=workspace,
                stream_id=stream_id,
            )
        finally:
            STREAM_CHUNK_HOOKS.pop(stream_id_local, None)

        with SWARMS_LOCK:
            if worker['status'] == 'running':
                worker['status'] = 'done'
                worker['completed_at'] = time.time()
                worker['result'] = '(completed)'

            swarm = SWARMS.get(swarm_id)
            if swarm and all(w['status'] in ('done', 'error') for w in swarm['workers']):
                if swarm['status'] != 'completed':
                    swarm['status'] = 'completed'
                    swarm['completed_at'] = time.time()
                    results = {w['worker_id']: {'task': w['task'], 'status': w['status'], 'result': (w.get('result') or '')[:2000]} for w in swarm['workers']}
                    swarm['aggregated_result'] = results
                    _fanout_swarm_event('swarm.completed', swarm_id, {
                        'task': swarm['task'],
                        'worker_count': len(swarm['workers']),
                        'results': results,
                        'duration': round(swarm['completed_at'] - swarm['created_at'], 1),
                    })
                    # Inject results into parent session
                    try:
                        inject_results_into_session(swarm_id, session_id)
                    except Exception:
                        pass

    except Exception as e:
        error_text = str(e)
        logger.error(f"swarm worker {worker_id} error: {error_text}\n{traceback.format_exc()}")

        with SWARMS_LOCK:
            worker['status'] = 'error'
            worker['result'] = error_text
            worker['completed_at'] = time.time()

        _post_coord_message(swarm_id, worker_id, worker_name, 'agent',
            f"✗ {worker_name} hit an error: {error_text[:200]}", 'error')
        _fanout_swarm_event('swarm.worker_error', swarm_id, {
            'worker_id': worker_id,
            'stream_id': stream_id,
            'task': worker['task'],
            'status': 'error',
            'error': error_text[:500],
        })

        swarm = SWARMS.get(swarm_id)
        if swarm and all(w['status'] in ('done', 'error') for w in swarm['workers']):
            if swarm['status'] != 'completed':
                swarm['status'] = 'completed'
                swarm['completed_at'] = time.time()
                _fanout_swarm_event('swarm.completed', swarm_id, {
                    'task': swarm['task'],
                    'worker_count': len(swarm['workers']),
                    'results': {w['worker_id']: {'task': w['task'], 'status': w['status'], 'result': (w.get('result') or '')[:2000]} for w in swarm['workers']},
                    'duration': round(swarm['completed_at'] - swarm['created_at'], 1),
                })

    finally:
        _monitor_running[0] = False
        try:
            _monitor_thread.join(timeout=2)
        except Exception as e:
            logger.debug(f"Failed to join monitor thread: {e}")
        unregister_stream_hook(stream_id)
        with SWARMS_LOCK:
            _STREAM_TO_SWARM.pop(stream_id, None)
            _STREAM_TO_WORKER.pop(stream_id, None)

# ── Cancel / Kill ──────────────────────────────────────────────────────────────

def cancel_worker(swarm_id, worker_id):
    """Cancel a single worker in a swarm without stopping others."""
    from api.config import CANCEL_FLAGS
    
    with SWARMS_LOCK:
        swarm = SWARMS.get(swarm_id)
        if not swarm:
            return False, 'swarm not found'
        if swarm['status'] not in ('running',):
            return False, 'swarm is not running'
        
        worker = None
        worker_idx = None
        for i, w in enumerate(swarm['workers']):
            if w['worker_id'] == worker_id:
                worker = w
                worker_idx = i
                break
        
        if not worker:
            return False, 'worker not found'
        if worker['status'] not in ('running',):
            return False, f'worker is already {worker["status"]}'
        
        worker['status'] = 'cancelled'
        worker['completed_at'] = time.time()
        
        stream_id = worker['stream_id']
        flag = CANCEL_FLAGS.get(stream_id)
        if flag and not flag.is_set():
            flag.set()
        
        try:
            from api.streaming import cancel_stream
            cancel_stream(stream_id)
        except Exception:
            pass
        
        worker_name = worker.get('name', WORKER_NAMES[worker_idx] if worker_idx is not None and worker_idx < len(WORKER_NAMES) else worker_id[:6])
        _post_coord_message(swarm_id, worker_id, worker_name, 'agent',
            f'❌ {worker_name} cancelled (killed by user)', 'cancelled')
        
        # Check if all workers are done
        all_done = all(w['status'] in ('done', 'error', 'cancelled') for w in swarm['workers'])
        if all_done:
            swarm['status'] = 'completed' if any(w['status'] in ('done', 'error') for w in swarm['workers']) else 'cancelled'
            swarm['completed_at'] = time.time()
            _fanout_swarm_event('swarm.completed' if swarm['status'] == 'completed' else 'swarm.cancelled',
                swarm_id, {'worker_id': worker_id, 'status': worker['status']})
    
    _fanout_swarm_event('swarm.worker_cancelled', swarm_id, {
        'worker_id': worker_id,
        'worker_name': worker_name,
    })
    return True, f'worker {worker_name} cancelled'

def cancel_swarm(swarm_id):
    from api.config import CANCEL_FLAGS, STREAMS_LOCK, STREAMS

    with SWARMS_LOCK:
        swarm = SWARMS.get(swarm_id)
        if not swarm:
            return False
        if swarm['status'] not in ('running',):
            return False

        cancelled_workers = []
        for w in swarm['workers']:
            if w['status'] == 'running':
                w['status'] = 'cancelled'
                w['completed_at'] = time.time()
                cancelled_workers.append(w['worker_id'])

                stream_id = w['stream_id']
                flag = CANCEL_FLAGS.get(stream_id)
                if flag and not flag.is_set():
                    flag.set()

                try:
                    from api.streaming import cancel_stream
                    cancel_stream(stream_id)
                except Exception:
                    pass

                worker_idx = swarm['workers'].index(w)
                worker_name = w.get('name', WORKER_NAMES[worker_idx] if worker_idx < len(WORKER_NAMES) else w['worker_id'][:6])
                _post_coord_message(swarm_id, w['worker_id'], worker_name, 'agent', '❌ cancelled by user', 'cancelled')

        swarm['status'] = 'cancelled'
        swarm['completed_at'] = time.time()

    _fanout_swarm_event('swarm.cancelled', swarm_id, {
        'cancelled_workers': cancelled_workers,
    })

    return True

def kill_worker(swarm_id, worker_id):
    """Kill a single worker in a swarm without affecting others."""
    from api.config import CANCEL_FLAGS, STREAMS_LOCK, STREAMS

    with SWARMS_LOCK:
        swarm = SWARMS.get(swarm_id)
        if not swarm:
            return False
        worker = None
        for w in swarm['workers']:
            if w['worker_id'] == worker_id:
                worker = w
                break
        if not worker or worker['status'] != 'running':
            return False

        worker['status'] = 'cancelled'
        worker['completed_at'] = time.time()

        stream_id = worker['stream_id']
        flag = CANCEL_FLAGS.get(stream_id)
        if flag and not flag.is_set():
            flag.set()

        try:
            from api.streaming import cancel_stream
            cancel_stream(stream_id)
        except Exception:
            pass

        worker_idx = swarm['workers'].index(worker)
        worker_name = worker.get('name', WORKER_NAMES[worker_idx] if worker_idx < len(WORKER_NAMES) else worker_id[:6])
        _post_coord_message(swarm_id, worker_id, worker_name, 'agent',
            f'{worker_name} was removed from the swarm', 'cancelled')

        _fanout_swarm_event('swarm.worker_cancelled', swarm_id, {
            'worker_id': worker_id,
            'stream_id': stream_id,
        })

        # Check if all workers are done
        all_done = all(w['status'] in ('done', 'error', 'cancelled') for w in swarm['workers'])
        if all_done:
            swarm['status'] = 'completed'
            swarm['completed_at'] = time.time()
            results = {}
            for w in swarm['workers']:
                results[w['worker_id']] = {
                    'task': w['task'],
                    'status': w['status'],
                    'result': (w.get('result') or '')[:2000],
                }
            swarm['aggregated_result'] = results
            _fanout_swarm_event('swarm.completed', swarm_id, {
                'task': swarm['task'],
                'worker_count': len(swarm['workers']),
                'results': results,
                'duration': round(swarm['completed_at'] - swarm['created_at'], 1),
            })
            try:
                inject_results_into_session(swarm_id, swarm['session_id'])
            except Exception as e:
                logger.warning(f"Failed to inject swarm results into session: {e}")
            clear_swarm_context(swarm_id)

    clean_coord = None  # Keep only latest 200 msgs
    with COORD_LOCK:
        if swarm_id in SWARM_COORD and len(SWARM_COORD[swarm_id]) > 200:
            SWARM_COORD[swarm_id] = SWARM_COORD[swarm_id][-200:]

    return True


# ── Status / listing ──────────────────────────────────────────────────────────

def get_swarm_status(swarm_id):
    with SWARMS_LOCK:
        swarm = SWARMS.get(swarm_id)
        if not swarm:
            return None
        return _sanitize_swarm_for_api(swarm)

def list_active_swarms():
    with SWARMS_LOCK:
        return [_sanitize_swarm_for_api(s) for s in SWARMS.values() if s['status'] == 'running']

def list_all_swarms():
    with SWARMS_LOCK:
        return [_sanitize_swarm_for_api(s) for s in SWARMS.values()]


def aggregate_results(swarm_id):
    """Analyze results across workers and detect patterns."""
    with SWARMS_LOCK:
        swarm = SWARMS.get(swarm_id)
        if not swarm:
            return None

        workers = swarm['workers']
        done_workers = [w for w in workers if w['status'] == 'done' and w.get('result')]
        failed_workers = [w for w in workers if w['status'] == 'error']
        cancelled_workers = [w for w in workers if w['status'] == 'cancelled']

        # Detect patterns
        all_results = []
        for w in done_workers:
            result = w.get('result', '') or ''
            all_results.append({
                'worker_id': w['worker_id'],
                'worker_name': w.get('name', w['worker_id'][:6]),
                'task': w['task'],
                'result': result[:3000],
                'duration': round((w.get('completed_at') or time.time()) - (w.get('started_at') or time.time()), 1) if w.get('started_at') else None,
            })

        # Pattern detection
        patterns = {}
        # Check for code blocks
        code_workers = [r for r in all_results if '```' in r['result']]
        if code_workers:
            patterns['has_code'] = len(code_workers)

        # Check for file paths
        import re
        path_workers = [r for r in all_results if re.search(r'[/\\]\w+\.[a-z]+', r['result'])]
        if path_workers:
            patterns['mentions_files'] = len(path_workers)

        # Check for consensus (same first sentence or key phrase)
        first_sentences = []
        for r in all_results:
            lines = r['result'].strip().split('\n')
            if lines:
                first = lines[0].strip().lower()
                if len(first) > 10:
                    first_sentences.append(first)
        if len(first_sentences) >= 2:
            from collections import Counter
            counts = Counter(first_sentences)
            most_common = counts.most_common(1)
            if most_common and most_common[0][1] >= 2:
                patterns['consensus'] = f"{most_common[0][1]}/{len(first_sentences)} workers agree"

        summary = {
            'swarm_id': swarm_id,
            'task': swarm['task'],
            'done': len(done_workers),
            'failed': len(failed_workers),
            'cancelled': len(cancelled_workers),
            'total': len(workers),
            'results': all_results,
            'patterns': patterns,
            'context': get_swarm_context(swarm_id),
        }

        return summary

def inject_results_into_session(swarm_id, parent_session_id):
    """Inject swarm results as a single message in the parent session."""
    aggregate = aggregate_results(swarm_id)
    if not aggregate:
        return False

    try:
        from api.models import get_session
        session = get_session(parent_session_id)

        # Build summary message
        lines = []
        lines.append(f"🐝 swarm results: {aggregate['task']}\n")
        lines.append(f"agents: {aggregate['total']} | done: {aggregate['done']} | failed: {aggregate['failed']} | cancelled: {aggregate['cancelled']}\n")

        if aggregate['patterns']:
            lines.append("patterns detected:")
            for k, v in aggregate['patterns'].items():
                lines.append(f"  · {k}: {v}")
            lines.append("")

        for r in aggregate['results']:
            status_icon = '✓' if r['result'] else '✗'
            duration = f" ({r['duration']}s)" if r['duration'] else ""
            lines.append(f"--- {r['worker_name']} {status_icon}{duration} ---")
            lines.append(f"task: {r['task']}")
            lines.append(r['result'][:2000])
            if len(r['result']) > 2000:
                lines.append("... (truncated)")
            lines.append("")

        if aggregate['context']:
            lines.append("--- shared context ---")
            for key, entry in aggregate['context'].items():
                val = entry['value']
                lines.append(f"{key}: {str(val)[:200]}")
            lines.append("")

        summary_text = '\n'.join(lines)

        # Append as assistant message
        session.messages.append({
            'role': 'assistant',
            'content': summary_text,
            'swarm_summary': True,
            'swarm_id': swarm_id,
        })
        session.save(touch_updated_at=True)
        return True
    except Exception as e:
        logger.error(f"failed to inject swarm results: {e}")
        return False

def save_swarm_template(name, config):
    """Save a swarm configuration as a reusable template."""
    import json, os
    template_dir = os.path.expanduser('~/.hermes/swarm_templates')
    os.makedirs(template_dir, exist_ok=True)
    template = {
        'name': name,
        'config': config,
        'created_at': time.time(),
        'last_used': time.time(),
    }
    fname = os.path.join(template_dir, f"{name.lower().replace(' ', '_')}.json")
    with open(fname, 'w') as f:
        json.dump(template, f, indent=2)
    return template

def load_swarm_template(name):
    """Load a saved swarm template."""
    import json, os
    template_dir = os.path.expanduser('~/.hermes/swarm_templates')
    fname = os.path.join(template_dir, f"{name.lower().replace(' ', '_')}.json")
    if not os.path.exists(fname):
        return None
    with open(fname, 'r') as f:
        return json.load(f)

def list_swarm_templates():
    """List all saved swarm templates."""
    import json, os
    template_dir = os.path.expanduser('~/.hermes/swarm_templates')
    if not os.path.exists(template_dir):
        return []
    templates = []
    for fname in os.listdir(template_dir):
        if fname.endswith('.json'):
            try:
                with open(os.path.join(template_dir, fname), 'r') as f:
                    templates.append(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to inject swarm results into session: {e}")
    return sorted(templates, key=lambda t: t['last_used'], reverse=True)

def delete_swarm_template(name):
    """Delete a swarm template."""
    import os
    template_dir = os.path.expanduser('~/.hermes/swarm_templates')
    fname = os.path.join(template_dir, f"{name.lower().replace(' ', '_')}.json")
    if os.path.exists(fname):
        os.remove(fname)
        return True
    return False
def aggregate_results(swarm_id):
    """Aggregate worker results with pattern detection."""
    with SWARMS_LOCK:
        swarm = SWARMS.get(swarm_id)
        if not swarm:
            return None
    
    workers = swarm['workers']
    all_results = []
    code_patterns = {}
    file_mentions = set()
    consensus_points = []
    
    for i, w in enumerate(workers):
        result = (w.get('result') or '').strip()
        if not result:
            continue
        
        # Extract code blocks
        code_blocks = re.findall(r'```(\w*)\n(.*?)```', result, re.DOTALL)
        for lang, code in code_blocks:
            code_patterns.setdefault(lang or 'text', []).append(code.strip())
        
        # Extract file paths
        files = re.findall(r'(?:^|\s)([/~][\w./-]+)', result)
        for f in files:
            file_mentions.add(f)
        
        all_results.append({
            'worker_id': w['worker_id'],
            'worker_name': WORKER_NAMES[i] if i < len(WORKER_NAMES) else str(i+1),
            'task': w['task'],
            'status': w['status'],
            'result': result[:2000],  # capped for API
            'result_full': result,
            'code_blocks': len(code_blocks),
            'duration': round(
                (w.get('completed_at') or time.time()) - (w.get('started_at') or time.time()), 1
            ) if w.get('started_at') else None,
        })
    
    # Simple pattern detection
    if len(all_results) > 1:
        # Check for consensus: same file mentioned by 2+ workers
        for fpath in file_mentions:
            count = sum(1 for r in all_results if fpath in r.get('result_full', ''))
            if count >= 2:
                consensus_points.append({
                    'type': 'shared_file',
                    'file': fpath,
                    'mentioned_by': count,
                })
    
    return {
        'swarm_id': swarm_id,
        'task': swarm['task'],
        'total_workers': len(workers),
        'completed': sum(1 for w in workers if w['status'] == 'done'),
        'failed': sum(1 for w in workers if w['status'] == 'error'),
        'cancelled': sum(1 for w in workers if w['status'] == 'cancelled'),
        'results': all_results,
        'code_patterns': {k: len(v) for k, v in code_patterns.items()},
        'shared_files': [f for f in file_mentions if sum(1 for r in all_results if f in r.get('result_full', '')) >= 2],
        'consensus': consensus_points,
    }

def attach_swarm_to_session(swarm_id):
    """Inject a swarm summary message into the parent session's message history."""
    with SWARMS_LOCK:
        swarm = SWARMS.get(swarm_id)
        if not swarm:
            return None
    
    session_id = swarm['session_id']
    if not session_id:
        return None
    
    try:
        from api.models import get_session
        s = get_session(session_id)
        if not s:
            return None
        
        # Build summary message
        lines = [f"🐝 swarm completed: {swarm['task']}\n"]
        lines.append(f"mode: {swarm['mode']} | model: {swarm['model']}\n")
        
        for i, w in enumerate(swarm['workers']):
            name = WORKER_NAMES[i] if i < len(WORKER_NAMES) else w.get('worker_name', f'worker-{i+1}')
            status_icon = '✓' if w['status'] == 'done' else '✗' if w['status'] == 'error' else '❌'
            lines.append(f"\n{status_icon} **{name}**: {w['task']}")
            result = (w.get('result') or '').strip()
            if result:
                snippet = result[:500]
                if len(result) > 500:
                    snippet += '...'
                lines.append(f"```\n{snippet}\n```")
        
        lines.append(f"\n---\nswarm id: `{swarm_id}` | duration: {round((swarm.get('completed_at') or time.time()) - swarm['created_at'], 1)}s")
        
        summary = '\n'.join(lines)
        
        # Append as assistant message
        if not hasattr(s, 'messages') or s.messages is None:
            s.messages = []
        s.messages.append({'role': 'assistant', 'content': summary})
        s.save()
        
        return session_id
    except Exception as e:
        logger.error(f"attach_swarm_to_session failed: {e}")
        return None

def _sanitize_swarm_for_api(swarm):
    workers = []
    for i, w in enumerate(swarm['workers']):
        workers.append({
            'worker_id': w['worker_id'],
            'worker_name': w.get('name', WORKER_NAMES[i] if i < len(WORKER_NAMES) else f'worker-{i+1}'),
            'stream_id': w['stream_id'],
            'session_id': w.get('session_id'),
            'task': w['task'],
            'status': w['status'],
            'result': (w.get('result') or '')[:1000],
            'color': _get_swarm_color(i),
            'duration': round(
                (w.get('completed_at') or time.time()) - (w.get('started_at') or time.time()), 1
            ) if w.get('started_at') else None,
        })

    coord_msgs = _get_coord_messages(swarm['id'])
    last_msg = coord_msgs[-1] if coord_msgs else None

    return {
        'id': swarm['id'],
        'session_id': swarm['session_id'],
        'coord_session_id': swarm.get('coord_session_id'),
        'task': swarm['task'],
        'mode': swarm['mode'],
        'model': swarm['model'],
        'workers': workers,
        'status': swarm['status'],
        'created_at': swarm['created_at'],
        'completed_at': swarm.get('completed_at'),
        'duration': round(
            (swarm.get('completed_at') or time.time()) - swarm['created_at'], 1
        ),
        'last_coord_message': {
            'content': last_msg['content'][:120] if last_msg else '',
            'worker_name': last_msg['worker_name'] if last_msg else '',
            'timestamp': last_msg['timestamp'] if last_msg else None,
        } if last_msg else None,
    }