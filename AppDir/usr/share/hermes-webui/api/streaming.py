"""
Hermes Web UI -- SSE streaming engine and agent thread runner.
Includes Sprint 10 cancel support via CANCEL_FLAGS.
"""
import json
import logging
import os
import queue
import re
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from api.config import (
    STREAMS, STREAMS_LOCK, CANCEL_FLAGS, AGENT_INSTANCES,
    LOCK, SESSIONS, SESSION_DIR,
    _get_session_agent_lock, _set_thread_env, _clear_thread_env,
    resolve_model_provider,
)
from api.helpers import redact_session_data

# Global lock for os.environ writes. Per-session locks (_agent_lock) prevent
# concurrent runs of the SAME session, but two DIFFERENT sessions can still
# interleave their os.environ writes. This global lock serializes the env
# save/restore around the entire agent run.
_ENV_LOCK = threading.Lock()

# Round-robin API key rotation for NVIDIA NIM
_nvidia_key_lock = threading.Lock()
_nvidia_key_index = 0

def _get_nvidia_api_key_round_robin() -> tuple[str, int]:
    """
    Get the next NVIDIA API key using round-robin rotation.
    Returns (api_key, index_used).
    """
    global _nvidia_key_index
    
    # Try to get API keys from config
    try:
        from api.config import cfg
        nvidia_config = cfg.get("nvidia", {})
        if isinstance(nvidia_config, dict):
            api_keys = nvidia_config.get("api_keys", [])
            if isinstance(api_keys, list) and len(api_keys) > 0:
                with _nvidia_key_lock:
                    # Get current index and increment for next request
                    idx = _nvidia_key_index % len(api_keys)
                    _nvidia_key_index = (_nvidia_key_index + 1) % len(api_keys)
                    return api_keys[idx], idx
            # Fallback to single api_key if no api_keys list
            single_key = nvidia_config.get("api_key", "")
            if single_key:
                return single_key, 0
    except Exception:
        pass
    
    # Fallback to environment variable
    env_key = os.getenv("NVIDIA_API_KEY", os.getenv("NGC_API_KEY", ""))
    return env_key, 0

# Lazy import to avoid circular deps -- hermes-agent is on sys.path via api/config.py
try:
    from run_agent import AIAgent
except ImportError:
    AIAgent = None

def _get_ai_agent():
    """Return AIAgent class, retrying the import if the initial attempt failed.

    auto_install_agent_deps() in server.py may install missing packages after
    this module is first imported (common in Docker with a volume-mounted agent).
    Re-attempting the import here picks up the newly installed packages without
    requiring a server restart.
    """
    global AIAgent
    if AIAgent is None:
        try:
            from run_agent import AIAgent as _cls  # noqa: PLC0415
            AIAgent = _cls
        except ImportError:
            pass
    return AIAgent
from api.models import get_session, title_from
from api.workspace import set_last_workspace

# Fields that are safe to send to LLM provider APIs.
# Everything else (attachments, timestamp, _ts, etc.) is display-only
# metadata added by the webui and must be stripped before the API call.
_API_SAFE_MSG_KEYS = {'role', 'content', 'tool_calls', 'tool_call_id', 'name', 'refusal', 'reasoning', 'reasoning_content', 'finish_reason', 'id', 'call_id', 'response_item_id', 'extra_content', 'codex_reasoning_items', 'codex_message_items', 'reasoning_details'}


def _strip_thinking_markup(text: str) -> str:
    """Remove common reasoning/thinking wrappers from model text."""
    if not text:
        return ''
    s = str(text)
    s = re.sub(r'<think>.*?</think>', ' ', s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r'<thinking>.*?</thinking>', ' ', s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r'<reasoning>.*?</reasoning>', ' ', s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r'<\|channel\|>thought.*?<channel\|>', ' ', s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r'^\s*(the|ther)\s+user\s+is\s+asking.*$', ' ', s, flags=re.IGNORECASE | re.MULTILINE)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _sanitize_generated_title(text: str) -> str:
    """Sanitize LLM-generated title text before persisting to session."""
    s = _strip_thinking_markup(text or '')
    s = re.sub(r'^\s*title\s*:\s*', '', s, flags=re.IGNORECASE)
    s = s.strip(" \t\r\n\"'`")
    s = re.sub(r'\s+', ' ', s).strip()
    # Guard against chain-of-thought leakage and meta-reasoning patterns.
    if _looks_invalid_generated_title(s):
        return ''
    return s[:80]


def _looks_invalid_generated_title(text: str) -> bool:
    s = str(text or '')
    if not s.strip():
        return True
    return bool(
        re.search(r'<think>|<\|channel\|>thought', s, flags=re.IGNORECASE)
        or re.search(r'^\s*(the|ther)\s+user\s+', s, flags=re.IGNORECASE)
        or re.search(r'^\s*user\s+\w+\s+', s, flags=re.IGNORECASE)
        or re.search(r'\b(they|user)\s+want(s)?\s+me\s+to\b', s, flags=re.IGNORECASE)
        or re.search(r'^\s*(i|we)\s+(should|need to|will|can)\b', s, flags=re.IGNORECASE)
        or re.search(r'^\s*let me\b', s, flags=re.IGNORECASE)
        or re.search(r'用户(要求|希望|想让|让我)', s)
        or re.search(r'请只?回复', s)
        or re.search(r'^\s*(ok|okay|done|all set|complete|completed|finished)\b[\s.!?]*$', s, flags=re.IGNORECASE)
        or re.search(r'^\s*(好的|好啦|完成了|已完成|测试完成|测试已完成|可以了|没问题)\s*[！!。\.\s]*$', s)
    )


def _message_text(value) -> str:
    """Extract plain text from mixed message content payloads."""
    if isinstance(value, list):
        parts = []
        for p in value:
            if not isinstance(p, dict):
                continue
            ptype = str(p.get('type') or '').lower()
            if ptype in ('', 'text', 'input_text', 'output_text'):
                parts.append(str(p.get('text') or p.get('content') or ''))
        return _strip_thinking_markup('\n'.join(parts).strip())
    return _strip_thinking_markup(str(value or '').strip())


def _first_exchange_snippets(messages):
    """Return (first_user_text, first_assistant_text) snippets for title generation."""
    user_text = ''
    asst_text = ''
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = m.get('role')
        if role == 'user' and not user_text:
            user_text = _message_text(m.get('content'))
        elif role == 'assistant' and not asst_text:
            asst_text = _message_text(m.get('content'))
        if user_text and asst_text:
            break
    return user_text[:500], asst_text[:500]


def _is_provisional_title(current_title: str, messages) -> bool:
    """Heuristic: title equals first-message substring placeholder."""
    derived = title_from(messages, '') or ''
    if not derived:
        return False
    return (str(current_title or '').strip() == derived[:64])


def _title_prompts(user_text: str, assistant_text: str) -> tuple[str, list[str]]:
    qa = f"User question:\n{user_text[:500]}\n\nAssistant answer:\n{assistant_text[:500]}"
    prompts = [
        (
            "Generate a short session title from this conversation start.\n"
            "Use BOTH the user's question and the assistant's visible answer.\n"
            "Return only the title text, 3-8 words, as a topic label.\n"
            "Do not output a full sentence.\n"
            "Do not output acknowledgements or completion phrases like OK, done, all set, 测试完成.\n"
            "Do not describe internal reasoning.\n"
            "Bad: The user is asking..., OK, 好的，测试完成！\n"
            "Good: 自动标题生成测试, Clarify Dialog Layout, GitHub Issue Triage"
        ),
        (
            "Rewrite this conversation start as a concise noun-phrase title.\n"
            "Use the actual topic, not the task outcome.\n"
            "Return title text only.\n"
            "Never output acknowledgements, completion status, or meta commentary."
        ),
    ]
    return qa, prompts


def _is_minimax_route(provider: str = '', model: str = '', base_url: str = '') -> bool:
    text = ' '.join([
        str(provider or '').lower(),
        str(model or '').lower(),
        str(base_url or '').lower(),
    ])
    return 'minimax' in text or 'minimaxi.com' in text


def _title_completion_budget(provider: str = '', model: str = '', base_url: str = '') -> int:
    if _is_minimax_route(provider, model, base_url):
        return 384
    return 160


def generate_title_raw_via_aux(
    user_text: str,
    assistant_text: str,
    provider: str = '',
    model: str = '',
    base_url: str = '',
) -> tuple[Optional[str], str]:
    """Return (raw_text, status) via auxiliary LLM route."""
    if not user_text or not assistant_text:
        return None, 'missing_exchange'
    qa, prompts = _title_prompts(user_text, assistant_text)
    max_tokens = _title_completion_budget(provider, model, base_url)
    reasoning_extra = {"reasoning": {"enabled": False}}
    if _is_minimax_route(provider, model, base_url):
        reasoning_extra["reasoning_split"] = True
    try:
        from agent.auxiliary_client import call_llm
        for idx, prompt in enumerate(prompts):
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": qa},
            ]
            try:
                resp = call_llm(
                    task='title_generation',
                    provider=provider or None,
                    model=model or None,
                    base_url=base_url or None,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.2,
                    timeout=15.0,
                    extra_body=reasoning_extra,
                )
                raw = ''
                try:
                    raw = resp.choices[0].message.content or ''
                except Exception:
                    raw = ''
                raw = str(raw or '').strip()
                if raw:
                    return raw, ('llm_aux' if idx == 0 else 'llm_aux_retry')
            except Exception as e:
                logger.debug("Aux title generation attempt %s failed: %s", idx + 1, e)
        return None, 'llm_error_aux'
    except Exception as e:
        logger.debug("Aux title generation failed: %s", e)
        return None, 'llm_error_aux'


