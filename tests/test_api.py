"""
Hermes Web UI -- API testing framework.
Provides comprehensive testing for API endpoints and functionality.
"""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.config import SESSION_DIR, STATE_DIR
from api.models import Session
from api.security import validate_input, sanitize_filename, check_rate_limit
from api.memory_optimizer import LRUCache
from api.monitoring import MetricsCollector

class TestSecurity(unittest.TestCase):
    """Test security functions."""
    
    def test_validate_input_valid(self):
        """Test valid input validation."""
        valid, msg = validate_input("test_session_123", "session_id")
        self.assertTrue(valid)
        self.assertEqual(msg, "")
    
    def test_validate_input_invalid(self):
        """Test invalid input validation."""
        valid, msg = validate_input("../../../etc/passwd", "session_id")
        self.assertFalse(valid)
        self.assertIn("Invalid", msg)
    
    def test_validate_input_xss(self):
        """Test XSS prevention."""
        valid, msg = validate_input("<script>alert('xss')</script>", "session_id")
        self.assertFalse(valid)
        self.assertIn("dangerous", msg)
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        self.assertEqual(sanitize_filename("../../../test.txt"), "test.txt")
        self.assertEqual(sanitize_filename("test<>.txt"), "test.txt")
        self.assertEqual(sanitize_filename(""), "unnamed")
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        # Reset rate limiter
        identifier = "test_client"
        
        # Should be allowed initially
        allowed, info = check_rate_limit(identifier, 'auth')
        self.assertTrue(allowed)
        
        # Exhaust rate limit
        for _ in range(15):  # More than auth limit
            check_rate_limit(identifier, 'auth')
        
        # Should be limited now
        allowed, info = check_rate_limit(identifier, 'auth')
        self.assertFalse(allowed)
        self.assertIn('retry_after', info)

class TestMemoryOptimizer(unittest.TestCase):
    """Test memory optimization functions."""
    
    def setUp(self):
        """Set up test cache."""
        self.cache = LRUCache(max_size=3, ttl=1)
    
    def test_cache_basic_operations(self):
        """Test basic cache operations."""
        self.cache.set("key1", "value1")
        self.assertEqual(self.cache.get("key1"), "value1")
        self.assertIsNone(self.cache.get("nonexistent"))
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.set("key3", "value3")
        self.cache.set("key4", "value4")  # Should evict key1
        
        self.assertIsNone(self.cache.get("key1"))
        self.assertEqual(self.cache.get("key2"), "value2")
        self.assertEqual(self.cache.get("key3"), "value3")
        self.assertEqual(self.cache.get("key4"), "value4")
    
    def test_cache_ttl_expiration(self):
        """Test TTL expiration."""
        self.cache.set("key1", "value1")
        time.sleep(1.1)  # Wait for TTL to expire
        self.assertIsNone(self.cache.get("key1"))

class TestMonitoring(unittest.TestCase):
    """Test monitoring and metrics."""
    
    def setUp(self):
        """Set up test metrics collector."""
        self.metrics = MetricsCollector()
    
    def test_request_recording(self):
        """Test request metric recording."""
        self.metrics.record_request("/api/test", 0.5, 200)
        self.metrics.record_request("/api/test", 0.3, 200)
        self.metrics.record_request("/api/test", 1.0, 500)
        
        summary = self.metrics.get_summary()
        self.assertEqual(summary['performance']['total_requests'], 3)
        self.assertGreater(summary['performance']['avg_response_time'], 0)
    
    def test_error_recording(self):
        """Test error recording."""
        self.metrics.record_error("test_error", "Test error message", {"context": "test"})
        
        summary = self.metrics.get_summary()
        self.assertIn("test_error", summary['top_errors'])
    
    def test_health_status(self):
        """Test health status calculation."""
        # Healthy status
        health = self.metrics.get_health_status()
        self.assertEqual(health['status'], 'healthy')
        
        # Add some errors to trigger degraded status
        for _ in range(20):
            self.metrics.record_error("test_error", "Test error")
        
        health = self.metrics.get_health_status()
        self.assertIn(health['status'], ['degraded', 'critical'])

