#!/bin/bash
# Build vibecode Tauri Desktop AppImage
set -e

echo "=== vibecode Tauri Desktop Builder ==="
echo "Target: releases/vibecode.appimage"
echo "Using packaged UI assets from ../dist"
echo ""

# Check dependencies
if ! command -v npx &> /dev/null; then
    echo "ERROR: npx not found!"
    echo "Install with: sudo apt install nodejs npm"
    exit 1
fi

if ! command -v cargo &> /dev/null; then
    echo "ERROR: Rust/Cargo not found!"
    echo "Install with: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

if ! command -v appimagetool &> /dev/null; then
    echo "ERROR: appimagetool not found!"
    echo "Install with: sudo apt install appimagetool"
    echo "or from https://appimage.github.io/AppImageKit/#appimagetool"
    exit 1
fi

# Create releases directory
mkdir -p releases

# Prepare frontend assets
./build-tauri-dist.sh

# Build Tauri AppImage
echo "[1/3] Building Tauri AppImage..."
npx tauri build

# Patch GTK backend detection in AppImage hook if needed
APPIMAGE_APPDIR="src-tauri/target/release/bundle/appimage/vibecode.AppDir"
HOOK_FILE="$APPIMAGE_APPDIR/apprun-hooks/linuxdeploy-plugin-gtk.sh"
if [ -f "$HOOK_FILE" ]; then
  echo "[2/3] Patching GTK backend detection in AppImage hook..."
  python3 - "$HOOK_FILE" <<'PY'
import pathlib
import re
import sys
path = pathlib.Path(sys.argv[1])
text = path.read_text()
if 'export GDK_BACKEND=x11' in text:
    print('GDK_BACKEND already set to x11; no patch needed')
    sys.exit(0)
patched = re.sub(r'^export GDK_BACKEND=.*$', 'export GDK_BACKEND=x11 # Crash with Wayland backend on Wayland - We tested it without it and ended up with this: https://github.com/tauri-apps/tauri/issues/8541', text, flags=re.MULTILINE)
if patched == text:
    raise SystemExit("AppImage GTK hook export line not found; cannot enforce X11 backend")
path.write_text(patched)
PY
else
  echo "WARNING: GTK AppImage hook not found; AppImage backend detection will not be patched"
fi

# Rebuild AppImage from AppDir
if command -v appimagetool &> /dev/null; then
  echo "[3/3] Rebuilding AppImage from AppDir..."
  appimagetool "$APPIMAGE_APPDIR" "releases/vibecode.appimage"
  chmod +x releases/vibecode.appimage
else
  echo "ERROR: appimagetool not found; cannot rebuild patched AppImage"
  exit 1
fi

# Verify
if [ -f "releases/vibecode.appimage" ]; then
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
    echo "The app loads the bundled UI from releases/vibecode.appimage"
    echo "If you want local backend access, run the server on localhost:8786 before opening the app."
    echo ""
    echo "Note: This is a native desktop shell with bundled UI assets."
else
    echo "ERROR: AppImage not found after build"
    exit 1
fi
