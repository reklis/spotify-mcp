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
        
        if self.logger:
            self.logger.info(f"CredsManager initializing with config_dir: {self.config_dir}")
            self.logger.info(f"Credentials file path: {self.creds_file}")
        
        # Ensure config directory exists
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            if self.logger:
                self.logger.info(f"Config directory created/verified: {self.config_dir}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to create config directory: {str(e)}")
        
        # Load initial credentials
        self.creds = self._load_credentials()
    
    def _load_credentials(self) -> Dict[str, Optional[str]]:
        """Load credentials from file first, then fall back to environment variables"""
        # Start with empty credentials
        creds = {
            "client_id": None,
            "client_secret": None,
            "redirect_uri": None,
            "access_token": None,
            "refresh_token": None,
            "device_name": None,
            "token_expires_at": None,
        }
        
        # First, try to load from file if it exists (PRIORITY)
        if self.creds_file.exists():
            try:
                with open(self.creds_file, 'r') as f:
                    file_creds = json.load(f)
                    
                # Use all values from file first
                for key in creds.keys():
                    if file_creds.get(key) is not None:
                        creds[key] = file_creds[key]
                
                if self.logger:
                    self.logger.info(f"Loaded credentials from {self.creds_file}")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to load creds.json: {str(e)}")
        
        # Then, use environment variables as fallback for any missing values
        env_mapping = {
            "client_id": "SPOTIFY_CLIENT_ID",
            "client_secret": "SPOTIFY_CLIENT_SECRET",
            "redirect_uri": "SPOTIFY_REDIRECT_URI",
            "access_token": "SPOTIFY_ACCESS_TOKEN",
            "refresh_token": "SPOTIFY_REFRESH_TOKEN",
            "device_name": "SPOTIFY_DEVICE_NAME",
        }
        
        for key, env_var in env_mapping.items():
            if creds[key] is None:
                env_value = os.getenv(env_var)
                if env_value:
                    creds[key] = env_value
                    if self.logger:
                        self.logger.info(f"Using {env_var} from environment for {key}")
        
        return creds
    
    def save_credentials(self):
        """Save current credentials to file"""
        try:
            # Log what we're about to save (without sensitive data)
            if self.logger:
                self.logger.info(f"Attempting to save credentials to {self.creds_file}")
                self.logger.info(f"Config directory exists: {self.config_dir.exists()}")
                self.logger.info(f"Config directory is writable: {os.access(self.config_dir, os.W_OK)}")
                
                # Log which credentials are present (not the values)
                creds_status = {
                    key: "present" if self.creds.get(key) else "missing"
                    for key in self.creds.keys()
                }
                self.logger.info(f"Credentials status: {creds_status}")
            
            with open(self.creds_file, 'w') as f:
                json.dump(self.creds, f, indent=2)
            
            if self.logger:
                self.logger.info(f"Successfully saved credentials to {self.creds_file}")
                # Verify the file was written
                if self.creds_file.exists():
                    file_size = self.creds_file.stat().st_size
                    self.logger.info(f"Verified: File exists with size {file_size} bytes")
                else:
                    self.logger.error(f"Warning: File {self.creds_file} does not exist after write!")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save credentials: {str(e)}", exc_info=True)
    
    def update_tokens(self, access_token: Optional[str] = None, refresh_token: Optional[str] = None, token_expires_at: Optional[float] = None):
        """Update tokens and save to file"""
        if self.logger:
            self.logger.info("update_tokens called")
            self.logger.info(f"Updating: access_token={'yes' if access_token is not None else 'no'}, "
                           f"refresh_token={'yes' if refresh_token is not None else 'no'}, "
                           f"expires_at={'yes' if token_expires_at is not None else 'no'}")
        
        if access_token is not None:
            self.creds["access_token"] = access_token
        if refresh_token is not None:
            self.creds["refresh_token"] = refresh_token
        if token_expires_at is not None:
            self.creds["token_expires_at"] = token_expires_at
        
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
    
    def get_token_expires_at(self) -> Optional[float]:
        return self.creds.get("token_expires_at")
    
    def set_device_name(self, device_name: str):
        """Update device name and save"""
        self.creds["device_name"] = device_name
        self.save_credentials()