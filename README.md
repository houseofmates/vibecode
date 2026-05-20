<h1 align="center">VibeCode</h1>

<p align="center">
  <strong>A lightweight browser-based IDE for local development with AI integration</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/version-0.50.38-orange.svg" alt="Version">
</p>

VibeCode is a local web workspace for coding, terminal sessions, and AI-enabled development. It runs entirely on your machine, keeps your code accessible through any browser, and preserves project structure and git history. Zero cloud dependencies - your code stays local.

Originally forked from [hermes-webui](https://github.com/nesquena/hermes-webui) by Nicolas Esquivel. This fork adds the git auto-sync service, AppImage/APK packaging, multi-provider AI support, and extensive local improvements.

## Features

### Core Development Environment
- **Browser Terminal** - Full xterm.js terminal emulation connected to your host shell with PTY support
- **File Explorer** - Browse, create, rename, delete, and search files and folders with syntax highlighting
- **Multi-Tab Workspace** - Work across multiple files and terminal sessions simultaneously
- **Drag-and-Drop Upload** - Drop files and folders directly into the workspace
- **Session Persistence** - All work persists across browser refreshes and server restarts

### AI Assistant Integration
- **Multi-Provider Support** - Connect to 20+ AI providers:
  - Anthropic Claude (claude-4, claude-3.5-sonnet, opus)
  - OpenAI GPT (gpt-4o, gpt-4-turbo, o1, o3)
  - Google Gemini (gemini-2.5-pro, gemini-2.5-flash)
  - DeepSeek, Qwen, Mistral, xAI Grok
  - OpenRouter (access to 100+ models)
  - Ollama & LM Studio (local models)
  - Custom OpenAI-compatible endpoints
- **Streaming Responses** - Real-time SSE streaming with thinking/reasoning display
- **Context-Aware Assistance** - AI understands your project structure and codebase
- **Memory System** - Persistent knowledge base for project-specific context

### Git Integration
- **Auto-Sync Watcher** - systemd user service watches for file changes; commits and pushes after 10-second debounce
- **Branch Management** - Works with your existing git workflow
- **Commit History** - Full git log visualization in the UI

### Multi-Platform Deployment
- **Web Server** - Python HTTP server (zero framework dependencies)
- **Desktop App** - Tauri 2.0 builds for Linux, Windows, and macOS
- **Mobile App** - Capacitor 8 for Android APK packaging
- **AppImage** - Portable Linux distribution
- **Docker** - Container deployment with compose support

### Security
- **Optional Password Authentication** - PBKDF2-HMAC-SHA256 password hashing
- **JWT Token Support** - Secure API authentication
- **CORS Protection** - Configurable cross-origin policies
- **CSRF Tokens** - Protection against cross-site request forgery
- **TLS/HTTPS** - Optional encrypted connections

## Requirements

- **Python 3.10+**
- **Git** (for auto-sync features)
- **Node.js** (only for desktop/mobile builds)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/anomalyco/vibecode.git
cd vibecode

# Install Python dependencies
pip install -r requirements.txt

# Start the server
python server.py
```

The web UI opens at `http://localhost:8786` by default.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HERMES_WEBUI_HOST` | Server bind address | `127.0.0.1` |
| `HERMES_WEBUI_PORT` | Server port | `8786` |
| `HERMES_WEBUI_PASSWORD` | Enable authentication | (none) |
| `HERMES_WEBUI_WORKSPACE` | Default workspace path | `~/workspace` |
| `ANTHROPIC_API_KEY` | Anthropic API key | (none) |
| `OPENAI_API_KEY` | OpenAI API key | (none) |
| `OPENROUTER_API_KEY` | OpenRouter API key | (none) |
| `HERMES_WEBUI_TLS_CERT` | TLS certificate path | (none) |
| `HERMES_WEBUI_TLS_KEY` | TLS private key path | (none) |

### AI Provider Setup

Configure at least one AI provider to enable the assistant:

```bash
# Anthropic (recommended)
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# OpenRouter (access to many models)
export OPENROUTER_API_KEY="sk-or-..."

# Custom endpoint
export OPENAI_API_BASE="https://your-api.com/v1"
```

## Git Auto-Sync

The auto-sync watcher commits changes to git after files settle for 10 seconds:

```bash
# Configure git identity
git config --global user.name "Your Name"
git config --global user.email "you@example.com"

# Install and enable the systemd user service
systemctl --user daemon-reload
systemctl --user enable --now vibecode-auto-sync.service
```

## Desktop & Mobile Builds

### Tauri Desktop App

```bash
# Install Tauri CLI
npm install

# Build for current platform
npm run tauri build
```

### Android APK

```bash
# Initialize Capacitor
npx cap init

# Build APK
./build-apk.sh
```

### AppImage

```bash
./build-appimage.sh
```

## Architecture

```
vibecode/
├── server.py          # Main entry point - HTTP server
├── api/               # Backend modules
│   ├── routes.py      # Request routing
│   ├── streaming.py   # SSE streaming & AI agent execution
│   ├── config.py      # Configuration & provider discovery
│   ├── models.py      # Session persistence
│   ├── terminal.py    # PTY terminal sessions
│   ├── workspace.py   # File system operations
│   └── auth.py        # Authentication
├── static/            # Frontend assets
│   ├── index.html     # SPA shell
│   ├── panels.js      # Panel system
│   ├── sessions.js    # Session management
│   ├── terminal.js    # Terminal integration
│   └── style.css      # Core styling
└── src-tauri/         # Tauri desktop config
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve web UI |
| `/api/sessions` | GET/POST | List/create chat sessions |
| `/api/stream` | POST | SSE streaming for AI responses |
| `/api/files` | GET/POST | File operations |
| `/api/terminal` | GET/POST | Terminal sessions |
| `/api/settings` | GET/POST | User preferences |
| `/api/workspace` | GET/POST | Workspace management |

## What It Is Not

- **Not a full IDE** - No debugger integration, no LSP, no refactoring engine. This is a browser workspace for terminal and AI-assisted coding.
- **Not resource-isolated** - The workspace runs with your user permissions. Secure the endpoint appropriately.
- **Not multi-tenant** - Designed for single-user local development.

## License

MIT License - see [LICENSE](LICENSE)

Based on [hermes-webui](https://github.com/nesquena/hermes-webui) by Nicolas Esquivel.
