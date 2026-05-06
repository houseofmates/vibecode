#!/bin/bash
# Build script for Tauri - creates proper directory structure
set -e

echo "Building Tauri distribution..."

# Create dist directory
mkdir -p dist/static

# Copy all static files to dist/static/
cp static/*.css dist/static/
cp static/*.js dist/static/
cp static/*.png dist/static/

# Copy index.html to dist/ and fix paths
cp static/index.html dist/

# In dist/index.html, replace static/ with just the filename for CSS and JS
sed -i 's|href="static/style.css|href="static/style.css|g' dist/index.html
sed -i 's|src="static/|src="static/|g' dist/index.html

# Actually, we need to create the structure so that static/ paths work
# The web server expects index.html at root and files at static/
# So for Tauri, we need the same structure

echo "Tauri dist structure created"
echo "- dist/index.html"
echo "- dist/static/ (CSS, JS, images)"
