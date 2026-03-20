from __future__ import annotations

import logging
import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any, Optional, Protocol, Set, Iterable

logger = logging.getLogger(__name__)


class SpotifyClient(Protocol):
    def get_playlist_details(self) -> tuple[str, str]: ...

    def next(self, playlist: dict[str, Any]) -> dict[str, Any]: ...


class YouTubeClient(Protocol):
    def get_or_create_playlist_id(self, title: str, description: str = ...) -> tuple[str, bool]: ...

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


@dataclass(frozen=True, slots=True)
class _TrackOutcome:
    song_query: str | None
    added_to_youtube: int = 0
    downloaded: int = 0
    skipped_unavailable: int = 0
    skipped_existing: int = 0
    skipped_already_downloaded: int = 0
    skipped_not_found: int = 0


def _iter_playlist_items(spotify: SpotifyClient, first_page: dict[str, Any]) -> Iterable[Any]:
    page: dict[str, Any] = first_page
    while True:
        items = page.get("items") or []
        if isinstance(items, list):
            for item in items:
                yield item

        if not page.get("next"):
            break
        page = spotify.next(page)


def convert_playlist(
    *,
    spotify: SpotifyClient,
    youtube: YouTubeClient,
    spotify_playlist: dict[str, Any],
    search_strategy: YtDlpStrategy,
    download_strategy: YtDlpStrategy | None,
    tracker: DownloadTracker | None,
    download_songs: bool,
    workers: int = 1,
    progress: Progress | None = None,
) -> ConvertResult:
    if download_songs and (not download_strategy or not tracker):
        raise ValueError("Download strategy and tracker are required when download_songs=True")
    if workers < 1:
        raise ValueError("workers must be >= 1")

    progress = progress or _NullProgress()

    playlist_name, playlist_description = spotify.get_playlist_details()
    youtube_playlist_id, created = youtube.get_or_create_playlist_id(
        title=playlist_name, description=playlist_description
    )
    existing_video_ids = set() if created else youtube.get_existing_video_ids(playlist_id=youtube_playlist_id)

    total = int(spotify_playlist.get("total") or 0)
    processed = 0
    added_to_youtube = 0
    downloaded = 0
    skipped_unavailable = 0
    skipped_existing = 0
    skipped_already_downloaded = 0
    skipped_not_found = 0

    existing_video_ids_lock = threading.Lock()
    youtube_lock = threading.Lock()

    def process_track(item: Any) -> _TrackOutcome:
        if not isinstance(item, dict):
            return _TrackOutcome(song_query=None, skipped_unavailable=1)

        meta = parse_track(item.get("track"))
        if not meta:
            return _TrackOutcome(song_query=None, skipped_unavailable=1)

        track_metadata = {"title": meta.title, "album": meta.album, "artist": meta.artist, "cover_url": meta.cover_url}
        song_query = meta.query
        logger.debug("Processing: %s", song_query)

        video_id = search_strategy.execute(song=song_query)

        added = 0
        skipped_existing_local = 0
        skipped_not_found_local = 0

        if video_id:
            should_add = False
            with existing_video_ids_lock:
                if video_id in existing_video_ids:
                    skipped_existing_local = 1
                else:
                    existing_video_ids.add(video_id)
                    should_add = True

            if should_add:
                with youtube_lock:
                    youtube.add_song_to_playlist(video_id=video_id, playlist_id=youtube_playlist_id)
                added = 1
        else:
            skipped_not_found_local = 1

        downloaded_local = 0
        skipped_already_downloaded_local = 0

        if download_songs:
            assert tracker is not None
            assert download_strategy is not None
            if tracker.is_downloaded(song_query):
                skipped_already_downloaded_local = 1
            else:
                output_path = download_strategy.execute(song=song_query, video_id=video_id, track_metadata=track_metadata)
                if output_path:
                    tracker.mark_downloaded(song_query)
                    downloaded_local = 1

        return _TrackOutcome(
            song_query=song_query,
            added_to_youtube=added,
            downloaded=downloaded_local,
            skipped_existing=skipped_existing_local,
            skipped_already_downloaded=skipped_already_downloaded_local,
            skipped_not_found=skipped_not_found_local,
        )

    pending: set[Future[_TrackOutcome]] = set()
    max_pending = max(1, workers * 2)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for item in _iter_playlist_items(spotify, spotify_playlist):
            pending.add(executor.submit(process_track, item))
            if len(pending) < max_pending:
                continue

            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                outcome = future.result()
                processed += 1
                added_to_youtube += outcome.added_to_youtube
                downloaded += outcome.downloaded
                skipped_unavailable += outcome.skipped_unavailable
                skipped_existing += outcome.skipped_existing
                skipped_already_downloaded += outcome.skipped_already_downloaded
                skipped_not_found += outcome.skipped_not_found
                if outcome.song_query:
                    progress.set_postfix_str(outcome.song_query[:50])
                progress.update(1)

        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                outcome = future.result()
                processed += 1
                added_to_youtube += outcome.added_to_youtube
                downloaded += outcome.downloaded
                skipped_unavailable += outcome.skipped_unavailable
                skipped_existing += outcome.skipped_existing
                skipped_already_downloaded += outcome.skipped_already_downloaded
                skipped_not_found += outcome.skipped_not_found
                if outcome.song_query:
                    progress.set_postfix_str(outcome.song_query[:50])
                progress.update(1)

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
