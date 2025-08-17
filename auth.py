#!/usr/bin/env python3
"""
Spotify OAuth Token Generator
Runs the OAuth flow to get access and refresh tokens, then saves them to .env
"""

import os
import sys
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
    
    # Save to .env file
    env_path = ".env"
    print(f"\nSaving tokens to {env_path}...")
    
    set_key(env_path, "SPOTIFY_ACCESS_TOKEN", access_token)
    set_key(env_path, "SPOTIFY_REFRESH_TOKEN", refresh_token)
    
    print("Tokens saved successfully!")
    print("\nYou can now use these tokens in your Docker container by setting:")
    print("  SPOTIFY_ACCESS_TOKEN")
    print("  SPOTIFY_REFRESH_TOKEN")
    print("\nThe refresh token will be used to automatically get new access tokens as needed.")

if __name__ == "__main__":
    main()