#!/usr/bin/env python3
import subprocess
import json
import re

host = '192.168.4.250'
user = 'house'
sessions_dir = '/home/house/.hermes/sessions'

# List files
cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {user}@{host} 'ls -1t {sessions_dir}/*.json 2>/dev/null | head -5'"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
files = [f.strip().replace(f'{sessions_dir}/', '') for f in result.stdout.strip().split('\n') if f.strip()]
print(f'Files found: {files}')

# Batch fetch using the same logic as routes.py
file_list = ' '.join(files)
remote_cmd = f"cd {sessions_dir} && for f in {file_list}; do echo '===" + "FILE:'\"\"$f\"\"'==='; head -c 512 \"" + "$f\" 2>/dev/null | head -3; done"
cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {user}@{host} '{remote_cmd}'"
print(f'Command: {cmd}')
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
print(f'Return code: {result.returncode}')
print(f'Stderr: {result.stderr[:200]}')
print(f'Stdout length: {len(result.stdout)}')
print(f'Output:\n{result.stdout}')

# Count delimiters
delimiters = [l for l in result.stdout.split('\n') if l.startswith('===FILE:')]
print(f'\nFound {len(delimiters)} delimiters: {delimiters}')
