import logging
import os
import time
from typing import Optional, Dict, List

import spotipy
from dotenv import load_dotenv
from spotipy.cache_handler import CacheFileHandler, MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth

from . import utils

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
ACCESS_TOKEN = os.getenv("SPOTIFY_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")
DEFAULT_DEVICE_ID = os.getenv("SPOTIFY_DEVICE_ID")

# Normalize the redirect URI to meet Spotify's requirements
if REDIRECT_URI:
    REDIRECT_URI = utils.normalize_redirect_uri(REDIRECT_URI)

SCOPES = ["user-read-currently-playing", "user-read-playback-state", "user-read-currently-playing",  # spotify connect
          "app-remote-control", "streaming",  # playback
          "playlist-read-private", "playlist-read-collaborative", "playlist-modify-private", "playlist-modify-public",
          # playlists
          "user-read-playback-position", "user-top-read", "user-read-recently-played",  # listening history
          "user-library-modify", "user-library-read",  # library
          ]


class Client:
    def __init__(self, logger: logging.Logger):
        """Initialize Spotify client with necessary permissions"""
        self.logger = logger

        scope = "user-library-read,user-read-playback-state,user-modify-playback-state,user-read-currently-playing,playlist-read-private,playlist-read-collaborative,playlist-modify-private,playlist-modify-public"

        try:
            if REFRESH_TOKEN:
                # Use refresh token to get access token
                self.logger.info(f"Using refresh token from environment variable")
                self.logger.info(f"ACCESS_TOKEN provided: {bool(ACCESS_TOKEN)}")
                self.logger.info(f"CLIENT_ID: {CLIENT_ID[:10]}..." if CLIENT_ID else "CLIENT_ID not set")
                
                # Create an in-memory cache with the refresh token
                cache_handler = MemoryCacheHandler()
                
                # If we have an access token, try to use it; otherwise force immediate refresh
                if ACCESS_TOKEN:
                    # Assume token is valid for a short time to allow testing
                    expires_at = int(time.time()) + 300  # 5 minutes
                    self.logger.info("ACCESS_TOKEN provided, assuming valid for 5 minutes")
                else:
                    # Force immediate refresh by setting expiry in the past
                    expires_at = int(time.time()) - 1
                    self.logger.info("No ACCESS_TOKEN, will refresh immediately")
                
                token_info = {
                    "access_token": ACCESS_TOKEN or "",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "refresh_token": REFRESH_TOKEN,
                    "scope": scope,
                    "expires_at": expires_at
                }
                cache_handler.save_token_to_cache(token_info)
                
                auth_manager = SpotifyOAuth(
                    scope=scope,
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET,
                    redirect_uri=REDIRECT_URI or "http://127.0.0.1:8888",
                    cache_handler=cache_handler
                )
                
                # This will automatically refresh the token if needed
                self.sp = spotipy.Spotify(auth_manager=auth_manager)
                self.auth_manager = auth_manager
                self.cache_handler = cache_handler
                self.logger.info("Spotify client initialized with refresh token")
                
            elif ACCESS_TOKEN:
                # Use provided access token directly (no refresh capability)
                self.logger.info("Using access token from environment variable (no refresh)")
                self.sp = spotipy.Spotify(auth=ACCESS_TOKEN)
                self.auth_manager = None
                self.cache_handler = None
            else:
                # Use OAuth flow with file cache
                self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    scope=scope,
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET,
                    redirect_uri=REDIRECT_URI))

                self.auth_manager: SpotifyOAuth = self.sp.auth_manager
                self.cache_handler: CacheFileHandler = self.auth_manager.cache_handler
        except Exception as e:
            self.logger.error(f"Failed to initialize Spotify client: {str(e)}")
            raise

        self.username = None

    @utils.validate
    def set_username(self, device=None):
        self.username = self.sp.current_user()['display_name']

    @utils.validate
    def search(self, query: str, qtype: str = 'track', limit=10, device=None):
        """
        Searches based of query term.
        - query: query term
        - qtype: the types of items to return. One or more of 'artist', 'album',  'track', 'playlist'.
                 If multiple types are desired, pass in a comma separated string; e.g. 'track,album'
        - limit: max # items to return
        """
        if self.username is None:
            self.set_username()
        results = self.sp.search(q=query, limit=limit, type=qtype)
        if not results:
            raise ValueError("No search results found.")
        return utils.parse_search_results(results, qtype, self.username)

    def recommendations(self, artists: Optional[List] = None, tracks: Optional[List] = None, limit=20):
        # doesnt work
        recs = self.sp.recommendations(seed_artists=artists, seed_tracks=tracks, limit=limit)
        return recs

    def get_info(self, item_uri: str) -> dict:
        """
        Returns more info about item.
        - item_uri: uri. Looks like 'spotify:track:xxxxxx', 'spotify:album:xxxxxx', etc.
        """
        _, qtype, item_id = item_uri.split(":")
        match qtype:
            case 'track':
                return utils.parse_track(self.sp.track(item_id), detailed=True)
            case 'album':
                album_info = utils.parse_album(self.sp.album(item_id), detailed=True)
                return album_info
            case 'artist':
                artist_info = utils.parse_artist(self.sp.artist(item_id), detailed=True)
                albums = self.sp.artist_albums(item_id)
                top_tracks = self.sp.artist_top_tracks(item_id)['tracks']
                albums_and_tracks = {
                    'albums': albums,
                    'tracks': {'items': top_tracks}
                }
                parsed_info = utils.parse_search_results(albums_and_tracks, qtype="album,track")
                artist_info['top_tracks'] = parsed_info['tracks']
                artist_info['albums'] = parsed_info['albums']

                return artist_info
            case 'playlist':
                if self.username is None:
                    self.set_username()
                playlist = self.sp.playlist(item_id)
                self.logger.info(f"playlist info is {playlist}")
                playlist_info = utils.parse_playlist(playlist, self.username, detailed=True)

                return playlist_info

        raise ValueError(f"Unknown qtype {qtype}")

    def get_current_track(self) -> Optional[Dict]:
        """Get information about the currently playing track"""
        try:
            # current_playback vs current_user_playing_track?
            current = self.sp.current_user_playing_track()
            if not current:
                self.logger.info("No playback session found")
                return None
            if current.get('currently_playing_type') != 'track':
                self.logger.info("Current playback is not a track")
                return None

            track_info = utils.parse_track(current['item'])
            if 'is_playing' in current:
                track_info['is_playing'] = current['is_playing']

            self.logger.info(
                f"Current track: {track_info.get('name', 'Unknown')} by {track_info.get('artist', 'Unknown')}")
            return track_info
        except Exception as e:
            self.logger.error("Error getting current track info.")
            raise

    @utils.validate
    def start_playback(self, spotify_uri=None, device=None):
        """
        Starts spotify playback of uri. If spotify_uri is omitted, resumes current playback.
        - spotify_uri: ID of resource to play, or None. Typically looks like 'spotify:track:xxxxxx' or 'spotify:album:xxxxxx'.
        """
        try:
            self.logger.info(f"start_playback called with spotify_uri: {spotify_uri}, device: {device}")
            self.logger.info(f"DEFAULT_DEVICE_ID is: {DEFAULT_DEVICE_ID}")
            
            if not spotify_uri:
                if self.is_track_playing():
                    self.logger.info("No track_id provided and playback already active.")
                    return
                if not self.get_current_track():
                    raise ValueError("No track_id provided and no current playback to resume.")

            if spotify_uri is not None:
                if spotify_uri.startswith('spotify:track:'):
                    uris = [spotify_uri]
                    context_uri = None
                else:
                    uris = None
                    context_uri = spotify_uri
            else:
                uris = None
                context_uri = None

            device_id = device.get('id') if device else DEFAULT_DEVICE_ID
            
            self.logger.info(f"About to call Spotify API with device_id={device_id}, context_uri={context_uri}, uris={uris}")
            result = self.sp.start_playback(uris=uris, context_uri=context_uri, device_id=device_id)
            self.logger.info(f"Spotify API returned: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error in start_playback: {str(e)}", exc_info=True)
            raise

    @utils.validate
    def pause_playback(self, device=None):
        """Pauses playback."""
        playback = self.sp.current_playback()
        if playback and playback.get('is_playing'):
            self.sp.pause_playback(device.get('id') if device else DEFAULT_DEVICE_ID)

    @utils.validate
    def add_to_queue(self, track_id: str, device=None):
        """
        Adds track to queue.
        - track_id: ID of track to play.
        """
        self.sp.add_to_queue(track_id, device.get('id') if device else DEFAULT_DEVICE_ID)

    @utils.validate
    def get_queue(self, device=None):
        """Returns the current queue of tracks."""
        queue_info = self.sp.queue()
        queue_info['currently_playing'] = self.get_current_track()

        queue_info['queue'] = [utils.parse_track(track) for track in queue_info.pop('queue')]

        return queue_info

    def get_liked_songs(self):
        # todo
        results = self.sp.current_user_saved_tracks()
        for idx, item in enumerate(results['items']):
            track = item['track']
            print(idx, track['artists'][0]['name'], " – ", track['name'])

    def is_track_playing(self) -> bool:
        """Returns if a track is actively playing."""
        curr_track = self.get_current_track()
        if not curr_track:
            return False
        if curr_track.get('is_playing'):
            return True
        return False

    def get_current_user_playlists(self, limit=50) -> List[Dict]:
        """
        Get current user's playlists.
        - limit: Max number of playlists to return.
        """
        playlists = self.sp.current_user_playlists()
        if not playlists:
            raise ValueError("No playlists found.")
        return [utils.parse_playlist(playlist, self.username) for playlist in playlists['items']]
    
    @utils.ensure_username
    def get_playlist_tracks(self, playlist_id: str, limit=50) -> List[Dict]:
        """
        Get tracks from a playlist.
        - playlist_id: ID of the playlist to get tracks from.
        - limit: Max number of tracks to return.
        """
        playlist = self.sp.playlist(playlist_id)
        if not playlist:
            raise ValueError("No playlist found.")
        return utils.parse_tracks(playlist['tracks']['items'])
    
    @utils.ensure_username
    def add_tracks_to_playlist(self, playlist_id: str, track_ids: List[str], position: Optional[int] = None):
        """
        Add tracks to a playlist.
        - playlist_id: ID of the playlist to modify.
        - track_ids: List of track IDs to add.
        - position: Position to insert the tracks at (optional).
        """
        if not playlist_id:
            raise ValueError("No playlist ID provided.")
        if not track_ids:
            raise ValueError("No track IDs provided.")
        
        try:
            response = self.sp.playlist_add_items(playlist_id, track_ids, position=position)
            self.logger.info(f"Response from adding tracks: {track_ids} to playlist {playlist_id}: {response}")
        except Exception as e:
            self.logger.error(f"Error adding tracks to playlist: {str(e)}")

    @utils.ensure_username
    def remove_tracks_from_playlist(self, playlist_id: str, track_ids: List[str]):
        """
        Remove tracks from a playlist.
        - playlist_id: ID of the playlist to modify.
        - track_ids: List of track IDs to remove.
        """
        if not playlist_id:
            raise ValueError("No playlist ID provided.")
        if not track_ids:
            raise ValueError("No track IDs provided.")
        
        try:
            response = self.sp.playlist_remove_all_occurrences_of_items(playlist_id, track_ids)
            self.logger.info(f"Response from removing tracks: {track_ids} from playlist {playlist_id}: {response}")
        except Exception as e:
            self.logger.error(f"Error removing tracks from playlist: {str(e)}")

    @utils.ensure_username
    def create_playlist(self, name: str, description: Optional[str] = None, public: bool = True):
        """
        Create a new playlist.
        - name: Name for the playlist.
        - description: Description for the playlist.
        - public: Whether the playlist should be public.
        """
        if not name:
            raise ValueError("Playlist name is required.")
        
        try:
            user = self.sp.current_user()
            user_id = user['id']
            
            playlist = self.sp.user_playlist_create(
                user=user_id,
                name=name,
                public=public,
                description=description
            )
            self.logger.info(f"Created playlist: {name} (ID: {playlist['id']})")
            return utils.parse_playlist(playlist, self.username, detailed=True)
        except Exception as e:
            self.logger.error(f"Error creating playlist: {str(e)}")
            raise

    @utils.ensure_username
    def change_playlist_details(self, playlist_id: str, name: Optional[str] = None, description: Optional[str] = None):
        """
        Change playlist details.
        - playlist_id: ID of the playlist to modify.
        - name: New name for the playlist.
        - public: Whether the playlist should be public.
        - description: New description for the playlist.
        """
        if not playlist_id:
            raise ValueError("No playlist ID provided.")
        
        try:
            response = self.sp.playlist_change_details(playlist_id, name=name, description=description)
            self.logger.info(f"Response from changing playlist details: {response}")
        except Exception as e:
            self.logger.error(f"Error changing playlist details: {str(e)}")
       
    def get_devices(self) -> dict:
        return self.sp.devices()['devices']

    def is_active_device(self):
        return any([device.get('is_active') for device in self.get_devices()])

    def _get_candidate_device(self):
        devices = self.get_devices()
        if not devices:
            raise ConnectionError("No active device. Is Spotify open?")
        for device in devices:
            if device.get('is_active'):
                return device
        self.logger.info(f"No active device, assigning {devices[0]['name']}.")
        return devices[0]

    def auth_ok(self) -> bool:
        try:
            # If using direct access token without refresh capability
            if ACCESS_TOKEN and not self.auth_manager:
                # When using direct token, we can't check expiration easily
                # Try a simple API call to verify token is valid
                try:
                    self.sp.current_user()
                    self.logger.info("Auth check result: token valid (direct token)")
                    return True
                except Exception as e:
                    self.logger.info(f"Auth check result: token invalid (direct token) - {str(e)}")
                    return False
            
            # If using auth manager (either OAuth flow or refresh token)
            if self.auth_manager and self.cache_handler:
                token = self.cache_handler.get_cached_token()
                if token is None:
                    self.logger.info("Auth check result: no token exists in cache")
                    return False
                    
                is_expired = self.auth_manager.is_token_expired(token)
                self.logger.info(f"Auth check result: token {'expired' if is_expired else 'valid'} (managed token)")
                return not is_expired  # Return True if token is NOT expired
            
            # No auth method available
            self.logger.error("Auth check result: no authentication method available")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking auth status: {str(e)}", exc_info=True)
            return False  # Return False on error rather than raising

    def auth_refresh(self):
        if not self.auth_manager:
            self.logger.warning("Cannot refresh token without auth manager")
            return
        
        try:
            self.logger.info("Attempting to refresh authentication token")
            token = self.cache_handler.get_cached_token()
            refreshed_token = self.auth_manager.validate_token(token)
            
            if refreshed_token:
                self.logger.info("Token refreshed successfully")
                # Update the Spotify client with the new token
                if refreshed_token != token:
                    self.sp._auth = refreshed_token.get('access_token')
            else:
                self.logger.error("Failed to refresh token")
        except Exception as e:
            self.logger.error(f"Error refreshing token: {str(e)}", exc_info=True)
            raise

    def skip_track(self, n=1):
        # todo: Better error handling
        for _ in range(n):
            self.sp.next_track(device_id=DEFAULT_DEVICE_ID)

    def previous_track(self):
        self.sp.previous_track(device_id=DEFAULT_DEVICE_ID)

    def seek_to_position(self, position_ms):
        self.sp.seek_track(position_ms=position_ms, device_id=DEFAULT_DEVICE_ID)

    def set_volume(self, volume_percent):
        self.sp.volume(volume_percent, device_id=DEFAULT_DEVICE_ID)
