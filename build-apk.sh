#!/bin/bash
# Build vibecode APK for Android
set -e

echo "=== vibecode APK Builder ==="
echo "Target: releases/vibecode.apk"
echo "Server: https://vc.${HERMES_DOMAIN:-your-domain.com} (or local fallback)"
echo ""

# Check dependencies
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found!"
    echo "Install with: sudo apt install nodejs npm"
    exit 1
fi

if ! command -v java &> /dev/null; then
    echo "ERROR: Java not found!"
    echo "Install with: sudo apt install default-jdk"
    exit 1
fi

# Create releases directory
mkdir -p releases

# Initialize Capacitor if not already done
if [ ! -d "android" ]; then
    echo "[1/5] Initializing Capacitor Android project..."

    # Install Capacitor CLI and core
    npm install --save-dev @capacitor/cli @capacitor/core
    npm install @capacitor/android

    # Initialize Capacitor config if not present
    if [ ! -f "capacitor.config.json" ]; then
        echo '{"appId":"app.vibecode.mobile","appName":"vibecode","webDir":"static",}' > capacitor.config.json
    fi

    # Add Android platform
    npx cap add android
else
    echo "[1/5] Android platform already initialized"
fi

# Ensure node_modules exists
if [ ! -d "node_modules" ]; then
    echo "[2/5] Installing dependencies..."
    npm install
else
    echo "[2/5] Dependencies already installed"
fi

# Refresh dist so Capacitor packages the current mobile assets
echo "[3/6] Refreshing dist web assets..."
./build-tauri-dist.sh

# Sync web assets
echo "[4/6] Syncing web assets..."
npx cap sync android

# Skip keystore for debug build
echo "[5/6] Using debug build (no signing required)"

# Build APK
echo "[6/6] Building APK..."
cd android

# Build debug APK (no signing required, easier to build)
./gradlew assembleDebug

# Copy debug APK
cd ..
apk_source="android/app/build/outputs/apk/debug/app-debug.apk"

if [ ! -f "$apk_source" ]; then
    echo "ERROR: Expected APK not found at $apk_source"
    exit 1
fi

cp "$apk_source" releases/vibecode.apk

# Verify APK was created
if [ -f "releases/vibecode.apk" ]; then
    echo ""
    echo "✓ SUCCESS: Built releases/vibecode.apk"
    echo ""
    echo "To install on Android:"
    echo "  adb install releases/vibecode.apk"
    echo ""
    echo "Or transfer to phone and install manually"
    echo ""
    echo "Note: The APK connects to https://vc.${HERMES_DOMAIN:-your-domain.com}"
    echo "Ensure you have internet connectivity before using the app"
    echo ""
    echo "Note: Using debug build (no signing required)"
else
    echo "ERROR: APK build failed"
    exit 1
fi
