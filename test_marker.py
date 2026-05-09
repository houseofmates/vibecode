#!/usr/bin/env python3
import subprocess

import os
host = os.environ.get('MEMSTER_HOST', os.environ.get('UBUNTU_IP', '127.0.0.1'))
user = os.environ.get('MEMSTER_USER', 'house')
files = [
    _HOME = os.path.expanduser('~')
    f"{os.environ.get('DEFAULT_HOME', _HOME)}/.hermes/sessions/session_cron_9df1b36267c3_20260425_223017.json",
    f"{os.environ.get('DEFAULT_HOME', _HOME)}/.hermes/sessions/session_20260425_211328_73856f.json"
]

cmd_parts = []
for f in files:
    safe_f = f.replace('"', '\\"')
    cmd_parts.append(f'echo "===FILE:{safe_f}==="')
    cmd_parts.append(f'head -c 512 "{safe_f}" 2>/dev/null | head -5')

inner_cmd = '; '.join(cmd_parts)
cmd = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {user}@{host} "{inner_cmd}"'
print(f'Command: {cmd[:200]}...')

result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
print(f'Return code: {result.returncode}')
print(f'Stdout length: {len(result.stdout)}')
print(f'Stderr: {result.stderr[:200]}')
print()
print(f'First 800 chars of stdout:')
print(result.stdout[:800])
print()
markers = [l for l in result.stdout.split('\n') if l.startswith('===FILE:')]
print(f'Number of ===FILE: markers: {len(markers)}')
for m in markers[:3]:
    print(f'  {m[:80]}')
