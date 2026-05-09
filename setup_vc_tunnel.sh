#!/bin/bash

# Setup reverse tunnel from a remote host to local machine
# This allows a remote client or APK to reach the local server through SSH reverse tunneling

echo "=== Setting up ${VIBECODE_REMOTE_HOST:-remote} Reverse Tunnel ==="
echo

# Local configuration
LOCAL_IP="${HERMES_WEBUI_HOST:-${POPOS_IP:-127.0.0.1}}"
LOCAL_PORT="8786"
REMOTE_SERVER="${VIBECODE_REMOTE_HOST:-localhost}"
REMOTE_USER="${VIBECODE_REMOTE_USER:-$USER}"

echo "Local server: $LOCAL_IP:$LOCAL_PORT"
echo "Remote server: $REMOTE_SERVER"
echo

# Kill existing SSH tunnels to this server
echo "Cleaning up existing tunnels..."
pkill -f "ssh.*-R.*8786.*$REMOTE_SERVER" 2>/dev/null

# Set up reverse tunnel
echo "Establishing reverse tunnel..."
echo "Command: ssh -R 8786:$LOCAL_IP:$LOCAL_PORT $REMOTE_USER@$REMOTE_SERVER"
echo

# Start the tunnel in background
ssh -N -R 8786:$LOCAL_IP:$LOCAL_PORT $REMOTE_USER@$REMOTE_SERVER &
TUNNEL_PID=$!

echo "Tunnel PID: $TUNNEL_PID"
echo

# Wait for tunnel to establish
echo "Waiting for tunnel to establish..."
sleep 5

# Test if tunnel is working
echo "Testing tunnel connection..."
if curl -s --max-time 10 "http://$REMOTE_SERVER/api/sessions" > /dev/null; then
    echo "✅ Tunnel is working!"
    echo ""
    echo "Remote access is now active:"
    echo "APK can connect to: https://${REMOTE_SERVER}"
    echo "Which proxies to: $LOCAL_IP:$LOCAL_PORT"
    echo ""
    echo "Keep this script running to maintain the tunnel."
    echo "Press Ctrl+C to stop the tunnel"
    
    # Keep script running
    trap "echo 'Stopping tunnel...'; kill $TUNNEL_PID 2>/dev/null; echo 'Tunnel stopped'; exit" INT
    
    # Monitor tunnel status
    while true; do
        if ! kill -0 $TUNNEL_PID 2>/dev/null; then
            echo "Tunnel process died, restarting..."
            ssh -N -R 8786:$LOCAL_IP:$LOCAL_PORT $REMOTE_USER@$REMOTE_SERVER &
            TUNNEL_PID=$!
        fi
        sleep 30
    done
else
    echo "❌ Tunnel test failed"
    echo "Please check:"
    echo "1. SSH access to $REMOTE_SERVER works"
    echo "2. Local server is running on $LOCAL_IP:$LOCAL_PORT"
    echo "3. No firewall blocking the connection"
    kill $TUNNEL_PID 2>/dev/null
    exit 1
fi
