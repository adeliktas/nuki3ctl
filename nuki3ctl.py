#!/usr/bin/env python
import argparse
import json
import os
import requests
import time

# Docs used:
# https://nuki-shop-prod-eu-content.s3.de.perf.cloud.ovh.net/legacy/2024/10/20241024NukiBridgeAPI1_13_3.pdf

# Global variables as requested
nuki_ip = None
nuki_token = None
nuki_devices_list = []  # Will be populated as list of NukiDevice instances when listing

# Define default config as a constant for comparison
DEFAULT_CONFIG = {
    'ip': '0.0.0.0',
    'token': '1mytkn',
    'nukiId': '123456789',
    'retry': 3
}

class NukiDevice:
    """
    Class representing a Nuki device based on the /list JSON response structure.
    Attributes correspond to the keys in the API response for Smart Lock 3.0.
    """
    def __init__(self, data):
        self.deviceType = data.get('deviceType')
        self.nukiId = data.get('nukiId')
        self.name = data.get('name')
        self.firmwareVersion = data.get('firmwareVersion')
        self.lastKnownState = data.get('lastKnownState', {})
        # Expand lastKnownState attributes for easier access (based on API docs)
        if self.lastKnownState:
            self.mode = self.lastKnownState.get('mode')
            self.state = self.lastKnownState.get('state')
            self.stateName = self.lastKnownState.get('stateName')
            self.batteryCritical = self.lastKnownState.get('batteryCritical')
            self.batteryCharging = self.lastKnownState.get('batteryCharging')
            self.batteryChargeState = self.lastKnownState.get('batteryChargeState')
            self.keypadBatteryCritical = self.lastKnownState.get('keypadBatteryCritical')
            self.doorsensorState = self.lastKnownState.get('doorsensorState')
            self.doorsensorStateName = self.lastKnownState.get('doorsensorStateName')
            self.timestamp = self.lastKnownState.get('timestamp')

    def __repr__(self):
        return json.dumps(self.__dict__, indent=4, default=str)