class TestSessionModel(unittest.TestCase):
    """Test session model functionality."""
    
    def setUp(self):
        """Set up temporary session directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_session_dir = SESSION_DIR
        os.environ['HERMES_WEBUI_SESSION_DIR'] = self.temp_dir
        
        # Update SESSION_DIR path
        import api.config
        api.config.SESSION_DIR = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up temporary session directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        os.environ.pop('HERMES_WEBUI_SESSION_DIR', None)
        
        # Restore original SESSION_DIR
        import api.config
        api.config.SESSION_DIR = self.original_session_dir
    
    def test_session_creation(self):
        """Test session creation and saving."""
        session = Session(
            session_id="test_session",
            title="Test Session",
            messages=[{"role": "user", "content": "test"}]
        )
        
        session.save()
        
        # Verify session was saved
        loaded_session = Session.load("test_session")
        self.assertIsNotNone(loaded_session)
        self.assertEqual(loaded_session.title, "Test Session")
        self.assertEqual(len(loaded_session.messages), 1)
    
    def test_session_validation(self):
        """Test session ID validation."""
        # Valid session ID
        self.assertIsNotNone(Session.load("valid_session_123"))
        
        # Invalid session ID (path traversal)
        self.assertIsNone(Session.load("../../../etc/passwd"))

class TestAPIEndpoints(unittest.TestCase):
    """Test API endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock environment
        os.environ['HERMES_WEBUI_SESSION_DIR'] = self.temp_dir
        os.environ['HERMES_WEBUI_STATE_DIR'] = self.temp_dir
        
        # Import after setting environment
        from api import routes
        self.routes = routes
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        os.environ.pop('HERMES_WEBUI_SESSION_DIR', None)
        os.environ.pop('HERMES_WEBUI_STATE_DIR', None)
    
    def test_session_list_endpoint(self):
        """Test session list endpoint."""
        # Create mock handler
        handler = Mock()
        handler.path = "/api/sessions"
        handler.headers = {}
        handler.client_address = ("127.0.0.1", 12345)
        
        # Test the endpoint
        try:
            result = self.routes.handle_get(handler, handler.path)
            # Should not return False (404)
            self.assertNotEqual(result, False)
        except Exception as e:
            # Expected if not fully mocked
            self.assertIn("mock", str(e).lower())
    
    def test_authentication_check(self):
        """Test authentication functionality."""
        from api.auth import check_auth
        
        # Mock handler and parsed URL
        handler = Mock()
        parsed = Mock()
        parsed.path = "/api/sessions"
        
        # Test without authentication (should work for localhost)
        handler.client_address = ("127.0.0.1", 12345)
        result = check_auth(handler, parsed)
        self.assertTrue(result)

class TestPerformance(unittest.TestCase):
    """Test performance optimizations."""
    
    def test_large_session_handling(self):
        """Test handling of large sessions."""
        # Create session with many messages
        messages = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(1000)
        ]
        
        session = Session(
            session_id="large_session",
            title="Large Session",
            messages=messages
        )
        
        # Test compacting
        compacted = session.compact()
        self.assertEqual(compacted['message_count'], 1000)
        self.assertNotIn('messages', compacted)  # Messages should not be in compacted view
    
    def test_concurrent_access(self):
        """Test concurrent session access."""
        import threading
        
        session = Session(
            session_id="concurrent_session",
            title="Concurrent Session"
        )
        session.save()
        
        results = []
        
        def load_session():
            loaded = Session.load("concurrent_session")
            results.append(loaded is not None)
        
        # Create multiple threads loading the same session
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=load_session)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All loads should succeed
        self.assertTrue(all(results))
        self.assertEqual(len(results), 10)

def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestSecurity,
        TestMemoryOptimizer,
        TestMonitoring,
        TestSessionModel,
        TestAPIEndpoints,
        TestPerformance
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return {
        'tests_run': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    }

if __name__ == '__main__':
    print("Running vibecode API tests...")
    results = run_tests()
    print(f"\nTest Results:")
    print(f"Tests run: {results['tests_run']}")
    print(f"Failures: {results['failures']}")
    print(f"Errors: {results['errors']}")
    print(f"Success rate: {results['success_rate']:.1f}%")