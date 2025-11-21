# Nuki Smart Lock CLI Tool

This tool provides a command-line interface (CLI) for interacting with the Nuki Smart Lock 3.0 via its Bridge HTTP API (version 1.13.3). It allows you to list devices, check status, unlock (open), and lock (close) your smart lock entirely locally on your LAN without internet access after initial setup. The tool is available in three implementations: Python (`nuki3ctl.py`), Lua (`nuki3ctl.lua`), and PHP (`nuki3ctl.php`), with the CLI versions (Python/Lua) having identical functionality and usage, while PHP is a web-based interface.

## Features
- List all paired Nuki devices with detailed info (e.g., state, battery level).
- Get the current real-time status of a specific device.
- Unlock (open) or lock (close) a device.
- Uses a `config.json` file for default values (IP, token, device ID), with CLI overrides.
- Warns if using default config values to encourage customization.
- Offline-compatible once API is enabled on the Bridge.

## Requirements
### Python Version (`nuki3ctl.py`)
- Python 3.12+ (your Gentoo host likely has this; check with `python --version`).
- Dependencies: `requests` (for HTTP calls) and `argparse` (built-in).
  - Install on Gentoo: `emerge dev-python/requests`.
- Size: Minimal (~50 KB for requests).

### Lua Version (`nuki3ctl.lua`)
- Lua 5.4+ (common on OpenWRT; check with `lua -v`).
- Dependencies: `dkjson` (for JSON handling, <10 KB) and `luasocket` (for HTTP, ~380 KB). Note: If size is a concern on OpenWRT, consider the alternative curl-based version mentioned below.
  - Install on OpenWRT: `opkg update && opkg install dkjson lua-socket`.
  - Install on Gentoo: `emerge dev-lua/dkjson dev-lua/luasocket` (ensure `LUA_TARGETS="lua5-4"` in `/etc/portage/make.conf` for compatibility).
- Alternative for low-storage OpenWRT: Use the curl-based variant (`nuki3ctl_curl.lua`), which replaces luasocket with system `curl` (install via `opkg install curl` if not present, ~200-300 KB). It requires only dkjson and uses `io.popen` for HTTP, keeping the script lightweight.

### PHP Version (`nuki3ctl.php`)
- PHP 8+ (check with `php -v`).
- Dependencies: JSON (built-in) and curl extensions.
  - Install on OpenWRT: `opkg update && opkg install php8-mod-curl`.
  - Install on Gentoo: `emerge --ask dev-php/pecl-curl` (enable in php.ini with `extension=curl.so` if needed).
- Web server: Place in a web-accessible directory (e.g., `/www/nuki3web/index.php` for OpenWRT's lighttpd). Access via browser (e.g., http://your-router-ip/nuki3web/index.php).
- Size: Curl module ~100-200 KB.
- Note: Checks for curl at startup; if missing, prints "The php8-mod-curl package is required to install." and exits.

Both CLI scripts include checks at startup: If dependencies are missing, they print a friendly message (e.g., "The packages/modules dkjson + luasocket (<400 KB) are required to run.") and exit.

## Installation
1. Download the scripts (`nuki3ctl.py`, `nuki3ctl.lua`, and/or `nuki3ctl.php`) to a directory in your PATH (e.g., `~/bin` or `/usr/local/bin` for CLI, or web root for PHP).
2. Make CLI scripts executable: `chmod +x nuki3ctl.py nuki3ctl.lua`.
   - Explanation: Both CLI scripts include shebangs (`#!/usr/bin/env python3` for Python, `#!/usr/bin/lua` for Lua), so you can run them directly as `./nuki3ctl.py` or `./nuki3ctl.lua` without specifying the interpreter.
3. Install dependencies as above.
4. Enable the Nuki Bridge HTTP API via the Nuki app (generates a token; requires temporary internet for activation, then works offline).

## Configuration
The tool looks for a `config.json` file in the current directory. If missing, it creates one with defaults:
```json
{
    "ip": "0.0.0.0",
    "token": "1mytkn",
    "nukiId": "123456789"
}
```
- Edit this with your Bridge IP, API token, and default device ID.
- Warnings are printed if defaults are used or if the config matches defaults exactly—edit to avoid this.
- CLI flags override config values (Python/Lua only; PHP uses config.json exclusively).

## Usage
### Python/Lua CLI
Run the script with options and an action. The Lua version has **exactly the same usage** as Python.

#### Syntax
```
./nuki3ctl.py [options] [action]
```
or
```
./nuki3ctl.lua [options] [action]
```

#### Options
- `-i, --ip <IP>`: Nuki Bridge IP address (overrides config.json).
- `-t, --token <TOKEN>`: API token (overrides config.json).
- `-id, --nukiid <ID>`: Nuki device ID (overrides config.json; required for actions except 'list').
- `-h, --help`: Show usage help (no action needed).

#### Actions
- `open`: Unlock the door (action=1 in API).
- `close`: Lock the door (action=2 in API).
- `status`: Get current lock state (real-time poll; use sparingly to save battery).
- `list`: List all devices with info (JSON output).

IP and token are always required (via flags or config). For 'open', 'close', 'status', device ID is required.

#### Examples
1. List devices using config defaults:
   ```
   ./nuki3ctl.py list
   ```
   Output: JSON array of devices (e.g., state, battery).

2. Unlock with overrides:
   ```
   ./nuki3ctl.py -i 192.168.107.194 -t 1mytkn -id 123456789 open
   ```
   Output: JSON response (e.g., {"success": true}).

3. Get status:
   ```
   ./nuki3ctl.py -i 192.168.107.194 -t 1mytkn -id 123456789 status
   ```
   Output: JSON with state (e.g., {"state": 3, "stateName": "unlocked"}).

4. Help:
   ```
   ./nuki3ctl.py -h
   ```

### PHP Web Interface (`nuki3ctl.php`)
Access via browser (e.g., http://your-router-ip/nuki3ctl.php or rename to index.php).
- Displays devices as cards with name, ID, state text, and a colored div (red=locked/state 1, green=unlocked/state 3, default gray for others).
- Click the div to toggle state (unlock if locked, lock if unlocked) via API and reload the page.
- No CLI args; uses config.json for IP/token.
- Example: If multiple devices, each has its own clickable status box.

## Notes
- **Lua Parity**: The Lua script mirrors Python exactly, including config handling, warnings, and output. Use it on resource-constrained systems like OpenWRT.
- **Direct Execution**: Thanks to shebangs, run CLI as executables (e.g., add to PATH for `nuki3ctl.py list`).
- **Security**: Token is sent in plain text; use on trusted LAN. For production, consider hashed auth (not implemented here).
- **Battery Tip**: 'status' polls via Bluetooth—limit usage.
- **Troubleshooting**: If errors (e.g., HTTP 401), check token/IP. Bridge must be in range of lock.

If you need expansions (e.g., more actions like unlatch), provide details.