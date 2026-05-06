#!/bin/bash
# Extract AppImage since FUSE mount fails
echo 'Extracting AppImage...'
/home/house/apps/vibecode.appimage --appimage-extract
echo 'Extracted to squashfs-root/'
echo 'To run the extracted app:'
echo 'cd squashfs-root'
echo './usr/bin/vibe-code-desktop'
echo ''
echo 'Or with debugging:'
echo 'gdb ./usr/bin/vibe-code-desktop'
echo 'Then: run, and bt on crash'

