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

# Set AppDir path early so it's available for all steps
APPIMAGE_APPDIR="src-tauri/target/release/bundle/appimage/vibecode.AppDir"

# Prepare frontend assets
./build-tauri-dist.sh

# Build Tauri AppImage
echo "[1/3] Building Tauri AppImage..."
npx tauri build

# Fix AppDir structure for compatibility
echo "[1.5/3] Fixing AppDir structure..."
cd "$APPIMAGE_APPDIR"
# Create WebKit process copies in expected location
if [ -d "usr/lib/x86_64-linux-gnu/webkit2gtk-4.1" ]; then
  mkdir -p lib/x86_64-linux-gnu/webkit2gtk-4.1
  cp usr/lib/x86_64-linux-gnu/webkit2gtk-4.1/WebKitNetworkProcess lib/x86_64-linux-gnu/webkit2gtk-4.1/ 2>/dev/null || true
  cp usr/lib/x86_64-linux-gnu/webkit2gtk-4.1/WebKitWebProcess lib/x86_64-linux-gnu/webkit2gtk-4.1/ 2>/dev/null || true
  echo "Copied WebKit processes to lib/"
else
  echo "WebKit processes not found in usr/lib"
fi
cd -

# Patch GTK backend detection in AppImage hook if needed
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

# Remove linuxdeploy GTK plugin and create minimal AppRun
APP_RUN_FILE="$APPIMAGE_APPDIR/AppRun"
if [ -f "$APP_RUN_FILE" ]; then
  echo "[2/3] Creating minimal AppRun without GTK plugin..."
  # Remove the problematic GTK plugin entirely
  rm -rf "$APPIMAGE_APPDIR/apprun-hooks"
  
  # Create minimal AppRun
  cat > "$APP_RUN_FILE" <<'APP_RUN_EOF'
#! /usr/bin/env bash

# Minimal AppRun for Tauri application
set -e

this_dir="$(readlink -f "$(dirname "$0")")"

# Only set essential environment variables
export PATH="$this_dir/usr/bin:$PATH"
export GDK_BACKEND=x11

# Force X11 rendering to avoid GBM/EGL issues
export GSK_RENDERER=x11
export QT_QPA_PLATFORM=xcb

# Force software rendering if needed
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe

# Disable WebKit GPU compositing to prevent GBM/EGL crashes on systems
# without proper GPU drivers or in remote/VNC sessions
export WEBKIT_DISABLE_COMPOSITING_MODE=1
export WEBKIT_DISABLE_DMABUF_RENDERER=1
export WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1

# Disable GTK overlay scrollbars so CSS ::-webkit-scrollbar styles work
export GTK_OVERLAY_SCROLLING=0

exec "$this_dir"/AppRun.wrapped "$@"
APP_RUN_EOF
  chmod +x "$APP_RUN_FILE"
else
  echo "WARNING: AppRun not found; cannot fix library paths"
fi

# Rebuild AppImage from AppDir
if command -v appimagetool &> /dev/null; then
  echo "[3/3] Rebuilding AppImage from AppDir..."
  rm -f "releases/vibecode.appimage"
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
