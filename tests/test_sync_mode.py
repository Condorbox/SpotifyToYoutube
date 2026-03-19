from __future__ import annotations

from typing import Any

from sync_mode import collect_playlist_items, diff_playlist_items, extract_track_identifier


def _track_item(track_id: str | None, *, uri: str | None = None) -> dict[str, Any]:
    track: dict[str, Any] | None
    if track_id is None and uri is None:
        track = None
    else:
        track = {}
        if track_id is not None:
            track["id"] = track_id
        if uri is not None:
            track["uri"] = uri
    return {"track": track}


class _FakeSpotifyPager:
    def __init__(self, pages: list[dict[str, Any]]):
        self._pages = pages
        self._idx = 0

    def next(self, playlist: dict[str, Any]) -> dict[str, Any]:
        self._idx += 1
        return self._pages[self._idx]


def test_extract_track_identifier_prefers_id_over_uri():
    assert extract_track_identifier(_track_item("id1", uri="spotify:track:uri1")) == "id1"
    assert extract_track_identifier(_track_item(None, uri="spotify:track:uri1")) == "spotify:track:uri1"
    assert extract_track_identifier(_track_item(None)) is None


def test_collect_playlist_items_paginates():
    pages = [
        {"items": [_track_item("id1")], "next": True},
        {"items": [_track_item("id2")], "next": None},
    ]
    spotify = _FakeSpotifyPager(pages)

    items = collect_playlist_items(spotify, pages[0])
    assert [extract_track_identifier(i) for i in items] == ["id1", "id2"]


def test_diff_playlist_items_finds_additions_and_removals():
    current_items = [_track_item("id1"), _track_item("id2"), _track_item(None)]
    diff = diff_playlist_items(previous_track_ids={"id2", "old"}, current_items=current_items)

    assert diff.added_track_ids == {"id1"}
    assert diff.removed_track_ids == {"old"}
    assert [extract_track_identifier(i) for i in diff.items_to_process] == ["id1"]
    assert diff.missing_identifier_count == 1

