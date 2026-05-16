#!/bin/bash
# Alternative: Run server directly and access via browser
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
cd "$SCRIPT_DIR"
./start-server.sh &
echo 'Server started on http://127.0.0.1:8786'
echo 'Access the web UI in your browser'

