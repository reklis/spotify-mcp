#!/usr/bin/env python3
"""
Spotify Device Selector
Lists available Spotify devices and saves the selected device ID to .env
"""

import os
import sys
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
        
        env_path = ".env"
        print(f"\nSaving device ID to {env_path}...")
        set_key(env_path, "SPOTIFY_DEVICE_ID", device_id)
        
        print("Device ID saved successfully!")
        print(f"\nYou can now use this device as the default for all Spotify operations.")
        print(f"The environment variable SPOTIFY_DEVICE_ID has been set to: {device_id}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nMake sure:")
        print("1. Your access token is valid (run auth.py if needed)")
        print("2. Spotify is open on at least one device")
        print("3. You have the necessary permissions")
        sys.exit(1)

if __name__ == "__main__":
    main()