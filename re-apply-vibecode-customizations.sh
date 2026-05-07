#!/usr/bin/env bash
# re-apply-vibecode-customizations.sh
# Idempotent script to verify and re-apply vibecode customizations on shared files.
# Safe to run multiple times. Run after any git merge or pull.
# Usage: bash re-apply-vibecode-customizations.sh

set -euo pipefail
cd "$(dirname "$0")"

echo "=== vibecode customization verifier ==="

# 1. Checks all vibecode-only files exist
echo "--- Checking vibecode-only files ---"
missing=0
declare -a VIBECODE_FILES=(
    "api/swarm.py"
    "api/wiki_memory_api.py"
    "api/wiki_memory_api_enhanced.py"
    "api/_wiki_memory_handlers.py"
    "api/jwt_auth.py"
    "api/security.py"
    "api/structured_logging.py"
    "api/metrics_dashboard.py"
    "api/http2_optimizer.py"
    "api/importance_calc.py"
    "api/websocket_manager.py"
    "api/sudo_password.py"
    "api/version_manager.py"
    "static/swarm.js"
    "static/swarm.css"
    "static/swarm-input.js"
    "static/swarm-input.css"
    "static/swarm-icon.svg"
    "static/canvas.js"
    "static/canvas.css"
    "static/enhancedWikiMemoryPanel.js"
    "static/custom.css"
    "static/mobile.css"
    "src-tauri/Cargo.toml"
    "src-tauri/src/lib.rs"
    "src-tauri/src/main.rs"
    "src-tauri/tauri.conf.json"
    "vibecode.service"
    "start-server.sh"
    "stop-server.sh"
)

for f in "${VIBECODE_FILES[@]}"; do
    if [ ! -f "$f" ]; then
        echo "MISSING: $f"
        missing=$((missing + 1))
    fi
done
echo "$missing vibecode-only files missing"

# 2. Check server.py has vibecode features
echo "--- Checking server.py features ---"
SERVER_MISSING=0
grep -q "do_OPTIONS" server.py || { echo "MISSING: CORS do_OPTIONS handler in server.py"; SERVER_MISSING=$((SERVER_MISSING+1)); }
grep -q "warmup\|session_warm" server.py || { echo "MISSING: session warmup in server.py"; SERVER_MISSING=$((SERVER_MISSING+1)); }
grep -q "_start_cron_session_cleanup\|cron.*_session" server.py || { echo "MISSING: cron session cleanup in server.py"; SERVER_MISSING=$((SERVER_MISSING+1)); }
grep -q "rfile.read" server.py || { echo "MISSING: POST body pre-read (rfile.read) in server.py"; SERVER_MISSING=$((SERVER_MISSING+1)); }
grep -q "listen(128)\|request_queue_size\|socketserver.TCPServer" server.py || { echo "MISSING: request queue size in server.py"; SERVER_MISSING=$((SERVER_MISSING+1)); }
echo "$SERVER_MISSING server.py features missing"

# 3. Check routes.py has vibecode imports
echo "--- Checking routes.py imports ---"
ROUTES_MISSING=0
grep -q "from api.swarm import" api/routes.py || { echo "MISSING: swarm import in routes.py"; ROUTES_MISSING=$((ROUTES_MISSING+1)); }
grep -q "from api.wiki_memory_api import" api/routes.py || { echo "MISSING: wiki_memory_api import in routes.py"; ROUTES_MISSING=$((ROUTES_MISSING+1)); }
grep -q "from api._wiki_memory_handlers import" api/routes.py || { echo "MISSING: _wiki_memory_handlers import in routes.py"; ROUTES_MISSING=$((ROUTES_MISSING+1)); }
grep -q "from api.sudo_password import" api/routes.py || { echo "MISSING: sudo_password import in routes.py"; ROUTES_MISSING=$((ROUTES_MISSING+1)); }
echo "$ROUTES_MISSING routes.py imports missing"

# 4. Check routes.py has vibecode route handlers
echo "--- Checking routes.py route handlers ---"
ROUTE_MISSING=0
grep -q "/api/swarm/list" api/routes.py || { echo "MISSING: /api/swarm/list route"; ROUTE_MISSING=$((ROUTE_MISSING+1)); }
grep -q "/api/swarm/status" api/routes.py || { echo "MISSING: /api/swarm/status route"; ROUTE_MISSING=$((ROUTE_MISSING+1)); }
grep -q "/api/swarm/templates" api/routes.py || { echo "MISSING: /api/swarm/templates route"; ROUTE_MISSING=$((ROUTE_MISSING+1)); }
grep -q "wiki-memory-api\|wiki_memory" api/routes.py || { echo "MISSING: wiki-memory-api routes"; ROUTE_MISSING=$((ROUTE_MISSING+1)); }
grep -q "sudo_password" api/routes.py || { echo "MISSING: sudo_password routes"; ROUTE_MISSING=$((ROUTE_MISSING+1)); }
echo "$ROUTE_MISSING route handlers missing"

# 5. Syntax check all Python files
echo "--- Syntax checking all Python files ---"
SYNTAX_ERRORS=0
while IFS= read -r f; do
    if ! python3 -m py_compile "$f" 2>/dev/null; then
        echo "SYNTAX ERROR: $f"
        SYNTAX_ERRORS=$((SYNTAX_ERRORS+1))
    fi
done < <(find api -name '*.py')
python3 -m py_compile server.py 2>/dev/null || { echo "SYNTAX ERROR: server.py"; SYNTAX_ERRORS=$((SYNTAX_ERRORS+1)); }
echo "$SYNTAX_ERRORS syntax errors"

# 6. Check for conflict markers
echo "--- Checking for merge conflict markers ---"
CONFLICT_MARKERS=$(grep -rlE '^<{7}|^={7}|^>{7}' --include='*.py' . 2>/dev/null || true)
if [ -n "$CONFLICT_MARKERS" ]; then
    echo "CONFLICT MARKERS FOUND in:"
    echo "$CONFLICT_MARKERS"
    CONFLICT=1
else
    echo "No conflict markers found"
    CONFLICT=0
fi

# 7. Summary
echo ""
echo "=== Summary ==="
echo "Missing vibecode-only files:  $missing"
echo "Missing server.py features:   $SERVER_MISSING"
echo "Missing routes.py imports:    $ROUTES_MISSING"
echo "Missing route handlers:       $ROUTE_MISSING"
echo "Python syntax errors:         $SYNTAX_ERRORS"
echo "Merge conflict markers:       $CONFLICT"
echo ""

TOTAL=$((missing + SERVER_MISSING + ROUTES_MISSING + ROUTE_MISSING + SYNTAX_ERRORS + CONFLICT))
if [ "$TOTAL" -eq 0 ]; then
    echo "ALL CUSTOMIZATIONS INTACT AND VALID"
    exit 0
else
    echo "WARNING: $TOTAL issues found. Review above."
    exit 1
fi