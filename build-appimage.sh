#!/bin/bash
# Build VibeCode AppImage (portable Python runtime)
set -e

echo "=== VibeCode AppImage Builder ==="
echo "Target: releases/vibecode.appimage"
echo "URL: http://192.168.4.233:8786"
echo ""
echo "Note: This AppImage runs from local or remote codebase."
echo "Code changes will be reflected on app restart."
echo ""

# Check for appimagetool
if ! command -v appimagetool &> /dev/null; then
    echo "ERROR: appimagetool not found!"
    echo ""
    echo "Install it with:"
    echo "  wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    echo "  chmod +x appimagetool-x86_64.AppImage"
    echo "  sudo mv appimagetool-x86_64.AppImage /usr/local/bin/appimagetool"
    exit 1
fi

# Create releases directory
mkdir -p releases

# Clean old builds
echo "[1/4] Cleaning old builds..."
rm -f releases/vibecode.appimage releases/vibecode-x86_64.AppImage *.AppImage

# Ensure AppDir is properly set up
echo "[2/4] Setting up AppDir..."
make check-appdir 2>/dev/null || true

# Build the AppImage
echo "[3/4] Building AppImage (this may take a few minutes)..."
appimagetool AppDir releases/vibecode.appimage

# Check result
echo "[4/4] Finalizing build..."
if [ -f "releases/vibecode.appimage" ]; then
    chmod +x releases/vibecode.appimage

    echo ""
    echo "✓ SUCCESS: Built releases/vibecode.appimage"
    echo ""
    echo "To run:"
    echo "  ./releases/vibecode.appimage"
    echo ""
    echo "To install system-wide:"
    echo "  mkdir -p ~/Applications"
    echo "  cp releases/vibecode.appimage ~/Applications/"
    echo ""
    echo "The app will run from: ~/vibecode (or set VIBECODE_HOME/VIBECODE_GIT)"
    echo "Server URL: http://192.168.4.233:8786"
    echo ""
    echo "Code changes: Edit files in codebase, then restart the app to see changes"
    echo ""
    echo "Remote codebase options:"
    echo "  VIBECODE_HOME=/path/to/mount/remote/dir"
    echo "  VIBECODE_GIT=https://github.com/yourusername/vibecode.git"
else
    echo "ERROR: AppImage not found after build"
    exit 1
fi
