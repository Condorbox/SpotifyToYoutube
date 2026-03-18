from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Protocol, Set

logger = logging.getLogger(__name__)


class SpotifyClient(Protocol):
    def get_playlist_details(self) -> tuple[str, str]: ...

    def next(self, playlist: dict[str, Any]) -> dict[str, Any]: ...


class YouTubeClient(Protocol):
    def get_or_create_playlist_id(self, title: str, description: str = ...) -> str: ...

    def get_existing_video_ids(self, playlist_id: str) -> Set[str]: ...

    def add_song_to_playlist(self, video_id: str, playlist_id: str): ...


class Progress(Protocol):
    def update(self, n: int) -> None: ...

    def set_postfix_str(self, s: str) -> None: ...


class YtDlpStrategy(Protocol):
    def execute(
        self, song: str, video_id: Optional[str] = None, track_metadata: Optional[dict] = None
    ) -> Optional[str]: ...


class DownloadTracker(Protocol):
    def is_downloaded(self, song_query: str) -> bool: ...

    def mark_downloaded(self, song_query: str) -> None: ...


class _NullProgress:
    def update(self, n: int) -> None:
        return None

    def set_postfix_str(self, s: str) -> None:
        return None


@dataclass(slots=True)
class ConvertResult:
    playlist_name: str
    youtube_playlist_id: str
    total: int
    processed: int
    added_to_youtube: int
    downloaded: int
    skipped_unavailable: int
    skipped_existing: int
    skipped_already_downloaded: int
    skipped_not_found: int


def convert_playlist(
    *,
    spotify: SpotifyClient,
    youtube: YouTubeClient,
    spotify_playlist: dict[str, Any],
    search_strategy: YtDlpStrategy,
    download_strategy: YtDlpStrategy | None,
    tracker: DownloadTracker | None,
    download_songs: bool,
    progress: Progress | None = None,
) -> ConvertResult:
    progress = progress or _NullProgress()

    playlist_name, playlist_description = spotify.get_playlist_details()
    youtube_playlist_id = youtube.get_or_create_playlist_id(title=playlist_name, description=playlist_description)
    existing_video_ids = youtube.get_existing_video_ids(playlist_id=youtube_playlist_id)

    total = int(spotify_playlist.get("total") or 0)
    processed = 0
    added_to_youtube = 0
    downloaded = 0
    skipped_unavailable = 0
    skipped_existing = 0
    skipped_already_downloaded = 0
    skipped_not_found = 0

    sp_playlist = spotify_playlist
    while True:
        for track in sp_playlist.get("items", []):
            track_info = track.get("track")

            if not track_info:
                skipped_unavailable += 1
                processed += 1
                progress.update(1)
                continue

            track_metadata = {
                "title": track_info["name"],
                "album": track_info["album"]["name"],
                "artist": "/".join([artist["name"] for artist in track_info["artists"]]),
                "cover_url": track_info["album"]["images"][0]["url"] if track_info["album"]["images"] else None,
            }

            song_query = f"{track_metadata['artist']} - {track_metadata['title']}"
            progress.set_postfix_str(song_query[:50])
            logger.debug("Processing: %s", song_query)

            video_id = search_strategy.execute(song=song_query)

            if video_id:
                if video_id in existing_video_ids:
                    skipped_existing += 1
                else:
                    youtube.add_song_to_playlist(video_id=video_id, playlist_id=youtube_playlist_id)
                    existing_video_ids.add(video_id)
                    added_to_youtube += 1
            else:
                skipped_not_found += 1

            if download_songs:
                if not download_strategy or not tracker:
                    raise ValueError("Download strategy and tracker are required when download_songs=True")

                if tracker.is_downloaded(song_query):
                    skipped_already_downloaded += 1
                else:
                    output_path = download_strategy.execute(
                        song=song_query, video_id=video_id, track_metadata=track_metadata
                    )
                    if output_path:
                        tracker.mark_downloaded(song_query)
                        downloaded += 1

            processed += 1
            progress.update(1)

        if not sp_playlist.get("next"):
            break
        sp_playlist = spotify.next(sp_playlist)

    return ConvertResult(
        playlist_name=playlist_name,
        youtube_playlist_id=youtube_playlist_id,
        total=total,
        processed=processed,
        added_to_youtube=added_to_youtube,
        downloaded=downloaded,
        skipped_unavailable=skipped_unavailable,
        skipped_existing=skipped_existing,
        skipped_already_downloaded=skipped_already_downloaded,
        skipped_not_found=skipped_not_found,
    )
