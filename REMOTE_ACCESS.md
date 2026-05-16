# Remote Access Setup for Hermes WebUI

This guide explains how to set up remote access so you can use the Hermes WebUI APK from anywhere using mobile data.

## Current Status
✅ **Local Server**: Running on `http://$HERMES_WEBUI_HOST:8786`  
✅ **CSP Updated**: Allows connections to `http://192.168.*:*`  
✅ **APK Configured**: Uses `https://vc.$HERMES_DOMAIN` as remote server  
✅ **Setup Script**: `./setup_remote_access.sh` ready to use

## Quick Start Options

### Option 1: Automated Tunnel (Recommended)
```bash
./setup_remote_access.sh
```
This will:
- Set up ngrok tunnel automatically
- Provide public URL for APK configuration
- Keep tunnel active as long as script runs

### Option 2: Router Port Forwarding
1. Access your router admin panel
2. Find "Port Forwarding" section
3. Forward external port 8786 to internal IP: `$HERMES_WEBUI_HOST:8786`
4. Save settings

### Option 3: SSH Reverse Tunnel
If you have SSH access to a public server:
```bash
ssh -R 8786:localhost:8786 user@your-public-server.com
```

## APK Configuration
Once you have a public URL, configure the APK:
1. Open Hermes WebUI APK
2. Go to Settings
3. Enter the public URL in the server field
4. Save and reconnect

## Verification
Test the setup by:
1. Opening Hermes WebUI APK
2. Sending a test prompt
3. Confirm you receive a response

## Troubleshooting
- **CSP Errors**: Make sure your public URL uses HTTP (not HTTPS) for local IP addresses
- **Firewall Issues**: Check that port 8786 isn't blocked by firewall
- **Network Changes**: If your local IP changes, update port forwarding rules

## Security Notes
- The tunnel provides public access but keeps your local server secure
- APK uses HTTPS for the remote server connection
- All API calls are encrypted even over HTTP locally
