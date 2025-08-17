#!/usr/bin/env python3
"""
Spotify Device Selector
Lists available Spotify devices and saves the selected device name to .env and creds.json
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv, set_key
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Load existing .env file
load_dotenv()

# Get credentials from environment
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888")
ACCESS_TOKEN = os.getenv("SPOTIFY_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env")
    sys.exit(1)

def get_spotify_client():
    """Create Spotify client using tokens or OAuth"""
    if REFRESH_TOKEN:
        # Use refresh token
        from spotipy.cache_handler import MemoryCacheHandler
        import time
        
        cache_handler = MemoryCacheHandler()
        token_info = {
            "access_token": ACCESS_TOKEN or "",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": REFRESH_TOKEN,
            "scope": "user-read-playback-state",
            "expires_at": int(time.time()) - 1 if not ACCESS_TOKEN else int(time.time()) + 3600
        }
        cache_handler.save_token_to_cache(token_info)
        
        auth_manager = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            cache_handler=cache_handler,
            scope="user-read-playback-state"
        )
        return spotipy.Spotify(auth_manager=auth_manager)
    elif ACCESS_TOKEN:
        # Use access token directly
        return spotipy.Spotify(auth=ACCESS_TOKEN)
    else:
        # Use OAuth flow
        auth_manager = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope="user-read-playback-state"
        )
        return spotipy.Spotify(auth_manager=auth_manager)

def main():
    print("Spotify Device Selector")
    print("=" * 40)
    
    try:
        # Get Spotify client
        sp = get_spotify_client()
        
        # Get available devices
        print("\nFetching available devices...")
        devices_response = sp.devices()
        devices = devices_response.get('devices', [])
        
        if not devices:
            print("\nNo devices found!")
            print("Make sure Spotify is open on at least one device (desktop app, phone, web player, etc.)")
            sys.exit(1)
        
        # Display devices
        print(f"\nFound {len(devices)} device(s):\n")
        for i, device in enumerate(devices, 1):
            status = "🎵 ACTIVE" if device.get('is_active') else "⏸  Inactive"
            restricted = " [Restricted]" if device.get('is_restricted') else ""
            print(f"{i}. {device['name']} ({device['type']}){restricted}")
            print(f"   ID: {device['id']}")
            print(f"   Volume: {device.get('volume_percent', 'N/A')}%")
            print(f"   Status: {status}")
            print()
        
        # Get user selection
        while True:
            try:
                choice = input(f"Select a device (1-{len(devices)}) or 0 to cancel: ").strip()
                if choice == '0':
                    print("Cancelled")
                    sys.exit(0)
                
                device_index = int(choice) - 1
                if 0 <= device_index < len(devices):
                    selected_device = devices[device_index]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(devices)}")
            except ValueError:
                print("Please enter a valid number")
        
        # Save to .env
        device_id = selected_device['id']
        device_name = selected_device['name']
        
        print(f"\nSelected: {device_name}")
        print(f"Device ID: {device_id}")
        
        # Save to .env file
        env_path = ".env"
        print(f"\nSaving device name to {env_path}...")
        
        # Read existing .env content
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add device name line
        device_name_set = False
        
        for i, line in enumerate(env_lines):
            if line.startswith('SPOTIFY_DEVICE_NAME='):
                env_lines[i] = f'SPOTIFY_DEVICE_NAME={device_name}\n'
                device_name_set = True
                break
        
        # Add device name if not found
        if not device_name_set:
            env_lines.append(f'SPOTIFY_DEVICE_NAME={device_name}\n')
        
        # Write back to file
        with open(env_path, 'w') as f:
            f.writelines(env_lines)
        
        # Also save to creds.json in current directory for persistent storage
        creds_file = Path("creds.json")
        
        # Load existing creds or create new
        creds = {}
        if creds_file.exists():
            try:
                with open(creds_file, 'r') as f:
                    creds = json.load(f)
            except:
                pass
        
        # Update with device name
        creds["device_name"] = device_name
        
        # Save to file
        try:
            with open(creds_file, 'w') as f:
                json.dump(creds, f, indent=2)
            print(f"Also saved to {creds_file} for persistent storage")
        except Exception as e:
            print(f"Note: Could not save to {creds_file}: {e}")
        
        print("\nDevice name saved successfully!")
        print(f"\nYou can now use this device as the default for all Spotify operations.")
        print(f"The environment variable SPOTIFY_DEVICE_NAME has been set to: {device_name}")
        print(f"The device will be looked up by name when the server starts.")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nMake sure:")
        print("1. Your access token is valid (run auth.py if needed)")
        print("2. Spotify is open on at least one device")
        print("3. You have the necessary permissions")
        sys.exit(1)

if __name__ == "__main__":
    main()