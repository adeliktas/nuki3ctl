#!/usr/bin/env python
import argparse
import json
import os
import requests

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
    'nukiId': '123456789'
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

def main():
    global nuki_ip, nuki_token, nuki_devices_list

    parser = argparse.ArgumentParser(
        description="Nuki Smart Lock CLI tool using HTTP API (v1.13.3). Defaults from config.json if not overridden.",
        epilog="Example: python nuki3ctl.py -i 192.168.107.194 -t 1mytkn -id 123456789 open"
    )
    parser.add_argument('-i', '--ip', help='Nuki Bridge IP address (overrides config.json)')
    parser.add_argument('-t', '--token', help='API token (overrides config.json)')
    parser.add_argument('-id', '--nukiid', help='Nuki device ID (overrides config.json)')
    parser.add_argument('action', nargs='?', choices=['open', 'close', 'status', 'list'],
                        help='Action: open (unlock), close (lock), status (current state), list (all devices)')
    args = parser.parse_args()

    # Load config and apply overrides
    config = load_config()
    nuki_ip = args.ip or config.get('ip')
    nuki_token = args.token or config.get('token')
    nuki_id = args.nukiid or config.get('nukiId')

    # Warn if using defaults from config
    if args.ip is None and nuki_ip:
        print(f"Using default IP from config.json: {nuki_ip}")
    if args.token is None and nuki_token:
        print(f"Using default token from config.json: {nuki_token}")
    if args.action != 'list' and args.nukiid is None and nuki_id:
        print(f"Using default Nuki ID from config.json: {nuki_id}")

    if not nuki_ip or not nuki_token:
        parser.error("IP and token are required (via flags or config.json).")

    base_url = f"http://{nuki_ip}:8080"

    if args.action == 'list':
        try:
            response = requests.get(f"{base_url}/list?token={nuki_token}")
            response.raise_for_status()
            devices_data = response.json()
            nuki_devices_list = [NukiDevice(device) for device in devices_data]
            print(json.dumps([device.__dict__ for device in nuki_devices_list], indent=4, default=str))
        except requests.RequestException as e:
            print(f"Error listing devices: {e}")
        return

    if not nuki_id:
        parser.error("Nuki ID is required for actions other than 'list' (via -id or config.json).")

    if args.action == 'open':
        # Action=1: unlock (based on API: unlocks the lock)
        try:
            response = requests.get(f"{base_url}/lockAction?nukiId={nuki_id}&action=1&token={nuki_token}&deviceType=4")
            response.raise_for_status()
            print(response.json())
        except requests.RequestException as e:
            print(f"Error opening device: {e}")

    elif args.action == 'close':
        # Action=2: lock (based on API: locks the lock)
        try:
            response = requests.get(f"{base_url}/lockAction?nukiId={nuki_id}&action=2&token={nuki_token}&deviceType=4")
            response.raise_for_status()
            print(response.json())
        except requests.RequestException as e:
            print(f"Error closing device: {e}")

    elif args.action == 'status':
        # Use /lockState for current real-time status (polls device; use sparingly for battery)
        try:
            response = requests.get(f"{base_url}/lockState?nukiId={nuki_id}&token={nuki_token}&deviceType=4")
            response.raise_for_status()
            print(response.json())
        except requests.RequestException as e:
            print(f"Error getting status: {e}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