def generate_title_raw_via_agent(agent, user_text: str, assistant_text: str) -> tuple[Optional[str], str]:
    """Return (raw_text, status) via active-agent route."""
    if not user_text or not assistant_text:
        return None, 'missing_exchange'
    if agent is None:
        return None, 'missing_agent'

    qa, prompts = _title_prompts(user_text, assistant_text)
    max_tokens = _title_completion_budget(
        getattr(agent, 'provider', ''),
        getattr(agent, 'model', ''),
        getattr(agent, 'base_url', ''),
    )
    disabled_reasoning = {"enabled": False}
    prev_reasoning = getattr(agent, 'reasoning_config', None)
    try:
        agent.reasoning_config = disabled_reasoning
        for idx, prompt in enumerate(prompts):
            api_messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": qa},
            ]
            try:
                raw = ""
                if getattr(agent, 'api_mode', '') == 'codex_responses':
                    codex_kwargs = agent._build_api_kwargs(api_messages)
                    codex_kwargs.pop('tools', None)
                    if 'max_output_tokens' in codex_kwargs:
                        codex_kwargs['max_output_tokens'] = max_tokens
                    resp = agent._run_codex_stream(codex_kwargs)
                    assistant_message, _ = agent._normalize_codex_response(resp)
                    raw = (assistant_message.content or '') if assistant_message else ''
                elif getattr(agent, 'api_mode', '') == 'anthropic_messages':
                    from agent.anthropic_adapter import build_anthropic_kwargs, normalize_anthropic_response
                    ant_kwargs = build_anthropic_kwargs(
                        model=agent.model,
                        messages=api_messages,
                        tools=None,
                        max_tokens=max_tokens,
                        reasoning_config=disabled_reasoning,
                        is_oauth=getattr(agent, '_is_anthropic_oauth', False),
                        preserve_dots=agent._anthropic_preserve_dots(),
                        base_url=getattr(agent, '_anthropic_base_url', None),
                    )
                    resp = agent._anthropic_messages_create(ant_kwargs)
                    assistant_message, _ = normalize_anthropic_response(
                        resp, strip_tool_prefix=getattr(agent, '_is_anthropic_oauth', False)
                    )
                    raw = (assistant_message.content or '') if assistant_message else ''
                else:
                    api_kwargs = agent._build_api_kwargs(api_messages)
                    api_kwargs.pop('tools', None)
                    api_kwargs['temperature'] = 0.1
                    api_kwargs['timeout'] = 15.0
                    if _is_minimax_route(getattr(agent, 'provider', ''), getattr(agent, 'model', ''), getattr(agent, 'base_url', '')):
                        extra_body = dict(api_kwargs.get('extra_body') or {})
                        extra_body['reasoning_split'] = True
                        api_kwargs['extra_body'] = extra_body
                    if 'max_completion_tokens' in api_kwargs:
                        api_kwargs['max_completion_tokens'] = max_tokens
                    else:
                        api_kwargs['max_tokens'] = max_tokens
                    resp = agent._ensure_primary_openai_client(reason='title_generation').chat.completions.create(
                        **api_kwargs,
                    )
                    try:
                        raw = resp.choices[0].message.content or ""
                    except Exception:
                        raw = ""
                raw = str(raw or '').strip()
                if raw:
                    return raw, ('llm' if idx == 0 else 'llm_retry')
            except Exception as e:
                logger.debug(
                    "Agent title generation attempt %s failed: provider=%s model=%s error=%s",
                    idx + 1,
                    getattr(agent, 'provider', None),
                    getattr(agent, 'model', None),
                    e,
                )
        return None, 'llm_error'
    except Exception as e:
        logger.debug("Agent title generation failed: %s", e)
        return None, 'llm_error'
    finally:
        agent.reasoning_config = prev_reasoning


def _generate_llm_session_title_for_agent(agent, user_text: str, assistant_text: str) -> tuple[Optional[str], str, str]:
    """Generate a title via active-agent route, then sanitize/validate result."""
    raw, status = generate_title_raw_via_agent(agent, user_text, assistant_text)
    if not raw:
        return None, status, ''
    title = _sanitize_generated_title(raw)
    if title:
        return title, status, ''
    return None, 'llm_invalid', str(raw)[:120]


def _generate_llm_session_title_via_aux(user_text: str, assistant_text: str, agent=None) -> tuple[Optional[str], str, str]:
    """Generate a title via dedicated auxiliary LLM route, then sanitize/validate result."""
    raw, status = generate_title_raw_via_aux(
        user_text,
        assistant_text,
        provider=getattr(agent, 'provider', '') if agent else '',
        model=getattr(agent, 'model', '') if agent else '',
        base_url=getattr(agent, 'base_url', '') if agent else '',
    )
    if not raw:
        return None, status, ''
    title = _sanitize_generated_title(raw)
    if title:
        return title, status, ''
    return None, 'llm_invalid_aux', str(raw)[:120]


def _put_title_status(put_event, session_id: str, status: str, reason: str = '', title: str = '', raw_preview: str = '') -> None:
    payload = {'session_id': session_id, 'status': status}
    if reason:
        payload['reason'] = reason
    if title:
        payload['title'] = title
    if raw_preview:
        payload['raw_preview'] = raw_preview
    put_event('title_status', payload)
    logger.info(
        "title_status session=%s status=%s reason=%s title=%r raw_preview=%r",
        session_id,
        status,
        reason or '-',
        title or '',
        (raw_preview or '')[:120],
    )


def _fallback_title_from_exchange(user_text: str, assistant_text: str) -> Optional[str]:
    """Generate a readable local fallback title when LLM title generation fails."""
    user_text = (user_text or '').strip()
    assistant_text = _strip_thinking_markup(assistant_text or '').strip()
    if not user_text:
        return None
    user_text = re.sub(r'^\[Workspace:[^\]]+\]\s*', '', user_text)
    user_text = re.sub(r'\s+', ' ', user_text).strip()
    assistant_text = re.sub(r'\s+', ' ', assistant_text).strip()
    combined = f"{user_text} {assistant_text}".strip().lower()
    combined_raw = f"{user_text} {assistant_text}".strip()

    def _extract_named_topic(text: str) -> str:
        m = re.search(r'《([^》]{2,24})》', text)
        if m:
            return (m.group(1) or '').strip()
        m = re.search(r'"([^"\n]{2,24})"', text)
        if m:
            return (m.group(1) or '').strip()
        m = re.search(r'“([^”\n]{2,24})”', text)
        if m:
            return (m.group(1) or '').strip()
        return ''

    topic_name = _extract_named_topic(combined_raw)
    if topic_name:
        if any(k in combined for k in ('时间', 'time', '安排', '效率', '怎么办', '健身', '唱歌', '写毛笔', '不够用了')):
            return f'{topic_name}与时间管理'
        if any(k in combined for k in ('hermes', 'codex', 'ai')):
            return f'{topic_name}与AI效率'
        return f'{topic_name}讨论'

    if any(k in combined for k in ('title', '标题')) and any(k in combined for k in ('summary', 'summar', '摘要', '短标题')):
        if any(k in combined for k in ('test', '测试', 'ok', '回复ok')):
            return '会话标题自动摘要测试'
        return '会话标题自动摘要'
    if any(k in combined for k in ('clarify', '澄清')) and any(k in combined for k in ('dialog', 'card', '对话', '卡片')):
        return 'Clarify 对话卡片'
    if any(k in combined for k in ('issue', 'github', 'pr')) and any(k in combined for k in ('triage', 'bug', 'review', '问题')):
        return 'GitHub Issue Triage'

    head = re.split(r'[。！？.!?\n]', user_text)[0].strip()
    if not head:
        return None

    stop_cjk = {
        '我们', '看看', '一下', '这个', '标题', '是否', '可以', '用户', '理解', '这里', '测试', '一下',
        '你只', '需要', '回复', '就可', '可以', '不需', '需要做', '什么', '自动', '成用户', '短标题',
    }
    stop_en = {
        'the', 'this', 'that', 'with', 'from', 'into', 'just', 'reply', 'please',
        'need', 'needs', 'want', 'wants', 'user', 'assistant', 'could', 'would',
        'should', 'about', 'there', 'here', 'test', 'testing', 'title', 'summary',
    }
    tokens = re.findall(r'[\u4e00-\u9fff]{2,6}|[A-Za-z0-9][A-Za-z0-9_./+-]*', head)
    if not tokens:
        return head[:64]

    picked = []
    for tok in tokens:
        lower_tok = tok.lower()
        if re.search(r'[\u4e00-\u9fff]', tok):
            if tok in stop_cjk:
                continue
        else:
            if lower_tok in stop_en or len(lower_tok) < 3:
                continue
        if tok not in picked:
            picked.append(tok)
        if len(picked) >= 4:
            break

    if picked:
        if any(re.search(r'[\u4e00-\u9fff]', t) for t in picked):
            return ''.join(picked)[:20]
        return ' '.join(picked)[:60]
    return head[:24]


def _run_background_title_update(session_id: str, user_text: str, assistant_text: str, placeholder_title: str, put_event, agent=None):
    """Generate and publish a better title after `done`, then end the stream."""
    try:
        try:
            s = get_session(session_id)
        except KeyError:
            _put_title_status(put_event, session_id, 'skipped', 'missing_session')
            return
        # Allow self-heal when a previously generated title leaked thinking text.
        _invalid_existing = _looks_invalid_generated_title(s.title)
        if getattr(s, 'llm_title_generated', False) and not _invalid_existing:
            _put_title_status(put_event, session_id, 'skipped', 'already_generated', str(s.title or ''))
            return
        current = str(s.title or '').strip()
        still_auto = (
            current == placeholder_title
            or current in ('Untitled', 'New Chat', '')
            or _is_provisional_title(current, s.messages)
            or _invalid_existing
        )
        if not still_auto:
            _put_title_status(put_event, session_id, 'skipped', 'manual_title', current)
            return
        # Prefer the active session model when available so title generation
        # matches the user's chosen runtime and can use provider-specific fixes.
        if agent:
            next_title, llm_status, raw_preview = _generate_llm_session_title_for_agent(agent, user_text, assistant_text)
            if not next_title and llm_status in ('llm_error', 'llm_invalid'):
                next_title, llm_status, raw_preview = _generate_llm_session_title_via_aux(user_text, assistant_text, agent=agent)
        else:
            next_title, llm_status, raw_preview = _generate_llm_session_title_via_aux(user_text, assistant_text, agent=agent)
        source = llm_status
        if not next_title:
            next_title = _fallback_title_from_exchange(user_text, assistant_text)
            if next_title:
                logger.debug("Using local fallback for session title generation")
                source = 'fallback'
        if next_title and next_title != current:
            s.title = next_title
            s.llm_title_generated = True
            # Keep chronological ordering stable in the sidebar.
            s.save(touch_updated_at=False)
            if source == 'fallback':
                _put_title_status(put_event, session_id, source, 'local_summary', s.title, raw_preview)
            else:
                _put_title_status(put_event, session_id, source, llm_status, s.title, raw_preview)
            put_event('title', {'session_id': s.session_id, 'title': s.title})
        else:
            _put_title_status(put_event, session_id, 'skipped', source or 'unchanged', current, raw_preview)
    finally:
        put_event('stream_end', {'session_id': session_id})


