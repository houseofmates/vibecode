#!/bin/bash
# Check for and install vibecode updates
# This script can be run manually or via cron

set -e

REPO_OWNER="anomalyco"
REPO_NAME="vibecode"
CURRENT_FILE="${HOME}/Applications/vibecode.appimage"
RELEASES_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/latest"

echo "=== vibecode Update Checker ==="
echo ""

# Check if AppImage is installed
if [ ! -f "$CURRENT_FILE" ]; then
    # Try to find it elsewhere
    CURRENT_FILE=$(find ~ -name "vibecode.appimage" -type f 2>/dev/null | head -1)
    if [ -z "$CURRENT_FILE" ]; then
        echo "vibecode.appimage not found in home directory"
        echo "Download from: $RELEASES_URL"
        exit 1
    fi
fi

echo "Current installation: $CURRENT_FILE"

# Method 1: Using appimageupdatetool (if available)
if command -v appimageupdatetool &> /dev/null; then
    echo "Checking for updates via appimageupdatetool..."
    if appimageupdatetool -j "$CURRENT_FILE" 2>/dev/null | grep -q "update available"; then
        echo "Update available!"
        read -p "Install update now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            appimageupdatetool "$CURRENT_FILE"
            echo "Update complete!"
        fi
    else
        echo "You have the latest version."
    fi
    exit 0
fi

# Method 2: Manual check via GitHub API
echo "Checking for updates via GitHub API..."

# Get latest release info
LATEST_JSON=$(curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/releases/latest")
LATEST_TAG=$(echo "$LATEST_JSON" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
LATEST_URL=$(echo "$LATEST_JSON" | grep '"browser_download_url":.*vibecode.*appimage"' | head -1 | sed -E 's/.*"([^"]+)".*/\1/')

if [ -z "$LATEST_TAG" ]; then
    echo "ERROR: Could not fetch latest release info"
    echo "Check your internet connection or GitHub API rate limits"
    exit 1
fi

echo "Latest release: $LATEST_TAG"

# Extract version from current file (if possible)
# AppImage embeds version info, but we can also check embedded metadata
CURRENT_VERSION=$(strings "$CURRENT_FILE" 2>/dev/null | grep -E "^v[0-9]+\.[0-9]+" | head -1 || echo "unknown")
if [ "$CURRENT_VERSION" = "unknown" ]; then
    # Try to get from file metadata
    CURRENT_VERSION=$(stat -c %y "$CURRENT_FILE" 2>/dev/null | cut -d' ' -f1 || echo "unknown")
fi

echo "Current version: $CURRENT_VERSION"

# Compare versions (simple string comparison)
if [ "$LATEST_TAG" != "$CURRENT_VERSION" ]; then
    echo ""
    echo "Update available: $LATEST_TAG"
    echo ""
    read -p "Download and install update? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -n "$LATEST_URL" ]; then
            echo "Downloading..."
            TEMP_FILE="${CURRENT_FILE}.tmp"
            curl -L -o "$TEMP_FILE" "$LATEST_URL"
            chmod +x "$TEMP_FILE"
            mv "$TEMP_FILE" "$CURRENT_FILE"
            echo "Update complete! Restart vibecode to use the new version."
        else
            echo "Download URL not found. Please download manually from:"
            echo "  $RELEASES_URL"
        fi
    fi
else
    echo "You have the latest version ($LATEST_TAG)"
fi
