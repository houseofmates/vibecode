#!/bin/bash
# Stop the vibecode background server

PID_FILE="${HOME}/.vibecode-server.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        kill "$PID"
        echo "vibecode server stopped (PID: $PID)"
    else
        echo "vibecode server not running"
    fi
    rm -f "$PID_FILE"
else
    echo "vibecode server not running"
fi
