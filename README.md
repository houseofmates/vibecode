# vibecode

Browser-based coding interface with AI agent integration.

## Quick Start

```bash
# Install
pip install -e .

# Run
vibecode
# or
python server.py
```

Open http://$HERMES_WEBUI_HOST:8786 in your browser.

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
# Edit .env with your settings
```

### Key Options

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_WEBUI_HOST` | `127.0.0.1` | Bind address |
| `HERMES_WEBUI_PORT` | `8786` | Port |
| `HERMES_WEBUI_PASSWORD` | (none) | Set for security |
| `HERMES_WEBUI_AGENT_DIR` | auto | Path to hermes-agent |
| `HERMES_WEBUI_DEFAULT_WORKSPACE` | `~/workspace` | Default workspace |
| `HERMES_DOMAIN` | (none) | Domain for web interface |
| `UBUNTU_IP` | `127.0.0.1` | IP address of Ubuntu machine |
| `POPOS_IP` | `127.0.0.1` | IP address of Pop!_OS machine |
| `DEFAULT_HOME` | `~` | Default home directory path |
| `MEMSTER_USER` | (current user) | SSH username for remote machines |

## Development

```bash
make install   # Install in editable mode
make run       # Run the server
make dev       # Run with auto-reload
make test      # Run tests
make clean     # Clean artifacts
```

## Packaging

Build standalone applications for distribution:

### Linux AppImage

```bash
make appimage    # Build releases/vibecode.appimage
```

**Requirements:** `pip install appimage-builder`

**Additional build dependency:** install `appimagetool` so the packaging script can rebuild the AppImage with a GTK backend compatibility fix.

**Install:**
```bash
# Run directly (no installation needed)
./releases/vibecode.appimage

# Or install for GNOME integration
mkdir -p ~/Applications
cp releases/vibecode.appimage ~/Applications/
```

**Features:**
- Portable Python runtime (no system Python needed)
- Runs from local or remote codebase
- Code changes reflected on app restart
- Runs at http://$HERMES_WEBUI_HOST:8786

**Remote Codebase Options:**

**Option 1: Mount via SSHFS**
```bash
# Install sshfs
sudo apt install sshfs

# Mount remote directory
mkdir -p ~/vibecode-remote
sshfs $USER@$HERMES_WEBUI_HOST:/home/$USER/vibecode ~/vibecode-remote

# Run AppImage
export VIBECODE_HOME=~/vibecode-remote
./releases/vibecode.appimage
```

**Option 2: Git Repository**
```bash
# Run AppImage with git repo URL
export VIBECODE_GIT=https://github.com/yourusername/vibecode.git
./releases/vibecode.appimage

# On subsequent runs, it will auto-pull latest changes
```

### Android APK

```bash
make apk         # Build releases/vibecode.apk
```

**Requirements:**
- Node.js: `sudo apt install nodejs npm`
- Java JDK: `sudo apt install default-jdk`
- Android SDK (for `zipalign`): `sudo apt install android-sdk`

**Install:**
```bash
adb install releases/vibecode.apk
```

**Note:** The APK connects to `http://$HERMES_WEBUI_HOST:8786`. Ensure your server is running and accessible from your phone on the same network.

### Build All

```bash
make all         # Build both AppImage and APK
```

## Auto-Updates

The AppImage supports automatic delta updates:

```bash
make update      # Check for and install updates
```

**How it works:**
- Uses GitHub Releases + zsync for delta updates
- Only downloads changed parts (faster than full download)
- Update metadata embedded in the AppImage

**Setup for publishers:**
1. Build: `make appimage`
2. Upload `releases/vibecode.appimage` to GitHub Releases
3. Also upload the `.zsync` file for delta updates

## TLS/HTTPS

Set certificate paths:

```bash
export HERMES_WEBUI_TLS_CERT=/path/to/cert.pem
export HERMES_WEBUI_TLS_KEY=/path/to/key.pem
```

## Remote Access

SSH tunnel for secure remote access:

```bash
ssh -N -L 8786:$HERMES_WEBUI_HOST:8786 $USER@your-server
```

Then open http://localhost:8786

## Build Reference

| Command | Output | Description |
|---------|--------|-------------|
| `make appimage` | `releases/vibecode.appimage` | Linux desktop app |
| `make apk` | `releases/vibecode.apk` | Android mobile app |
| `make all` | Both above | Complete build |
| `make update` | - | Check for updates |

## License

MIT