def load_config():
    """Load defaults from config.json if it exists, or create a default if not."""
    config_path = 'config.json'
    if not os.path.exists(config_path):
        try:
            with open(config_path, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            print(f"Created default {config_path}. Please edit it with your values.")
        except IOError as e:
            print(f"Error creating {config_path}: {e}")
            return {}
    
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            # Check if loaded config matches defaults exactly
            if config == DEFAULT_CONFIG:
                print("Warning: config.json contains default values. Please edit it with your actual settings.")
        except json.JSONDecodeError:
            print("Warning: config.json is malformed. Ignoring it.")
    return config

def resolve_name_to_id(base_url, token, device_name):
    """Fetch device list and resolve name to nukiId (first match)."""
    try:
        response = requests.get(f"{base_url}/list?token={token}", timeout=10)
        response.raise_for_status()
        devices_data = response.json()
        for device in devices_data:
            if device.get('name') == device_name:
                return device['nukiId']
        raise ValueError(f"No device found with name '{device_name}'.")
    except requests.RequestException as e:
        raise ValueError(f"Error fetching device list for name resolution: {e}")

def perform_action_with_retry(url, retry_count, action_desc):
    """Perform HTTP GET with retries and 1s delay on failure."""
    success = False
    last_resp = None
    for attempt in range(1, retry_count + 1):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            last_resp = response.json()
            if last_resp.get('success', False) or 'state' in last_resp:  # For status, no 'success' key
                success = True
                break
        except requests.RequestException as e:
            print(f"Attempt {attempt} failed for {action_desc}: {e}")
        time.sleep(1)  # 1s delay after failure
    return success, last_resp

def main():
    global nuki_ip, nuki_token, nuki_devices_list

    parser = argparse.ArgumentParser(
        description="Nuki Smart Lock CLI tool using HTTP API (v1.13.3). Defaults from config.json if not overridden.",
        epilog="Example: python nuki3ctl.py -i 192.168.107.194 -t 1mytkn -id 123456789 open"
    )
    parser.add_argument('-i', '--ip', help='Nuki Bridge IP address (overrides config.json)')
    parser.add_argument('-t', '--token', help='API token (overrides config.json)')
    parser.add_argument('-id', '--nukiid', help='Nuki device ID (overrides config.json)')
    parser.add_argument('-n', '--name', help='Nuki device name (resolves to ID; overrides if -id not set)')
    parser.add_argument('-r', '--retry', type=int, help='Retry count for actions (overrides config.json, default 3)')
    parser.add_argument('action', nargs='?', choices=['open', 'close', 'status', 'list', 'info', 'openall', 'closeall'],
                        help='Action: open (unlock), close (lock), status (current state), list (all devices), info (bridge info), openall (unlock all), closeall (lock all)')
    args = parser.parse_args()

    # Load config and apply overrides
    config = load_config()
    nuki_ip = args.ip or config.get('ip')
    nuki_token = args.token or config.get('token')
    nuki_id = args.nukiid or config.get('nukiId')
    retry = args.retry or config.get('retry', 3)

    # Warn if using defaults from config
    if args.ip is None and nuki_ip:
        print(f"Using default IP from config.json: {nuki_ip}")
    if args.token is None and nuki_token:
        print(f"Using default token from config.json: {nuki_token}")
    if args.action not in ['list', 'info', 'openall', 'closeall'] and args.nukiid is None and nuki_id:
        print(f"Using default Nuki ID from config.json: {nuki_id}")
    if args.retry is None and 'retry' in config:
        print(f"Using default retry from config.json: {retry}")

    if not nuki_ip or not nuki_token:
        parser.error("IP and token are required (via flags or config.json).")

    base_url = f"http://{nuki_ip}:8080"

    # Resolve --name to ID if provided and no --id (for device-specific actions)
    if args.action in ['open', 'close', 'status']:
        if not args.nukiid and args.name:
            try:
                nuki_id = resolve_name_to_id(base_url, nuki_token, args.name)
                print(f"Resolved name '{args.name}' to ID: {nuki_id}")
            except ValueError as e:
                parser.error(str(e))
        if not nuki_id:
            parser.error("Nuki ID or name is required for this action (via -id, --name, or config.json).")

    if args.action == 'list':
        try:
            response = requests.get(f"{base_url}/list?token={nuki_token}", timeout=10)
            response.raise_for_status()
            devices_data = response.json()
            nuki_devices_list = [NukiDevice(device) for device in devices_data]
            print(json.dumps([device.__dict__ for device in nuki_devices_list], indent=4, default=str))
        except requests.RequestException as e:
            print(f"Error listing devices: {e}")
        return

    if args.action == 'info':
        try:
            response = requests.get(f"{base_url}/info?token={nuki_token}", timeout=10)
            response.raise_for_status()
            print(json.dumps(response.json(), indent=4))
        except requests.RequestException as e:
            print(f"Error getting bridge info: {e}")
        return

    if args.action in ['openall', 'closeall']:
        action_num = 1 if args.action == 'openall' else 2
        action_verb = 'Unlocked' if action_num == 1 else 'Locked'
        try:
            # Fetch list first
            response = requests.get(f"{base_url}/list?token={nuki_token}", timeout=10)
            response.raise_for_status()
            devices_data = response.json()
            for device in devices_data:
                dev_id = device['nukiId']
                dev_name = device.get('name', 'Unnamed')
                url = f"{base_url}/lockAction?nukiId={dev_id}&action={action_num}&token={nuki_token}&deviceType=4"
                success, last_resp = perform_action_with_retry(url, retry, f"{action_verb.lower()} {dev_name} (ID: {dev_id})")
                if success:
                    print(f"{action_verb} {dev_name} (ID: {dev_id}): {last_resp}")
                else:
                    print(f"Failed to {action_verb.lower()} {dev_name} (ID: {dev_id}) after {retry} attempts: {last_resp}")
        except requests.RequestException as e:
            print(f"Error {action_verb.lower()} all: {e}")
        return

    # For single device actions with retry
    url = None
    action_desc = None
    if args.action == 'open':
        url = f"{base_url}/lockAction?nukiId={nuki_id}&action=1&token={nuki_token}&deviceType=4"
        action_desc = "open device"
    elif args.action == 'close':
        url = f"{base_url}/lockAction?nukiId={nuki_id}&action=2&token={nuki_token}&deviceType=4"
        action_desc = "close device"
    elif args.action == 'status':
        url = f"{base_url}/lockState?nukiId={nuki_id}&token={nuki_token}&deviceType=4"
        action_desc = "get status"

    success, last_resp = perform_action_with_retry(url, retry, action_desc)
    if success:
        print(json.dumps(last_resp, indent=4))
    else:
        print(f"Failed after {retry} attempts: {json.dumps(last_resp, indent=4)}")

if __name__ == "__main__":
    main()