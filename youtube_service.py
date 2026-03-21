import logging
import random
import time
from typing import Set, Any
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

from config import Settings
from utils import RETRYABLE_403_REASONS

logger = logging.getLogger(__name__)


class YouTubeQuotaExceededError(Exception):
    """Raised when the YouTube API quota has been exceeded."""
    pass


class YouTubeService:
    def __init__(self, settings: Settings, youtube_client=None):
        self.youtube = youtube_client or self._authenticate(settings)

    def _authenticate(self, settings: Settings):
        """Authenticate and return a YouTube API client."""
        if not settings.json_url:
            raise ValueError("Missing path to Google credentials JSON file")

        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            settings.json_url,
            ["https://www.googleapis.com/auth/youtube.force-ssl"]
        )   

        credentials = flow.run_local_server(port=8080, prompt="consent")
        return googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)

    def _execute(self, request, *, retries: int = 3, backoff: float = 2.0) -> Any:
        """
        Execute a YouTube API request with retry logic and quota handling.

        - Retries on transient 5xx errors and short-term rate limits with
          exponential backoff.
        - Raises YouTubeQuotaExceededError immediately on 403 quotaExceeded,
          since retrying won't help until the daily quota resets at midnight PT.
        - Lets other 4xx client errors propagate immediately as they are not
          retryable.
        """
        if retries < 1:
            raise ValueError("'retries' must at leats 1.")

        last_exc: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                return request.execute()

            except googleapiclient.errors.HttpError as exc:
                last_exc = exc
                status: int = exc.resp.status
                reason: str = (
                    exc.error_details[0].get("reason", "")
                    if exc.error_details
                    else ""
                )

                if status == 403 and reason == "quotaExceeded":
                    raise YouTubeQuotaExceededError(
                        "YouTube API  quota exceeded"
                    ) from exc

                is_retryable = status >= 500 or reason in RETRYABLE_403_REASONS
                if is_retryable and attempt < retries:
                    # Exponential backoff with jitter
                    base_wait = backoff ** attempt
                    jitter = random.uniform(0, 1)  # Adds up to 1 second of randomness
                    wait = base_wait + jitter
                    logger.warning(
                        "YouTube API error %s/%s (attempt %d/%d). Retrying in %.1fs…",
                        status, reason or "unknown", attempt, retries, wait,
                    )
                    time.sleep(wait)
                    continue

                raise

        # Should be unreachable, but keeps type checkers happy
        raise last_exc
    
    def get_or_create_playlist_id(self, title: str, description: str = "Playlist from Spotify") -> tuple[str, bool]:
        """
        Retrieve an existing playlist ID by title or create a new one if it doesn't exist.

        Returns a tuple of (playlist_id, created).
        
        If `description` is not provided, defaults to 'Playlist from Spotify'.
        """
        request = self.youtube.playlists().list(part="snippet", mine=True, maxResults=50)
        while request:
            response = self._execute(request)
            for playlist in response.get("items", []):
                if playlist["snippet"]["title"] == title:
                    return playlist["id"], False
            request = self.youtube.playlists().list_next(request, response)
            
        # Create playlist
        response = self._execute(
            self.youtube.playlists().insert(
                part='snippet,status',
                body={
                    'snippet': {'title': title, 'description': description},
                    'status': {'privacyStatus': 'private'}
                }
            )
        )

        return response["id"], True
    
    def get_existing_video_ids(self, playlist_id: str) -> Set[str]:
        """
        Retrieve a set of video IDs currently in the given playlist.
        """
        video_ids = set()
        # Paginate through all results
        request = self.youtube.playlistItems().list(
            part="snippet", playlistId=playlist_id, maxResults=50
        )

        while request:
            response = self._execute(request)
            video_ids.update(item["snippet"]["resourceId"]["videoId"] for item in response.get("items", []))
            request = self.youtube.playlistItems().list_next(request, response)
        return video_ids
    
    def add_song_to_playlist(self, video_id: str, playlist_id: str):
        """
        Add a video to a playlist using its video ID.
        """
        self._execute(
            self.youtube.playlistItems().insert(
                part='snippet',
                body={
                    'snippet': {
                        'playlistId': playlist_id,
                        'resourceId': {'kind': 'youtube#video', 'videoId': video_id}
                    }
                }
            )
        )