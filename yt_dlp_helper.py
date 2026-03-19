from abc import ABC, abstractmethod
from enum import Enum
import logging
import os
import subprocess
from typing import List, Optional
import urllib.request

from config import ERROR_COLOR, RESET_COLOR
from utils import sanitize_filename

logger = logging.getLogger(__name__)


class YTDLPMode(Enum):
    SEARCH = "search"
    DOWNLOAD = "download"

# Abstract Strategy Interface
class YTDLPStrategy(ABC):
    @abstractmethod
    def execute(self, song: str, video_id: Optional[str] = None, track_metadata: Optional[dict] = None) -> Optional[str]:
        """Abstract method to be implemented by all strategies"""
        raise NotImplementedError
    
class SearchStrategy(YTDLPStrategy):
    def execute(self, song: str, video_id: Optional[str] = None, track_metadata: Optional[dict] = None) -> str | None:
        """Search a video on YouTube and return its video ID."""
        return YTDLPHelper._run_yt_dlp(["--print", "%(id)s", f"ytsearch1:{song}"])

class DownloadStrategy(YTDLPStrategy):
    def __init__(self, download_dir: str):
        self._download_dir = download_dir

    def execute(self, song: str, video_id: Optional[str] = None, track_metadata: Optional[dict] = None) -> str | None:
        """
        Download the audio for the given song.
        If `video_id` is not provided or None, first search for the song.
        """
        try:
            if not video_id:
                video_id = YTDLPHelper.create_strategy(YTDLPMode.SEARCH).execute(song)

            if not video_id:
                return None

            webm_output_path = os.path.join(self._download_dir, sanitize_filename(f"{song}.webm"))
            mp3_output_path = os.path.join(self._download_dir, sanitize_filename(f"{song}.mp3"))
            temp_output_file = mp3_output_path.replace(".mp3", "_tmp.mp3")
            cover_path = mp3_output_path.replace(".mp3", "_cover.jpg")

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            try:
                if YTDLPHelper._run_yt_dlp(["-f", "bestaudio", "-o", webm_output_path, video_url]) is None:
                    return None

                if not os.path.exists(webm_output_path):
                    return None

                cover_url = track_metadata.get("cover_url") if track_metadata else None
                cover_available = False
                if isinstance(cover_url, str) and cover_url.strip():
                    try:
                        urllib.request.urlretrieve(cover_url, cover_path)
                        cover_available = True
                    except Exception:
                        logger.warning("Failed downloading cover art for %s", song, exc_info=True)

                command = ["ffmpeg", "-y", "-i", webm_output_path]
                if cover_available:
                    command.extend(
                        [
                            "-i",
                            cover_path,
                            "-map",
                            "0:a",
                            "-map",
                            "1:v",
                            "-disposition:v:0",
                            "attached_pic",
                            "-metadata:s:v",
                            "title=Album cover",
                            "-metadata:s:v",
                            "comment=Cover (front)",
                            "-c:v",
                            "mjpeg",
                        ]
                    )
                else:
                    command.extend(["-map", "0:a"])

                command.extend(
                    [
                        "-c:a",
                        "libmp3lame",
                        "-b:a",
                        "128k",
                        "-id3v2_version",
                        "3",
                    ]
                )

                if track_metadata:
                    metadata_fields = {
                        "title": track_metadata.get("title", ""),
                        "artist": track_metadata.get("artist", ""),
                        "album": track_metadata.get("album", ""),
                    }

                    for key, value in metadata_fields.items():
                        if value:
                            command.extend(["-metadata", f"{key}={value}"])

                command.append(temp_output_file)
                subprocess.run(command, check=True)
                os.replace(temp_output_file, mp3_output_path)

                return mp3_output_path

            finally:
                # Remove original WebM file
                if os.path.exists(webm_output_path):
                    os.remove(webm_output_path)
                if os.path.exists(temp_output_file):
                    os.remove(temp_output_file)
                if os.path.exists(cover_path):
                    os.remove(cover_path)

        except Exception:
            logger.exception("Conversion failed for %s", song)
            return None
    
class YTDLPHelper:
    @staticmethod
    def create_strategy(mode: YTDLPMode, *, download_dir: str | None = None) -> YTDLPStrategy:
        """Factory method to return the appropriate strategy."""
        if mode == YTDLPMode.SEARCH:
            return SearchStrategy()
        elif mode == YTDLPMode.DOWNLOAD:
            if not download_dir:
                raise ValueError("download_dir is required for download mode")
            return DownloadStrategy(download_dir)
        else:
            raise ValueError(f"{ERROR_COLOR}Invalid mode: {mode}{RESET_COLOR}")

    @staticmethod
    def _run_yt_dlp(command_args: List[str]) -> Optional[str]:
        """Private method to run yt-dlp."""
        command = ["yt-dlp"] + command_args
        try:
            result = subprocess.run(command, capture_output=True, text=True)
        except FileNotFoundError:
            logger.error("yt-dlp not found on PATH. Install it and try again.")
            return None
        except Exception:
            logger.exception("Unexpected error running yt-dlp")
            return None

        # Check for errors
        if result.returncode != 0:
            logger.error("Error executing yt-dlp: %s", (result.stderr or "").strip())
            return None  # Return None to indicate failure
        
        # Check for warnings in stderr (yt-dlp may still succeed with warnings)
        if result.stderr:
            logger.debug("yt-dlp stderr: %s", result.stderr.strip())

        return result.stdout.strip()
