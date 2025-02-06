from enum import Enum
import subprocess
from typing import List, Optional

from config import ERROR_COLOR, RESET_COLOR, WARNING_COLOR, download_dir


class YTDLPMode(Enum):
    SEARCH = "search"
    DOWNLOAD = "download"
    
class YTDLPHelper:
    @staticmethod
    def yt_dlp_action(song: str, mode: YTDLPMode, video_id: Optional[str] = None) -> Optional[str]:
        strategies = {
            YTDLPMode.SEARCH: YTDLPHelper._search_strategy,
            YTDLPMode.DOWNLOAD: YTDLPHelper._download_strategy,
        }

        strategy = strategies[mode]
        return strategy(song=song, video_id=video_id)
    
    @staticmethod
    def _search_strategy(song: str, video_id: Optional[str] = None) -> str:
        return YTDLPHelper._run_yt_dlp(["--print", "%(id)s", f"ytsearch1:{song}"])

    @staticmethod
    def _download_strategy(song: str, video_id: Optional[str]):
        if not video_id:
            video_id = YTDLPHelper.yt_dlp_action(song, YTDLPMode.SEARCH) 
        
        if video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            YTDLPHelper._run_yt_dlp(["-f", "bestaudio", "-o", f"{download_dir}/%(title)s.%(ext)s", video_url])

    @staticmethod
    def _run_yt_dlp(command_args: List[str]) -> Optional[str]:
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