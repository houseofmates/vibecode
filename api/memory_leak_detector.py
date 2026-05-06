"""
Advanced memory leak detection and prevention system.
Monitors memory usage patterns, detects leaks, and provides automatic cleanup.
"""
import gc
import time
import threading
import logging
import psutil
import tracemalloc
import weakref
from typing import Dict, List, Any, Optional, Callable, Set
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import inspect

logger = logging.getLogger(__name__)

@dataclass
class MemorySnapshot:
    """Snapshot of memory usage at a point in time."""
    timestamp: float
    process_memory_mb: float
    system_memory_mb: float
    gc_objects: int
    gc_collections: int
    tracked_objects: int
    untracked_objects: int

@dataclass
class LeakReport:
    """Report of potential memory leak."""
    detection_time: float
    leak_type: str
    severity: str  # low, medium, high, critical
    description: str
    object_counts: Dict[str, int]
    memory_increase_mb: float
    growth_rate_mb_per_hour: float
    recommendations: List[str]

class MemoryLeakDetector:
    """Advanced memory leak detection with real-time monitoring."""
    
    def __init__(self, check_interval: float = 60.0, history_size: int = 100):
        self.check_interval = check_interval
        self.history_size = history_size
        
        # Monitoring state
        self.snapshots: deque = deque(maxlen=history_size)
        self.object_trackers: Dict[str, weakref.WeakSet] = defaultdict(weakref.WeakSet)
        self.custom_trackers: List[Callable] = []
        
        # Leak detection thresholds
        self.thresholds = {
            'memory_growth_rate': 10.0,  # MB per hour
            'object_growth_rate': 1000,  # objects per hour
            'gc_efficiency_threshold': 0.3,  # GC should free at least 30%
            'memory_leak_threshold': 100.0,  # MB increase considered leak
            'object_leak_threshold': 10000  # Object increase considered leak
        }
        
        # Statistics
        self.stats = {
            'total_checks': 0,
            'leaks_detected': 0,
            'auto_cleanups': 0,
            'memory_peak': 0.0,
            'object_peak': 0
        }
        
        # Background monitoring
        self.running = False
        self.monitor_thread = None
        self.gc_thread = None
        
        # Leak patterns
        self.leak_patterns: List[LeakReport] = []
        self.object_growth: Dict[str, List[int]] = defaultdict(list)
        
        # Enable tracemalloc if available
        try:
            tracemalloc.start()
            self.tracemalloc_enabled = True
            logger.info("Tracemalloc enabled for detailed memory tracking")
        except Exception as e:
            self.tracemalloc_enabled = False
            logger.warning(f"Tracemalloc not available: {e}")
        
        logger.info("Memory leak detector initialized")
    
    def start_monitoring(self):
        """Start memory leak detection."""
        if self.running:
            return
        
        self.running = True
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self.monitor_thread.start()
        
        # Start GC optimization thread
        self.gc_thread = threading.Thread(target=self._gc_worker, daemon=True)
        self.gc_thread.start()
        
        # Enable GC debugging
        gc.set_debug(gc.DEBUG_STATS)
        
        # Take initial snapshot
        self._take_snapshot()
        
        logger.info("Memory leak monitoring started")
    
    def stop_monitoring(self):
        """Stop memory leak detection."""
        self.running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        if self.gc_thread and self.gc_thread.is_alive():
            self.gc_thread.join(timeout=5.0)
        
        # Disable GC debugging
        gc.set_debug(0)
        
        logger.info("Memory leak monitoring stopped")
    
    def track_object(self, category: str, obj: Any):
        """Track an object for leak detection."""
        self.object_trackers[category].add(obj)
    
    def track_object_creation(self, category: str = "general"):
        """Decorator to track object creation."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                if result is not None:
                    self.track_object(category, result)
                return result
            return wrapper
        return decorator
    
    def add_custom_tracker(self, tracker_func: Callable):
        """Add custom memory tracking function."""
        self.custom_trackers.append(tracker_func)
    
    def _monitoring_worker(self):
        """Background worker for memory monitoring."""
        while self.running:
            try:
                self._take_snapshot()
                self._analyze_memory_trends()
                self._detect_leaks()
                self._cleanup_if_needed()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                time.sleep(10.0)
    
    def _gc_worker(self):
        """Background worker for optimized garbage collection."""
        while self.running:
            try:
                # Get current GC stats
                gc_stats = gc.get_stats()
                
                # Run optimized collection
                gc.collect()
                
                # Check collection efficiency
                new_stats = gc.get_stats()
                collected = new_stats['collected'] - gc_stats['collected']
                uncollectable = new_stats['uncollectable']
                
                if collected > 0:
                    logger.debug(f"GC collected {collected} objects, {uncollectable} uncollectable")
                
                time.sleep(30.0)  # Run GC every 30 seconds
                
            except Exception as e:
                logger.error(f"GC worker error: {e}")
                time.sleep(60.0)
    
    def _take_snapshot(self):
        """Take a memory snapshot."""
        try:
            # Process memory
            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024 * 1024)  # MB
            
            # System memory
            system_memory = psutil.virtual_memory().used / (1024 * 1024)  # MB
            
            # GC statistics
            gc_stats = gc.get_stats()
            gc_objects = sum(gc_stats.get(f'generation{i}', {}).get('objects', 0) for i in range(3))
            gc_collections = sum(gc_stats.get(f'generation{i}', {}).get('collections', 0) for i in range(3))
            
            # Tracked objects
            tracked_objects = sum(len(tracker) for tracker in self.object_trackers.values())
            
            # Estimate untracked objects
            total_objects = len(gc.get_objects())
            untracked_objects = total_objects - tracked_objects
            
            snapshot = MemorySnapshot(
                timestamp=time.time(),
                process_memory_mb=process_memory,
                system_memory_mb=system_memory,
                gc_objects=gc_objects,
                gc_collections=gc_collections,
                tracked_objects=tracked_objects,
                untracked_objects=untracked_objects
            )
            
            self.snapshots.append(snapshot)
            
            # Update peaks
            self.stats['memory_peak'] = max(self.stats['memory_peak'], process_memory)
            self.stats['object_peak'] = max(self.stats['object_peak'], total_objects)
            
        except Exception as e:
            logger.error(f"Snapshot error: {e}")
    
    def _analyze_memory_trends(self):
        """Analyze memory usage trends."""
        if len(self.snapshots) < 3:
            return
        
        recent = list(self.snapshots)[-3:]  # Last 3 snapshots
        
        # Calculate growth rates
        if len(recent) >= 2:
            time_diff = recent[-1].timestamp - recent[0].timestamp
            if time_diff > 0:
                memory_growth = (recent[-1].process_memory_mb - recent[0].process_memory_mb)
                memory_growth_rate = (memory_growth / time_diff) * 3600  # MB per hour
                
                object_growth = (recent[-1].gc_objects - recent[0].gc_objects)
                object_growth_rate = (object_growth / time_diff) * 3600  # Objects per hour
                
                # Track growth by category
                for category, tracker in self.object_trackers.items():
                    self.object_growth[category].append(len(tracker))
                
                # Check if growth is concerning
                if memory_growth_rate > self.thresholds['memory_growth_rate']:
                    logger.warning(f"High memory growth rate: {memory_growth_rate:.1f} MB/hour")
                
                if object_growth_rate > self.thresholds['object_growth_rate']:
                    logger.warning(f"High object growth rate: {object_growth_rate:.0f} objects/hour")
    
    def _detect_leaks(self):
        """Detect potential memory leaks."""
        if len(self.snapshots) < 5:
            return
        
        # Get recent snapshots for analysis
        recent = list(self.snapshots)[-5:]
        oldest = recent[0]
        newest = recent[-1]
        
        time_diff = newest.timestamp - oldest.timestamp
        if time_diff <= 0:
            return
        
        # Memory leak detection
        memory_increase = newest.process_memory_mb - oldest.process_memory_mb
        memory_growth_rate = (memory_increase / time_diff) * 3600  # MB per hour
        
        if memory_increase > self.thresholds['memory_leak_threshold']:
            severity = 'critical' if memory_growth_rate > 50 else 'high'
            leak_report = LeakReport(
                detection_time=time.time(),
                leak_type='memory',
                severity=severity,
                description=f"Memory increased by {memory_increase:.1f} MB over {time_diff/60:.1f} minutes",
                object_counts={},
                memory_increase_mb=memory_increase,
                growth_rate_mb_per_hour=memory_growth_rate,
                recommendations=[
                    "Check for circular references",
                    "Review object lifecycle management",
                    "Consider using weak references",
                    "Profile memory allocation patterns"
                ]
            )
            self._report_leak(leak_report)
        
        # Object leak detection
        object_increase = newest.gc_objects - oldest.gc_objects
        object_growth_rate = (object_increase / time_diff) * 3600  # Objects per hour
        
        if object_increase > self.thresholds['object_leak_threshold']:
            severity = 'critical' if object_growth_rate > 5000 else 'high'
            
            # Find growing object categories
            growing_categories = {}
            for category, counts in self.object_growth.items():
                if len(counts) >= 2:
                    growth = counts[-1] - counts[0]
                    if growth > 0:
                        growing_categories[category] = growth
            
            leak_report = LeakReport(
                detection_time=time.time(),
                leak_type='object',
                severity=severity,
                description=f"Objects increased by {object_increase} over {time_diff/60:.1f} minutes",
                object_counts=growing_categories,
                memory_increase_mb=memory_increase,
                growth_rate_mb_per_hour=memory_growth_rate,
                recommendations=[
                    "Check for unreleased event listeners",
                    "Review closure variable capture",
                    "Check for cached references",
                    "Use profiling tools to identify sources"
                ]
            )
            self._report_leak(leak_report)
        
        # GC efficiency check
        if len(recent) >= 2:
            gc_efficiency = self._calculate_gc_efficiency(recent)
            if gc_efficiency < self.thresholds['gc_efficiency_threshold']:
                leak_report = LeakReport(
                    detection_time=time.time(),
                    leak_type='gc_efficiency',
                    severity='medium',
                    description=f"GC efficiency low: {gc_efficiency:.1%}",
                    object_counts={},
                    memory_increase_mb=0,
                    growth_rate_mb_per_hour=0,
                    recommendations=[
                        "Check for object resurrection",
                        "Review finalizer methods",
                        "Consider manual object cleanup",
                        "Profile object allocation patterns"
                    ]
                )
                self._report_leak(leak_report)
    
    def _calculate_gc_efficiency(self, snapshots: List[MemorySnapshot]) -> float:
        """Calculate garbage collection efficiency."""
        if len(snapshots) < 2:
            return 1.0
        
        total_objects_before = sum(s.gc_objects for s in snapshots[:-1])
        total_objects_after = snapshots[-1].gc_objects
        total_collections = sum(s.gc_collections for s in snapshots)
        
        if total_collections == 0:
            return 1.0
        
        # Estimate objects freed by GC
        objects_freed = max(0, total_objects_before - total_objects_after)
        efficiency = objects_freed / total_objects_before if total_objects_before > 0 else 1.0
        
        return efficiency
    
    def _cleanup_if_needed(self):
        """Perform automatic cleanup if needed."""
        try:
            # Get current memory usage
            current_snapshot = self.snapshots[-1] if self.snapshots else None
            if not current_snapshot:
                return
            
            # Check if memory usage is high
            if current_snapshot.process_memory_mb > 500:  # 500MB threshold
                logger.info("High memory usage detected, performing cleanup")
                
                # Force garbage collection
                collected = gc.collect()
                
                # Clear caches if available
                self._clear_caches()
                
                # Clear old snapshots
                if len(self.snapshots) > self.history_size // 2:
                    excess = len(self.snapshots) - self.history_size // 2
                    for _ in range(excess):
                        self.snapshots.popleft()
                
                self.stats['auto_cleanups'] += 1
                logger.info(f"Automatic cleanup completed, collected {collected} objects")
        
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def _clear_caches(self):
        """Clear common caches to free memory."""
        # Clear object trackers
        for tracker in self.object_trackers.values():
            tracker.clear()
        
        # Clear growth history
        for category in self.object_growth:
            self.object_growth[category] = self.object_growth[category][-10:]  # Keep last 10
        
        # Custom cleanup functions
        for tracker_func in self.custom_trackers:
            try:
                tracker_func()
            except Exception as e:
                logger.error(f"Custom tracker cleanup error: {e}")
    
    def _report_leak(self, leak_report: LeakReport):
        """Report a detected memory leak."""
        self.leak_patterns.append(leak_report)
        self.stats['leaks_detected'] += 1
        
        logger.warning(f"Memory leak detected - {leak_report.leak_type}: {leak_report.description}")
        
        # Trigger alerts if severity is high
        if leak_report.severity in ['high', 'critical']:
            self._trigger_leak_alert(leak_report)
    
    def _trigger_leak_alert(self, leak_report: LeakReport):
        """Trigger alert for serious memory leaks."""
        alert_data = {
            'type': 'memory_leak',
            'severity': leak_report.severity,
            'description': leak_report.description,
            'memory_increase': leak_report.memory_increase_mb,
            'growth_rate': leak_report.growth_rate_mb_per_hour,
            'recommendations': leak_report.recommendations
        }
        
        # In real implementation, this would trigger alerts
        logger.critical(f"MEMORY LEAK ALERT: {alert_data}")
    
    def force_memory_analysis(self):
        """Force detailed memory analysis."""
        if not self.tracemalloc_enabled:
            logger.warning("Tracemalloc not enabled, cannot perform detailed analysis")
            return
        
        try:
            # Get tracemalloc statistics
            current, peak = tracemalloc.get_traced_memory()
            snapshot = tracemalloc.take_snapshot()
            
            # Get top memory allocations
            top_stats = snapshot.statistics('lineno')
            
            logger.info("Memory Analysis Results:")
            logger.info(f"  Current memory: {current / (1024*1024):.1f} MB")
            logger.info(f"  Peak memory: {peak / (1024*1024):.1f} MB")
            logger.info(f"  Traced allocations: {len(snapshot.traces)}")
            
            # Show top 10 allocations
            logger.info("  Top 10 memory allocations:")
            for i, stat in enumerate(top_stats[:10], 1):
                logger.info(f"    {i}. {stat.traceback.format()}: {stat.size / 1024:.1f} KB")
            
            return {
                'current_memory_mb': current / (1024*1024),
                'peak_memory_mb': peak / (1024*1024),
                'traced_allocations': len(snapshot.traces),
                'top_allocations': [
                    {
                        'location': stat.traceback.format(),
                        'size_kb': stat.size / 1024,
                        'count': stat.count
                    } for stat in top_stats[:10]
                ]
            }
            
        except Exception as e:
            logger.error(f"Memory analysis error: {e}")
            return None
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report."""
        if not self.snapshots:
            return {'message': 'No memory data available'}
        
        current = self.snapshots[-1]
        
        # Calculate trends
        if len(self.snapshots) >= 2:
            previous = self.snapshots[-2]
            memory_change = current.process_memory_mb - previous.process_memory_mb
            object_change = current.gc_objects - previous.gc_objects
        else:
            memory_change = 0
            object_change = 0
        
        return {
            'current_memory_mb': current.process_memory_mb,
            'system_memory_mb': current.system_memory_mb,
            'gc_objects': current.gc_objects,
            'tracked_objects': current.tracked_objects,
            'untracked_objects': current.untracked_objects,
            'memory_change_mb': memory_change,
            'object_change': object_change,
            'memory_peak_mb': self.stats['memory_peak'],
            'object_peak': self.stats['object_peak'],
            'total_checks': self.stats['total_checks'],
            'leaks_detected': self.stats['leaks_detected'],
            'auto_cleanups': self.stats['auto_cleanups'],
            'leak_reports': [
                {
                    'type': report.leak_type,
                    'severity': report.severity,
                    'description': report.description,
                    'memory_increase_mb': report.memory_increase_mb,
                    'growth_rate_mb_per_hour': report.growth_rate_mb_per_hour,
                    'recommendations': report.recommendations
                } for report in self.leak_patterns[-5:]  # Last 5 reports
            ],
            'object_trackers': {
                category: len(tracker) 
                for category, tracker in self.object_trackers.items()
            },
            'object_growth_trends': {
                category: {
                    'current': counts[-1] if counts else 0,
                    'growth': counts[-1] - counts[0] if len(counts) >= 2 else 0,
                    'trend': 'increasing' if len(counts) >= 2 and counts[-1] > counts[0] else 'stable'
                } for category, counts in self.object_growth.items()
            }
        }

