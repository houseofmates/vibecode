#!/bin/bash

# Remote Access Setup Script for Hermes WebUI
# This script helps set up remote access for APK usage

echo "=== Hermes WebUI Remote Access Setup ==="
echo

# Get current local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "Local IP: $LOCAL_IP"

# Check if ngrok is available
if command -v ngrok &> /dev/null; then
    echo "ngrok found - setting up tunnel..."
    
    # Kill existing ngrok processes
    pkill -f ngrok 2>/dev/null
    
    # Start ngrok tunnel
    ngrok http 8786 --log=stdout &
    NGROK_PID=$!
    
    echo "Waiting for ngrok to establish tunnel..."
    sleep 10
    
    # Get the public URL from ngrok API
    NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o '"public_url":"[^"]*' | cut -d'"' -f4)
    
    if [ ! -z "$NGROK_URL" ]; then
        echo "✅ Ngrok tunnel established!"
        echo "Public URL: $NGROK_URL"
        echo ""
        echo "To use this in APK:"
        echo "1. Open Hermes WebUI APK"
        echo "2. Go to Settings"
        echo "3. Enter this URL in server field: $NGROK_URL"
        echo ""
        echo "Tunnel will remain active as long as this script runs."
        echo "Press Ctrl+C to stop"
        
        # Keep script running
        trap "echo 'Stopping ngrok...'; kill $NGROK_PID 2>/dev/null; exit" INT
        wait $NGROK_PID
    else
        echo "❌ Failed to get ngrok URL"
        exit 1
    fi
else
    echo "❌ ngrok not found"
    echo ""
    echo "Install ngrok with: npm install -g ngrok"
    echo ""
    echo "Alternative options:"
    echo "1. Router port forwarding (forward port 8786 to $LOCAL_IP)"
    echo "2. SSH reverse tunnel: ssh -R 8786:localhost:8786 user@your-server.com"
fi
