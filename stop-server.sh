#!/bin/bash
# Stop Hermes Web UI backend
PIDFILE="/tmp/hermes-webui.pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo "Stopping server (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
        sleep 1
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null || true
        fi
        echo "Server stopped."
    else
        echo "Server not running."
    fi
    rm -f "$PIDFILE"
else
    echo "No PID file found. Killing any server.py processes..."
    pkill -f "python.*server.py" 2>/dev/null || true
    echo "Done."
fi
