#!/usr/bin/env bash
# setup-cron.sh
# Sets up automatic upstream checking via cron
# Run once to install the cron job

cd "$(dirname "$0")"

CRON_LINE="0 */6 * * * cd $(pwd) && bash sync-vibecode.sh >> vibecode-sync.log 2>&1"
CRON_FILE="/tmp/vibecode-cron-$$"

# Check if already installed
if crontab -l 2>/dev/null | grep -q "sync-vibecode.sh"; then
  echo "Cron job already installed"
else
  # Add to crontab
  (crontab -l 2>/dev/null || true; echo "$CRON_LINE") | crontab -
  echo "Cron job installed: runs sync-vibecode.sh every 6 hours"
fi

echo "Sync will check for upstream changes, AI-filter them, and auto-merge if safe"
echo "Logs go to vibecode-sync.log"