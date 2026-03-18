from typing import Any, Dict
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config import Settings

class SpotifyService:
    def __init__(self, settings: Settings):
        if not settings.playlist_id:
            raise ValueError("Missing Spotify playlist ID")

        if not settings.client_id or not settings.client_secret or not settings.redirect_uri:
            raise ValueError("Missing Spotify API credentials")

        self._playlist_id = settings.playlist_id
        self._playlist_offset = settings.playlist_offset
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                settings.client_id,
                settings.client_secret,
                settings.redirect_uri,
                scope="playlist-read-private",
            )
        )

    def get_playlist_details(self) -> tuple[str, str]:
        """Retrieve the playlist name and description."""
        details = self.sp.playlist(self._playlist_id)
        return details["name"], details["description"]

    def get_playlist(self) -> Dict[str, Any]:
        """
        Retrieve the playlist tracks.
        Returns a dictionary containing track details, limited to 100 tracks per request.
        """
        return self.sp.playlist_tracks(self._playlist_id, limit=100, offset=self._playlist_offset)
    
    def next(self, playlist) -> Dict[str, Any]:
        """
        Retrieve the next batch of tracks.
        """
        return self.sp.next(playlist)
