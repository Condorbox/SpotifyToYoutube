import json
import logging
import os
import threading

from config import TRACKER_FILE

logger = logging.getLogger(__name__)

class ResumeTracker:
    """
    Persists a set of already-downloaded song queries to a local JSON file.
    Allows resuming interrupted downloads without re-downloading completed tracks.
    """

    def __init__(self, filepath: str = TRACKER_FILE):
        self.filepath = filepath
        self._lock = threading.Lock()
        self._downloaded: set[str] = self._load()

    @classmethod
    def from_settings(cls, custom_path: str | None) -> "ResumeTracker":
        """Resolve the tracker filepath, warning and falling back to default if custom path doesn't exist."""
        if custom_path:
            if not os.path.exists(custom_path):
                logger.warning(
                    f"Tracker file '{custom_path}' does not exist. Falling back to default: {TRACKER_FILE}"
                )
            elif not os.path.isfile(custom_path):
                logger.warning(
                    f"Tracker path '{custom_path}' is not a file. Falling back to default: {TRACKER_FILE}"
                )
            else:
                return cls(filepath=custom_path)
        return cls()

    def _load(self) -> set[str]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data.get("downloaded", []))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not read resume tracker file '{self.filepath}': {e}. Starting fresh.")
        return set()

    def _save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({"downloaded": sorted(self._downloaded)}, f, indent=2)
        except OSError as e:
            logger.error(f"Could not save resume tracker: {e}")

    def is_downloaded(self, song_query: str) -> bool:
        with self._lock:
            return song_query in self._downloaded

    def mark_downloaded(self, song_query: str):
        with self._lock:
            if song_query in self._downloaded:
                return
            self._downloaded.add(song_query)
            self._save()

    def reset(self):
        """Clear all tracked downloads."""
        with self._lock:
            self._downloaded.clear()
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
        logger.info("Resume tracker reset.")
