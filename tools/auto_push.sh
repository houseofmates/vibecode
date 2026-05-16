#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d .git ]; then
  echo "ERROR: this script must be run from inside a git repository." >&2
  exit 1
fi

GIT_SYNC_REMOTE="${GIT_SYNC_REMOTE:-}"
if [ -z "$GIT_SYNC_REMOTE" ]; then
  if git remote | grep -qx upstream; then
    GIT_SYNC_REMOTE="upstream"
  elif git remote | grep -qx origin; then
    GIT_SYNC_REMOTE="origin"
  else
    echo "ERROR: no git remote named 'upstream' or 'origin' found. set GIT_SYNC_REMOTE." >&2
    exit 1
  fi
fi

GIT_SYNC_BRANCH="${GIT_SYNC_BRANCH:-main}"
DEBOUNCE_SECONDS="${DEBOUNCE_SECONDS:-10}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"

if ! git config user.email >/dev/null 2>&1 || [ -z "$(git config --get user.email)" ]; then
  echo "ERROR: git user.email is not configured. run 'git config --global user.email \"you@example.com\"'." >&2
  exit 1
fi
if ! git config user.name >/dev/null 2>&1 || [ -z "$(git config --get user.name)" ]; then
  echo "ERROR: git user.name is not configured. run 'git config --global user.name \"your name\"'." >&2
  exit 1
fi

ensure_main_branch() {
  if ! git show-ref --verify --quiet "refs/heads/$GIT_SYNC_BRANCH"; then
    if git show-ref --verify --quiet refs/heads/master; then
      echo "renaming local master to $GIT_SYNC_BRANCH"
      git branch -m master "$GIT_SYNC_BRANCH"
    else
      echo "creating local branch $GIT_SYNC_BRANCH"
      git checkout -b "$GIT_SYNC_BRANCH"
    fi
  fi

  if [ "$(git symbolic-ref --short HEAD)" != "$GIT_SYNC_BRANCH" ]; then
    git checkout "$GIT_SYNC_BRANCH"
  fi
}

ensure_main_branch

if git config branch."$GIT_SYNC_BRANCH".remote >/dev/null 2>&1; then
  true
else
  git branch --set-upstream-to "$GIT_SYNC_REMOTE/$GIT_SYNC_BRANCH" "$GIT_SYNC_BRANCH" >/dev/null 2>&1 || true
fi

git fetch "$GIT_SYNC_REMOTE" "$GIT_SYNC_BRANCH" >/dev/null 2>&1 || true

auto_sync() {
  echo "syncing changes into ${GIT_SYNC_REMOTE}/${GIT_SYNC_BRANCH}"
  git fetch "$GIT_SYNC_REMOTE" "$GIT_SYNC_BRANCH" >/dev/null 2>&1 || true

  if [ -n "$(git status --porcelain)" ]; then
    echo "detected local changes, staging and committing"
    git add -A
    git commit -m "auto-save: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  else
    echo "no local changes to commit"
  fi

  if git show-ref --verify --quiet "refs/remotes/$GIT_SYNC_REMOTE/$GIT_SYNC_BRANCH"; then
    if git merge --ff-only "$GIT_SYNC_REMOTE/$GIT_SYNC_BRANCH" >/dev/null 2>&1; then
      echo "fast-forwarded remote changes"
    else
      echo "merging remote changes into local $GIT_SYNC_BRANCH"
      if git merge --no-edit "$GIT_SYNC_REMOTE/$GIT_SYNC_BRANCH" >/dev/null 2>&1; then
        echo "merge completed"
      else
        echo "merge conflict detected, aborting merge and leaving branch in a safe state" >&2
        git merge --abort >/dev/null 2>&1 || true
        return 1
      fi
    fi
  fi

  if git push "$GIT_SYNC_REMOTE" "$GIT_SYNC_BRANCH"; then
    echo "push successful"
  else
    echo "warning: push failed, will retry on the next sync" >&2
  fi
}

watch_pattern='(^./\.git|./dist|./appimage-build/apt/lists|./node_modules|./\.playwright-mcp)'

if command -v inotifywait >/dev/null 2>&1; then
  echo "watching repository with inotifywait; changes must remain stable for $DEBOUNCE_SECONDS seconds"
  while true; do
    inotifywait -r -e modify,create,delete,move --exclude "$watch_pattern" "$REPO_ROOT" >/dev/null 2>&1
    echo "change detected, waiting $DEBOUNCE_SECONDS seconds for stability"
    while inotifywait -r -e modify,create,delete,move --exclude "$watch_pattern" --timeout "$DEBOUNCE_SECONDS" "$REPO_ROOT" >/dev/null 2>&1; do
      echo "additional changes detected, resetting stability timer"
    done
    auto_sync
  done
else
  echo "inotifywait not available, falling back to polling every $POLL_INTERVAL seconds"
  last_checksum=""
  while true; do
    checksum=$(find . -path './.git' -prune -o -path './dist' -prune -o -path './appimage-build/apt/lists' -prune -o -path './node_modules' -prune -o -path './.playwright-mcp' -prune -o -type f -print0 | sort -z | xargs -0 sha1sum | sha1sum | awk '{print $1}')
    if [ "$checksum" != "$last_checksum" ]; then
      echo "change detected, waiting $DEBOUNCE_SECONDS seconds for stability"
      sleep "$DEBOUNCE_SECONDS"
      checksum2=$(find . -path './.git' -prune -o -path './dist' -prune -o -path './appimage-build/apt/lists' -prune -o -path './node_modules' -prune -o -path './.playwright-mcp' -prune -o -type f -print0 | sort -z | xargs -0 sha1sum | sha1sum | awk '{print $1}')
      if [ "$checksum2" = "$checksum" ]; then
        auto_sync
        last_checksum="$checksum2"
      else
        last_checksum="$checksum2"
      fi
    fi
    sleep "$POLL_INTERVAL"
  done
fi
