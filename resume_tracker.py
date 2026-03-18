import json
import logging
import os

logger = logging.getLogger(__name__)

TRACKER_FILE = "downloaded_songs.json"


class ResumeTracker:
    """
    Persists a set of already-downloaded song queries to a local JSON file.
    Allows resuming interrupted downloads without re-downloading completed tracks.
    """

    def __init__(self, filepath: str = TRACKER_FILE):
        self.filepath = filepath
        self._downloaded: set[str] = self._load()

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
                json.dump({"downloaded": list(self._downloaded)}, f, indent=2)
        except OSError as e:
            logger.error(f"Could not save resume tracker: {e}")

    def is_downloaded(self, song_query: str) -> bool:
        return song_query in self._downloaded

    def mark_downloaded(self, song_query: str):
        self._downloaded.add(song_query)
        self._save()

    def reset(self):
        """Clear all tracked downloads."""
        self._downloaded.clear()
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
        logger.info("Resume tracker reset.")