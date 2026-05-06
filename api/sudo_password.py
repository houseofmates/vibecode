"""Sudo password prompt state for the WebUI.

This mirrors the approval/clarify flow structure, but for sudo password prompts.
The terminal tool sends an SSE event when a sudo password is needed, and the
UI shows a secure password popup. The password is cached locally in the browser
for the session duration.
"""

from __future__ import annotations

import threading
from typing import Optional


_lock = threading.Lock()
_pending: dict[str, dict] = {}
_gateway_queues: dict[str, list] = {}
_gateway_notify_cbs: dict[str, object] = {}


class _SudoPasswordEntry:
    """One pending sudo password request inside a session."""

    __slots__ = ("event", "data", "result")

    def __init__(self, data: dict):
        self.event = threading.Event()
        self.data = data
        self.result: Optional[str] = None


def register_gateway_notify(session_key: str, cb) -> None:
    """Register a per-session callback for sending sudo password requests to the UI."""
    with _lock:
        _gateway_notify_cbs[session_key] = cb


def _clear_queue_locked(session_key: str) -> list[_SudoPasswordEntry]:
    entries = _gateway_queues.pop(session_key, [])
    _pending.pop(session_key, None)
    return entries


def unregister_gateway_notify(session_key: str) -> None:
    """Unregister the per-session callback and unblock any waiting password prompt."""
    with _lock:
        _gateway_notify_cbs.pop(session_key, None)
        entries = _clear_queue_locked(session_key)
    for entry in entries:
        entry.event.set()


def clear_pending(session_key: str) -> int:
    """Clear any pending sudo password prompts for the session without removing the callback."""
    with _lock:
        entries = _clear_queue_locked(session_key)
    for entry in entries:
        entry.event.set()
    return len(entries)


def submit_pending(session_key: str, data: dict) -> _SudoPasswordEntry:
    """Queue a pending sudo password request and notify the UI callback if registered."""
    with _lock:
        queue = _gateway_queues.setdefault(session_key, [])
        # De-duplicate while unresolved: if there's already a pending request,
        # reuse it instead of stacking duplicates.
        if queue:
            entry = queue[-1]
            cb = _gateway_notify_cbs.get(session_key)
            _pending[session_key] = queue[0].data
            if cb:
                try:
                    cb(dict(entry.data))
                except Exception:
                    pass
            return entry

        entry = _SudoPasswordEntry(data)
        queue.append(entry)
        _pending[session_key] = queue[0].data
        cb = _gateway_notify_cbs.get(session_key)
    if cb:
        try:
            cb(data)
        except Exception:
            pass
    return entry


def get_pending(session_key: str) -> dict | None:
    """Return the oldest pending sudo password request for this session, if any."""
    with _lock:
        queue = _gateway_queues.get(session_key) or []
        if queue:
            return dict(queue[0].data)
        pending = _pending.get(session_key)
        return dict(pending) if pending else None


def has_pending(session_key: str) -> bool:
    with _lock:
        return bool(_gateway_queues.get(session_key))


def resolve_sudo_password(session_key: str, password: str) -> int:
    """Resolve the pending sudo password request for a session."""
    with _lock:
        queue = _gateway_queues.get(session_key)
        if not queue:
            _pending.pop(session_key, None)
            return 0
        entry = queue.pop(0)
        if queue:
            _pending[session_key] = queue[0].data
        else:
            _clear_queue_locked(session_key)
    entry.result = password
    entry.event.set()
    return 1
