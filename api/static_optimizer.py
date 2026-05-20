"""
Advanced static asset optimization with compression, minification, and HTTP caching.
Optimizes delivery of CSS, JS, and other static resources.
"""
import os
import gzip
import brotli
import hashlib
import mimetypes
import time
import logging
from pathlib import Path
from typing import Any, Dict, Tuple, Optional, List
import re

logger = logging.getLogger(__name__)

class StaticOptimizer:
    """Optimizes static assets with compression and intelligent caching."""
    
    def __init__(self, static_dir: str, cache_dir: str = None):
        self.static_dir = Path(static_dir)
        self.cache_dir = Path(cache_dir or static_dir) / '.optimized'
        self.cache_dir.mkdir(exist_ok=True)
        
        # Compression settings
        self.compression_enabled = True
        self.brotli_enabled = True
        self.minify_enabled = True
        
        # File type settings
        self.compressible_types = {
            'text/css', 'text/javascript', 'application/javascript',
            'application/json', 'text/html', 'text/xml',
            'application/xml', 'text/plain'
        }
        
        self.minifiable_extensions = {
            '.css', '.js', '.html', '.json', '.xml', '.svg'
        }
        
        # Cache headers
        self.max_age = {
            'default': 3600,  # 1 hour
            'immutable': 31536000,  # 1 year for hashed files
            'short': 300  # 5 minutes for dynamic content
        }
        
        # Preload critical assets
        self.critical_assets = [
            'style.css', 'custom.css', 'boot.js', 'messages.js'
        ]
        
        logger.info(f"Static optimizer initialized for {static_dir}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Get content hash for cache invalidation."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()[:16]
    
    def _minify_css(self, content: str) -> str:
        """Simple CSS minification."""
        if not self.minify_enabled:
            return content
        
        # Remove comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r';\s*}', '}', content)
        content = re.sub(r'{\s*', '{', content)
        content = re.sub(r';\s*', ';', content)
        content = re.sub(r'\s*([{}:;,])\s*', r'\1', content)
        
        return content.strip()
    
    def _minify_js(self, content: str) -> str:
        """Simple JavaScript minification."""
        if not self.minify_enabled:
            return content
        
        # Remove single-line comments (but preserve // in strings)
        content = re.sub(r'//.*?(?=["\']|$)', '', content)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove whitespace around operators
        content = re.sub(r'\s*([=+\-*/%<>!&|,;:{}()[\]])\s*', r'\1', content)
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
    
    def _compress_content(self, content: bytes, encoding: str = 'gzip') -> bytes:
        """Compress content with specified encoding."""
        if encoding == 'gzip':
            return gzip.compress(content, compresslevel=6)
        elif encoding == 'br' and self.brotli_enabled:
            return brotli.compress(content, quality=6)
        return content
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type for file."""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or 'application/octet-stream'
    
    def _should_compress(self, mime_type: str) -> bool:
        """Check if content should be compressed."""
        return mime_type in self.compressible_types
    
    def _get_cache_headers(self, file_path: Path, file_hash: str = None) -> Dict[str, str]:
        """Generate appropriate cache headers."""
        headers = {}
        
        # Check if file has hash in name (immutable)
        is_immutable = file_hash and any(
            file_hash in part for part in file_path.name.split('.')
        )
        
        if is_immutable:
            headers['Cache-Control'] = f"public, max-age={self.max_age['immutable']}, immutable"
        else:
            headers['Cache-Control'] = f"public, max-age={self.max_age['default']}"
        
        # Add ETag
        if file_hash:
            headers['ETag'] = f'"{file_hash}"'
        
        return headers
    
    def get_optimized_asset(self, relative_path: str, accept_encoding: str = '') -> Tuple[bytes, Dict[str, str]]:
        """Get optimized asset with compression and headers."""
        file_path = self.static_dir / relative_path
        
        if not file_path.exists():
            return None, {'Content-Type': 'text/plain'}
        
        # Get file info
        file_hash = self._get_file_hash(file_path)
        mime_type = self._get_mime_type(file_path)
        
        # Check cache
        cache_key = f"{relative_path}:{file_hash}:{accept_encoding}"
        cache_file = self.cache_dir / cache_key.replace('/', '_')
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    data = f.read()
                # Split headers and content
                header_end = data.find(b'\n\n')
                if header_end > 0:
                    headers_text = data[:header_end].decode('utf-8')
                    content = data[header_end + 2:]
                    headers = dict(line.split(': ', 1) for line in headers_text.split('\n') if line)
                    return content, headers
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        # Read and process original content
        with open(file_path, 'rb') as f:
            original_content = f.read()
        
        content = original_content
        headers = self._get_cache_headers(file_path, file_hash)
        headers['Content-Type'] = mime_type
        
        # Minify if applicable
        if file_path.suffix in self.minifiable_extensions:
            try:
                if file_path.suffix == '.css':
                    content = self._minify_css(content.decode('utf-8')).encode('utf-8')
                elif file_path.suffix in ['.js', '.mjs']:
                    content = self._minify_js(content.decode('utf-8')).encode('utf-8')
            except Exception as e:
                logger.warning(f"Minification error for {file_path}: {e}")
                content = original_content
        
        # Compress if applicable
        if self._should_compress(mime_type) and self.compression_enabled:
            # Parse Accept-Encoding header
            preferred_encoding = 'none'
            if accept_encoding:
                encodings = [e.strip().split(';')[0] for e in accept_encoding.split(',')]
                if 'br' in encodings and self.brotli_enabled:
                    preferred_encoding = 'br'
                elif 'gzip' in encodings:
                    preferred_encoding = 'gzip'
            
            if preferred_encoding != 'none':
                compressed_content = self._compress_content(content, preferred_encoding)
                # Only use compression if it's smaller
                if len(compressed_content) < len(content) * 0.95:
                    content = compressed_content
                    headers['Content-Encoding'] = preferred_encoding
                    headers['Vary'] = 'Accept-Encoding'
        
        headers['Content-Length'] = str(len(content))
        headers['X-Content-Hash'] = file_hash
        
        # Add optimization info
        if file_path.suffix in self.minifiable_extensions and self.minify_enabled:
            headers['X-Minified'] = 'true'
        
        if self._should_compress(mime_type) and 'Content-Encoding' in headers:
            headers['X-Compressed'] = 'true'
        
        # Cache the optimized version
        try:
            headers_text = '\n'.join(f"{k}: {v}" for k, v in headers.items())
            cache_data = headers_text.encode('utf-8') + b'\n\n' + content
            with open(cache_file, 'wb') as f:
                f.write(cache_data)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
        
        return content, headers
    
    def get_critical_css_inlined(self) -> str:
        """Get critical CSS for inlining."""
        critical_css = []
        for asset in self.critical_assets:
            if asset.endswith('.css'):
                content, _ = self.get_optimized_asset(asset)
                if content:
                    critical_css.append(content.decode('utf-8'))
        
        return '\n'.join(critical_css)
    
    def get_preload_links(self) -> List[str]:
        """Generate preload link tags for critical assets."""
        links = []
        for asset in self.critical_assets:
            file_path = self.static_dir / asset
            if file_path.exists():
                file_hash = self._get_file_hash(file_path)
                mime_type = self._get_mime_type(file_path)
                
                if 'css' in mime_type:
                    links.append(f'<link rel="preload" href="/static/{asset}?v={file_hash}" as="style">')
                elif 'javascript' in mime_type:
                    links.append(f'<link rel="preload" href="/static/{asset}?v={file_hash}" as="script">')
        
        return links
    
    def clear_cache(self):
        """Clear optimization cache."""
        try:
            for cache_file in self.cache_dir.glob('*'):
                cache_file.unlink()
            logger.info("Static optimization cache cleared")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        stats = {
            'cache_enabled': True,
            'compression_enabled': self.compression_enabled,
            'brotli_enabled': self.brotli_enabled,
            'minify_enabled': self.minify_enabled,
            'cache_files': len(list(self.cache_dir.glob('*')))
        }
        
        # Calculate cache size
        try:
            cache_size = sum(f.stat().st_size for f in self.cache_dir.glob('*'))
            stats['cache_size_mb'] = round(cache_size / (1024 * 1024), 2)
        except (OSError, IOError):
            stats['cache_size_mb'] = 0
        
        return stats

# Global optimizer instance
_optimizer: Optional[StaticOptimizer] = None

def initialize_optimizer(static_dir: str, cache_dir: str = None):
    """Initialize global static optimizer."""
    global _optimizer
    _optimizer = StaticOptimizer(static_dir, cache_dir)
    logger.info("Static optimizer initialized")

def get_optimized_asset(relative_path: str, accept_encoding: str = '') -> Tuple[bytes, Dict[str, str]]:
    """Get optimized asset through global optimizer."""
    if not _optimizer:
        raise RuntimeError("Static optimizer not initialized")
    return _optimizer.get_optimized_asset(relative_path, accept_encoding)

def get_preload_links() -> List[str]:
    """Get preload links for critical assets."""
    if _optimizer:
        return _optimizer.get_preload_links()
    return []

def clear_static_cache():
    """Clear static optimization cache."""
    if _optimizer:
        _optimizer.clear_cache()

def get_optimizer_stats() -> Dict[str, Any]:
    """Get optimizer statistics."""
    if _optimizer:
        return _optimizer.get_stats()
    return {}