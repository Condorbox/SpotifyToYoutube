import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config import client_id, client_secret, redirect_uri, spoti_playlist_id, playlist_offset

class SpotifyService:
    def __init__(self):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id, client_secret, redirect_uri, scope="playlist-read-private"))

    def get_playlist_details(self) -> tuple[str, str]:
        """Retrieve the playlist name and description."""
        details = self.sp.playlist(spoti_playlist_id)
        return details["name"], details["description"]

    def get_playlist(self):
        return self.sp.playlist_tracks(spoti_playlist_id, limit=100, offset=playlist_offset)
    
    def next(self, playlist):
        return self.sp.next(playlist)