from __future__ import annotations

import logging
import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, Protocol, Set

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

    def try_claim(self, song_query: str) -> bool: ...

    def mark_downloaded(self, song_query: str) -> None: ...

    def release_claim(self, song_query: str) -> None: ...


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


@dataclass(slots=True)
class _OutcomeTally:
    processed: int = 0
    added_to_youtube: int = 0
    downloaded: int = 0
    skipped_unavailable: int = 0
    skipped_existing: int = 0
    skipped_already_downloaded: int = 0
    skipped_not_found: int = 0

    def add(self, outcome: _TrackOutcome) -> None:
        self.processed += 1
        self.added_to_youtube += outcome.added_to_youtube
        self.downloaded += outcome.downloaded
        self.skipped_unavailable += outcome.skipped_unavailable
        self.skipped_existing += outcome.skipped_existing
        self.skipped_already_downloaded += outcome.skipped_already_downloaded
        self.skipped_not_found += outcome.skipped_not_found

    def to_result(self, *, playlist_name: str, youtube_playlist_id: str, total: int) -> ConvertResult:
        return ConvertResult(
            playlist_name=playlist_name,
            youtube_playlist_id=youtube_playlist_id,
            total=total,
            processed=self.processed,
            added_to_youtube=self.added_to_youtube,
            downloaded=self.downloaded,
            skipped_unavailable=self.skipped_unavailable,
            skipped_existing=self.skipped_existing,
            skipped_already_downloaded=self.skipped_already_downloaded,
            skipped_not_found=self.skipped_not_found,
        )


@dataclass(slots=True)
class _TrackProcessor:
    youtube: YouTubeClient
    youtube_playlist_id: str
    existing_video_ids: set[str]
    youtube_lock: threading.Lock
    search_strategy: YtDlpStrategy
    download_strategy: YtDlpStrategy | None
    tracker: DownloadTracker | None
    download_songs: bool
    tracker_lock: threading.Lock | None

    def __call__(self, item: Any) -> _TrackOutcome:
        meta = self._parse_item(item)
        if not meta:
            return _TrackOutcome(song_query=None, skipped_unavailable=1)

        track_metadata = {
            "title": meta.title,
            "album": meta.album,
            "artist": meta.artist,
            "cover_url": meta.cover_url,
        }
        song_query = meta.query
        logger.debug("Processing: %s", song_query)

        video_id = self.search_strategy.execute(song=song_query)

        added_to_youtube, skipped_existing, skipped_not_found = self._maybe_add_to_youtube(video_id)
        downloaded, skipped_already_downloaded = self._maybe_download(
            song_query=song_query,
            video_id=video_id,
            track_metadata=track_metadata,
        )

        return _TrackOutcome(
            song_query=song_query,
            added_to_youtube=added_to_youtube,
            downloaded=downloaded,
            skipped_existing=skipped_existing,
            skipped_already_downloaded=skipped_already_downloaded,
            skipped_not_found=skipped_not_found,
        )

    @staticmethod
    def _parse_item(item: Any) -> TrackMeta | None:
        if not isinstance(item, dict):
            return None
        return parse_track(item.get("track"))

    def _maybe_add_to_youtube(self, video_id: str | None) -> tuple[int, int, int]:
        if not video_id:
            return 0, 0, 1

        with self.youtube_lock:
            if video_id in self.existing_video_ids:
                return 0, 1, 0
            self.existing_video_ids.add(video_id)
            self.youtube.add_song_to_playlist(video_id=video_id, playlist_id=self.youtube_playlist_id)
            return 1, 0, 0

    def _maybe_download(
        self, *, song_query: str, video_id: str | None, track_metadata: dict[str, Any]
    ) -> tuple[int, int]:
        if not self.download_songs:
            return 0, 0

        if self.tracker is None or self.download_strategy is None:
            raise ValueError("tracker and download_strategy must be provided when download_songs=True")

        tracker_lock = self.tracker_lock
        if tracker_lock is None:
            claimed = self.tracker.try_claim(song_query)
        else:
            with tracker_lock:
                claimed = self.tracker.try_claim(song_query)

        if not claimed:
            return 0, 1

        try:
            output_path = self.download_strategy.execute(
                song=song_query,
                video_id=video_id,
                track_metadata=track_metadata,
            )
        except Exception:
            if tracker_lock is None:
                self.tracker.release_claim(song_query)
            else:
                with tracker_lock:
                    self.tracker.release_claim(song_query)
            raise

        if output_path:
            if tracker_lock is None:
                self.tracker.mark_downloaded(song_query)
            else:
                with tracker_lock:
                    self.tracker.mark_downloaded(song_query)
            return 1, 0

        if tracker_lock is None:
            self.tracker.release_claim(song_query)
        else:
            with tracker_lock:
                self.tracker.release_claim(song_query)
        return 0, 0


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


def _drain(done: set[Future[_TrackOutcome]], tally: _OutcomeTally, progress: Progress) -> None:
    for future in done:
        outcome = future.result()
        tally.add(outcome)
        if outcome.song_query:
            progress.set_postfix_str(outcome.song_query[:50])
        progress.update(1)


def _process_items_concurrently(
    *,
    items: Iterable[Any],
    processor: Callable[[Any], _TrackOutcome],
    workers: int,
    progress: Progress,
    tally: _OutcomeTally,
) -> None:
    pending: set[Future[_TrackOutcome]] = set()
    max_pending = max(1, workers * 2)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for item in items:
            pending.add(executor.submit(processor, item))
            if len(pending) >= max_pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                _drain(done, tally, progress)

        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            _drain(done, tally, progress)


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

    raw_total = spotify_playlist.get("total") or 0
    raw_offset = spotify_playlist.get("offset") or 0
    try:
        total_value = int(raw_total)
    except (TypeError, ValueError):
        total_value = 0
    try:
        offset_value = int(raw_offset)
    except (TypeError, ValueError):
        offset_value = 0

    if total_value < 0:
        total_value = 0
    if offset_value < 0:
        offset_value = 0
    total = max(0, total_value - offset_value)

    youtube_lock = threading.Lock()
    tracker_lock = threading.Lock() if download_songs else None

    processor = _TrackProcessor(
        youtube=youtube,
        youtube_playlist_id=youtube_playlist_id,
        existing_video_ids=existing_video_ids,
        youtube_lock=youtube_lock,
        search_strategy=search_strategy,
        download_strategy=download_strategy,
        tracker=tracker,
        download_songs=download_songs,
        tracker_lock=tracker_lock,
    )

    tally = _OutcomeTally()
    _process_items_concurrently(
        items=_iter_playlist_items(spotify, spotify_playlist),
        processor=processor,
        workers=workers,
        progress=progress,
        tally=tally,
    )

    return tally.to_result(
        playlist_name=playlist_name,
        youtube_playlist_id=youtube_playlist_id,
        total=total,
    )
