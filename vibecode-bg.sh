#!/bin/bash
# vibecode background server runner
# Runs the vibecode server in the background with nohup

REPO_ROOT="${VIBECODE_HOME:-$(dirname "$(readlink -f "$0")")}"
LOG_FILE="${DEFAULT_HOME:-$HOME}/.vibecode-server.log"
PID_FILE="${DEFAULT_HOME:-$HOME}/.vibecode-server.pid"

cd "$REPO_ROOT" || exit 1

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "vibecode server already running (PID: $PID)"
        echo "http://$HERMES_WEBUI_HOST:8786"
        exit 0
    fi
fi

# Start server in background
nohup python3 server.py > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

echo "vibecode server started (PID: $SERVER_PID)"
echo "http://$HERMES_WEBUI_HOST:8786"
echo "Log: $LOG_FILE"
