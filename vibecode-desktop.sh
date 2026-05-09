#!/bin/bash
# vibecode Desktop - Opens remote vibecode in a dedicated browser window
# This connects to the existing server at $HERMES_WEBUI_HOST:8786

REMOTE_URL="http://${HERMES_WEBUI_HOST:-${POPOS_IP:-127.0.0.1}}:8786"

echo "[vibecode] Opening vibecode Desktop..."
echo "[vibecode] Connecting to: $REMOTE_URL"

# Check if server is reachable
if ! curl -s "$REMOTE_URL" > /dev/null 2>&1; then
    echo "[vibecode] ERROR: Cannot connect to $REMOTE_URL"
    echo "[vibecode] Make sure the server is running on $HERMES_WEBUI_HOST"
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

echo "[vibecode] vibecode Desktop opened!"
