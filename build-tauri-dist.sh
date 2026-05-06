#!/bin/bash
# Build script for Tauri - creates proper directory structure
set -e

echo "Building Tauri distribution..."

# Recreate dist so packaged root assets cannot stay stale between builds
rm -rf dist
mkdir -p dist/static

# Copy web assets to the dist root because index.html references them directly
cp static/*.css dist/
cp static/*.js dist/
cp static/*.png dist/

# Keep a mirrored static/ directory for consumers that expect that layout
cp static/*.css dist/static/
cp static/*.js dist/static/
cp static/*.png dist/static/

# Copy index.html to dist/
cp static/index.html dist/

echo "Tauri dist structure created:"
echo "  - dist/index.html"
echo "  - dist/static/ (CSS, JS, images)"
