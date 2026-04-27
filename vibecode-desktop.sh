#!/bin/bash
# VibeCode Desktop - Opens remote VibeCode in a dedicated browser window
# This connects to the existing server at 192.168.4.233:8786

REMOTE_URL="http://192.168.4.233:8786"

echo "[vibecode] Opening VibeCode Desktop..."
echo "[vibecode] Connecting to: $REMOTE_URL"

# Check if server is reachable
if ! curl -s "$REMOTE_URL" > /dev/null 2>&1; then
    echo "[vibecode] ERROR: Cannot connect to $REMOTE_URL"
    echo "[vibecode] Make sure the server is running on 192.168.4.233"
    exit 1
fi

# Open in browser with app-like appearance (no toolbars)
if command -v google-chrome >/dev/null 2>&1; then
    google-chrome --app="$REMOTE_URL" --window-size=1400,900 &
elif command -v chromium >/dev/null 2>&1; then
    chromium --app="$REMOTE_URL" --window-size=1400,900 &
elif command -v firefox >/dev/null 2>&1; then
    firefox --kiosk "$REMOTE_URL" &
else
    xdg-open "$REMOTE_URL"
fi

echo "[vibecode] VibeCode Desktop opened!"
