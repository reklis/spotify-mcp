"""
Credential manager for persistent token storage
Manages credentials in /config/creds.json with fallback to environment variables
"""

import json
import os
from typing import Optional, Dict
from pathlib import Path

class CredsManager:
    def __init__(self, config_dir: str = "/config", logger=None):
        self.config_dir = Path(config_dir)
        self.creds_file = self.config_dir / "creds.json"
        self.logger = logger
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load initial credentials
        self.creds = self._load_credentials()
    
    def _load_credentials(self) -> Dict[str, Optional[str]]:
        """Load credentials from file or environment variables"""
        creds = {
            "client_id": os.getenv("SPOTIFY_CLIENT_ID"),
            "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET"),
            "redirect_uri": os.getenv("SPOTIFY_REDIRECT_URI"),
            "access_token": os.getenv("SPOTIFY_ACCESS_TOKEN"),
            "refresh_token": os.getenv("SPOTIFY_REFRESH_TOKEN"),
            "device_name": os.getenv("SPOTIFY_DEVICE_NAME"),
        }
        
        # Try to load from file if it exists
        if self.creds_file.exists():
            try:
                with open(self.creds_file, 'r') as f:
                    file_creds = json.load(f)
                    
                # File takes precedence for tokens (they might be updated)
                # But env vars take precedence for client credentials
                if file_creds.get("access_token"):
                    creds["access_token"] = file_creds["access_token"]
                if file_creds.get("refresh_token"):
                    creds["refresh_token"] = file_creds["refresh_token"]
                
                # Use file values if env vars not set
                for key in ["client_id", "client_secret", "redirect_uri", "device_name"]:
                    if not creds[key] and file_creds.get(key):
                        creds[key] = file_creds[key]
                
                if self.logger:
                    self.logger.info(f"Loaded credentials from {self.creds_file}")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to load creds.json: {str(e)}")
        else:
            if self.logger:
                self.logger.info("No creds.json found, using environment variables")
        
        return creds
    
    def save_credentials(self):
        """Save current credentials to file"""
        try:
            with open(self.creds_file, 'w') as f:
                json.dump(self.creds, f, indent=2)
            if self.logger:
                self.logger.info(f"Saved credentials to {self.creds_file}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save credentials: {str(e)}")
    
    def update_tokens(self, access_token: Optional[str] = None, refresh_token: Optional[str] = None):
        """Update tokens and save to file"""
        if access_token:
            self.creds["access_token"] = access_token
        if refresh_token:
            self.creds["refresh_token"] = refresh_token
        self.save_credentials()
    
    def get_client_id(self) -> Optional[str]:
        return self.creds.get("client_id")
    
    def get_client_secret(self) -> Optional[str]:
        return self.creds.get("client_secret")
    
    def get_redirect_uri(self) -> Optional[str]:
        return self.creds.get("redirect_uri")
    
    def get_access_token(self) -> Optional[str]:
        return self.creds.get("access_token")
    
    def get_refresh_token(self) -> Optional[str]:
        return self.creds.get("refresh_token")
    
    def get_device_name(self) -> Optional[str]:
        return self.creds.get("device_name")
    
    def set_device_name(self, device_name: str):
        """Update device name and save"""
        self.creds["device_name"] = device_name
        self.save_credentials()