
from typing import Set
import google_auth_oauthlib.flow
import googleapiclient.discovery
from config import json_url

class YouTubeService:
    def __init__(self):
        self.youtube = self._authenticate()

    def _authenticate(self):
        """Authenticate and return a YouTube API client."""
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            json_url,
            ["https://www.googleapis.com/auth/youtube.force-ssl"]
        )   

        credentials = flow.run_local_server(port=8080, prompt="consent")
        return googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
    
    def get_or_create_playlist_id(self, title: str, description: str = "Playlist from Spotify") -> str:
        """
        Retrieve an existing playlist ID by title or create a new one if it doesn't exist.
        
        If `description` is not provided, defaults to 'Playlist from Spotify'.
        """
        playlists = self.youtube.playlists().list(part="snippet", mine=True).execute()
        for playlist in playlists.get("items", []):
            if playlist["snippet"]["title"] == title:
                return playlist["id"]
            
        # Create playlist
        response = self.youtube.playlists().insert(
            part='snippet,status',
            body={
                'snippet': {
                    'title': title,
                    'description': description
                },
                'status': {
                    'privacyStatus': 'private'
                }
            }
        ).execute()

        return response["id"]
    
    def get_existing_video_ids(self, playlist_id: str) -> Set[str]:
        """
        Retrieve a set of video IDs currently in the given playlist.
        """
        video_ids = set()
        request = self.youtube.playlistItems().list(part="snippet", playlistId=playlist_id, maxResults=50) # YouTube API allows up to 50 per request
        while request:
            response = request.execute()
            video_ids.update(item["snippet"]["resourceId"]["videoId"] for item in response.get("items", []))
            request = self.youtube.playlistItems().list_next(request, response)
        return video_ids
    
    def add_song_to_playlist(self, video_id: str, playlist_id: str):
        """
        Add a video to a playlist using its video ID.
        """
        self.youtube.playlistItems().insert(
            part='snippet',
            body={
                'snippet': {
                    'playlistId': playlist_id,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video_id
                    }
                }
            }
        ).execute()


