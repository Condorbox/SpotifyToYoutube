from abc import ABC, abstractmethod
from enum import Enum
import os
import subprocess
from typing import List, Optional
import urllib.request

from config import ERROR_COLOR, RESET_COLOR, WARNING_COLOR
from utils import sanitize_filename


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

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            try:
                if YTDLPHelper._run_yt_dlp(["-f", "bestaudio", "-o", webm_output_path, video_url]) is None:
                    return None

                if not os.path.exists(webm_output_path):
                    return None

                # Convert WebM to MP3
                convert_command = [
                    "ffmpeg",
                    "-y",  # Automatically overwrite existing files
                    "-i", f"{webm_output_path}",
                    "-vn",  # Ignore video
                    "-acodec", "libmp3lame",  # Use MP3 codec
                    "-b:a", "128k",  # Bitrate
                    f"{mp3_output_path}",
                ]
                subprocess.run(convert_command, check=True)

                if track_metadata:
                    self._add_metadata(mp3_output_path, track_metadata)

                return mp3_output_path

            finally:
                # Remove original WebM file
                if os.path.exists(webm_output_path):
                    os.remove(webm_output_path)

        except Exception as e:
            print(f"Conversion failed for {song}: {e}")
            return None

    def _add_metadata(self, input_file: str, track_metadata: dict):
        """Embed metadata (title, artist, album, and cover) into the file."""
        cover_path = input_file.replace(".mp3", "_cover.jpg")
        temp_output_file = input_file.replace(".mp3", "_tmp.mp3")
        try:
            cover_url = track_metadata.get("cover_url")

            command = ["ffmpeg", "-y", "-i", input_file]

            if cover_url:
                urllib.request.urlretrieve(cover_url, cover_path)
                command.extend(
                    [
                        "-i",
                        cover_path,
                        "-map",
                        "0:a",
                        "-map",
                        "1:v",
                        "-c",
                        "copy",
                        "-id3v2_version",
                        "3",
                        "-metadata:s:v",
                        "title=Album cover",
                        "-metadata:s:v",
                        "comment=Cover (front)",
                    ]
                )
            else:
                command.extend(["-map", "0:a", "-c", "copy", "-id3v2_version", "3"])

            # Add metadata fields
            metadata_fields = {
                "title": track_metadata.get("title", ""),
                "artist": track_metadata.get("artist", ""),
                "album": track_metadata.get("album", ""),
            }
            
            for key, value in metadata_fields.items():
                command.extend(["-metadata", f"{key}={value}"])
            
            command.append(temp_output_file)
            
            subprocess.run(command, check=True)
            os.replace(temp_output_file, input_file)
        
        except subprocess.CalledProcessError as e:
            print(f"{ERROR_COLOR}Error adding metadata to {input_file}: {e}{RESET_COLOR}")
        except Exception as e:
            print(f"{ERROR_COLOR}Unexpected error: {e}{RESET_COLOR}")
        finally:
            if os.path.exists(temp_output_file):
                os.remove(temp_output_file)
            if os.path.exists(cover_path):
                os.remove(cover_path)
    
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
        result = subprocess.run(command, capture_output=True, text=True)

        # Check for errors
        if result.returncode != 0:
            print(f"{ERROR_COLOR}Error executing yt-dlp: {result.stderr}{RESET_COLOR}")
            return None  # Return None to indicate failure
        
        # Check for warnings in stderr (yt-dlp may still succeed with warnings)
        if result.stderr:
            print(f"{WARNING_COLOR}Warning from yt-dlp: {result.stderr.strip()}{RESET_COLOR}")

        return result.stdout.strip()