def _sanitize_messages_for_api(messages):
    """Return a deep copy of messages with only API-safe fields.

    The webui stores extra metadata on messages (attachments, timestamp, _ts)
    for display purposes. Some providers (e.g. Z.AI/GLM) reject unknown fields
    instead of ignoring them, causing HTTP 400 errors on subsequent messages.

    Also strips orphaned tool-role messages whose tool_call_id cannot be linked
    to a preceding assistant message with tool_calls. Strictly-conformant providers
    (Mercury-2/Inception, newer OpenAI models) reject histories containing dangling
    tool results with a 400 error: "Message has tool role, but there was no previous
    assistant message with a tool call."
    """
    # First pass: collect all tool_call_ids declared by assistant messages.
    # Handles both OpenAI ('id') and Anthropic ('call_id') field names.
    valid_tool_call_ids: set = set()
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if msg.get('role') == 'assistant':
            for tc in msg.get('tool_calls') or []:
                if isinstance(tc, dict):
                    tid = tc.get('id') or tc.get('call_id') or ''
                    if tid:
                        valid_tool_call_ids.add(tid)

    # Second pass: build the sanitized list, dropping orphaned tool messages.
    clean = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get('role')
        if role == 'tool':
            tid = msg.get('tool_call_id') or ''
            if not tid or tid not in valid_tool_call_ids:
                # Orphaned tool result — skip to avoid 400 from strict providers.
                continue
        sanitized = {k: v for k, v in msg.items() if k in _API_SAFE_MSG_KEYS}
        if sanitized.get('role'):
            clean.append(sanitized)
    return clean


def _sse(handler, event, data):
    """Write one SSE event to the response stream."""
    payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    handler.wfile.write(payload.encode('utf-8'))
    handler.wfile.flush()




# --- Swarm helper: called after agent stream completes to notify swarm system ---
def _swarm_notify_done(stream_id, messages, usage):
    """If this stream is a swarm worker, notify the swarm that it completed."""
    try:
        from api.swarm import on_worker_stream_done
        _assistant_text = ''
        for _m in reversed(messages):
            if isinstance(_m, dict) and _m.get('role') == 'assistant':
                _assistant_text = _m.get('content', '')
                break
        on_worker_stream_done(stream_id, _assistant_text, usage)
    except Exception:
        pass  # Not a swarm worker or swarm module unavailable

