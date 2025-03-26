from enum import Enum
import os
import subprocess
from typing import List, Optional

from config import ERROR_COLOR, RESET_COLOR, WARNING_COLOR, download_dir


class YTDLPMode(Enum):
    SEARCH = "search"
    DOWNLOAD = "download"

# Abstract Strategy Interface
class YTDLPStrategy:
    def execute(self, song: str, video_id: Optional[str] = None, track_metadata: Optional[dict] = None) -> Optional[str]:
        """Abstract method to be implemented by all strategies"""
        raise NotImplementedError
    
class SearchStrategy(YTDLPStrategy):
    def execute(self, song: str, video_id: Optional[str] = None, track_metadata: Optional[dict] = None) -> str:
        """Search a video on YouTube and return its video ID."""
        return YTDLPHelper._run_yt_dlp(["--print", "%(id)s", f"ytsearch1:{song}"])

class DownloadStrategy(YTDLPStrategy):
    def execute(self, song: str, video_id: Optional[str] = None, track_metadata: Optional[dict] = None):
        """
        Download the audio for the given song.
        If `video_id` is not provided or None, first search for the song.
        """
        try:
            if not video_id:
                video_id = YTDLPHelper.create_strategy(YTDLPMode.SEARCH).execute(song)

            if video_id:
                webm_output_path = os.path.join(download_dir, f"{song}.webm")
                mp3_output_path = os.path.join(download_dir, f"{song}.mp3")
                
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                YTDLPHelper._run_yt_dlp(["-f", "bestaudio", "-o", webm_output_path, video_url])

                # Convert WebM to MP3
                convert_command = [
                    "ffmpeg", 
                    "-i", webm_output_path, 
                    "-vn",  # Ignore video
                    "-acodec", "libmp3lame",  # Use MP3 codec
                    "-b:a", "128k",  # Bitrate
                    mp3_output_path
                ]
                subprocess.run(convert_command, check=True)

                if track_metadata:
                    self._add_metadata(mp3_output_path, track_metadata)
        
                # Remove original WebM file
                os.remove(webm_output_path)

        except Exception as e:
            print(f"Conversion failed for {song}: {e}")

    def _add_metadata(self, input_file: str, track_metadata: dict):
        """Embed metadata (title, artist, album, and cover) into the file."""
        try:
            command = [
                "ffmpeg", 
                "-i", input_file,
                "-c", "copy"  # Copy audio without re-encoding
            ]
            
            # Add metadata fields
            metadata_fields = {
                "title": track_metadata.get('title', ''),
                "artist": track_metadata.get('artist', ''),
                "album": track_metadata.get('album', '')
            }
            
            for key, value in metadata_fields.items():
                command.extend(["-metadata", f"{key}={value}"])
            
            # Generate temporary output file
            temp_output_file = input_file.replace('.mp3', f'_tmp.mp3')
            command.append(temp_output_file)
            
            subprocess.run(command, check=True)
            os.replace(temp_output_file, input_file)
        
        except subprocess.CalledProcessError as e:
            print(f"{ERROR_COLOR}Error adding metadata to {input_file}: {e}{RESET_COLOR}")
        except Exception as e:
            print(f"{ERROR_COLOR}Unexpected error: {e}{RESET_COLOR}")
            # Cleanup temp file if it exists
            temp_output_file = input_file.replace('.mp3', f'_tmp.mp3')
            if os.path.exists(temp_output_file):
                os.remove(temp_output_file)
    
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