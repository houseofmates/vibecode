#!/bin/bash
# Start vibecode server in the background with optimized startup
set -e

VIBECODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
VENV_PYTHON="${VIBECODE_ROOT}/venv/bin/python"
if [ -f "$VENV_PYTHON" ]; then
  PYTHON="$VENV_PYTHON"
else
  PYTHON=python3
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="/tmp/vibecode.pid"
LOGFILE="/tmp/vibecode.log"

# Export environment for ultra-low-latency startup
export HERMES_WEBUI_PORT=8786
export PYTHONUNBUFFERED=1
export PYTHONOPTIMIZE=2
export PYTHONPATH="${VIBECODE_ROOT}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=random
export OMP_NUM_THREADS=4
# Aggressive optimizations for faster startup
export PYTHONASYNCIODEBUG=0
export PYTHONTRACEMALLOC=0
export PYTHONFAULTHANDLER=0
export PYTHONPROFILEIMPORTTIME=0
export PYTHONMALLOC=malloc

# Kill any existing server gracefully
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing server (PID: $OLD_PID)..."
        kill -TERM "$OLD_PID" 2>/dev/null || true
        sleep 2
        # Force kill if still running
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill -KILL "$OLD_PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PIDFILE"
fi

# Also kill any orphaned processes
pkill -f "python.*server.py" 2>/dev/null || true
sleep 1

cd "$SCRIPT_DIR"
echo "Starting vibecode server in background..."
echo "Log file: $LOGFILE"
echo "Port: $HERMES_WEBUI_PORT"

# Start with optimized Python flags and resource limits
ulimit -n 65536 2>/dev/null || true
ulimit -u 4096 2>/dev/null || true

# Health check function
check_server_health() {
    local pid=$1
    local timeout=10
    local count=0
    
    while [ $count -lt $timeout ]; do
        if kill -0 "$pid" 2>/dev/null; then
            # Check if server is responding on port
            if curl -s --max-time 2 "http://127.0.0.1:$HERMES_WEBUI_PORT" >/dev/null 2>&1; then
                echo "Server is healthy and responding"
                return 0
            fi
        else
            echo "Server process died"
            return 1
        fi
        sleep 1
        count=$((count + 1))
    done
    echo "Server health check timed out"
    return 1
}

# Preload critical modules synchronously for faster startup
echo "Preloading modules..."
$PYTHON -c "
import sys
import json
import logging
import threading
import queue
import time
import os
from pathlib import Path
# Preload API modules
sys.path.insert(0, os.environ.get("PYTHONPATH", os.path.dirname(os.path.abspath(__file__))))
try:
    from api import config, helpers, models
    from api.streaming import _get_ai_agent
except ImportError:
    pass
" 2>/dev/null

# Start with ultra-optimized Python flags for fastest startup
$PYTHON -u -OO -X importtime=0 -X pycache_prefix=/tmp/vibecode_pycache server.py > "$LOGFILE" 2>&1 &
NEW_PID=$!
echo $NEW_PID > "$PIDFILE"

# Quick health check
if ! check_server_health $NEW_PID; then
    echo "Warning: Server may not be responding properly"
    echo "Check logs: tail -f $LOGFILE"
fi

echo "Server started with PID: $NEW_PID"
echo ""
echo "Access URL: http://127.0.0.1:$HERMES_WEBUI_PORT"
echo "To view logs: tail -f $LOGFILE"
echo "To stop: ./stop-server.sh"