def _run_agent_streaming(session_id, msg_text, model, workspace, stream_id, attachments=None):
    """Run agent in background thread, writing SSE events to STREAMS[stream_id]."""
    q = STREAMS.get(stream_id)
    if q is None:
        return
    s = None
    _rt = {}
    old_cwd = None
    old_exec_ask = None
    old_session_key = None
    old_hermes_home = None

    # ── MCP Server Discovery (lazy import, idempotent) ──
    # discover_mcp_tools() is called here (rather than at server startup) so that
    # the hermes-agent package is fully initialized before we try to connect.
    # It is safe to call multiple times — already-connected servers are skipped.
    try:
        from tools.mcp_tool import discover_mcp_tools
        discover_mcp_tools()
    except Exception:
        pass  # MCP not available or not configured — non-fatal

    # Sprint 10: create a cancel event for this stream
    cancel_event = threading.Event()
    with STREAMS_LOCK:
        CANCEL_FLAGS[stream_id] = cancel_event

    # Progress tracker for slow/hung streams
    _progress_event = threading.Event()

    def _slow_response_watch():
        if not _progress_event.wait(timeout=15):
            put('warning', {
                'message': 'Still waiting for Hermes to respond. This may be due to a slow model or provider connectivity issue.',
                'type': 'slow_response',
            })

    def put(event, data):
        # If cancelled, drop all further events except the cancel event itself
        if cancel_event.is_set() and event not in ('cancel', 'error'):
            return
        _progress_event.set()
        try:
            q.put_nowait((event, data))
            print(f"[webui] put event: {event}", flush=True)
        except Exception as e:
            logger.debug(f"Failed to put event to queue: {e}")
        # Fan out to multiplex clients so a single SSE connection can carry
        # events for many concurrent streams (bypasses browser 6-conn limit).
        try:
            from api.config import MULTIPLEX_QUEUES, MULTIPLEX_LOCK
            # -- Swarm: tag multiplex events with swarm_id --
            _swarm_id = None
            try:
                from api.swarm import get_swarm_for_stream
                _swarm_id, _ = get_swarm_for_stream(stream_id)
            except Exception:
                pass
            multiplex_data = {**data, 'stream_id': stream_id, 'session_id': session_id}
            if _swarm_id:
                multiplex_data['swarm_id'] = _swarm_id
            with MULTIPLEX_LOCK:
                clients = list(MULTIPLEX_QUEUES.items())
            for _cid, mq in clients:
                try:
                    mq.put_nowait((event, multiplex_data))
                except Exception:
                    pass
        except Exception:
            pass

    threading.Thread(target=_slow_response_watch, daemon=True).start()

    try:
        s = get_session(session_id)
        s.workspace = str(Path(workspace).expanduser().resolve())
        s.model = model

        _agent_lock = _get_session_agent_lock(session_id)
        # TD1: set thread-local env context so concurrent sessions don't clobber globals
        # Check for pre-flight cancel (user cancelled before agent even started)
        if cancel_event.is_set():
            put('cancel', {'message': 'Cancelled before start'})
            return

        # Resolve profile home for this agent run (snapshot at start)
        try:
            from api.profiles import get_active_hermes_home
            _profile_home = str(get_active_hermes_home())
        except ImportError:
            _profile_home = os.environ.get('HERMES_HOME', '')

        _set_thread_env(
            TERMINAL_CWD=str(s.workspace),
            HERMES_EXEC_ASK='1',
            HERMES_SESSION_KEY=session_id,
            HERMES_HOME=_profile_home,
        )
        # Still set process-level env as fallback for tools that bypass thread-local
        # Acquire lock only for the env mutation, then release before the agent runs.
        # The finally block re-acquires to restore — keeping critical sections short
        # and preventing a deadlock where the restore would re-enter the same lock.
        with _ENV_LOCK:
            old_cwd = os.environ.get('TERMINAL_CWD')
            old_exec_ask = os.environ.get('HERMES_EXEC_ASK')
            old_session_key = os.environ.get('HERMES_SESSION_KEY')
            old_hermes_home = os.environ.get('HERMES_HOME')
            os.environ['TERMINAL_CWD'] = str(s.workspace)
            os.environ['HERMES_EXEC_ASK'] = '1'
            os.environ['HERMES_SESSION_KEY'] = session_id
            if _profile_home:
                os.environ['HERMES_HOME'] = _profile_home
        # Lock released — agent runs without holding it
        # Register a gateway-style notify callback so the approval system can
        # push the `approval` SSE event the moment a dangerous command is
        # detected, without waiting for the next on_tool() poll cycle.
        # Without this, the agent thread blocks inside the terminal tool
        # waiting for approval that the UI never knew to ask for, leaving
        # the chat stuck in "Thinking…" forever.
        _approval_registered = False
        _unreg_notify = None
        try:
            from tools.approval import (
                register_gateway_notify as _reg_notify,
                unregister_gateway_notify as _unreg_notify,
            )
            def _approval_notify_cb(approval_data):
                put('approval', approval_data)
            _reg_notify(session_id, _approval_notify_cb)
            _approval_registered = True
        except ImportError:
            logger.debug("Approval module not available, falling back to polling")

        _clarify_registered = False
        _unreg_clarify_notify = None
        try:
            from api.clarify import (
                register_gateway_notify as _reg_clarify_notify,
                unregister_gateway_notify as _unreg_clarify_notify,
            )

            def _clarify_notify_cb(clarify_data):
                put('clarify', clarify_data)

            _reg_clarify_notify(session_id, _clarify_notify_cb)
            _clarify_registered = True
        except ImportError:
            logger.debug("Clarify module not available, falling back to polling")

        _sudo_password_registered = False
        _unreg_sudo_password_notify = None
        try:
            from api.sudo_password import (
                register_gateway_notify as _reg_sudo_password_notify,
                unregister_gateway_notify as _unreg_sudo_password_notify,
            )

            def _sudo_password_notify_cb(sudo_data):
                put('sudo_password', sudo_data)

            _reg_sudo_password_notify(session_id, _sudo_password_notify_cb)
            _sudo_password_registered = True
        except ImportError:
            logger.debug("Sudo password module not available, falling back to polling")

        def _sudo_password_callback_impl(sid, cancel_evt, put_event):
            """Bridge Hermes sudo password prompts to the WebUI."""
            timeout = 120
            data = {
                'session_id': sid,
                'kind': 'sudo_password',
                'requested_at': time.time(),
            }
            try:
                from api.sudo_password import submit_pending as _submit_sudo_password_pending, clear_pending as _clear_sudo_password_pending
            except ImportError:
                return ""

            entry = _submit_sudo_password_pending(sid, data)
            deadline = time.monotonic() + timeout
            while True:
                if cancel_evt.is_set():
                    _clear_sudo_password_pending(sid)
                    return ""
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    _clear_sudo_password_pending(sid)
                    return ""
                if entry.event.wait(timeout=min(1.0, remaining)):
                    password = str(entry.result or "").strip()
                    return password
                # Continue waiting...

        # Register the sudo password callback with the terminal tool
        try:
            from tools.terminal_tool import set_sudo_password_callback
            set_sudo_password_callback(lambda: _sudo_password_callback_impl(session_id, cancel_event, put))
        except ImportError:
            logger.debug("Terminal tool not available, sudo password callback not registered")

        def _clarify_callback_impl(question, choices, sid, cancel_evt, put_event):
            """Bridge Hermes clarify prompts to the WebUI."""
            timeout = 120
            choices_list = [str(choice) for choice in (choices or [])]
            data = {
                'question': str(question or ''),
                'choices_offered': choices_list,
                'session_id': sid,
                'kind': 'clarify',
                'requested_at': time.time(),
            }
            try:
                from api.clarify import submit_pending as _submit_clarify_pending, clear_pending as _clear_clarify_pending
            except ImportError:
                return (
                    "The user did not provide a response within the time limit. "
                    "Use your best judgement to make the choice and proceed."
                )

            entry = _submit_clarify_pending(sid, data)
            deadline = time.monotonic() + timeout
            while True:
                if cancel_evt.is_set():
                    _clear_clarify_pending(sid)
                    return (
                        "The user did not provide a response within the time limit. "
                        "Use your best judgement to make the choice and proceed."
                    )
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    _clear_clarify_pending(sid)
                    return (
                        "The user did not provide a response within the time limit. "
                        "Use your best judgement to make the choice and proceed."
                    )
                if entry.event.wait(timeout=min(1.0, remaining)):
                    response = str(entry.result or "").strip()
                    return (
                        response
                        or "The user did not provide a response within the time limit. "
                           "Use your best judgement to make the choice and proceed."
                    )

        try:
            _token_sent = False  # tracks whether any streamed tokens were sent
            _reasoning_text = ''  # accumulates reasoning/thinking trace for persistence
            _accumulated_text = ''  # accumulates assistant response for periodic save
            _save_counter = 0  # counter for periodic session saves

            def on_token(text):
                nonlocal _token_sent, _accumulated_text, _save_counter, _reasoning_text
                if text is None:
                    return  # end-of-stream sentinel
                _token_sent = True
                text_str = str(text)
                # Suppress ghost text when tool call in progress (GLM/NIM dual-render)
                if getattr(on_token, '_tool_in_progress', False):
                    print(f"[webui] Suppressing token due to _tool_in_progress: {text_str[:80]}...", flush=True)
                    return


                # ── Extract inline thinking/reasoning blocks ──
                # Some models output reasoning wrapped in <thinking>/<reasoning> tags,
                # while others use <think>...</think> or Gemma-style channel tokens.
                # Detect these wrappers, emit them as reasoning events, and strip them
                # from live token display. Loop until no more thinking tags remain,
                # handling multiple blocks or interleaved text in a single chunk.
                tag_pairs = [
                    ('<thinking>', '</thinking>'),
                    ('<reasoning>', '</reasoning>'),
                    ('<think>', '</think>'),
                    ('<|channel>thought', '<channel|>'),
                ]

                while True:
                    lower_text = text_str.lower()

                    if getattr(on_token, '_in_thinking_block', False):
                        # We are inside a thinking block carried over from a previous chunk.
                        open_tag, close_tag = on_token._thinking_pair or tag_pairs[0]
                        # Combine any buffered partial close-tag prefix from the previous chunk.
                        _buf = getattr(on_token, '_thinking_buffer', '')
                        combined = _buf + text_str
                        combined_lower = combined.lower()
                        close_idx = combined_lower.find(close_tag)
                        if close_idx != -1:
                            # Close tag found — emit reasoning (including any buffered prefix)
                            # and resume normal processing.
                            reasoning_part = combined[:close_idx]
                            if reasoning_part:
                                _reasoning_text += reasoning_part
                                print(f"[webui] Extracted thinking block end: {reasoning_part[:100]}...", flush=True)
                                put('reasoning', {'text': reasoning_part})
                            on_token._in_thinking_block = False
                            on_token._thinking_pair = None
                            on_token._thinking_buffer = ''
                            text_str = combined[close_idx + len(close_tag):]
                            if not text_str.strip():
                                return
                            continue  # Check for more tags in the remaining text
                        else:
                            # Still inside thinking block. If the combined text ends with a
                            # prefix of the close tag, buffer that prefix and only emit the
                            # preceding text. This handles close tags split across chunks.
                            _buffered = ''
                            _emit = combined
                            for _prefix_len in range(len(close_tag) - 1, 0, -1):
                                if combined_lower.endswith(close_tag[:_prefix_len].lower()):
                                    _buffered = combined[-_prefix_len:]
                                    _emit = combined[:-_prefix_len]
                                    break
                            if _emit:
                                _reasoning_text += _emit
                                print(f"[webui] Inside thinking block: {_emit[:100]}...", flush=True)
                                put('reasoning', {'text': _emit})
                            on_token._thinking_buffer = _buffered
                            return

                    # Not inside a thinking block — look for an open tag.
                    open_pair = None
                    for open_tag, close_tag in tag_pairs:
                        if open_tag in lower_text:
                            open_pair = (open_tag, close_tag)
                            break

                    if not open_pair:
                        break  # No thinking tags — normal token

                    open_tag, close_tag = open_pair
                    open_idx = lower_text.find(open_tag)
                    close_idx = lower_text.find(close_tag, open_idx + len(open_tag))

                    if open_idx != -1 and close_idx != -1:
                        # Complete thinking block in this chunk.
                        reasoning_content = text_str[open_idx + len(open_tag) : close_idx]
                        if reasoning_content:
                            _reasoning_text += reasoning_content
                            print(f"[webui] Extracted thinking block content: {reasoning_content[:100]}...", flush=True)
                            put('reasoning', {'text': reasoning_content})
                        before_think = text_str[:open_idx] if open_idx > 0 else ''
                        after_think = text_str[close_idx + len(close_tag):]
                        text_str = before_think + after_think
                        if not text_str.strip():
                            return
                        continue  # Check for more tags in the remaining text

                    # Open tag found with no close tag — start of a thinking block.
                    before_think = text_str[:open_idx] if open_idx > 0 else ''
                    reasoning_part = text_str[open_idx + len(open_tag):]
                    if reasoning_part:
                        _reasoning_text += reasoning_part
                        print(f"[webui] Extracted thinking block start: {reasoning_part[:100]}...", flush=True)
                        put('reasoning', {'text': reasoning_part})
                    # Set state BEFORE potentially emitting before_think so the NEXT
                    # chunk knows we are inside a thinking block.
                    on_token._in_thinking_block = True
                    on_token._thinking_pair = open_pair
                    if before_think:
                        # Emit the text before the open tag as a normal token now,
                        # then let subsequent chunks handle the thinking block.
                        text_str = before_think
                        break
                    else:
                        return

                # ── Extract inline tool call blocks (NVIDIA NIM and other models) ──
                # Some models (especially NVIDIA NIM) output tool calls as regular text
                # in addition to structured tool_calls. Detect and strip these from the
                # visible stream, emitting complete blocks as reasoning previews.
                # Incomplete blocks spanning chunks are buffered and discarded.
                tool_call_pairs = [
                    ('<tool_call>', '</tool_call>'),
                    ('<|tool_call_section_begin|>', '<|tool_call_section_end|>'),
                    ('<tool_call_end>', ''),  # NVIDIA NIM single marker
                    ('<tool_calls_section_end>', ''),  # NVIDIA NIM section end marker
                    ('<tool_calls>', '</tool_calls>'),
                    ('<tool>', '</tool>'),
                    ('<|tool_calls_section_begin|>', '<|tool_calls_section_end|>'),
                    ('<|tool_call_begin|>', '<|tool_call_end|>'),
                    ('<functions>', '</functions>'),
                    ('<function_calls>', '</function_calls>'),
                    ('<function>', '</function>'),
                    ('<invoke>', '</invoke>'),
                    ('<tool_calls>', '</tool_calls>'),
                    ('<tool>', '</tool>'),
                    ('<｜tool▁calls▁begin｜>', '<｜tool▁calls▁end｜>'),
                    ('<｜tool▁call▁begin｜>', '<｜tool▁call▁end｜>'),
                ]

                # Resume a cross-chunk incomplete tool call block
                if getattr(on_token, '_in_tool_call_block', False):
                    open_tag, close_tag = on_token._tool_call_pair or tool_call_pairs[0]
                    _buf = getattr(on_token, '_tool_call_buffer', '')
                    combined = _buf + text_str
                    close_idx = combined.lower().find(close_tag)
                    if close_idx != -1:
                        # Close tag found - discard everything up to and including it
                        on_token._in_tool_call_block = False
                        on_token._tool_in_progress = False
                        on_token._tool_call_pair = None
                        on_token._tool_call_buffer = ''
                        text_str = combined[close_idx + len(close_tag):]
                        if not text_str.strip():
                            return
                        # Fall through to check for more tool call tags
                    else:
                        # Still inside tool call block - buffer partial close-tag prefix
                        _buffered = ''
                        for _prefix_len in range(len(close_tag) - 1, 0, -1):
                            if combined.lower().endswith(close_tag[:_prefix_len].lower()):
                                _buffered = combined[-_prefix_len:]
                                break
                        on_token._tool_call_buffer = _buffered
                        return

                while True:
                    lower_text = text_str.lower()
                    open_pair = None
                    open_idx = -1
                    for open_tag, close_tag in tool_call_pairs:
                        idx = lower_text.find(open_tag)
                        if idx != -1 and (open_idx == -1 or idx < open_idx):
                            open_idx = idx
                            open_pair = (open_tag, close_tag)
                    if not open_pair:
                        break
                    open_tag, close_tag = open_pair
                    close_idx = lower_text.find(close_tag, open_idx + len(open_tag))
                    if close_idx != -1:
                        # Complete tool call block in this chunk
                        tool_content = text_str[open_idx + len(open_tag):close_idx]
                        if tool_content.strip():
                            print(f"[webui] Extracted inline tool call block: {tool_content[:80]}...", flush=True)
                            put('reasoning', {'text': f'[Tool Call Preview]\n{tool_content[:500]}'})
                        before = text_str[:open_idx] if open_idx > 0 else ''
                        after = text_str[close_idx + len(close_tag):]
                        text_str = before + after
                        if not text_str.strip():
                            return
                        continue
                    # Open tag found with no close tag - start of incomplete block
                    before = text_str[:open_idx] if open_idx > 0 else ''
                    on_token._in_tool_call_block = True
                    on_token._tool_call_pair = open_pair
                    _buffered = ''
                    for _prefix_len in range(len(close_tag) - 1, 0, -1):
                        if text_str.lower().endswith(close_tag[:_prefix_len].lower()):
                            _buffered = text_str[-_prefix_len:]
                            break
                    on_token._tool_call_buffer = _buffered
                    if before:
                        text_str = before
                        break
                    else:
                        return
                # Strip JSON-formatted tool calls that may appear inline
                # Pattern: [{"name": "func", "arguments": {...}}] or {"name": "func", ...}
                # Also handles NVIDIA NIM format with "parameters" instead of "arguments"
                try:
                    import re as _re
                    # Match JSON array of tool calls (with arguments or parameters)
                    json_tool_pattern = r'\[\s*\{[^\}]*"name"\s*:\s*"[^"]+"[^\]]*\}\s*\]'
                    json_match = _re.search(json_tool_pattern, text_str)
                    if json_match:
                        tool_json = json_match.group(0)
                        print(f"[webui] Extracted inline JSON tool call: {tool_json[:80]}...", flush=True)
                        put('reasoning', {'text': f'[Tool Call Preview]\n{tool_json[:500]}'})
                        text_str = text_str[:json_match.start()] + text_str[json_match.end():]
                    # Match single JSON object tool call at start of string
                    single_tool_pattern = r'^\s*\{\s*"name"\s*:\s*"[^"]+"[^\}]*\}'
                    single_match = _re.search(single_tool_pattern, text_str)
                    if single_match:
                        tool_json = single_match.group(0)
                        print(f"[webui] Extracted inline JSON tool call: {tool_json[:80]}...", flush=True)
                        put('reasoning', {'text': f'[Tool Call Preview]\n{tool_json[:500]}'})
                        text_str = text_str[:single_match.start()] + text_str[single_match.end():]
                    # Match NVIDIA NIM format with "parameters" field anywhere in string
                    # Pattern: {"name": "...", "parameters": {...}, "id": "..."}
                    nim_param_pattern = r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^\}]*\}[^\}]*\}'
                    nim_match = _re.search(nim_param_pattern, text_str)
                    if nim_match:
                        tool_json = nim_match.group(0)
                        print(f"[webui] Extracted NIM parameters-style tool call: {tool_json[:80]}...", flush=True)
                        put('reasoning', {'text': f'[Tool Call Preview]\n{tool_json[:500]}'})
                        text_str = text_str[:nim_match.start()] + text_str[nim_match.end():]
                    # Match partial JSON fragments like ,"id":"skills_list:1"}
                    # These are remnants of incomplete tool call JSON
                    partial_json_pattern = r',\s*"id"\s*:\s*"[^"]+"\s*\}'
                    partial_match = _re.search(partial_json_pattern, text_str)
                    if partial_match:
                        text_str = text_str[:partial_match.start()] + text_str[partial_match.end():]
                except Exception:
                    pass  # Regex errors shouldn't break streaming

                # Strip DeepSeek/NVIDIA hallucinated custom markup fragments
                # that leak into the content stream when tool calling fails.
                try:
                    import re as _re
                    text_str = _re.sub(r'<\s*\|\s*[dD][sS][mM][lL]\s*\|\s*tool_calls\s*>', '', text_str, flags=_re.IGNORECASE)
                    text_str = _re.sub(r'</\s*\|\s*[dD][sS][mM][lL]\s*\|\s*tool_calls\s*>', '', text_str, flags=_re.IGNORECASE)
                    text_str = _re.sub(r'\w*\|ToolPill\|[^\s|]*', '', text_str, flags=_re.IGNORECASE)
                    text_str = _re.sub(r'\w*\|toolpill\|[^\s|]*', '', text_str, flags=_re.IGNORECASE)
                    text_str = _re.sub(r'tool-result\|ToolResult\|tool_result[^\n]*', '', text_str, flags=_re.IGNORECASE)
                except Exception:
                    pass

                # ── Deduplicate reasoning text from normal tokens ──
                # When a provider sends reasoning in both delta.reasoning and
                # delta.content, the same text appears twice. We track a cursor
                # into _reasoning_text and strip any matching prefix from tokens
                # so the visible stream doesn't echo the thinking card.
                # Case-insensitive matching handles models that vary casing
                # (e.g. uppercase SQL keywords in reasoning, lowercase in content).
                if _reasoning_text and text_str:
                    _dedup_cursor = getattr(on_token, '_dedup_cursor', 0)
                    _reasoning_boundary = getattr(on_token, '_reasoning_boundary', 0)
                    # Only deduplicate against reasoning accumulated AFTER the
                    # most recent tool boundary so pre-tool reasoning doesn't
                    # swallow post-tool content.
                    _reasoning = _reasoning_text[_reasoning_boundary:]
                    _token = text_str
                    _matched = False

                    # 1) Cursor-based forward matching (aligned chunks)
                    # Adjust cursor to be relative to the post-tool slice.
                    _effective_cursor = max(0, _dedup_cursor - _reasoning_boundary)
                    if _effective_cursor < len(_reasoning):
                        _match_len = 0
                        _max_match = min(len(_token), len(_reasoning) - _effective_cursor)
                        for _i in range(_max_match):
                            if _token[_i].lower() == _reasoning[_effective_cursor + _i].lower():
                                _match_len += 1
                            else:
                                break
                        if _match_len > 5:
                            on_token._dedup_cursor = _reasoning_boundary + _effective_cursor + _match_len
                            text_str = _token[_match_len:].lstrip()
                            _matched = True

                    # 2) Fallback: if the entire token is contained anywhere in
                    # post-boundary reasoning text (case-insensitive), skip it.
                    # This catches out-of-order delivery where content chunks
                    # arrive before their corresponding reasoning.
                    if not _matched and len(_token) > 20:
                        if _token.lower() in _reasoning.lower():
                            return

                    if _matched and not text_str:
                        return

                _accumulated_text += text_str
                _save_counter += 1
                print(f"[webui] on_token called: {text_str[:50] if text_str else 'None'}...", flush=True)
                # Periodic save every 20 tokens to preserve partial response on reload
                if _save_counter >= 20:
                    _save_counter = 0
                    try:
                        # Save partial assistant message to session for recovery
                        if s.messages and s.messages[-1].get('role') == 'assistant':
                            s.messages[-1]['content'] = _accumulated_text
                        else:
                            s.messages.append({'role': 'assistant', 'content': _accumulated_text, '_live': True})
                        s.save()
                    except Exception:
                        pass  # Non-critical, don't interrupt streaming on save failure
                put('token', {'text': text_str})

            def on_reasoning(text):
                nonlocal _reasoning_text
                if text is None:
                    return
                _reasoning_text += str(text)
                print(f"[webui] on_reasoning called: {str(text)[:100]}...", flush=True)
                put('reasoning', {'text': str(text)})

            def on_tool(*cb_args, **cb_kwargs):
                # If a previous assistant turn left an unclosed <think> or <tool_call>
                # tag, reset the state so subsequent turns don't treat everything
                # as reasoning or tool calls.
                on_token._in_thinking_block = False
                on_token._thinking_pair = None
                on_token._in_tool_call_block = False
                on_token._tool_call_pair = None
                on_token._tool_call_buffer = ''
                on_token._dedup_cursor = 0
                # Mark the boundary in the reasoning buffer so post-tool
                # deduplication only looks at reasoning emitted AFTER this tool
                # event. This prevents stale pre-tool reasoning from swallowing
                # legitimate content tokens without clearing the buffer entirely.
                on_token._reasoning_boundary = len(_reasoning_text)
                event_type = None
                name = None
                preview = None
                args = None

                if len(cb_args) >= 4:
                    event_type, name, preview, args = cb_args[:4]
                elif len(cb_args) == 3:
                    name, preview, args = cb_args
                    event_type = 'tool.started'
                elif len(cb_args) == 2:
                    event_type, name = cb_args
                elif len(cb_args) == 1:
                    name = cb_args[0]
                    event_type = 'tool.started'

                if event_type in ('reasoning.available', '_thinking'):
                    reason_text = preview if event_type == 'reasoning.available' else name
                    if reason_text:
                        put('reasoning', {'text': str(reason_text)})
                    return

                args_snap = {}
                if isinstance(args, dict):
                    for k, v in list(args.items())[:4]:
                        s2 = str(v)
                        args_snap[k] = s2[:120] + ('...' if len(s2) > 120 else '')

                if event_type in (None, 'tool.started'):
                    on_token._tool_in_progress = True
                    put('tool', {
                        'event_type': event_type or 'tool.started',
                        'name': name,
                        'preview': preview,
                        'args': args_snap,
                    })
                    # Fallback: poll for pending approval in case notify_cb wasn't
                    # registered (e.g. older approval module without gateway support).
                    try:
                        from tools.approval import has_pending as _has_pending, _pending, _lock
                        if _has_pending(session_id):
                            with _lock:
                                p = dict(_pending.get(session_id, {}))
                            if p:
                                put('approval', p)
                    except ImportError:
                        pass
                    return

                if event_type == 'tool.completed':
                    on_token._tool_in_progress = False
                    put('tool_complete', {
                        'event_type': event_type,
                        'name': name,
                        'preview': preview,
                        'args': args_snap,
                        'duration': cb_kwargs.get('duration'),
                        'is_error': bool(cb_kwargs.get('is_error', False)),
                    })
                    return

            _AIAgent = _get_ai_agent()
            if _AIAgent is None:
                raise ImportError("AIAgent not available -- check that hermes-agent is on sys.path")

            # Initialize SessionDB so session_search works in WebUI sessions
            _session_db = None
            try:
                from hermes_state import SessionDB
                _session_db = SessionDB()
            except Exception as _db_err:
                print(f"[webui] WARNING: SessionDB init failed — session_search will be unavailable: {_db_err}", flush=True)
            result = resolve_model_provider(model)
            # Handle optional 4th return value (api_key from custom provider)
            if len(result) == 4:
                resolved_model, resolved_provider, resolved_base_url, resolved_api_key = result
            else:
                resolved_model, resolved_provider, resolved_base_url = result
                resolved_api_key = None

            # Initialize _rt dict for runtime provider settings
            _rt = {}

            # Resolve API key via Hermes runtime provider (matches gateway behaviour).
            # Pass the resolved provider so non-default providers get their own credentials.
            # Only do this if we didn't get an API key from custom provider
            if not resolved_api_key:
                try:
                    from hermes_cli.runtime_provider import resolve_runtime_provider
                    _rt = resolve_runtime_provider(requested=resolved_provider)
                    resolved_api_key = _rt.get("api_key")
                    if not resolved_provider:
                        resolved_provider = _rt.get("provider")
                    if not resolved_base_url:
                        resolved_base_url = _rt.get("base_url")
                except Exception as _e:
                    print(f"[webui] WARNING: resolve_runtime_provider failed: {_e}", flush=True)

            # NVIDIA NIM: use round-robin API key rotation if provider is nvidia
            if resolved_provider == "nvidia":
                _nvidia_key, _nvidia_idx = _get_nvidia_api_key_round_robin()
                if _nvidia_key:
                    resolved_api_key = _nvidia_key
                    print(f"[webui] Using NVIDIA API key index {_nvidia_idx} (round-robin)", flush=True)
                # Ensure base_url is set to NIM endpoint
                if not resolved_base_url:
                    resolved_base_url = "https://integrate.api.nvidia.com/v1"

            # Read per-profile config at call time (not module-level snapshot)
            from api.config import get_config as _get_config
            _cfg = _get_config()

            # Per-profile toolsets — use _resolve_cli_toolsets() so MCP
            # server toolsets are included, matching native CLI behaviour.
            from api.config import _resolve_cli_toolsets
            _toolsets = _resolve_cli_toolsets(_cfg)

            # Fallback model from profile config (e.g. for rate-limit recovery)
            _fallback = _cfg.get('fallback_model') or None
            if _fallback:
                # Resolve the fallback through our provider logic too
                fb_model = _fallback.get('model', '')
                fb_provider = _fallback.get('provider', '')
                fb_base_url = _fallback.get('base_url')
                _fallback_resolved = {
                    'model': fb_model,
                    'provider': fb_provider,
                    'base_url': fb_base_url,
                }
            else:
                _fallback_resolved = None

            print(f"[webui] Creating AIAgent with model={resolved_model}, provider={resolved_provider}", flush=True)
            agent = _AIAgent(
                model=resolved_model,
                provider=resolved_provider,
                base_url=resolved_base_url,
                api_key=resolved_api_key,
                api_mode=_rt.get('api_mode'),
                acp_command=_rt.get('command'),
                acp_args=_rt.get('args'),
                credential_pool=_rt.get('credential_pool'),
                platform='cli',
                quiet_mode=True,
                enabled_toolsets=_toolsets,
                fallback_model=_fallback_resolved,
                session_id=session_id,
                session_db=_session_db,
                stream_delta_callback=on_token,
                reasoning_callback=on_reasoning,
                tool_progress_callback=on_tool,
                clarify_callback=(
                    lambda question, choices: _clarify_callback_impl(
                        question, choices, session_id, cancel_event, put
                    )
                ),
            )
            print(f"[webui] AIAgent created successfully", flush=True)

            # Store agent instance for cancel/interrupt propagation
            with STREAMS_LOCK:
                AGENT_INSTANCES[stream_id] = agent
                # Check if cancel was requested during agent initialization
                if stream_id in CANCEL_FLAGS and CANCEL_FLAGS[stream_id].is_set():
                    # Cancel arrived during agent creation - interrupt immediately
                    try:
                        agent.interrupt("Cancelled before start")
                    except Exception:
                        logger.debug("Failed to interrupt agent before start")
                    put('cancel', {'message': 'Cancelled by user'})
                    return

            # Prepend workspace context so the agent always knows which directory
            # to use for file operations, regardless of session age or AGENTS.md defaults.
            workspace_ctx = f"[Workspace: {s.workspace}]\n"
            workspace_system_msg = (
                f"Active workspace at session start: {s.workspace}\n"
                "Every user message is prefixed with [Workspace: /absolute/path] indicating the "
                "workspace the user has selected in the web UI at the time they sent that message. "
                "This tag is the single authoritative source of the active workspace and updates "
                "with every message. It overrides any prior workspace mentioned in this system "
                "prompt, memory, or conversation history. Always use the value from the most recent "
                "[Workspace: ...] tag as your default working directory for ALL file operations: "
                "write_file, read_file, search_files, terminal workdir, and patch. "
                "Never fall back to a hardcoded path when this tag is present."
            )
            # NVIDIA NIM: append explicit tool-use discipline so the model
            # actually calls tools instead of just describing intentions.
            if resolved_provider == 'nvidia' or 'integrate.api.nvidia.com' in (resolved_base_url or ''):
                workspace_system_msg += (
                    "\n\nIMPORTANT: When a task requires using a tool, you MUST call the tool "
                    "immediately. Do NOT say 'I will do that' or describe your plan. "
                    "Output the tool call as JSON: {\"name\": \"tool_name\", \"arguments\": {...}}."
                )
            # Resolve personality prompt from config.yaml agent.personalities
            # (matches hermes-agent CLI behavior — passes via ephemeral_system_prompt)
            _personality_prompt = None
            _pname = getattr(s, 'personality', None)
            if _pname:
                _agent_cfg = _cfg.get('agent', {})
                _personalities = _agent_cfg.get('personalities', {})
                if isinstance(_personalities, dict) and _pname in _personalities:
                    _pval = _personalities[_pname]
                    if isinstance(_pval, dict):
                        _parts = [_pval.get('system_prompt', '') or _pval.get('prompt', '')]
                        if _pval.get('tone'):
                            _parts.append(f'Tone: {_pval["tone"]}')
                        if _pval.get('style'):
                            _parts.append(f'Style: {_pval["style"]}')
                        _personality_prompt = '\n'.join(p for p in _parts if p)
                    else:
                        _personality_prompt = str(_pval)
            # Pass personality via ephemeral_system_prompt (agent's own mechanism)
            if _personality_prompt:
                agent.ephemeral_system_prompt = _personality_prompt
            # GLM and NVIDIA NIM models are not in the hardcoded tool-use
            # enforcement list, but they often need explicit steering to call
            # tools instead of describing actions. Force enforcement when the
            # user hasn't explicitly disabled it.
            _agent_cfg = _cfg.get('agent', {})
            if _agent_cfg.get('tool_use_enforcement') is None:
                _model_lower = (resolved_model or '').lower()
                if 'glm' in _model_lower:
                    agent._tool_use_enforcement = True
                    print(f"[webui] Forcing tool-use enforcement for GLM model", flush=True)
                if resolved_provider == 'nvidia' or 'integrate.api.nvidia.com' in (resolved_base_url or ''):
                    agent._tool_use_enforcement = True
                    print(f"[webui] Forcing tool-use enforcement for NVIDIA NIM", flush=True)
            print(f"[webui] Starting agent.run_conversation()...", flush=True)
            result = agent.run_conversation(
                user_message=workspace_ctx + msg_text,
                system_message=workspace_system_msg,
                conversation_history=_sanitize_messages_for_api(s.messages),
                task_id=session_id,
                persist_user_message=msg_text,
            )
            print(f"[webui] agent.run_conversation() returned. Result keys: {list(result.keys()) if result else 'None'}", flush=True)
            print(f"[webui] _token_sent: {_token_sent}, result error: {result.get('error') if result else 'N/A'}", flush=True)
            # Safety reset: ensure suppression flags are never stuck after the agent finishes.
            # If the agent framework missed a tool.completed event, _tool_in_progress could
            # stay True and silently drop all remaining tokens, making the stream appear to pause.
            on_token._tool_in_progress = False
            on_token._in_thinking_block = False
            on_token._thinking_pair = None
            on_token._thinking_buffer = ''
            on_token._in_tool_call_block = False
            on_token._tool_call_pair = None
            on_token._tool_call_buffer = ''
            s.messages = result.get('messages') or s.messages

            # Strip any remaining inline tool call XML from assistant message content.
            # Some providers (e.g. NVIDIA NIM) include raw tool call XML in message.content
            # in addition to structured tool_calls, and the agent framework may preserve it.
            for _m in s.messages:
                if _m.get('role') == 'assistant' and isinstance(_m.get('content'), str):
                    _c = _m['content']
                    _c = re.sub(r'<tool_call>.*?</tool_call>', '', _c, flags=re.IGNORECASE | re.DOTALL)
                    _c = re.sub(r'<arg_key>.*?</arg_key>\s*<arg_value>.*?</arg_value>', '', _c, flags=re.IGNORECASE | re.DOTALL)
                    _c = re.sub(r'<arg_key>.*?</arg_key>', '', _c, flags=re.IGNORECASE | re.DOTALL)
                    _c = re.sub(r'<arg_value>.*?</arg_value>', '', _c, flags=re.IGNORECASE | re.DOTALL)
                    _m['content'] = _c

            # ── Emit any unst streamed content ──
            # The agent's stream_delta_callback may not be called for all tokens
            # before run_conversation() returns. Emit remaining text from the
            # final assistant message to ensure the stream is complete.
            if _token_sent and _accumulated_text:
                _final_asst_content = ''
                for m in reversed(s.messages):
                    if m.get('role') == 'assistant' and m.get('content'):
                        _final_asst_content = str(m.get('content'))
                        break
                # Strip thinking tags from accumulated text for comparison
                # (on_token strips them before appending to _accumulated_text)
                _accum_clean = _accumulated_text
                for _open, _close in [('<thinking>', '</thinking>'), ('<reasoning>', '</reasoning>'), ('<|channel>thought', '<channel|>')]:
                    while _open in _accum_clean.lower():
                        _idx = _accum_clean.lower().find(_open)
                        _close_idx = _accum_clean.lower().find(_close, _idx + len(_open))
                        if _close_idx != -1:
                            _accum_clean = _accum_clean[:_idx] + _accum_clean[_close_idx + len(_close):]
                        else:
                            _accum_clean = _accum_clean[:_idx]
                            break
                # Check if final content has more than what was accumulated
                if _final_asst_content and len(_final_asst_content) > len(_accum_clean) + 10:
                    _remaining = _final_asst_content[len(_accum_clean):].lstrip()
                    if _remaining.strip():
                        print(f"[webui] Emitting {len(_remaining)} chars of remaining content", flush=True)
                        # Optimized: batch token delivery to reduce overhead
                        words = _remaining.split(' ')
                        for i, _word in enumerate(words):
                            put('token', {'text': ' ' + _word if i > 0 else _word})
                            if i % 10 == 0:  # Only sleep every 10 tokens for better performance
                                time.sleep(0.005)

            # ── Detect silent agent failure (no assistant reply produced) ──
            # When the agent catches an auth/network error internally it may return
            # an empty final_response without raising — the stream would end with
            # a done event containing zero assistant messages, leaving the user with
            # no feedback. Emit an apperror so the client shows an inline error.
            _assistant_added = any(
                m.get('role') == 'assistant' and str(m.get('content') or '').strip()
                for m in (result.get('messages') or [])
            )
            # _token_sent tracks whether on_token() was called (any streamed text)
            if not _assistant_added and not _token_sent:
                _last_err = getattr(agent, '_last_error', None) or result.get('error') or ''
                _err_str = str(_last_err) if _last_err else ''
                _is_auth = (
                    '401' in _err_str
                    or (_last_err and 'AuthenticationError' in type(_last_err).__name__)
                    or 'authentication' in _err_str.lower()
                    or 'unauthorized' in _err_str.lower()
                    or 'invalid api key' in _err_str.lower()
                    or 'invalid_api_key' in _err_str.lower()
                )

                def _run_nvidia_fallback(model_name: str) -> bool:
                    nonlocal agent, result, _assistant_added
                    try:
                        fallback_agent = _AIAgent(
                            model=model_name,
                            provider='nvidia',
                            base_url=resolved_base_url,
                            api_key=resolved_api_key,
                            api_mode=_rt.get('api_mode'),
                            acp_command=_rt.get('command'),
                            acp_args=_rt.get('args'),
                            credential_pool=_rt.get('credential_pool'),
                            platform='cli',
                            quiet_mode=True,
                            enabled_toolsets=_toolsets,
                            fallback_model=_fallback_resolved,
                            session_id=session_id,
                            session_db=_session_db,
                            reasoning_callback=on_reasoning,
                            tool_progress_callback=on_tool,
                            clarify_callback=(
                                lambda question, choices: _clarify_callback_impl(
                                    question, choices, session_id, cancel_event, put
                                )
                            ),
                        )
                        print(f"[webui] NVIDIA timeout fallback agent created for {model_name}", flush=True)
                        with STREAMS_LOCK:
                            AGENT_INSTANCES[stream_id] = fallback_agent
                            if stream_id in CANCEL_FLAGS and CANCEL_FLAGS[stream_id].is_set():
                                fallback_agent.interrupt("Cancelled before start")
                                put('cancel', {'message': 'Cancelled by user'})
                                return False

                        fallback_result = fallback_agent.run_conversation(
                            user_message=workspace_ctx + msg_text,
                            system_message=workspace_system_msg,
                            conversation_history=_sanitize_messages_for_api(s.messages),
                            task_id=session_id,
                            persist_user_message=msg_text,
                        )
                        print(f"[webui] NVIDIA timeout fallback returned for {model_name}. Result keys: {list(fallback_result.keys()) if fallback_result else 'None'}", flush=True)

                        fallback_messages = fallback_result.get('messages', [])
                        fallback_assistant_msg = None
                        for m in reversed(fallback_messages):
                            if m.get('role') == 'assistant' and str(m.get('content') or '').strip():
                                fallback_assistant_msg = m
                                break

                        if fallback_assistant_msg:
                            full_response = str(fallback_assistant_msg.get('content', ''))
                            print(f"[webui] NVIDIA timeout fallback succeeded for {model_name}, emitting {len(full_response)} chars as tokens...", flush=True)
                            words = full_response.split(' ')
                            for i, word in enumerate(words):
                                if cancel_event.is_set():
                                    put('cancel', {'message': 'Cancelled by user'})
                                    return False
                                token_text = word if i == 0 else ' ' + word
                                on_token(token_text)
                                if i % 10 == 0:  # Reduced sleep frequency for better throughput
                                    time.sleep(0.005)  # Reduced sleep duration
                            s.messages = fallback_messages
                            result = fallback_result
                            agent = fallback_agent
                            _assistant_added = True
                            print(f"[webui] NVIDIA timeout fallback emitted tokens successfully for {model_name}", flush=True)
                            return True
                        print(f"[webui] NVIDIA timeout fallback had no assistant message for {model_name}", flush=True)
                    except Exception as fallback_err:
                        print(f"[webui] NVIDIA timeout fallback failed for {model_name}: {fallback_err}", flush=True)
                    return False

                _is_nvidia_deepseek_timeout_error = (
                    resolved_provider == 'nvidia'
                    and resolved_model == 'deepseek-ai/deepseek-v4-pro'
                    and any(token in _err_str.lower() for token in (
                        '429', 'rate limit', 'too many requests', 'timeout', 'timed out',
                        'high usage', 'busy', 'service unavailable', '503', '504', 'throttled'
                    ))
                )
                if _is_nvidia_deepseek_timeout_error:
                    print("[webui] NVIDIA NIM DeepSeek timeout or high-usage error detected; retrying with Mistral fallback model...", flush=True)
                    if _run_nvidia_fallback('mistralai/mistral-medium-3.5-128b'):
                        pass
                # ── NVIDIA NIM / Streaming fallback: retry without streaming ──
                # When streaming endpoint errors (common with NVIDIA NIM), fall back
                # to non-streaming mode and emit the response as tokens on demand.
                _is_stream_error = (
                    not _is_auth
                    and resolved_provider in ('nvidia', 'openai', 'deepseek')
                    and ('stream' in _err_str.lower()
                         or 'chunk' in _err_str.lower()
                         or 'sse' in _err_str.lower()
                         or 'unexpected end' in _err_str.lower()
                         or not _err_str)  # Empty response often means stream died
                )
                if _is_stream_error and not _assistant_added:
                    print(f"[webui] Streaming failed for {resolved_provider}, attempting non-streaming fallback...", flush=True)
                    try:
                        # Create a non-streaming agent instance
                        fallback_agent = _AIAgent(
                            model=resolved_model,
                            provider=resolved_provider,
                            base_url=resolved_base_url,
                            api_key=resolved_api_key,
                            api_mode=_rt.get('api_mode'),
                            acp_command=_rt.get('command'),
                            acp_args=_rt.get('args'),
                            credential_pool=_rt.get('credential_pool'),
                            platform='cli',
                            quiet_mode=True,
                            enabled_toolsets=_toolsets,
                            fallback_model=_fallback_resolved,
                            session_id=session_id,
                            session_db=_session_db,
                            # No stream_delta_callback - this disables streaming
                            reasoning_callback=on_reasoning,
                            tool_progress_callback=on_tool,
                            clarify_callback=(
                                lambda question, choices: _clarify_callback_impl(
                                    question, choices, session_id, cancel_event, put
                                )
                            ),
                        )
                        print(f"[webui] Fallback agent created, running non-streaming conversation...", flush=True)
                        # Store fallback agent for cancel support
                        with STREAMS_LOCK:
                            AGENT_INSTANCES[stream_id] = fallback_agent
                            if stream_id in CANCEL_FLAGS and CANCEL_FLAGS[stream_id].is_set():
                                fallback_agent.interrupt("Cancelled before start")
                                put('cancel', {'message': 'Cancelled by user'})
                                return

                        fallback_result = fallback_agent.run_conversation(
                            user_message=workspace_ctx + msg_text,
                            system_message=workspace_system_msg,
                            conversation_history=_sanitize_messages_for_api(s.messages),
                            task_id=session_id,
                            persist_user_message=msg_text,
                        )
                        print(f"[webui] Non-streaming fallback returned. Result keys: {list(fallback_result.keys()) if fallback_result else 'None'}", flush=True)

                        # Check if fallback succeeded
                        fallback_messages = fallback_result.get('messages', [])
                        fallback_assistant_msg = None
                        for m in reversed(fallback_messages):
                            if m.get('role') == 'assistant' and str(m.get('content') or '').strip():
                                fallback_assistant_msg = m
                                break

                        if fallback_assistant_msg:
                            # Success! Emit the response as simulated tokens
                            full_response = str(fallback_assistant_msg.get('content', ''))
                            print(f"[webui] Fallback succeeded, emitting {len(full_response)} chars as tokens...", flush=True)

                            # Emit the response word-by-word to simulate streaming
                            # This gives the user visual feedback like streaming would
                            words = full_response.split(' ')
                            for i, word in enumerate(words):
                                if cancel_event.is_set():
                                    put('cancel', {'message': 'Cancelled by user'})
                                    return
                                # Add space back except for first word
                                token_text = word if i == 0 else ' ' + word
                                on_token(token_text)
                                # Small delay to make it feel like streaming (optional, can be 0)
                                if i % 5 == 0:
                                    time.sleep(0.01)

                            # Update session with fallback result
                            s.messages = fallback_messages
                            result = fallback_result
                            agent = fallback_agent  # Use fallback agent for stats
                            _assistant_added = True
                            print(f"[webui] Fallback tokens emitted successfully", flush=True)
                        else:
                            print(f"[webui] Fallback also failed, no assistant message in response", flush=True)
                            # Fall through to error handling
                    except Exception as fallback_err:
                        print(f"[webui] Non-streaming fallback failed: {fallback_err}", flush=True)
                        # Fall through to error handling

                # If still no assistant and no tokens after potential fallback, show error
                if not _assistant_added and not _token_sent:
                    if _is_auth:
                        put('apperror', {
                            'message': _err_str or 'Authentication failed — check your API key.',
                            'type': 'auth_mismatch',
                            'hint': (
                                'The selected model may not be supported by your configured provider or '
                                'your API key is invalid. Run `hermes model` in your terminal to '
                                'update credentials, then restart the WebUI.'
                            ),
                        })
                    else:
                        put('apperror', {
                            'message': _err_str or 'The agent returned no response. Check your API key and model selection.',
                            'type': 'no_response',
                            'hint': 'Verify your API key is valid and the selected model is available for your account.',
                        })
                    return  # Don't emit done — the apperror already closes the stream on the client

            # ── Handle context compression side effects ──
            # If compression fired inside run_conversation, the agent may have
            # rotated its session_id. Detect and fix the mismatch so the WebUI
            # continues writing to the correct session file.
            _agent_sid = getattr(agent, 'session_id', None)
            _compressed = False
            if _agent_sid and _agent_sid != session_id:
                old_sid = session_id
                new_sid = _agent_sid
                # Rename the session file
                old_path = SESSION_DIR / f'{old_sid}.json'
                new_path = SESSION_DIR / f'{new_sid}.json'
                s.session_id = new_sid
                with LOCK:
                    if old_sid in SESSIONS:
                        SESSIONS[new_sid] = SESSIONS.pop(old_sid)
                if old_path.exists() and not new_path.exists():
                    try:
                        old_path.rename(new_path)
                    except OSError:
                        logger.debug("Failed to rename session file during compression")
                _compressed = True
            # Also detect compression via the result dict or compressor state
            if not _compressed:
                _compressor = getattr(agent, 'context_compressor', None)
                if _compressor and getattr(_compressor, 'compression_count', 0) > 0:
                    _compressed = True
            # Notify the frontend that compression happened
            if _compressed:
                put('compressed', {
                    'message': 'Context auto-compressed to continue the conversation',
                })

            # Stamp 'timestamp' on any messages that don't have one yet
            _now = time.time()
            for _m in s.messages:
                if isinstance(_m, dict) and not _m.get('timestamp') and not _m.get('_ts'):
                    _m['timestamp'] = int(_now)
            # Only auto-generate title when still default; preserves user renames
            if s.title == 'Untitled' or s.title == 'New Chat' or not s.title:
                s.title = title_from(s.messages, s.title)
            _looks_default = (s.title == 'Untitled' or s.title == 'New Chat' or not s.title)
            _looks_provisional = _is_provisional_title(s.title, s.messages)
            _invalid_existing_title = _looks_invalid_generated_title(s.title)
            _should_bg_title = (
                (_looks_default or _looks_provisional or _invalid_existing_title)
                and (not getattr(s, 'llm_title_generated', False) or _invalid_existing_title)
            )
            _u0 = ''
            _a0 = ''
            if _should_bg_title:
                _u0, _a0 = _first_exchange_snippets(s.messages)
            # Read token/cost usage from the agent object (if available)
            input_tokens = getattr(agent, 'session_prompt_tokens', 0) or 0
            output_tokens = getattr(agent, 'session_completion_tokens', 0) or 0
            estimated_cost = getattr(agent, 'session_estimated_cost_usd', None)
            s.input_tokens = (s.input_tokens or 0) + input_tokens
            s.output_tokens = (s.output_tokens or 0) + output_tokens
            if estimated_cost:
                s.estimated_cost = (s.estimated_cost or 0) + estimated_cost
            # Extract tool call metadata grouped by assistant message index
            # Each tool call gets assistant_msg_idx so the client can render
            # cards inline with the assistant bubble that triggered them.
            tool_calls = []
            pending_names = {}   # tool_call_id -> name
            pending_args = {}    # tool_call_id -> args dict
            pending_asst_idx = {} # tool_call_id -> index in s.messages
            for msg_idx, m in enumerate(s.messages):
                if m.get('role') == 'assistant':
                    c = m.get('content', '')
                    # Anthropic format: content is a list with type=tool_use blocks
                    if isinstance(c, list):
                        for p in c:
                            if isinstance(p, dict) and p.get('type') == 'tool_use':
                                tid = p.get('id', '')
                                pending_names[tid] = p.get('name', '')
                                pending_args[tid] = p.get('input', {})
                                pending_asst_idx[tid] = msg_idx
                    # OpenAI format: tool_calls as top-level field on the message
                    for tc in m.get('tool_calls', []):
                        if not isinstance(tc, dict):
                            continue
                        tid = tc.get('id', '') or tc.get('call_id', '')
                        fn = tc.get('function', {})
                        name = fn.get('name', '')
                        try:
                            import json as _j
                            args = _j.loads(fn.get('arguments', '{}') or '{}')
                        except Exception:
                            args = {}
                        if tid and name:
                            pending_names[tid] = name
                            pending_args[tid] = args
                            pending_asst_idx[tid] = msg_idx
                elif m.get('role') == 'tool':
                    tid = m.get('tool_call_id') or m.get('tool_use_id', '')
                    name = pending_names.get(tid, '')
                    if not name or name == 'tool':
                        continue  # skip unresolvable tool entries
                    asst_idx = pending_asst_idx.get(tid, -1)
                    args = pending_args.get(tid, {})
                    raw = str(m.get('content', ''))
                    try:
                        rd = json.loads(raw)
                        snippet = str(rd.get('output') or rd.get('result') or rd.get('error') or raw)[:200]
                    except Exception:
                        snippet = raw[:200]
                    # Truncate args values for storage
                    args_snap = {}
                    if isinstance(args, dict):
                        for k, v in list(args.items())[:6]:
                            s2 = str(v)
                            args_snap[k] = s2[:120] + ('...' if len(s2) > 120 else '')
                    tool_calls.append({
                        'name': name, 'snippet': snippet, 'tid': tid,
                        'assistant_msg_idx': asst_idx, 'args': args_snap,
                    })
            s.tool_calls = tool_calls
            s.active_stream_id = None
            s.pending_user_message = None
            s.pending_attachments = []
            s.pending_started_at = None
            # Clear the transient _live flag from any assistant messages before saving
            for _m in s.messages:
                if isinstance(_m, dict) and _m.get('role') == 'assistant':
                    _m.pop('_live', None)
            # Tag the matching user message with attachment filenames for display on reload
            # Only tag a user message whose content relates to this turn's text
            # (msg_text is the full message including the [Attached files: ...] suffix)
            if attachments:
                for m in reversed(s.messages):
                    if m.get('role') == 'user':
                        content = str(m.get('content', ''))
                        # Match if content is part of the sent message or vice-versa
                        base_text = msg_text.split('\n\n[Attached files:')[0].strip() if '\n\n[Attached files:' in msg_text else msg_text
                        if base_text[:60] in content or content[:60] in msg_text:
                            m['attachments'] = attachments
                            break
            s.save()
            # Sync to state.db for /insights (opt-in setting)
            try:
                from api.config import load_settings as _load_settings
                if _load_settings().get('sync_to_insights'):
                    from api.state_sync import sync_session_usage
                    sync_session_usage(
                        session_id=s.session_id,
                        input_tokens=s.input_tokens or 0,
                        output_tokens=s.output_tokens or 0,
                        estimated_cost=s.estimated_cost,
                        model=model,
                        title=s.title,
                        message_count=len(s.messages),
                    )
            except Exception:
                logger.debug("Failed to sync session to insights")
            usage = {'input_tokens': input_tokens, 'output_tokens': output_tokens, 'estimated_cost': estimated_cost}
            # Include context window data from the agent's compressor for the UI indicator
            _cc = getattr(agent, 'context_compressor', None)
            if _cc:
                usage['context_length'] = getattr(_cc, 'context_length', 0) or 0
                usage['threshold_tokens'] = getattr(_cc, 'threshold_tokens', 0) or 0
                usage['last_prompt_tokens'] = getattr(_cc, 'last_prompt_tokens', 0) or 0
            # Persist reasoning trace in the session so it survives reload
            if _reasoning_text and s.messages:
                for _rm in reversed(s.messages):
                    if isinstance(_rm, dict) and _rm.get('role') == 'assistant':
                        _rm['reasoning'] = _reasoning_text
                        # Strip reasoning text from content to avoid duplication
                        # (case-insensitive since models may vary casing).
                        _content = str(_rm.get('content') or '')
                        _reasoning_trim = _reasoning_text.strip()
                        _content_strip = _content.strip()
                        if _reasoning_trim and _content_strip.lower().startswith(_reasoning_trim.lower()):
                            _match_len = 0
                            for i in range(min(len(_content_strip), len(_reasoning_trim))):
                                if _content_strip[i].lower() == _reasoning_trim[i].lower():
                                    _match_len += 1
                                else:
                                    break
                            # Preserve any original leading whitespace, then append
                            # the remainder after the matched prefix.
                            _leading_ws = _content[:len(_content) - len(_content.lstrip())]
                            _rm['content'] = _leading_ws + _content_strip[_match_len:].lstrip()
                        break
            raw_session = s.compact() | {'messages': s.messages, 'tool_calls': tool_calls}
            put('done', {'session': redact_session_data(raw_session), 'usage': usage})
            _swarm_notify_done(stream_id, s.messages, usage)
            if _should_bg_title and _u0 and _a0:
                threading.Thread(
                    target=_run_background_title_update,
                    args=(s.session_id, _u0, _a0, str(s.title or '').strip(), put, agent),
                    daemon=True,
                ).start()
            else:
                put('stream_end', {'session_id': s.session_id})
        finally:
            # Unregister the gateway approval callback and unblock any threads
            # still waiting on approval (e.g. stream cancelled mid-approval).
            if _approval_registered and _unreg_notify is not None:
                try:
                    _unreg_notify(session_id)
                except Exception:
                    logger.debug("Failed to unregister approval callback")
            if _clarify_registered and _unreg_clarify_notify is not None:
                try:
                    _unreg_clarify_notify(session_id)
                except Exception:
                    logger.debug("Failed to unregister clarify callback")
            if _sudo_password_registered and _unreg_sudo_password_notify is not None:
                try:
                    _unreg_sudo_password_notify(session_id)
                except Exception:
                    logger.debug("Failed to unregister sudo password callback")
            with _ENV_LOCK:
                if old_cwd is None: os.environ.pop('TERMINAL_CWD', None)
                else: os.environ['TERMINAL_CWD'] = old_cwd
                if old_exec_ask is None: os.environ.pop('HERMES_EXEC_ASK', None)
                else: os.environ['HERMES_EXEC_ASK'] = old_exec_ask
                if old_session_key is None: os.environ.pop('HERMES_SESSION_KEY', None)
                else: os.environ['HERMES_SESSION_KEY'] = old_session_key
                if old_hermes_home is None: os.environ.pop('HERMES_HOME', None)
                else: os.environ['HERMES_HOME'] = old_hermes_home

    except Exception as e:
        print('[webui] stream error:\n' + traceback.format_exc(), flush=True)
        if s is not None:
            s.active_stream_id = None
            s.pending_user_message = None
            s.pending_attachments = []
            s.pending_started_at = None
            # Clear the transient _live flag from any assistant messages before saving
            for _m in s.messages:
                if isinstance(_m, dict) and _m.get('role') == 'assistant':
                    _m.pop('_live', None)
            try:
                s.save()
            except Exception:
                pass
        err_str = str(e)
        # Detect rate limit errors specifically so the client can show a helpful card
        # rather than the generic "Connection lost" message
        is_rate_limit = 'rate limit' in err_str.lower() or '429' in err_str or 'RateLimitError' in type(e).__name__
        is_auth_error = (
            '401' in err_str
            or 'AuthenticationError' in type(e).__name__
            or 'authentication' in err_str.lower()
            or 'unauthorized' in err_str.lower()
            or 'invalid api key' in err_str.lower()
            or 'no cookie auth credentials' in err_str.lower()
        )
        if is_rate_limit:
            put('apperror', {
                'message': err_str,
                'type': 'rate_limit',
                'hint': 'Rate limit reached. The fallback model (if configured) was also exhausted. Try again in a moment.',
            })
        elif is_auth_error:
            put('apperror', {
                'message': err_str,
                'type': 'auth_mismatch',
                'hint': (
                    'The selected model may not be supported by your configured provider. '
                    'Run `hermes model` in your terminal to switch providers, then restart the WebUI.'
                ),
            })
        else:
            put('apperror', {'message': err_str, 'type': 'error'})
        # -- Swarm hook: notify swarm when a worker stream errors --
        try:
            from api.swarm import on_worker_stream_error
            on_worker_stream_error(stream_id, err_str)
        except Exception:
            pass
    finally:
        # Safety reset: clear any stuck suppression flags so the next stream starts fresh.
        # This is a defensive measure in case the agent thread exited abnormally.
        try:
            on_token._tool_in_progress = False
            on_token._in_thinking_block = False
            on_token._thinking_pair = None
            on_token._thinking_buffer = ''
            on_token._in_tool_call_block = False
            on_token._tool_call_pair = None
            on_token._tool_call_buffer = ''
        except Exception:
            pass
        _clear_thread_env()  # TD1: always clear thread-local context
        with STREAMS_LOCK:
            STREAMS.pop(stream_id, None)
            CANCEL_FLAGS.pop(stream_id, None)
            AGENT_INSTANCES.pop(stream_id, None)  # Clean up agent instance reference

