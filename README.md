# vibecode

vibecode is a local web workspace for coding, terminal sessions, and ai-enabled development flows.
it is designed to run on your machine and keep your code accessible through a browser while preserving local project structure and git history.

<h2 align="center">what vibecode does</h2>

- provides a browser-based interface for code, terminal, file browsing, and assistant workflows
- supports local ai assistance for shell commands, code editing, and project automation
- includes a persistent systemd watcher that syncs repo changes to the github `main` branch after they settle for 10 seconds
- uses env-based configuration so secrets and local settings stay out of the repo
- supports packaging for linux appimage and android apk
- works with local or remote code directories and remote access tunnels

<h2 align="center">features</h2>

- browser terminal and file explorer
- drag-and-drop file/folder support
- automatic code-change persistence into git `main`
- secure access via password, tls, and ssh forwarding
- local-first architecture with remote sync options
- packaged desktop and android build support
- simple setup with `.env.example`

<h2 align="center">quick start</h2>

copy the example env and set your preferred values:

```bash
cp .env.example .env
# edit .env for your environment
```

install the project dependencies and run the server:

```bash
pip install -e .
python server.py
```

open the interface in your browser at:

```bash
http://$HERMES_WEBUI_HOST:8786
```

<h2 align="center">enable the auto-sync watcher</h2>

vibecode includes a persistent watcher service that keeps code changes synced to `main`.
if the repository is configured with a github remote, the watcher will commit stable changes and merge them into the remote `main` branch.

enable it with:

```bash
systemctl --user daemon-reload
systemctl --user enable --now /home/$USER/vibecode/tools/auto_push.service
```

to check status:

```bash
systemctl --user status auto_push.service
```

<h2 align="center">configuration</h2>

copy `.env.example` to `.env` and customize the values.

### key options

| variable | default | description |
|----------|---------|-------------|
| `HERMES_WEBUI_HOST` | `127.0.0.1` | bind address |
| `HERMES_WEBUI_PORT` | `8786` | port |
| `HERMES_WEBUI_PASSWORD` | (none) | set a password for web access |
| `HERMES_WEBUI_AGENT_DIR` | `auto` | path to hermes-agent |
| `HERMES_WEBUI_DEFAULT_WORKSPACE` | `~/workspace` | default workspace |
| `HERMES_DOMAIN` | (none) | optional domain for web ui |
| `UBUNTU_IP` | `127.0.0.1` | optional ubuntu host ip |
| `POPOS_IP` | `127.0.0.1` | optional popos host ip |
| `DEFAULT_HOME` | `~` | default home directory |

<h2 align="center">development</h2>

```bash
make install
make run
make dev
make test
make clean
```

<h2 align="center">packaging</h2>

### linux appimage

```bash
make appimage
```

### android apk

```bash
make apk
```

<h2 align="center">branch and git sync</h2>

vibecode is built to sync changes into the `main` branch.
if the repository still has a local `master` branch, the watcher will rename it to `main` and keep the repository on `main`.

if git user config is not set, configure it before enabling the watcher:

```bash
git config --global user.name "your name"
git config --global user.email "you@example.com"
```

<h2 align="center">license</h2>

mit

mit