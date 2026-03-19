from __future__ import annotations

from typing import Any, Optional

from playlist_converter import convert_playlist


def _track_item(*, title: str, artist: str, album: str = "Album", cover_url: str | None = None) -> dict[str, Any]:
    return {
        "track": {
            "name": title,
            "album": {"name": album, "images": [{"url": cover_url}] if cover_url else []},
            "artists": [{"name": artist}],
        }
    }


class FakeSpotify:
    def __init__(self, pages: list[dict[str, Any]]):
        self._pages = pages
        self._page_index = 0

    def get_playlist_details(self) -> tuple[str, str]:
        return ("My Playlist", "From Spotify")

    def next(self, playlist: dict[str, Any]) -> dict[str, Any]:
        self._page_index += 1
        return self._pages[self._page_index]


class FakeYouTube:
    def __init__(self, existing: set[str] | None = None, *, created: bool = False):
        self.added: list[tuple[str, str]] = []
        self._existing = set(existing or set())
        self._created = created

    def get_or_create_playlist_id(self, title: str, description: str = "Playlist from Spotify") -> tuple[str, bool]:
        assert title == "My Playlist"
        return ("yt123", self._created)

    def get_existing_video_ids(self, playlist_id: str) -> set[str]:
        assert playlist_id == "yt123"
        if self._created:
            raise AssertionError("get_existing_video_ids should not be called for newly created playlists")
        return set(self._existing)

    def add_song_to_playlist(self, video_id: str, playlist_id: str):
        self.added.append((video_id, playlist_id))


class FakeSearchStrategy:
    def __init__(self, mapping: dict[str, str | None]):
        self.mapping = mapping
        self.queries: list[str] = []

    def execute(self, song: str, video_id: Optional[str] = None, track_metadata: Optional[dict] = None) -> str | None:
        self.queries.append(song)
        return self.mapping.get(song)


class FakeDownloadStrategy:
    def __init__(self, *, fail_songs: set[str] | None = None):
        self.fail_songs = set(fail_songs or set())
        self.calls: list[tuple[str, str | None]] = []

    def execute(self, song: str, video_id: Optional[str] = None, track_metadata: Optional[dict] = None) -> str | None:
        self.calls.append((song, video_id))
        if song in self.fail_songs:
            return None
        return "/tmp/out.mp3"


class FakeTracker:
    def __init__(self, downloaded: set[str] | None = None):
        self._downloaded = set(downloaded or set())
        self.marked: list[str] = []

    def is_downloaded(self, song_query: str) -> bool:
        return song_query in self._downloaded

    def mark_downloaded(self, song_query: str) -> None:
        self._downloaded.add(song_query)
        self.marked.append(song_query)


class FakeProgress:
    def __init__(self):
        self.updated = 0
        self.postfix: list[str] = []

    def update(self, n: int) -> None:
        self.updated += n

    def set_postfix_str(self, s: str) -> None:
        self.postfix.append(s)


def test_convert_playlist_adds_and_downloads_with_tracking():
    pages = [
        {
            "total": 4,
            "next": True,
            "items": [
                _track_item(title="Song1", artist="Artist1", cover_url="https://example/1.jpg"),
                {"track": None},
            ],
        },
        {
            "total": 4,
            "next": None,
            "items": [
                _track_item(title="Song3", artist="Artist3"),
                _track_item(title="Song4", artist="Artist4"),
            ],
        },
    ]

    spotify = FakeSpotify(pages=pages)
    youtube = FakeYouTube(existing={"v3"})

    song1 = "Artist1 - Song1"
    song3 = "Artist3 - Song3"
    song4 = "Artist4 - Song4"

    search = FakeSearchStrategy({song1: "v1", song3: "v3", song4: None})
    downloader = FakeDownloadStrategy(fail_songs={song4})
    tracker = FakeTracker(downloaded={song1})
    progress = FakeProgress()

    result = convert_playlist(
        spotify=spotify,
        youtube=youtube,
        spotify_playlist=pages[0],
        search_strategy=search,
        download_strategy=downloader,
        tracker=tracker,
        download_songs=True,
        progress=progress,
    )

    assert result.total == 4
    assert result.processed == 4
    assert result.skipped_unavailable == 1
    assert result.added_to_youtube == 1
    assert result.skipped_existing == 1
    assert result.skipped_not_found == 1
    assert result.skipped_already_downloaded == 1
    assert result.downloaded == 1

    assert youtube.added == [("v1", "yt123")]
    assert tracker.marked == [song3]
    assert progress.updated == 4


def test_convert_playlist_without_downloads():
    page = {
        "total": 1,
        "next": None,
        "items": [_track_item(title="Song1", artist="Artist1")],
    }

    spotify = FakeSpotify(pages=[page])
    youtube = FakeYouTube(existing=set())
    search = FakeSearchStrategy({"Artist1 - Song1": "v1"})
    progress = FakeProgress()

    result = convert_playlist(
        spotify=spotify,
        youtube=youtube,
        spotify_playlist=page,
        search_strategy=search,
        download_strategy=None,
        tracker=None,
        download_songs=False,
        progress=progress,
    )

    assert result.downloaded == 0
    assert youtube.added == [("v1", "yt123")]
    assert progress.updated == 1


def test_convert_playlist_skips_existing_video_ids_when_youtube_playlist_created():
    page = {
        "total": 1,
        "next": None,
        "items": [_track_item(title="Song1", artist="Artist1")],
    }

    spotify = FakeSpotify(pages=[page])
    youtube = FakeYouTube(existing={"v1"}, created=True)
    search = FakeSearchStrategy({"Artist1 - Song1": "v1"})
    progress = FakeProgress()

    result = convert_playlist(
        spotify=spotify,
        youtube=youtube,
        spotify_playlist=page,
        search_strategy=search,
        download_strategy=None,
        tracker=None,
        download_songs=False,
        progress=progress,
    )

    assert result.added_to_youtube == 1
    assert youtube.added == [("v1", "yt123")]
