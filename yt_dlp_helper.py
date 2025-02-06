from enum import Enum
import subprocess
from typing import List, Optional

from config import ERROR_COLOR, RESET_COLOR, WARNING_COLOR, download_dir


class YTDLPMode(Enum):
    SEARCH = "search"
    DOWNLOAD = "download"

# Abstract Strategy Interface
class YTDLPStrategy:
    def execute(self, song: str, video_id: Optional[str] = None) -> Optional[str]:
        """Abstract method to be implemented by all strategies"""
        raise NotImplementedError
    
class SearchStrategy(YTDLPStrategy):
    def execute(self, song: str, video_id: Optional[str] = None) -> str:
        """Search a video on YouTube and return its video ID."""
        return YTDLPHelper._run_yt_dlp(["--print", "%(id)s", f"ytsearch1:{song}"])

class DownloadStrategy(YTDLPStrategy):
    def execute(self, song: str, video_id: Optional[str] = None):
        """
        Download the audio for the given song.
        If `video_id` is not provided or None, first search for the song.
        """
        if not video_id:
            video_id = YTDLPHelper.create_strategy(YTDLPMode.SEARCH).execute(song)

        if video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            YTDLPHelper._run_yt_dlp(["-f", "bestaudio", "-o", f"{download_dir}/%(title)s.%(ext)s", video_url])

    
class YTDLPHelper:
    @staticmethod
    def create_strategy(mode: YTDLPMode) -> YTDLPStrategy:
        """Factory method to return the appropriate strategy."""
        strategies = {
            YTDLPMode.SEARCH: SearchStrategy,
            YTDLPMode.DOWNLOAD: DownloadStrategy,
        }

        if mode not in strategies:
            raise ValueError(f"{ERROR_COLOR}Invalid mode: {mode}{RESET_COLOR}")

        return strategies[mode]()  # Instantiate the strategy

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