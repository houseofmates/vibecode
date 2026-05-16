"""
Termisol Terminal Adapter for Vibecode
Provides advanced terminal features by integrating Termisol's capabilities
as a web service that replaces the basic PTY terminal.
"""
import asyncio
import json
import logging
import os
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Active Termisol sessions: session_id -> TermisolSession
TERMISOL_SESSIONS: Dict[str, 'TermisolSession'] = {}
TERMISOL_LOCK = threading.Lock()

@dataclass
class TerminalFeature:
    """Represents a terminal feature capability"""
    name: str
    enabled: bool
    description: str
    category: str

class TermisolSession:
    """Advanced terminal session using Termisol capabilities"""
    
    def __init__(self, session_id: str, cwd: str = None, features: Dict[str, bool] = None):
        self.session_id = session_id
        self.terminal_id = f"termisol_{int(time.time() * 1000)}_{os.urandom(4).hex()}"
        
        # Smart directory detection and device mapping
        self.cwd = self._detect_and_set_directory(cwd)
        self.name = 'Termisol Terminal'
        self.created_at = time.time()
        self.last_activity = time.time()
        
        # Feature flags
        self.features = features or self._get_default_features()
        
        # Termisol process management
        self.termisol_process: Optional[subprocess.Popen] = None
        self.websocket_port: Optional[int] = None
        self.communication_file: Optional[str] = None
        
        # Output queue for SSE streaming
        self.output_queue = asyncio.Queue(maxsize=10000)
        self.clients: set = set()
        
        # Terminal state
        self.cols = 80
        self.rows = 24
        self.connected = False
        
        # Advanced features state
        self.ai_enabled = self.features.get('ai_assistance', True)
        self.quantum_mode = self.features.get('quantum_computing', False)
        self.vr_mode = self.features.get('vr_support', False)
        self.video_playback = self.features.get('video_playback', True)
        self.audio_visualization = self.features.get('audio_visualization', True)
        self._3d_modeling = self.features.get('3d_modeling', True)
        self.git_integration = self.features.get('git_integration', True)
        self.docker_integration = self.features.get('docker_integration', True)
        self.database_client = self.features.get('database_client', True)
        
        self._initialize_termisol()
        self._start_monitor_thread()
    
    def _get_default_features(self) -> Dict[str, bool]:
        """Get default feature set for Termisol terminal"""
        return {
            'ai_assistance': True,
            'quantum_computing': False,
            'vr_support': False,
            'video_playback': True,
            'audio_visualization': True,
            '3d_modeling': True,
            'git_integration': True,
            'docker_integration': True,
            'database_client': True,
            'syntax_highlighting': True,
            'error_detection': True,
            'command_prediction': True,
            'file_manager': True,
            'collaboration': True,
            'session_recording': True,
            'performance_monitoring': True,
            'hotkeys': True,
            'notifications': True,
            'themes': True,
            'plugins': True
        }
    
    def _initialize_termisol(self):
        """Initialize Termisol as a background service"""
        try:
            # Create communication file for IPC
            self.communication_file = tempfile.mktemp(suffix='.termisol_ipc')
            
            # Find Termisol installation
            termisol_path = self._find_termisol_installation()
            if not termisol_path:
                logger.warning("Termisol installation not found, falling back to basic terminal")
                self._fallback_to_basic_terminal()
                return
            
            # Check if Termisol binary exists and is executable
            termisol_binary = os.path.join(termisol_path, 'bin/termisol.dart')
            if not os.path.exists(termisol_binary):
                logger.warning(f"Termisol binary not found at {termisol_binary}, falling back")
                self._fallback_to_basic_terminal()
                return
            
            # Prepare Termisol launch arguments
            cmd = [
                'dart', 'run', 
                termisol_binary,
                '--headless',
                '--websocket-port', '0',  # Auto-assign port
                '--ipc-file', self.communication_file,
                '--session-id', self.session_id,
                '--cwd', self.cwd,
                '--cols', str(self.cols),
                '--rows', str(self.rows)
            ]
            
            # Add feature flags
            if self.ai_enabled:
                cmd.append('--enable-ai')
            if self.quantum_mode:
                cmd.append('--quantum-mode')
            if self.vr_mode:
                cmd.append('--vr-mode')
            if self.video_playback:
                cmd.append('--video-playback')
            if self.audio_visualization:
                cmd.append('--audio-visualization')
            if self._3d_modeling:
                cmd.append('--3d-modeling')
            if self.git_integration:
                cmd.append('--git-integration')
            if self.docker_integration:
                cmd.append('--docker-integration')
            if self.database_client:
                cmd.append('--database-client')
            
            # Start Termisol process
            env = os.environ.copy()
            env['TERMISOL_HEADLESS'] = '1'
            env['TERMISOL_WEBSOCKET_ONLY'] = '1'
            
            try:
                self.termisol_process = subprocess.Popen(
                    cmd,
                    cwd=termisol_path,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    preexec_fn=os.setsid  # Create new process group
                )
            except FileNotFoundError:
                logger.error("Dart not found, cannot run Termisol")
                self._fallback_to_basic_terminal()
                return
            except Exception as e:
                logger.error(f"Failed to start Termisol process: {e}")
                self._fallback_to_basic_terminal()
                return
            
            # Wait for startup and get websocket port
            try:
                self._wait_for_startup()
                logger.info(f"Termisol session {self.terminal_id} started on port {self.websocket_port}")
            except Exception as e:
                logger.error(f"Termisol startup failed: {e}")
                if self.termisol_process:
                    self.termisol_process.terminate()
                    self.termisol_process = None
                self._fallback_to_basic_terminal()
            
        except Exception as e:
            logger.error(f"Failed to initialize Termisol: {e}")
            self._fallback_to_basic_terminal()
    
    def _find_termisol_installation(self) -> Optional[str]:
        """Find Termisol installation path"""
        possible_paths = [
            f"{os.environ.get('DEFAULT_HOME', os.path.expanduser('~'))}/termisol",
            '/opt/termisol',
            os.path.expanduser('~/termisol'),
            './termisol'
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.path.exists(os.path.join(path, 'pubspec.yaml')):
                return path
        
        return None
    
    def _wait_for_startup(self):
        """Wait for Termisol to start and get websocket port"""
        timeout = 30  # 30 seconds timeout
        start_time = time.time()
        check_interval = 0.5  # Check every 500ms
        
        while time.time() - start_time < timeout:
            # Check if process is still running
            if self.termisol_process and self.termisol_process.poll() is not None:
                # Process exited, check for error
                stderr = self.termisol_process.stderr.read() if self.termisol_process.stderr else ""
                stdout = self.termisol_process.stdout.read() if self.termisol_process.stdout else ""
                error_msg = stderr or stdout or "Unknown error"
                raise RuntimeError(f"Termisol process exited: {error_msg}")
            
            # Try to read websocket port from communication file
            if self.communication_file and os.path.exists(self.communication_file):
                try:
                    # Use file locking to prevent race conditions
                    with open(self.communication_file, 'r') as f:
                        content = f.read().strip()
                        if content:
                            data = json.loads(content)
                            if 'websocket_port' in data and data['websocket_port']:
                                self.websocket_port = int(data['websocket_port'])
                                self.connected = True
                                logger.debug(f"Termisol websocket port: {self.websocket_port}")
                                return
                            elif 'error' in data:
                                raise RuntimeError(f"Termisol startup error: {data['error']}")
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.debug(f"Failed to parse communication file: {e}")
                except IOError:
                    # File might be being written to, try again
                    pass
            
            time.sleep(check_interval)
        
        # If we get here, startup failed
        # Try to get any error output from the process
        error_output = ""
        if self.termisol_process:
            if self.termisol_process.poll() is not None:
                stderr = self.termisol_process.stderr.read() if self.termisol_process.stderr else ""
                stdout = self.termisol_process.stdout.read() if self.termisol_process.stdout else ""
                error_output = stderr or stdout or "Process exited without output"
            else:
                # Process is still running but didn't respond in time
                error_output = "Process running but failed to communicate within timeout"
        
        raise TimeoutError(f"Termisol failed to start within {timeout}s: {error_output}")
    
    def _fallback_to_basic_terminal(self):
        """Fallback to basic PTY terminal if Termisol fails"""
        logger.warning("Falling back to basic terminal implementation")
        # Import and use the existing terminal implementation
        from .terminal import TerminalSession as BasicTerminalSession
        
        # Create basic terminal as fallback
        basic_term = BasicTerminalSession(self.session_id, self.cwd)
        self.termisol_process = None  # Mark as not using Termisol
        self.connected = True
        
        # Store basic terminal for delegation
        self._basic_terminal = basic_term
    
    def _start_monitor_thread(self):
        """Start monitoring thread for Termisol process"""
        def monitor():
            while True:
                try:
                    if self.termisol_process and self.termisol_process.poll() is not None:
                        # Process exited
                        logger.warning(f"Termisol process {self.terminal_id} exited")
                        self.connected = False
                        break
                    
                    # Check for communication file updates
                    if self.communication_file and os.path.exists(self.communication_file):
                        self._process_communications()
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Monitor thread error: {e}")
                    break
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def _process_communications(self):
        """Process communications from Termisol via IPC file"""
        if not self.communication_file or not os.path.exists(self.communication_file):
            return
            
        try:
            # Read file with proper error handling
            try:
                with open(self.communication_file, 'r') as f:
                    content = f.read()
            except IOError as e:
                logger.debug(f"Failed to read communication file: {e}")
                return
            
            if not content.strip():
                return
                
            data = json.loads(content)
            
            # Process different message types
            if 'output' in data:
                try:
                    self.output_queue.put_nowait({
                        'type': 'output',
                        'data': data['output'],
                        'timestamp': time.time()
                    })
                except asyncio.QueueFull:
                    logger.warning("Output queue full, dropping message")
                    
            if 'features' in data:
                # Update feature status
                self.features.update(data['features'])
                logger.debug(f"Updated features: {data['features']}")
                
            if 'status' in data:
                # Update terminal status
                status = data['status']
                if status == 'exited':
                    self.output_queue.put_nowait({
                        'type': 'exit',
                        'code': data.get('code', 0),
                        'timestamp': time.time()
                    })
                    self.connected = False
                    logger.info(f"Termisol session {self.terminal_id} exited with code {data.get('code', 0)}")
                elif status == 'error':
                    logger.error(f"Termisol error: {data.get('message', 'Unknown error')}")
                    
            if 'resize' in data:
                # Handle terminal resize acknowledgment
                new_size = data['resize']
                if isinstance(new_size, dict):
                    self.cols = new_size.get('cols', self.cols)
                    self.rows = new_size.get('rows', self.rows)
                    
        except (json.JSONDecodeError, IOError) as e:
            logger.debug(f"Communication processing error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in communications: {e}")
    
    async def write(self, data: str) -> bool:
        """Write input to the terminal"""
        try:
            if self.termisol_process and self.connected:
                # Send to Termisol via IPC
                ipc_data = {
                    'input': data,
                    'timestamp': time.time()
                }
                with open(self.communication_file, 'w') as f:
                    json.dump(ipc_data, f)
                return True
            elif hasattr(self, '_basic_terminal'):
                # Fallback to basic terminal
                return self._basic_terminal.write(data)
            return False
        except Exception as e:
            logger.error(f"Write error: {e}")
            return False
    
    async def resize(self, cols: int, rows: int):
        """Resize the terminal"""
        self.cols = cols
        self.rows = rows
        
        try:
            if self.termisol_process and self.connected:
                # Send resize command to Termisol
                ipc_data = {
                    'resize': {'cols': cols, 'rows': rows},
                    'timestamp': time.time()
                }
                with open(self.communication_file, 'w') as f:
                    json.dump(ipc_data, f)
            elif hasattr(self, '_basic_terminal'):
                # Fallback to basic terminal
                self._basic_terminal.resize(cols, rows)
        except Exception as e:
            logger.error(f"Resize error: {e}")
    
    async def get_output(self, timeout: float = None) -> Optional[dict]:
        """Get pending output from queue"""
        try:
            return await asyncio.wait_for(self.output_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    def get_features(self) -> List[TerminalFeature]:
        """Get list of available features"""
        features = []
        for name, enabled in self.features.items():
            description = self._get_feature_description(name)
            category = self._get_feature_category(name)
            features.append(TerminalFeature(name, enabled, description, category))
        return features
    
    def _get_feature_description(self, feature: str) -> str:
        """Get feature description"""
        descriptions = {
            'ai_assistance': 'AI-powered command suggestions and assistance',
            'quantum_computing': 'Quantum circuit execution and visualization',
            'vr_support': 'Virtual reality terminal interface',
            'video_playback': 'Inline video playback in terminal',
            'audio_visualization': 'Audio spectrum visualization',
            '3d_modeling': '3D model viewing and interaction',
            'git_integration': 'Git operations and version control',
            'docker_integration': 'Docker container management',
            'database_client': 'Database connection management',
            'syntax_highlighting': 'Advanced syntax highlighting',
            'error_detection': 'Automatic error detection and fixes',
            'command_prediction': 'Smart command prediction',
            'file_manager': 'Integrated file manager',
            'collaboration': 'Terminal session collaboration',
            'session_recording': 'Session recording and playback',
            'performance_monitoring': 'Performance metrics and optimization',
            'hotkeys': 'Customizable hotkeys',
            'notifications': 'Native notifications',
            'themes': 'Terminal themes and customization',
            'plugins': 'Plugin ecosystem support'
        }
        return descriptions.get(feature, 'Advanced terminal feature')
    
    def _get_feature_category(self, feature: str) -> str:
        """Get feature category"""
        categories = {
            'ai_assistance': 'AI',
            'quantum_computing': 'Advanced',
            'vr_support': 'Interface',
            'video_playback': 'Media',
            'audio_visualization': 'Media',
            '3d_modeling': 'Media',
            'git_integration': 'Development',
            'docker_integration': 'Development',
            'database_client': 'Development',
            'syntax_highlighting': 'Display',
            'error_detection': 'Productivity',
            'command_prediction': 'Productivity',
            'file_manager': 'Productivity',
            'collaboration': 'Collaboration',
            'session_recording': 'Tools',
            'performance_monitoring': 'Tools',
            'hotkeys': 'Interface',
            'notifications': 'Interface',
            'themes': 'Interface',
            'plugins': 'Extensions'
        }
        return categories.get(feature, 'General')
    
    def _detect_and_set_directory(self, cwd: str = None) -> str:
        """Smart directory detection with device-specific workspace mapping"""
        import socket
        
        # If explicit CWD provided, use it
        if cwd and os.path.exists(cwd):
            return os.path.abspath(cwd)
        
        # Default to home directory when no explicit CWD provided

        return os.environ.get('DEFAULT_HOME', os.path.expanduser('~'))
    
    def enable_feature(self, feature: str, enabled: bool = True):
        """Enable or disable a feature"""
        if feature in self.features:
            self.features[feature] = enabled
            
            # Send feature update to Termisol
            if self.termisol_process and self.connected:
                ipc_data = {
                    'feature_update': {feature: enabled},
                    'timestamp': time.time()
                }
                try:
                    with open(self.communication_file, 'w') as f:
                        json.dump(ipc_data, f)
                except IOError:
                    pass
    
    def add_client(self, client_id: str):
        """Add an SSE client"""
        self.clients.add(client_id)
    
    def remove_client(self, client_id: str):
        """Remove an SSE client"""
        self.clients.discard(client_id)
        if not self.clients:
            # No more clients, schedule cleanup
            threading.Timer(30.0, self._check_idle).start()
    
    def _check_idle(self):
        """Check if session should be closed due to inactivity"""
        if not self.clients and time.time() - self.last_activity > 30:
            self.close()
    
    def close(self):
        """Close the terminal session"""
        self.connected = False
        
        try:
            # Close Termisol process if running
            if self.termisol_process:
                logger.debug(f"Terminating Termisol process {self.termisol_process.pid}")
                
                # Try graceful shutdown first
                try:
                    # Send SIGTERM to process group
                    os.killpg(os.getpgid(self.termisol_process.pid), signal.SIGTERM)
                    self.termisol_process.wait(timeout=5)
                    logger.debug("Termisol process terminated gracefully")
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    # Force kill if graceful shutdown fails
                    try:
                        os.killpg(os.getpgid(self.termisol_process.pid), signal.SIGKILL)
                        self.termisol_process.wait(timeout=2)
                        logger.debug("Termisol process force killed")
                    except (subprocess.TimeoutExpired, ProcessLookupError):
                        logger.warning("Failed to kill Termisol process")
                
                self.termisol_process = None
            
            # Clean up communication file
            if self.communication_file:
                try:
                    if os.path.exists(self.communication_file):
                        os.remove(self.communication_file)
                        logger.debug("Removed communication file")
                except OSError as e:
                    logger.warning(f"Failed to remove communication file: {e}")
                finally:
                    self.communication_file = None
            
            # Close fallback basic terminal if used
            if hasattr(self, '_basic_terminal'):
                try:
                    self._basic_terminal.close()
                except Exception as e:
                    logger.warning(f"Error closing fallback terminal: {e}")
                
        except Exception as e:
            logger.error(f"Error closing Termisol session {self.terminal_id}: {e}")
        
        # Remove from active sessions
        with TERMISOL_LOCK:
            if self.terminal_id in TERMISOL_SESSIONS:
                del TERMISOL_SESSIONS[self.terminal_id]
        
        logger.info(f"Closed Termisol session {self.terminal_id}")

def create_termisol_session(cwd: str = None, features: Dict[str, bool] = None, session_id: str = None) -> TermisolSession:
    """Create a new Termisol terminal session"""
    session = TermisolSession(session_id or 'anonymous', cwd, features)
    with TERMISOL_LOCK:
        TERMISOL_SESSIONS[session.terminal_id] = session
    return session

def get_termisol_session(terminal_id: str) -> Optional[TermisolSession]:
    """Get an existing Termisol session"""
    with TERMISOL_LOCK:
        return TERMISOL_SESSIONS.get(terminal_id)

def list_termisol_sessions(session_id: str = None) -> List[Dict]:
    """List all Termisol sessions"""
    with TERMISOL_LOCK:
        sessions = list(TERMISOL_SESSIONS.values())
        if session_id:
            sessions = [s for s in sessions if s.session_id == session_id]
        return [
            {
                'terminal_id': s.terminal_id,
                'name': s.name,
                'cwd': s.cwd,
                'created_at': s.created_at,
                'session_id': s.session_id,
                'features': s.features,
                'connected': s.connected
            }
            for s in sessions
        ]

def close_termisol_session(terminal_id: str) -> bool:
    """Close a Termisol session"""
    session = get_termisol_session(terminal_id)
    if session:
        session.close()
        return True
    return False

# Cleanup task
def _cleanup_task():
    """Background task to cleanup stale Termisol sessions"""
    while True:
        time.sleep(60)
        try:
            now = time.time()
            with TERMISOL_LOCK:
                stale = [
                    s for s in TERMISOL_SESSIONS.values()
                    if not s.clients and now - s.last_activity > 300  # 5 minutes
                ]
            for session in stale:
                logger.info(f"Cleaning up stale Termisol session {session.terminal_id}")
                session.close()
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")

# Start cleanup thread
_cleanup_thread = threading.Thread(target=_cleanup_task, daemon=True)
_cleanup_thread.start()
