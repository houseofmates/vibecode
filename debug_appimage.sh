#!/bin/bash
# Wrapper script to debug vibecode AppImage
echo 'Starting vibecode with debugging...'
echo 'DISPLAY='
echo 'WAYLAND_DISPLAY='
echo 'Running strace...'
strace -f ./releases/vibecode.appimage 2>&1 | head -100
echo 'AppImage exited'

