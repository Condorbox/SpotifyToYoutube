import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from config import SNAPSHOT_FILE

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PlaylistSnapshotEntry:
    track_ids: set[str]
    updated_at: str | None


class PlaylistSnapshot:
    """
    Persists a snapshot of Spotify playlist track identifiers to a local JSON file.

    The snapshot is keyed by Spotify playlist ID, allowing a single file to support
    multiple playlists.
    """

    def __init__(self, filepath: str = SNAPSHOT_FILE):
        self.filepath = filepath
        self._data: dict[str, Any] = self._load()

    @classmethod
    def from_settings(cls, custom_path: str | None) -> "PlaylistSnapshot":
        if custom_path:
            if os.path.exists(custom_path) and not os.path.isfile(custom_path):
                logger.warning(
                    "Snapshot path '%s' is not a file. Falling back to default: %s",
                    custom_path,
                    SNAPSHOT_FILE,
                )
                return cls()
            return cls(filepath=custom_path)
        return cls()

    def _load(self) -> dict[str, Any]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("snapshot JSON root must be an object")
                return data
            except (json.JSONDecodeError, OSError, ValueError) as e:
                logger.warning("Could not read snapshot file '%s': %s. Starting fresh.", self.filepath, e)
        return {"version": 1, "playlists": {}}

    def _save(self) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, sort_keys=True)
        except OSError as e:
            logger.error("Could not save snapshot file '%s': %s", self.filepath, e)

    def get(self, playlist_id: str) -> PlaylistSnapshotEntry:
        playlists = self._data.get("playlists") or {}
        if not isinstance(playlists, dict):
            playlists = {}

        raw_entry = playlists.get(playlist_id) or {}
        if not isinstance(raw_entry, dict):
            raw_entry = {}

        raw_ids = raw_entry.get("track_ids") or []
        if not isinstance(raw_ids, list):
            raw_ids = []
        track_ids = {tid for tid in raw_ids if isinstance(tid, str) and tid.strip()}
        updated_at = raw_entry.get("updated_at")
        if not isinstance(updated_at, str) or not updated_at.strip():
            updated_at = None

        return PlaylistSnapshotEntry(track_ids=track_ids, updated_at=updated_at)

    def set(self, playlist_id: str, track_ids: set[str]) -> None:
        playlists = self._data.get("playlists")
        if not isinstance(playlists, dict):
            playlists = {}
            self._data["playlists"] = playlists

        playlists[playlist_id] = {
            "track_ids": sorted({tid for tid in track_ids if isinstance(tid, str) and tid.strip()}),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

