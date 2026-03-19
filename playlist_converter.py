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


@dataclass(frozen=True, slots=True)
class TrackMeta:
    title: str
    artist: str
    album: str
    cover_url: str | None

    @property
    def query(self) -> str:
        return f"{self.artist} - {self.title}"


def parse_track(track_info: Any) -> TrackMeta | None:
    if not isinstance(track_info, dict):
        return None

    title = track_info.get("name")
    if not isinstance(title, str) or not title.strip():
        return None

    artists = track_info.get("artists") or []
    if not isinstance(artists, list):
        return None

    artist_names = [
        artist.get("name")
        for artist in artists
        if isinstance(artist, dict) and isinstance(artist.get("name"), str) and artist.get("name", "").strip()
    ]
    if not artist_names:
        return None

    album_info = track_info.get("album") or {}
    if not isinstance(album_info, dict):
        album_info = {}

    album_name = album_info.get("name")
    album = album_name.strip() if isinstance(album_name, str) else ""

    cover_url: str | None = None
    images = album_info.get("images") or []
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict) and isinstance(first.get("url"), str):
            cover_url = first["url"]

    return TrackMeta(
        title=title.strip(),
        artist="/".join(artist_names),
        album=album,
        cover_url=cover_url,
    )


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
    if download_songs and (not download_strategy or not tracker):
        raise ValueError("Download strategy and tracker are required when download_songs=True")

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
            meta = parse_track(track.get("track"))
            if not meta:
                skipped_unavailable += 1
                processed += 1
                progress.update(1)
                continue

            track_metadata = {"title": meta.title, "album": meta.album, "artist": meta.artist, "cover_url": meta.cover_url}
            song_query = meta.query
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
