#!/usr/bin/env bash
# sync-vibecode.sh
# Amnesia-proof vibecode upstream sync with AI filtering
# Keeps PKM visuals and custom features, discards bad changes

set -euo pipefail
cd "$(dirname "$0")"

# Load .env
if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo ".env file not found - create it with NVIDIA_API_KEY_1, NVIDIA_API_KEY_2, etc."
  exit 1
fi

# Get list of NVIDIA API keys
KEYS=($(env | grep ^NVIDIA_API_KEY_ | sort -V | cut -d= -f2-))
if [ ${#KEYS[@]} -eq 0 ]; then
  echo "No NVIDIA API keys found in .env"
  exit 1
fi

# Round-robin key selection
INDEX_FILE=".nim_key_index"
if [ ! -f "$INDEX_FILE" ]; then
  echo 0 > "$INDEX_FILE"
fi
INDEX=$(cat "$INDEX_FILE")
NEXT_INDEX=$(( (INDEX + 1) % ${#KEYS[@]} ))
echo "$NEXT_INDEX" > "$INDEX_FILE"
API_KEY="${KEYS[$INDEX]}"

echo "=== vibecode AI-sync starting ==="
echo "Using NVIDIA API key $((INDEX + 1)) of ${#KEYS[@]}"

# Backup
BACKUP_BRANCH="vibecode-backup-$(date +%Y%m%d-%H%M%S)"
git branch "$BACKUP_BRANCH"
git tag "backup-$(date +%Y%m%d-%H%M%S)"
echo "Backup created: $BACKUP_BRANCH"

# Fetch upstream
git fetch upstream
UPSTREAM_SHA=$(git rev-parse upstream/master)
LAST_MERGE_FILE=".last_upstream_merge"

if [ -f "$LAST_MERGE_FILE" ]; then
  LAST_MERGE=$(cat "$LAST_MERGE_FILE")
  COMMITS_BEHIND=$(git log --oneline "$LAST_MERGE"..upstream/master 2>/dev/null | wc -l)
  echo "Upstream commits since last sync: $COMMITS_BEHIND"
else
  echo "No previous merge recorded - will sync all"
fi

# Get diff
DIFF_FILE="/tmp/vibecode-diff-$$.patch"
git diff HEAD..upstream/master > "$DIFF_FILE"
DIFF_SIZE=$(stat -f%z "$DIFF_FILE" 2>/dev/null || stat -c%s "$DIFF_FILE" 2>/dev/null || echo "unknown")
echo "Diff size: $DIFF_SIZE bytes"

if [ ! -s "$DIFF_FILE" ]; then
  echo "No changes in upstream - nothing to do"
  rm -f "$DIFF_FILE"
  exit 0
fi

# Call NVIDIA NIM to filter diff
FILTERED_DIFF="/tmp/vibecode-filtered-$$.patch"

echo "Sending diff to NVIDIA NIM for AI filtering..."

# For very large diffs, save diff content to temp file and send via JSON
python3 -c "
import json
import sys

with open('$DIFF_FILE', 'r') as f:
    diff_content = f.read()

payload = {
    'model': 'meta/llama-4-maverick',
    'messages': [
        {
            'role': 'system',
            'content': 'You are a code reviewer for a forked project. Accept ALL new upstream features EXCEPT those that interfere with existing custom features. Keep: new features, improvements, bug fixes from upstream. Reject ONLY: changes that break or remove (1) PKM aesthetic (Varela Round font, lowercase UI text, solid #050505 backgrounds, #f6b012/#3c9fdd colors, no gradients/glows/box-shadows) (2) Custom features: swarm, filesystem sidebar, wiki memory, JWT auth, security modules, custom routes. Output ONLY the filtered git patch in plain text format, nothing else.'
        },
        {
            'role': 'user',
            'content': 'Analyze this git diff and output ONLY the safe changes to keep in git patch format. Discard changes that affect PKM visuals or remove custom features.\n\n' + diff_content[:500000]  # Limit to 500k chars
        }
    ],
    'temperature': 0.1,
    'max_tokens': 32000
}

with open('/tmp/vibecode-request.json', 'w') as f:
    json.dump(payload, f)
print('Request saved to /tmp/vibecode-request.json')
"

curl -s -X POST "https://api.nvidia.com/v1/inference/llm" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/vibecode-request.json > "$FILTERED_DIFF"

# Apply filtered changes if patch is valid
if [ -s "$FILTERED_DIFF" ] && head -1 "$FILTERED_DIFF" | grep -q "^diff\|^From "; then
  echo "Applying AI-filtered changes..."
  git apply "$FILTERED_DIFF" 2>/dev/null || echo "Some patches failed to apply (may be expected)"
else
  echo "No valid filtered patch - skipping changes"
fi

# Re-apply customizations to be safe
echo "Running customization verifier..."
bash re-apply-vibecode-customizations.sh || true

# Commit
if git diff --quiet; then
  echo "No changes to commit"
else
  git add .
  git commit -m "ai-filtered upstream sync: $(date +%Y-%m-%d)
- Kept safe upstream features
- Preserved PKM visuals and custom features"
  echo "Changes committed"
fi

# Record last merge
echo "$UPSTREAM_SHA" > "$LAST_MERGE_FILE"

# Cleanup
rm -f "$DIFF_FILE" "$FILTERED_DIFF"

echo "=== Sync complete ==="
echo "Run 'bash re-apply-vibecode-customizations.sh' if any issues"