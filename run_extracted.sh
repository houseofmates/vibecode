#!/bin/bash
# Run extracted vibecode with proper library paths
cd squashfs-root
export LD_LIBRARY_PATH="$PWD/usr/lib:$PWD/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"
export PATH="$PWD/usr/bin:$PATH"
export XDG_DATA_DIRS="$PWD/usr/share:$XDG_DATA_DIRS"
export GIO_MODULE_DIR="$PWD/usr/lib/x86_64-linux-gnu/gio/modules"
export GTK_IM_MODULE_FILE="$PWD/usr/lib/x86_64-linux-gnu/gtk-3.0/3.0.0/immodules.cache"
export GDK_PIXBUF_MODULE_FILE="$PWD/usr/lib/x86_64-linux-gnu/gdk-pixbuf-2.0/2.10.0/loaders.cache"
export WEBKIT_EXEC_PATH="$PWD/usr/lib/x86_64-linux-gnu/webkit2gtk-4.1/WebKitNetworkProcess"
export WEBKIT_WEB_PROCESS_PATH="$PWD/usr/lib/x86_64-linux-gnu/webkit2gtk-4.1/WebKitWebProcess"

echo 'Running with LD_LIBRARY_PATH set...'
./usr/bin/vibe-code-desktop

