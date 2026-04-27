#!/bin/bash
# Build VibeCode APK for Android
set -e

echo "=== VibeCode APK Builder ==="
echo "Target: releases/vibecode.apk"
echo "Server: http://192.168.4.233:8786"
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
        echo '{"appId":"app.vibecode.mobile","appName":"VibeCode","webDir":"static","server":{"url":"http://192.168.4.233:8786","cleartext":true}}' > capacitor.config.json
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

# Sync web assets
echo "[3/5] Syncing web assets..."
npx cap sync android

# Create keystore if not exists
if [ ! -f "releases/vibecode.keystore" ]; then
    echo "[4/5] Creating signing keystore..."
    keytool -genkey -v \
        -keystore releases/vibecode.keystore \
        -alias vibecode \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -dname "CN=VibeCode, OU=Mobile, O=AnomalyCo, L=Local, S=State, C=US" \
        -storepass vibecode123 \
        -keypass vibecode123
else
    echo "[4/5] Using existing keystore"
fi

# Build APK
echo "[5/5] Building APK..."
cd android
./gradlew assembleRelease

# Copy APK to releases
cd ..
cp android/app/build/outputs/apk/release/app-release-unsigned.apk releases/vibecode-unsigned.apk 2>/dev/null || true

# Sign the APK
if [ -f "releases/vibecode-unsigned.apk" ]; then
    jarsigner -verbose \
        -sigalg SHA256withRSA \
        -digestalg SHA-256 \
        -keystore releases/vibecode.keystore \
        -storepass vibecode123 \
        -keypass vibecode123 \
        releases/vibecode-unsigned.apk \
        vibecode

    # Align and zipalign
    if command -v zipalign &> /dev/null; then
        zipalign -v 4 releases/vibecode-unsigned.apk releases/vibecode.apk
        rm releases/vibecode-unsigned.apk
    else
        mv releases/vibecode-unsigned.apk releases/vibecode.apk
    fi
fi

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
    echo "Note: The APK connects to http://192.168.4.233:8786"
    echo "Ensure your server is running on that IP before using the app"
else
    echo "ERROR: APK build failed"
    exit 1
fi
