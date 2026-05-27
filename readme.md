<h1 align="center">vibecode</h1>

<p align="center">vibecode is a local web workspace for coding, terminal sessions, and ai-enabled development flows. it is designed to run on your machine and keep your code accessible through a browser while preserving local project structure and git history.</p>

<h2 align="center">what vibecode does</h2>

- provides a browser-based interface for code, terminal, file browsing, and assistant workflows
- supports local ai assistance for shell commands, code editing, and project automation
- includes a persistent systemd watcher that syncs repo changes to the github `main` branch after they settle for 10 seconds
- uses env-based configuration
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

<p align="center">copy the example env and set your preferred values:</p>

<pre align="center"><code>cp .env.example .env
# edit .env for your environment
</code></pre>

<p align="center">install the project dependencies and run the server:</p>

<pre align="center"><code>pip install -e .
python server.py
</code></pre>

<p align="center">open the interface in your browser at:</p>

<pre align="center"><code>http://$HERMES_WEBUI_HOST:8786
</code></pre>

<h2 align="center">enable the auto-sync watcher</h2>

<p align="center">vibecode includes a persistent watcher service that keeps code changes synced to <code>main</code>. if the repository is configured with a github remote, the watcher will commit stable changes and merge them into the remote <code>main</code> branch.</p>

<p align="center">enable it with:</p>

<pre align="center"><code>systemctl --user daemon-reload
systemctl --user enable --now /home/$USER/vibecode/tools/auto_push.service
</code></pre>

<p align="center">to check status:</p>

<pre align="center"><code>systemctl --user status auto_push.service
</code></pre>

<h2 align="center">configuration</h2>

<p align="center">copy <code>.env.example</code> to <code>.env</code> and customize the values.</p>

<h3 align="center">key options</h3>

<div align="center">
<table>
  <thead>
    <tr><th>variable</th><th>default</th><th>description</th></tr>
  </thead>
  <tbody>
    <tr><td><code>HERMES_WEBUI_HOST</code></td><td><code>127.0.0.1</code></td><td>bind address</td></tr>
    <tr><td><code>HERMES_WEBUI_PORT</code></td><td><code>8786</code></td><td>port</td></tr>
    <tr><td><code>HERMES_WEBUI_PASSWORD</code></td><td>(none)</td><td>set a password for web access</td></tr>
    <tr><td><code>HERMES_WEBUI_AGENT_DIR</code></td><td><code>auto</code></td><td>path to hermes-agent</td></tr>
    <tr><td><code>HERMES_WEBUI_DEFAULT_WORKSPACE</code></td><td><code>~/workspace</code></td><td>default workspace</td></tr>
    <tr><td><code>HERMES_DOMAIN</code></td><td>(none)</td><td>optional domain for web ui</td></tr>
    <tr><td><code>UBUNTU_IP</code></td><td><code>127.0.0.1</code></td><td>optional ubuntu host ip</td></tr>
    <tr><td><code>POPOS_IP</code></td><td><code>127.0.0.1</code></td><td>optional popos host ip</td></tr>
    <tr><td><code>DEFAULT_HOME</code></td><td><code>~</code></td><td>default home directory</td></tr>
  </tbody>
</table>
</div>

<h2 align="center">development</h2>

<pre align="center"><code>make install
make run
make dev
make test
make clean
</code></pre>

<h2 align="center">packaging</h2>

<h3 align="center">linux appimage</h3>

<pre align="center"><code>make appimage
</code></pre>

<h3 align="center">android apk</h3>

<pre align="center"><code>make apk
</code></pre>

<h2 align="center">branch and git sync</h2>

<p align="center">vibecode is built to sync changes into the <code>main</code> branch. if the repository still has a local <code>master</code> branch, the watcher will rename it to <code>main</code> and keep the repository on <code>main</code>.</p>

<p align="center">if git user config is not set, configure it before enabling the watcher:</p>

<pre align="center"><code>git config --global user.name "your name"
git config --global user.email "you@example.com"
</code></pre>

<h2 align="center">license</h2>

<p align="center"><a href="license">mit</a>; forked from <a href="https://github.com/nesquena/hermes-webui">hermes webui</a></p>