# Global memory leak detector
_memory_detector: Optional[MemoryLeakDetector] = None

def initialize_memory_detector(check_interval: float = 60.0, history_size: int = 100):
    """Initialize global memory leak detector."""
    global _memory_detector
    _memory_detector = MemoryLeakDetector(check_interval, history_size)
    _memory_detector.start_monitoring()
    logger.info("Global memory leak detector initialized")

def track_object(category: str, obj: Any):
    """Track object through global detector."""
    if _memory_detector:
        _memory_detector.track_object(category, obj)

def track_object_creation(category: str = "general"):
    """Decorator for tracking object creation."""
    if not _memory_detector:
        def decorator(func):
            return func
        return _memory_detector.track_object_creation(category)

def add_memory_tracker(tracker_func: Callable):
    """Add custom memory tracker."""
    if _memory_detector:
        _memory_detector.add_custom_tracker(tracker_func)

def get_memory_report() -> Dict[str, Any]:
    """Get memory report through global detector."""
    if _memory_detector:
        return _memory_detector.get_memory_report()
    return {}

def force_memory_analysis():
    """Force memory analysis through global detector."""
    if _memory_detector:
        return _memory_detector.force_memory_analysis()
    return None

def stop_memory_monitoring():
    """Stop memory monitoring."""
    if _memory_detector:
        _memory_detector.stop_monitoring()