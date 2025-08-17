#!/usr/bin/env python3
"""
Spotify OAuth Token Generator
Runs the OAuth flow to get access and refresh tokens, then saves them to creds.json
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv, set_key
from spotipy.oauth2 import SpotifyOAuth

# Load existing .env file
load_dotenv()

# Get credentials from environment
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env")
    sys.exit(1)

# Define the scopes needed
SCOPES = [
    "user-library-read",
    "user-read-playback-state", 
    "user-modify-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-private",
    "playlist-modify-public"
]

def main():
    print("Spotify OAuth Token Generator")
    print("=" * 40)
    print(f"Client ID: {CLIENT_ID}")
    print(f"Redirect URI: {REDIRECT_URI}")
    print()
    
    # Create auth manager
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=" ".join(SCOPES),
        open_browser=True
    )
    
    print("Opening browser for authorization...")
    print("If the browser doesn't open automatically, please visit this URL:")
    print(auth_manager.get_authorize_url())
    print()
    
    # Get the authorization code from the user
    auth_code = auth_manager.get_auth_response()
    
    if not auth_code:
        print("Error: No authorization code received")
        sys.exit(1)
    
    # Exchange code for tokens
    print("Getting tokens...")
    token_info = auth_manager.get_access_token(auth_code)
    
    if not token_info:
        print("Error: Failed to get tokens")
        sys.exit(1)
    
    access_token = token_info.get("access_token")
    refresh_token = token_info.get("refresh_token")
    
    if not access_token or not refresh_token:
        print("Error: Missing tokens in response")
        sys.exit(1)
    
    print("\nTokens obtained successfully!")
    print(f"Access Token: {access_token[:20]}...")
    print(f"Refresh Token: {refresh_token[:20]}...")
    
    # Save to .env file (for local development)
    env_path = ".env"
    print(f"\nSaving tokens to {env_path}...")
    
    # Read existing .env content
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
    
    # Update or add token lines
    access_token_set = False
    refresh_token_set = False
    
    for i, line in enumerate(env_lines):
        if line.startswith('SPOTIFY_ACCESS_TOKEN='):
            env_lines[i] = f'SPOTIFY_ACCESS_TOKEN={access_token}\n'
            access_token_set = True
        elif line.startswith('SPOTIFY_REFRESH_TOKEN='):
            env_lines[i] = f'SPOTIFY_REFRESH_TOKEN={refresh_token}\n'
            refresh_token_set = True
    
    # Add tokens if not found
    if not access_token_set:
        env_lines.append(f'SPOTIFY_ACCESS_TOKEN={access_token}\n')
    if not refresh_token_set:
        env_lines.append(f'SPOTIFY_REFRESH_TOKEN={refresh_token}\n')
    
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
    
    # Update with new tokens
    creds.update({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "access_token": access_token,
        "refresh_token": refresh_token
    })
    
    # Save to file
    try:
        with open(creds_file, 'w') as f:
            json.dump(creds, f, indent=2)
        print(f"\nAlso saved to {creds_file} for persistent storage")
    except Exception as e:
        print(f"Note: Could not save to {creds_file}: {e}")
    
    print("\nTokens saved successfully!")
    print("\nYou can now use these tokens in your Docker container.")
    print("Mount /config as a volume to persist tokens across container restarts.")
    print("\nThe refresh token will be used to automatically get new access tokens as needed.")

if __name__ == "__main__":
    main()