#!/bin/bash
# Run extracted AppImage with strace
cd squashfs-root
echo 'Running extracted app with strace...'
strace -f ./usr/bin/vibe-code-desktop 2>&1 | head -100
echo 'App exited'

