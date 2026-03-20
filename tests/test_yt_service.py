from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import Mode, Settings
from youtube_service import YouTubeService


def _settings() -> Settings:
    return Settings(
        client_id=None,
        client_secret=None,
        redirect_uri=None,
        playlist_id=None,
        json_url=None,
        download_dir=None,
        playlist_offset=0,
        tracker_file=None,
        snapshot_file=None,
        workers=1,
        download=False,
        no_download=False,
        mode=Mode.CONVERT,
        log_level="INFO",
        log_file=None,
    )


@dataclass(slots=True)
class _FakeRequest:
    response: dict[str, Any]
    page_index: int | None = None

    def execute(self) -> dict[str, Any]:
        return self.response


class _FakePlaylistsResource:
    def __init__(self, pages: list[dict[str, Any]], *, insert_response: dict[str, Any]):
        self._pages = pages
        self._insert_response = insert_response
        self.list_calls: list[dict[str, Any]] = []
        self.list_next_calls = 0
        self.insert_calls: list[dict[str, Any]] = []

    def list(self, *, part: str, mine: bool, maxResults: int):
        self.list_calls.append({"part": part, "mine": mine, "maxResults": maxResults})
        if not self._pages:
            return None
        return _FakeRequest(self._pages[0], page_index=0)

    def list_next(self, request: _FakeRequest, response: dict[str, Any]):
        self.list_next_calls += 1
        if request.page_index is None:
            raise AssertionError("list_next called with a request missing page_index")
        next_index = request.page_index + 1
        if next_index < len(self._pages):
            return _FakeRequest(self._pages[next_index], page_index=next_index)
        return None

    def insert(self, *, part: str, body: dict[str, Any]):
        self.insert_calls.append({"part": part, "body": body})
        return _FakeRequest(self._insert_response, page_index=None)


class _FakePlaylistItemsResource:
    def __init__(self, pages: list[dict[str, Any]]):
        self._pages = pages
        self.list_calls: list[dict[str, Any]] = []
        self.list_next_calls = 0

    def list(self, *, part: str, playlistId: str, maxResults: int):
        self.list_calls.append({"part": part, "playlistId": playlistId, "maxResults": maxResults})
        if not self._pages:
            return None
        return _FakeRequest(self._pages[0], page_index=0)

    def list_next(self, request: _FakeRequest, response: dict[str, Any]):
        self.list_next_calls += 1
        if request.page_index is None:
            raise AssertionError("list_next called with a request missing page_index")
        next_index = request.page_index + 1
        if next_index < len(self._pages):
            return _FakeRequest(self._pages[next_index], page_index=next_index)
        return None


class _FakeYouTubeClient:
    def __init__(
        self,
        *,
        playlist_pages: list[dict[str, Any]] | None = None,
        playlist_item_pages: list[dict[str, Any]] | None = None,
        insert_response: dict[str, Any] | None = None,
    ):
        self._playlists = _FakePlaylistsResource(
            playlist_pages or [],
            insert_response=insert_response or {"id": "new123"},
        )
        self._playlist_items = _FakePlaylistItemsResource(playlist_item_pages or [])

    def playlists(self) -> _FakePlaylistsResource:
        return self._playlists

    def playlistItems(self) -> _FakePlaylistItemsResource:
        return self._playlist_items



def test_get_or_create_playlist_id_returns_existing_first_page():
    yt_client = _FakeYouTubeClient(
        playlist_pages=[
            {
                "items": [
                    {"id": "pl1", "snippet": {"title": "My Playlist"}},
                    {"id": "pl2", "snippet": {"title": "Other"}},
                ]
            }
        ]
    )
    service = YouTubeService(_settings(), youtube_client=yt_client)

    assert service.get_or_create_playlist_id("My Playlist") == ("pl1", False)
    assert yt_client._playlists.insert_calls == []
    assert yt_client._playlists.list_calls == [{"part": "snippet", "mine": True, "maxResults": 50}]
    assert yt_client._playlists.list_next_calls == 0


def test_get_or_create_playlist_id_paginates_until_found():
    yt_client = _FakeYouTubeClient(
        playlist_pages=[
            {"items": [{"id": "pl1", "snippet": {"title": "Other"}}]},
            {"items": [{"id": "pl2", "snippet": {"title": "My Playlist"}}]},
        ]
    )
    service = YouTubeService(_settings(), youtube_client=yt_client)

    assert service.get_or_create_playlist_id("My Playlist") == ("pl2", False)
    assert yt_client._playlists.insert_calls == []
    assert yt_client._playlists.list_next_calls == 1


def test_get_or_create_playlist_id_creates_playlist_if_missing():
    yt_client = _FakeYouTubeClient(
        playlist_pages=[
            {"items": [{"id": "pl1", "snippet": {"title": "Other"}}]},
            {"items": []},
        ],
        insert_response={"id": "new999"},
    )
    service = YouTubeService(_settings(), youtube_client=yt_client)

    assert service.get_or_create_playlist_id("My Playlist", description="From Spotify") == ("new999", True)
    assert yt_client._playlists.list_next_calls == 2
    assert yt_client._playlists.insert_calls == [
        {
            "part": "snippet,status",
            "body": {
                "snippet": {"title": "My Playlist", "description": "From Spotify"},
                "status": {"privacyStatus": "private"},
            },
        }
    ]


def test_get_existing_video_ids_paginates_and_collects_ids():
    yt_client = _FakeYouTubeClient(
        playlist_item_pages=[
            {
                "items": [
                    {"snippet": {"resourceId": {"videoId": "v1"}}},
                    {"snippet": {"resourceId": {"videoId": "v2"}}},
                ]
            },
            {"items": [{"snippet": {"resourceId": {"videoId": "v3"}}}]},
        ]
    )
    service = YouTubeService(_settings(), youtube_client=yt_client)

    assert service.get_existing_video_ids("pl123") == {"v1", "v2", "v3"}
    assert yt_client._playlist_items.list_calls == [{"part": "snippet", "playlistId": "pl123", "maxResults": 50}]
    assert yt_client._playlist_items.list_next_calls == 2
