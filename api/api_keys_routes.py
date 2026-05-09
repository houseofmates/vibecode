# -*- coding: utf-8 -*-
"""
API Keys Management routes for vibecode
Handles NVIDIA API key rotation via SSH to .250 machine
"""
import json
import os
import yaml
from typing import List, Dict, Any, Optional

# Import the SSH client from enhanced_wiki_memory_routes
try:
    from api.enhanced_wiki_memory_routes import MemsterClient, MEMSTER_HOST, MEMSTER_USER, SSH_KEY_PATH
except ImportError:
    from enhanced_wiki_memory_routes import MemsterClient, MEMSTER_HOST, MEMSTER_USER, SSH_KEY_PATH

# Path to Hermes config on .250
HERMES_CONFIG_PATH = os.environ.get('HERMES_CONFIG_PATH', f"{os.environ.get('DEFAULT_HOME', os.path.expanduser('~'))}/.hermes/config.yaml")

class ApiKeysManager:
    """Manager for NVIDIA API keys via SSH to .250"""
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Fetch Hermes config from .250 machine"""
        try:
            ssh = MemsterClient._get_ssh()
            cmd = f'cat {HERMES_CONFIG_PATH} 2>/dev/null || echo "{{}}"'
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            
            if err:
                return {'error': f"Remote error: {err}"}
            
            if not out:
                return {}
            
            return yaml.safe_load(out) or {}
        except Exception as e:
            error_str = str(e)
            # Check if this is an SSH connection error from our improved handling
            if "SSH authentication failed" in error_str or "SSH connection failed" in error_str or "Failed to connect" in error_str:
                return {'error': error_str}
            return {'error': f"Failed to fetch config: {error_str}"}
    
    @classmethod
    def save_config(cls, config: Dict[str, Any]) -> tuple[bool, str]:
        """Save Hermes config to .250 machine. Returns (success, error_message)."""
        try:
            ssh = MemsterClient._get_ssh()
            yaml_content = yaml.dump(config, default_flow_style=False, allow_unicode=True)
            # Use base64 to avoid escaping issues
            import base64
            encoded = base64.b64encode(yaml_content.encode()).decode()
            cmd = f'echo "{encoded}" | base64 -d > {HERMES_CONFIG_PATH}'
            stdin, stdout, stderr = ssh.exec_command(cmd)
            err = stderr.read().decode().strip()
            
            if err:
                return False, f"Remote error: {err}"
            return True, ""
        except Exception as e:
            error_str = str(e)
            if "SSH authentication failed" in error_str or "SSH connection failed" in error_str or "Failed to connect" in error_str:
                return False, error_str
            return False, f"Failed to save config: {error_str}"
    
    @classmethod
    def get_api_keys(cls) -> List[Dict[str, Any]]:
        """Get API keys from config (NVIDIA and KiloCode)"""
        config = cls.get_config()
        
        if 'error' in config:
            return []
        
        # API keys are typically in config.nvidia.api_keys or similar
        # Try different common paths
        keys = []
        
        # Check for nvidia-specific config
        nvidia_config = config.get('nvidia', {})
        if isinstance(nvidia_config, dict):
            api_keys = nvidia_config.get('api_keys', [])
            if isinstance(api_keys, list):
                for i, key in enumerate(api_keys):
                    keys.append({
                        'id': f'nvidia_{i}',
                        'key': key,
                        'provider': 'nvidia',
                        'index': i
                    })
        
        # Check for kilocode-specific config
        kilocode_config = config.get('kilocode', {})
        if isinstance(kilocode_config, dict):
            api_key = kilocode_config.get('api_key', '')
            if api_key:
                keys.append({
                    'id': 'kilocode_0',
                    'key': api_key,
                    'provider': 'kilocode',
                    'index': 0
                })
        
        # Also check generic api_keys section
        generic_keys = config.get('api_keys', [])
        if isinstance(generic_keys, list):
            for i, key_obj in enumerate(generic_keys):
                if isinstance(key_obj, dict):
                    keys.append({
                        'id': key_obj.get('id', f'key_{i}'),
                        'key': key_obj.get('key', ''),
                        'provider': key_obj.get('provider', 'unknown'),
                        'index': i
                    })
                elif isinstance(key_obj, str):
                    keys.append({
                        'id': f'key_{i}',
                        'key': key_obj,
                        'provider': 'unknown',
                        'index': i
                    })
        
        return keys
    
    @classmethod
    def add_api_key(cls, key: str, provider: str = 'nvidia') -> bool:
        """Add a new API key to config"""
        config = cls.get_config()
        
        if 'error' in config:
            return False
        
        if provider == 'kilocode':
            # Initialize kilocode section if needed
            if 'kilocode' not in config:
                config['kilocode'] = {}
            
            kilocode_config = config['kilocode']
            if not isinstance(kilocode_config, dict):
                config['kilocode'] = {}
                kilocode_config = config['kilocode']
            
            kilocode_config['api_key'] = key
            success, _ = cls.save_config(config)
            return success
        
        # Initialize nvidia section if needed
        if 'nvidia' not in config:
            config['nvidia'] = {}
        
        nvidia_config = config['nvidia']
        if not isinstance(nvidia_config, dict):
            config['nvidia'] = {}
            nvidia_config = config['nvidia']
        
        if 'api_keys' not in nvidia_config:
            nvidia_config['api_keys'] = []
        
        nvidia_config['api_keys'].append(key)
        
        success, _ = cls.save_config(config)
        return success
    
    @classmethod
    def remove_api_key(cls, index: int, provider: str = 'nvidia') -> bool:
        """Remove an API key by index"""
        config = cls.get_config()
        
        if 'error' in config:
            return False
        
        if provider == 'kilocode':
            kilocode_config = config.get('kilocode', {})
            if isinstance(kilocode_config, dict) and 'api_key' in kilocode_config:
                del kilocode_config['api_key']
                success, _ = cls.save_config(config)
                return success
            return False
        
        nvidia_config = config.get('nvidia', {})
        if not isinstance(nvidia_config, dict):
            return False
        
        api_keys = nvidia_config.get('api_keys', [])
        if not isinstance(api_keys, list) or index >= len(api_keys):
            return False
        
        api_keys.pop(index)
        success, _ = cls.save_config(config)
        return success
    
    @classmethod
    def reorder_api_keys(cls, new_order: List[int]) -> bool:
        """Reorder API keys based on new index order"""
        config = cls.get_config()
        
        if 'error' in config:
            return False
        
        nvidia_config = config.get('nvidia', {})
        if not isinstance(nvidia_config, dict):
            return False
        
        api_keys = nvidia_config.get('api_keys', [])
        if not isinstance(api_keys, list):
            return False
        
        # Reorder based on new indices
        reordered = [api_keys[i] for i in new_order if i < len(api_keys)]
        nvidia_config['api_keys'] = reordered
        
        success, _ = cls.save_config(config)
        return success
    
    @classmethod
    def rotate_api_key(cls) -> Optional[str]:
        """Rotate to next API key and return it"""
        config = cls.get_config()
        
        if 'error' in config:
            return None
        
        nvidia_config = config.get('nvidia', {})
        if not isinstance(nvidia_config, dict):
            return None
        
        api_keys = nvidia_config.get('api_keys', [])
        if not isinstance(api_keys) or len(api_keys) == 0:
            return None
        
        # Get current index
        current_index = nvidia_config.get('current_key_index', 0)
        
        # Rotate to next
        next_index = (current_index + 1) % len(api_keys)
        nvidia_config['current_key_index'] = next_index
        
        # Also set as active API key
        nvidia_config['api_key'] = api_keys[next_index]
        
        success, _ = cls.save_config(config)
        if success:
            return api_keys[next_index]
        return None


# Route handlers for Flask/FastAPI integration
def get_api_keys_route():
    """Handler for GET /api/apikeys"""
    keys = ApiKeysManager.get_api_keys()
    return {'ok': True, 'keys': keys, 'count': len(keys)}

def add_api_key_route(key: str, provider: str = 'nvidia'):
    """Handler for POST /api/apikeys"""
    success = ApiKeysManager.add_api_key(key, provider)
    if success:
        return {'ok': True, 'message': 'API key added'}
    return {'ok': False, 'error': 'Failed to add API key'}, 500

def remove_api_key_route(index: int):
    """Handler for DELETE /api/apikeys/{index}"""
    success = ApiKeysManager.remove_api_key(index)
    if success:
        return {'ok': True, 'message': 'API key removed'}
    return {'ok': False, 'error': 'Failed to remove API key'}, 500

def reorder_api_keys_route(new_order: List[int]):
    """Handler for POST /api/apikeys/reorder"""
    success = ApiKeysManager.reorder_api_keys(new_order)
    if success:
        return {'ok': True, 'message': 'API keys reordered'}
    return {'ok': False, 'error': 'Failed to reorder API keys'}, 500

def rotate_api_key_route():
    """Handler for POST /api/apikeys/rotate"""
    new_key = ApiKeysManager.rotate_api_key()
    if new_key:
        return {'ok': True, 'key': new_key[:8] + '...', 'message': 'Rotated to next API key'}
    return {'ok': False, 'error': 'Failed to rotate API key'}, 500

def get_config_route():
    """Handler for GET /api/config"""
    config = ApiKeysManager.get_config()
    if 'error' in config:
        return {'ok': False, 'error': config['error']}, 500
    return {'ok': True, 'config': config}

def save_config_route(config: Dict[str, Any]):
    """Handler for POST /api/config"""
    success, error_msg = ApiKeysManager.save_config(config)
    if success:
        return {'ok': True, 'message': 'Config saved'}
    return {'ok': False, 'error': error_msg or 'Failed to save config'}, 500


# Flask route registration - add this to your main app.py
def register_api_keys_routes(app):
    """Register all API keys and config routes on the Flask app"""
    from flask import request, jsonify
    
    @app.route('/api/config', methods=['GET'])
    def api_config_get():
        """Get Hermes config from .250"""
        result = get_config_route()
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    
    @app.route('/api/config', methods=['POST'])
    def api_config_save():
        """Save Hermes config to .250"""
        data = request.get_json() or {}
        config = data.get('config', {})
        result = save_config_route(config)
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    
    @app.route('/api/apikeys', methods=['GET'])
    def api_apikeys_list():
        """List NVIDIA API keys"""
        return jsonify(get_api_keys_route())
    
    @app.route('/api/apikeys', methods=['POST'])
    def api_apikeys_add():
        """Add new API key"""
        data = request.get_json() or {}
        key = data.get('key', '')
        provider = data.get('provider', 'nvidia')
        result = add_api_key_route(key, provider)
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    
    @app.route('/api/apikeys/<int:index>', methods=['DELETE'])
    def api_apikeys_delete(index):
        """Remove API key by index"""
        result = remove_api_key_route(index)
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    
    @app.route('/api/apikeys/reorder', methods=['POST'])
    def api_apikeys_reorder():
        """Reorder API keys"""
        data = request.get_json() or {}
        new_order = data.get('order', [])
        result = reorder_api_keys_route(new_order)
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    
    @app.route('/api/apikeys/rotate', methods=['POST'])
    def api_apikeys_rotate():
        """Rotate to next API key"""
        result = rotate_api_key_route()
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
