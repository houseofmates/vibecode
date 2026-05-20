<h1 align="center">vibecode</h1>

a local web workspace for coding, terminal sessions, and ai-enabled development. runs on your machine, keeps your code accessible through a browser, and preserves project structure and git history. built for house because having a browser window open to the terminal is sometimes all the workspace needs to be, and sometimes a ui makes it better.

it is a fork of [hermes-webui](https://github.com/nesquena/hermes-webui) by nicolas esquivel (@nesquena). the upstream repo provides the foundation. this fork adds the git watch service, appimage / apk packaging, and a few local improvements. the original license is mit — see the license section below for the upstream link.

<h2 align="center">made for</h2>


vibecode is built for house so the workspace is there when it needs to be and stays in sync without thinking about it. the auto-sync watcher exists because maintaining a remote branch from a local repo manually is annoying and this setup does it ten seconds after the last file settles.

<h2 align="center">what makes it personal</h2>


vibecode exists because the terminal was sometimes all that was available and the browser added a layer that was useful when a ui was needed. the auto-sync watcher handles something specific to the setup: keeping a running github main branch up to date when work settles for ten seconds without a new commit. it is a narrow function that matters on a continuous-use setup.

the vue / django / docker / redis / django-channels stack is standard vibecode. there is a four-service stack that starts with a single compose command and gives you file browsing, terminal, assistant, and a persistent backing data layer.

<h2 align="center">features</h2>


- **browser terminal** — xterm.js terminal connected to your host shell
- **file explorer** — browse, create, rename, delete files and folders
- **drag-and-drop** — drop files and folders into the workspace; they show up with instant state updates
- **ai assistant** — openweave / cfd integration for code assistance directly in the workspace
- **auto-sync watcher** — systemd --user service watches for file changes; when things settle for 10 seconds, commits to branch and pushes to remote
- **docker compose setup** — four services (api, web, worker, redis) started from one command
- **persistent data** — source code and project files stored under workspace root, not a transient session
- **vite + vue frontend** — hot reload on change, dev server, css modules
- **systemd integration** — start at boot, auto-restart, watcher as a user-level systemd service

<h2 align="center">what it is not for</h2>


- **not a full ide** — there is no debugger integration, no language server protocol, no refactoring engine. this is a browser wrapper around a terminal and a file tree.
- **not a standalone editor with ai built in** — do not install this expecting cursor or windsurf. the ai features are basic context-aware assistance, not a coding agent.
- **multi-project support is limited** — vibecode maintains one active workspace. it is a single-project tool by design. the watcher service is intended to run on one repo at a time.
- **not resource-isolated** — the workspace lives on the host filesystem. if someone reaches the vibecode web ui they are in the same file permissions context as the user running the service. put access controls on the endpoint.

<h2 align="center">installation</h2>


```bash
<h1 align="center">prerequisites: python 3.8+, node.js, docker, redis</h1>

<h1 align="center">clone</h1>

git clone <vibecode-repo-url>
cd vibecode

<h1 align="center">copy env template</h1>

cp .env.example .env
<h1 align="center">edit .env — set workspace path, git config, universe endpoint</h1>


<h1 align="center">build and start the stack</h1>

docker compose build
docker compose up

<h1 align="center">install the auto-sync watcher</h1>

systemctl --user daemon-reload
systemctl --user enable --now vibecode-auto-sync.service
```

the web ui opens at the host and port set in .env. the terminal connects to the host shell through the django-channels websocket. the redis broker is required for the websocket transport.

<h1 align="center">git auto-sync</h1>

the watcher commits to git branch (default main, auto-renamed from master if needed) after a 10-second debounce. configure git before enabling:

```bash
git config --global user.name "your name"
git config --global user.email "you@example.com"
```

then enable the systemd user service. it restarts automatically on failure.

<h1 align="center">license</h1>

this project is licensed under the mit license — the same license as the original [hermes-webui](https://github.com/nesquena/hermes-webui) repo.

see the upstream license at https://github.com/nesquena/hermes-webui/blob/main/license
