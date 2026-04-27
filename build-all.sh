#!/bin/bash
# Build all VibeCode distribution packages
set -e

echo "======================================"
echo "    VibeCode Build System"
echo "======================================"
echo ""
echo "This will build:"
echo "  - releases/vibecode.appimage (Linux desktop)"
echo "  - releases/vibecode.apk (Android mobile)"
echo ""
echo "Server URL: http://192.168.4.233:8786"
echo ""

# Create releases directory
mkdir -p releases

# Track build status
APPIMAGE_SUCCESS=false
APK_SUCCESS=false

# Build AppImage
echo "========================================"
echo "Building AppImage..."
echo "========================================"
if [ -f "build-appimage.sh" ]; then
    if ./build-appimage.sh; then
        APPIMAGE_SUCCESS=true
    else
        echo "WARNING: AppImage build failed"
    fi
else
    echo "WARNING: build-appimage.sh not found"
fi

echo ""

# Build APK
echo "========================================"
echo "Building APK..."
echo "========================================"
if [ -f "build-apk.sh" ]; then
    if ./build-apk.sh; then
        APK_SUCCESS=true
    else
        echo "WARNING: APK build failed"
    fi
else
    echo "WARNING: build-apk.sh not found"
fi

echo ""
echo "======================================"
echo "    Build Summary"
echo "======================================"
echo ""

# Check results
if [ "$APPIMAGE_SUCCESS" = true ] && [ -f "releases/vibecode.appimage" ]; then
    echo "✓ AppImage: releases/vibecode.appimage"
    ls -lh releases/vibecode.appimage | awk '{print "  Size:", $5}'
else
    echo "✗ AppImage: FAILED"
fi

if [ "$APK_SUCCESS" = true ] && [ -f "releases/vibecode.apk" ]; then
    echo "✓ APK: releases/vibecode.apk"
    ls -lh releases/vibecode.apk | awk '{print "  Size:", $5}'
else
    echo "✗ APK: FAILED (or not built)"
fi

echo ""
echo "======================================"
echo ""

# Final status
if [ "$APPIMAGE_SUCCESS" = true ] || [ "$APK_SUCCESS" = true ]; then
    echo "Build complete! Files are in ./releases/"
    echo ""
    echo "Next steps:"
    if [ "$APPIMAGE_SUCCESS" = true ]; then
        echo "  Run AppImage: ./releases/vibecode.appimage"
        echo "  Install: cp releases/vibecode.appimage ~/Applications/"
    fi
    if [ "$APK_SUCCESS" = true ]; then
        echo "  Install APK: adb install releases/vibecode.apk"
    fi
    echo ""
    echo "Auto-update setup:"
    echo "  The AppImage supports delta updates via GitHub Releases."
    echo "  Publish releases/vibecode.appimage to GitHub Releases with"
echo "  the zsync file for automatic updates to work."
    exit 0
else
    echo "ERROR: All builds failed"
    exit 1
fi
