#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d .git ]; then
  echo "ERROR: This script must be run from inside a git repository." >&2
  exit 1
fi

GIT_SYNC_REMOTE="${GIT_SYNC_REMOTE:-}"
if [ -z "$GIT_SYNC_REMOTE" ]; then
  if git remote | grep -qx upstream; then
    GIT_SYNC_REMOTE="upstream"
  elif git remote | grep -qx origin; then
    GIT_SYNC_REMOTE="origin"
  else
    echo "ERROR: No git remote named 'upstream' or 'origin' found. Set GIT_SYNC_REMOTE." >&2
    exit 1
  fi
fi

GIT_SYNC_BRANCH="${GIT_SYNC_BRANCH:-master}"
GIT_SYNC_INTERVAL="${GIT_SYNC_INTERVAL:-10}"

if ! git config user.email >/dev/null 2>&1 || [ -z "$(git config --get user.email)" ]; then
  echo "ERROR: git user.email is not configured. Run 'git config --global user.email \"you@example.com\"'." >&2
  exit 1
fi
if ! git config user.name >/dev/null 2>&1 || [ -z "$(git config --get user.name)" ]; then
  echo "ERROR: git user.name is not configured. Run 'git config --global user.name \"Your Name\"'." >&2
  exit 1
fi

echo "Auto-push watcher starting for branch '$GIT_SYNC_BRANCH' -> remote '$GIT_SYNC_REMOTE'"
echo "Polling interval: ${GIT_SYNC_INTERVAL}s"

while true; do
  git fetch "$GIT_SYNC_REMOTE" "$GIT_SYNC_BRANCH" >/dev/null 2>&1 || true

  if [ -n "$(git status --porcelain)" ]; then
    echo "Changes detected: staging and committing..."
    git add -A
    git commit -m "auto-sync: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  else
    echo "No local changes to commit."
  fi

  if git rev-parse --verify "HEAD" >/dev/null 2>&1; then
    echo "Pushing current branch to ${GIT_SYNC_REMOTE}/${GIT_SYNC_BRANCH}..."
    if git push "$GIT_SYNC_REMOTE" "HEAD:${GIT_SYNC_BRANCH}"; then
      echo "Push successful."
    else
      echo "Warning: Push failed. Will retry after sleep." >&2
    fi
  else
    echo "No HEAD reference to push yet."
  fi

  sleep "$GIT_SYNC_INTERVAL"
done
