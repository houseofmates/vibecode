"""
Hermes Web UI -- Terminal API with PTY support.
Provides WebSocket-like terminal sessions via SSE/POST.
"""
import json
import logging
import os
import pty
import queue
import select
import struct
import fcntl
import termios
import signal
import threading
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Active terminal sessions: terminal_id -> TerminalSession
TERMINAL_SESSIONS: Dict[str, 'TerminalSession'] = {}
TERMINAL_LOCK = threading.Lock()


class TerminalSession:
    """Manages a PTY-based terminal session."""

    def __init__(self, session_id: str, cwd: str = None, shell: str = None, ssh_host: str = None):
        self.session_id = session_id
        self.terminal_id = f"term_{int(time.time() * 1000)}_{os.urandom(4).hex()}"
        self.cwd = cwd or os.path.expanduser('~')
        self.shell = shell or os.environ.get('SHELL', '/bin/bash')
        self.ssh_host = ssh_host
        self.name = 'terminal'
        self.created_at = time.time()
        self.last_activity = time.time()

        # PTY file descriptors
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self.pid: Optional[int] = None

        # Output queue for SSE streaming — thread-safe, blocking-capable
        self.output_queue: queue.Queue = queue.Queue(maxsize=10000)
        self.clients: set = set()  # Connected SSE client IDs

        # Terminal dimensions (default 80x24)
        self.cols = 80
        self.rows = 24

        self._spawn_pty()
        self._start_reader_thread()

    def _spawn_pty(self):
        """Spawn a new PTY with the shell process."""
        self.master_fd, self.slave_fd = pty.openpty()

        # Set initial window size BEFORE fork so the shell picks it up
        # (pty.openpty() defaults to 0x0 which breaks line wrapping)
        try:
            size = struct.pack('HHHH', self.rows, self.cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)
        except (OSError, IOError):
            pass

        # Set non-blocking mode on master
        flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Build prompt once — \033 is more portable than \e
        _yellow = '\\[\\033[38;2;246;176;18m\\]'
        _blue   = '\\[\\033[38;2;53;199;255m\\]'
        _reset  = '\\[\\033[0m\\]'
        _ps1    = f'{_yellow}\\u@\\h{_reset}:{_blue}\\w{_reset}\\$ '

        # Fork and execute shell
        self.pid = os.fork()
        if self.pid == 0:
            # Child process
            os.close(self.master_fd)

            # Set up slave as controlling terminal
            os.setsid()
            os.dup2(self.slave_fd, 0)
            os.dup2(self.slave_fd, 1)
            os.dup2(self.slave_fd, 2)

            if self.slave_fd > 2:
                os.close(self.slave_fd)

            # Set working directory
            try:
                os.chdir(self.cwd)
            except OSError:
                os.chdir(os.path.expanduser('~'))

            # Set environment
            env = os.environ.copy()
            env['TERM'] = 'xterm-256color'
            env['COLORTERM'] = 'truecolor'
            env['COLUMNS'] = str(self.cols)
            env['LINES'] = str(self.rows)
            # Force our custom prompt on every render so .bashrc overrides don't win
            env['PS1'] = _ps1
            env['PROMPT_COMMAND'] = f'PS1="{_ps1}"'
            # Prevent /etc/profile.d/vte-2.91.sh from overwriting PROMPT_COMMAND
            env['VTE_VERSION'] = '0'

            # Execute shell (or SSH if ssh_host is set)
            if self.ssh_host:
                shell = '/bin/bash'
                cmd = f"ssh -t {self.ssh_host}"
                os.execve(shell, [shell, '-c', cmd], env)
            else:
                shell = self.shell
                if shell.endswith('bash') or shell.endswith('sh'):
                    os.execve(shell, [shell, '-l'], env)
                else:
                    os.execve(shell, [shell], env)
            os._exit(1)
        else:
            # Parent process
            os.close(self.slave_fd)
            self.slave_fd = None
            logger.info(f"Spawned terminal {self.terminal_id} (pid={self.pid}) in {self.cwd}")

    def _start_reader_thread(self):
        """Start thread to read PTY output. Batches reads for efficiency."""
        def reader():
            while True:
                try:
                    if self.master_fd is None:
                        break

                    # Wait for data with 1s timeout (generous to avoid CPU spin)
                    ready, _, _ = select.select([self.master_fd], [], [], 1.0)
                    if not ready:
                        # Check if process is still alive
                        if self.pid:
                            try:
                                pid, status = os.waitpid(self.pid, os.WNOHANG)
                                if pid != 0:
                                    # Process exited
                                    self.output_queue.put({
                                        'type': 'exit',
                                        'code': os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
                                    })
                                    break
                            except ChildProcessError:
                                break
                        continue

                    # Batch all available output into one queue item
                    chunks = []
                    while True:
                        try:
                            data = os.read(self.master_fd, 16384)
                            if not data:
                                break
                            chunks.append(data.decode('utf-8', errors='replace'))
                            self.last_activity = time.time()
                        except BlockingIOError:
                            break
                        except (OSError, IOError):
                            break

                    if chunks:
                        # Coalesce multiple small reads into one event
                        self.output_queue.put({
                            'type': 'output',
                            'data': ''.join(chunks)
                        })

                except Exception as e:
                    logger.error(f"Terminal reader error: {e}")
                    break

            # Cleanup
            logger.info(f"Terminal reader thread ended for {self.terminal_id}")
            self.close()

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()

    def write(self, data: str) -> bool:
        """Write input to the PTY."""
        if self.master_fd is None:
            return False
        try:
            os.write(self.master_fd, data.encode('utf-8'))
            self.last_activity = time.time()
            return True
        except (OSError, IOError) as e:
            logger.error(f"Write error: {e}")
            return False

    def resize(self, cols: int, rows: int):
        """Resize the terminal."""
        if self.master_fd is None:
            return
        try:
            # TIOCSWINSZ - Set window size
            size = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)
            self.cols = cols
            self.rows = rows
            # Notify the shell process group so it re-reads LINES/COLUMNS
            if self.pid:
                try:
                    pgid = os.getpgid(self.pid)
                    os.killpg(pgid, signal.SIGWINCH)
                except (OSError, ProcessLookupError):
                    try:
                        os.kill(self.pid, signal.SIGWINCH)
                    except (OSError, ProcessLookupError):
                        pass
        except (OSError, IOError) as e:
            logger.error(f"Resize error: {e}")

    def close(self):
        """Close the terminal session."""
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except:
                pass
            self.master_fd = None

        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
                # Give it a moment to terminate
                time.sleep(0.1)
                try:
                    os.kill(self.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            except ProcessLookupError:
                pass
            self.pid = None

        with TERMINAL_LOCK:
            if self.terminal_id in TERMINAL_SESSIONS:
                del TERMINAL_SESSIONS[self.terminal_id]

        logger.info(f"Closed terminal {self.terminal_id}")

    def get_output(self, timeout: float = None) -> Optional[dict]:
        """Get pending output from queue. Blocks up to timeout seconds."""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def add_client(self, client_id: str):
        """Add an SSE client."""
        self.clients.add(client_id)

    def remove_client(self, client_id: str):
        """Remove an SSE client."""
        self.clients.discard(client_id)
        if not self.clients:
            # No more clients, close after timeout
            threading.Timer(30.0, self._check_idle).start()

    def _check_idle(self):
        """Check if terminal should be closed due to inactivity."""
        if not self.clients and time.time() - self.last_activity > 30:
            self.close()

    def rename(self, name: str):
        """Rename the terminal."""
        self.name = name[:32]  # Limit name length


def create_terminal(cwd: str = None, shell: str = None, session_id: str = None, ssh_host: str = None) -> TerminalSession:
    """Create a new terminal session."""
    term = TerminalSession(session_id or 'anonymous', cwd, shell, ssh_host)
    with TERMINAL_LOCK:
        TERMINAL_SESSIONS[term.terminal_id] = term
    return term


def get_terminal(terminal_id: str) -> Optional[TerminalSession]:
    """Get an existing terminal session."""
    with TERMINAL_LOCK:
        return TERMINAL_SESSIONS.get(terminal_id)


def list_terminals(session_id: str = None) -> list:
    """List all terminal sessions."""
    with TERMINAL_LOCK:
        terms = list(TERMINAL_SESSIONS.values())
        if session_id:
            terms = [t for t in terms if t.session_id == session_id]
        return [
            {
                'terminal_id': t.terminal_id,
                'name': t.name,
                'cwd': t.cwd,
                'created_at': t.created_at,
                'session_id': t.session_id
            }
            for t in terms
        ]


def close_terminal(terminal_id: str) -> bool:
    """Close a terminal session."""
    term = get_terminal(terminal_id)
    if term:
        term.close()
        return True
    return False


def rename_terminal(terminal_id: str, name: str) -> bool:
    """Rename a terminal session."""
    term = get_terminal(terminal_id)
    if term:
        term.rename(name)
        return True
    return False


# Cleanup old terminals periodically
def _cleanup_task():
    """Background task to cleanup stale terminals."""
    while True:
        time.sleep(60)
        try:
            now = time.time()
            with TERMINAL_LOCK:
                stale = [
                    t for t in TERMINAL_SESSIONS.values()
                    if not t.clients and now - t.last_activity > 300  # 5 minutes
                ]
            for t in stale:
                logger.info(f"Cleaning up stale terminal {t.terminal_id}")
                t.close()
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")


# Start cleanup thread
_cleanup_thread = threading.Thread(target=_cleanup_task, daemon=True)
_cleanup_thread.start()
