"""
Hermes Web UI -- Main server entry point.
Thin routing shell: imports Handler, delegates to api/routes.py, runs server.
All business logic lives in api/*.
"""
import logging
import socket
import sys
import time
import traceback
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Set up JSON logging for the root logger
from python_json_logger import JsonFormatter

logHandler = logging.StreamHandler(sys.stdout)
formatter = JsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
# Clear any existing handlers and set our own
logging.root.handlers.clear()
logging.root.addHandler(logHandler)
logging.root.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

from api.auth import check_auth
from api.config import HOST, PORT, STATE_DIR, SESSION_DIR, DEFAULT_WORKSPACE
from api.helpers import j
from api.routes import handle_get, handle_post
from api.startup import auto_install_agent_deps, fix_credential_permissions


def _warmup_session_cache():
    """Pre-build session index at startup for instant page loads."""
    try:
        from api.models import _rebuild_session_index
        _rebuild_session_index()
        print('[ok] Session index warmed up.', flush=True)
    except Exception as e:
        print(f'[!!] Session index warmup failed: {e}', flush=True)


class QuietHTTPServer(ThreadingHTTPServer):
    """Custom HTTP server that silently handles common network errors."""
    request_queue_size = 128  # Allow more pending connections (default is 5)
    
    def handle_error(self, request, client_address):
        """Override to suppress logging for common client disconnect errors."""
        exc_type, exc_value, _ = sys.exc_info()
        
        # Silently ignore common connection errors caused by client disconnects
        if exc_type in (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            return
        
        # Also handle socket errors that indicate client disconnect
        if exc_type is socket.error:
            # errno 54 is Connection reset by peer on macOS/BSD
            # errno 104 is Connection reset by peer on Linux
            if exc_value.errno in (54, 104, 32):  # ECONNRESET, EPIPE
                return
        
        # For other errors, use default logging
        super().handle_error(request, client_address)


class Handler(BaseHTTPRequestHandler):
    timeout = 0  # disabled — SSE streams must stay open indefinitely; OS handles dead connections
    server_version = 'HermesWebUI/0.50.38'
    def log_message(self, fmt, *args): pass  # suppress default Apache-style log

    def log_request(self, code: str='-', size: str='-') -> None:
        """Structured JSON logs for each request."""
        import json as _json
        duration_ms = round((time.time() - getattr(self, '_req_t0', time.time())) * 1000, 1)
        record = _json.dumps({
            'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'method': self.command or '-',
            'path': self.path or '-',
            'status': int(code) if str(code).isdigit() else code,
            'ms': duration_ms,
        })
        print(f'[webui] {record}', flush=True)

    def do_GET(self) -> None:
        self._req_t0 = time.time()
        try:
            parsed = urlparse(self.path)
            if not check_auth(self, parsed): return
            result = handle_get(self, parsed)
            if result is False:
                return j(self, {'error': 'not found'}, status=404)
        except Exception as e:
            print(f'[webui] ERROR {self.command} {self.path}\n' + traceback.format_exc(), flush=True)
            return j(self, {'error': 'Internal server error'}, status=500)

    def do_POST(self) -> None:
        self._req_t0 = time.time()
        try:
            parsed = urlparse(self.path)
            if not check_auth(self, parsed): return
            # Pre-read POST body to prevent rfile.read() hang
            try:
                _cl = int(self.headers.get('Content-Length', 0))
                self._post_body = self.rfile.read(_cl) if _cl else b'{}'
            except Exception:
                self._post_body = b'{}'
            result = handle_post(self, parsed)
            if result is False:
                return j(self, {'error': 'not found'}, status=404)
        except Exception as e:
            print(f'[webui] ERROR {self.command} {self.path}\n' + traceback.format_exc(), flush=True)
            return j(self, {'error': 'Internal server error'}, status=500)


def main() -> None:
    from api.config import print_startup_config, verify_hermes_imports, _HERMES_FOUND

    print_startup_config()

    # Fix sensitive file permissions before doing anything else
    fix_credential_permissions()

    within_container = False
    # Check for the "/.within_container" file to determine if we're running inside a container; this file is created in the Dockerfile
    try:
        with open('/.within_container', 'r') as f:
            within_container = True
    except FileNotFoundError:
        pass

    if within_container:
        print('[ok] Running within container.', flush=True)

    # Security: warn if binding non-loopback without authentication
    from api.auth import is_auth_enabled
    if HOST not in ('127.0.0.1', '::1', 'localhost') and not is_auth_enabled():
        print(f'[!!] WARNING: Binding to {HOST} with NO PASSWORD SET.', flush=True)
        print(f' Anyone on the network can access your filesystem and agent.', flush=True)
        print(f' Set a password via Settings or HERMES_WEBUI_PASSWORD env var.', flush=True)
        print(f' To suppress: bind to 127.0.0.1 or set a password.', flush=True)
        if within_container:
            print(f' Note: You are running within a container, must bind to 0.0.0.0 to publish the port.', flush=True)
    elif not is_auth_enabled():
        print(f' [tip] No password set. Any process on this machine can read sessions', flush=True)
        print(f' and memory via the local API. Set HERMES_WEBUI_PASSWORD to', flush=True)
        print(f' enable authentication.', flush=True)

    ok, missing, errors = verify_hermes_imports()
    if not ok and _HERMES_FOUND:
        print(f'[!!] Warning: Hermes agent found but missing modules: {missing}', flush=True)
        for mod, err in errors.items():
            print(f'    {mod}: {err}', flush=True)
        print('  Attempting to install missing dependencies from agent requirements.txt...', flush=True)
        auto_install_agent_deps()
        ok, missing, errors = verify_hermes_imports()
        if not ok:
            print(f'[!!] Still missing after install attempt: {missing}', flush=True)
            for mod, err in errors.items():
                print(f'    {mod}: {err}', flush=True)
            print('  Agent features may not work correctly.', flush=True)
        else:
            print('[ok] Agent dependencies installed successfully.', flush=True)

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_WORKSPACE.mkdir(parents=True, exist_ok=True)

     # Warm up session cache for instant page loads
     _warmup_session_cache()

     # Start the gateway session watcher for real-time SSE updates
     try:
         from api.gateway_watcher import start_watcher
         start_watcher()
     except Exception as e:
         print(f'[!!] WARNING: Gateway watcher failed to start: {e}', flush=True)

     # Start background cron session cleanup (every hour)
     def cleanup_cron_sessions():
         """Background cleanup of cron sessions only"""
         import time
         from api.config import SESSION_DIR, LOCK
         from api.models import Session
         
         while True:
             try:
                 time.sleep(3600)  # Run every hour
                 
                 cleaned = 0
                 for p in SESSION_DIR.glob("*.json"):
                     # Only clean sessions that start with cron or _cron
                     if not (p.stem.startswith('cron') or p.stem.startswith('_cron')):
                         continue
                         
                     try:
                         s = Session.load(p.stem)
                         if not s:
                             continue
                             
                         # Always delete cron/_cron sessions regardless of content
                         with LOCK:
                             SESSIONS.pop(p.stem, None)
                         p.unlink(missing_ok=True)
                         cleaned += 1
                     except Exception:
                         # Skip problematic files
                         continue
                         
                 # Rebuild index to remove cleaned sessions
                 try:
                     from api.models import _rebuild_session_index
                     _rebuild_session_index()
                 except Exception:
                     pass
                     
                 if cleaned > 0:
                     logger.info(f"Cleaned up {cron} cron/_cron sessions")
                     print(f'[ok] Cleaned up {cleaned} cron/_cron sessions', flush=True)
                     
             except Exception as e:
                 logger.error(f"Error in cron session cleanup: {e}")
                 # Continue the loop even if there's an error
                 continue

     # Start cleanup thread as daemon so it doesn't block shutdown
     cleanup_thread = threading.Thread(target=cleanup_cron_sessions, daemon=True)
     cleanup_thread.start()
     logger.info("Started cron session cleanup background thread")

     httpd = QuietHTTPServer((HOST, PORT), Handler)

    # ── TLS/HTTPS setup (optional) ─────────────────────────────────────────
    from api.config import TLS_ENABLED, TLS_CERT, TLS_KEY
    scheme = 'https' if TLS_ENABLED else 'http'
    if TLS_ENABLED:
        try:
            import ssl
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.load_cert_chain(TLS_CERT, TLS_KEY)
            httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
            print(f'  TLS enabled: cert={TLS_CERT}, key={TLS_KEY}', flush=True)
        except Exception as e:
            print(f'[!!] WARNING: TLS setup failed ({e}), falling back to HTTP', flush=True)
            scheme = 'http'

    print(f'  Hermes Web UI listening on {scheme}://{HOST}:{PORT}', flush=True)
    if HOST == '127.0.0.1' or within_container:
        print(f'  Remote access: ssh -N -L {PORT}:127.0.0.1:{PORT} <user>@<your-server>', flush=True)
        print(f'               Then open: {scheme}://localhost:{PORT}', flush=True)
    print('', flush=True)
    try:
        httpd.serve_forever()
    finally:
        # Stop the gateway watcher on shutdown
        try:
            from api.gateway_watcher import stop_watcher
            stop_watcher()
        except Exception:
            logger.debug("Failed to stop gateway watcher during shutdown")

if __name__ == '__main__':
    main()
