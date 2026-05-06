#!/bin/bash
# Extract AppImage for deeper debugging
./releases/vibecode.appimage --appimage-extract
echo 'Extracted to squashfs-root/'
echo 'Run with gdb: gdb squashfs-root/usr/bin/vibe-code-desktop'
echo 'In gdb: run, then bt on crash'