# ============================================================
# SECTION: HTTP Request Handler
# do_GET: read-only API endpoints + SSE stream + static HTML
# do_POST: mutating endpoints (session CRUD, chat, upload, approval)
# Routing is a flat if/elif chain. See ARCHITECTURE.md section 4.1.
# ============================================================


def cancel_stream(stream_id: str) -> bool:
    """Signal an in-flight stream to cancel. Returns True if the stream existed."""
    with STREAMS_LOCK:
        if stream_id not in STREAMS:
            return False

        # Set WebUI layer cancel flag
        flag = CANCEL_FLAGS.get(stream_id)
        if flag:
            flag.set()

        # Interrupt the AIAgent instance to stop tool execution
        agent = AGENT_INSTANCES.get(stream_id)
        if agent:
            try:
                agent.interrupt("Cancelled by user")
            except Exception as e:
                # Log but don't block the cancel flow
                import logging
                logging.getLogger(__name__).debug(
                    f"Failed to interrupt agent for stream {stream_id}: {e}"
                )
        else:
            # Agent not yet stored - cancel_event flag will be checked by agent thread
            import logging
            logging.getLogger(__name__).debug(
                f"Cancel requested for stream {stream_id} before agent ready - "
                f"cancel_event flag set, will be checked on agent startup"
            )

        # Clear any pending clarify prompt so the blocked tool call can unwind.
        try:
            from api.clarify import clear_pending as _clear_clarify_pending

            if agent and getattr(agent, "session_id", None):
                _clear_clarify_pending(agent.session_id)
        except Exception:
            logger.debug("Failed to clear clarify prompt during cancel")

        # Put a cancel sentinel into the queue so the SSE handler wakes up
        q = STREAMS.get(stream_id)
        if q:
            try:
                q.put_nowait(('cancel', {'message': 'Cancelled by user'}))
            except Exception:
                logger.debug("Failed to put cancel event to queue")
    return True
