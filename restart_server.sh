#!/bin/bash
# Kill any existing server processes
pkill -9 -f "python.*server.py" 2>/dev/null
sleep 2

# Kill any process using port 8786
fuser -k 8786/tcp 2>/dev/null
sleep 2

# Test server import
cd /home/house/vibecode
python3 -c "import server; print('Import OK')" || exit 1

# Start server in background
HERMES_WEBUI_PORT=8786 nohup python3 server.py >> server.log 2>&1 &
sleep 4

# Test if running
curl -s http://localhost:8786/api/health && echo "Server started successfully" || echo "Failed to start server"
