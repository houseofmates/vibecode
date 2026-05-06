#!/bin/bash
# Updated debug script for correct path
APPIMAGE_PATH='/home/house/apps/vibecode.appimage'
echo 'Starting vibecode with debugging...'
echo 'DISPLAY='
echo 'WAYLAND_DISPLAY='
echo 'XDG_SESSION_TYPE=tty'
echo 'AppImage path: '
ls -la $APPIMAGE_PATH
echo 'Running strace...'
strace -f $APPIMAGE_PATH 2>&1 | head -200
echo 'AppImage exited'

