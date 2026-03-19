from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class SpotifyPager(Protocol):
    def next(self, playlist: dict[str, Any]) -> dict[str, Any]: ...


def extract_track_identifier(item: dict[str, Any]) -> str | None:
    track = item.get("track")
    if not isinstance(track, dict):
        return None

    track_id = track.get("id")
    if isinstance(track_id, str) and track_id.strip():
        return track_id.strip()

    uri = track.get("uri")
    if isinstance(uri, str) and uri.strip():
        return uri.strip()

    return None


def collect_playlist_items(spotify: SpotifyPager, first_page: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page: dict[str, Any] = first_page

    while True:
        page_items = page.get("items") or []
        if isinstance(page_items, list):
            for item in page_items:
                if isinstance(item, dict):
                    items.append(item)

        if not page.get("next"):
            break
        page = spotify.next(page)

    return items


def collect_track_identifiers(items: list[dict[str, Any]]) -> tuple[set[str], int]:
    track_ids: set[str] = set()
    missing = 0
    for item in items:
        identifier = extract_track_identifier(item)
        if identifier:
            track_ids.add(identifier)
        else:
            missing += 1
    return track_ids, missing


@dataclass(frozen=True, slots=True)
class SyncDiff:
    current_track_ids: set[str]
    added_track_ids: set[str]
    removed_track_ids: set[str]
    items_to_process: list[dict[str, Any]]
    missing_identifier_count: int


def diff_playlist_items(*, previous_track_ids: set[str], current_items: list[dict[str, Any]]) -> SyncDiff:
    current_track_ids, missing = collect_track_identifiers(current_items)
    added = current_track_ids - previous_track_ids
    removed = previous_track_ids - current_track_ids

    items_to_process: list[dict[str, Any]] = []
    if added:
        for item in current_items:
            identifier = extract_track_identifier(item)
            if identifier and identifier in added:
                items_to_process.append(item)

    return SyncDiff(
        current_track_ids=current_track_ids,
        added_track_ids=added,
        removed_track_ids=removed,
        items_to_process=items_to_process,
        missing_identifier_count=missing,
    )


def build_single_page_playlist(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"total": len(items), "next": None, "items": items}

