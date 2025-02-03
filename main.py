import os
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import google_auth_oauthlib.flow
import googleapiclient.discovery
from colorama import Fore, Style
from enum import Enum
from typing import Optional, List
import shutil
import sys

RESET_COLOR = Style.RESET_ALL
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
MESSAGE_COLOR = Fore.BLUE

client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
redirect_uri = os.environ.get("REDIRECT_URI")
spoti_playlist_id = os.environ.get("PLALIST_ID")
json_url = os.environ.get("JSON_URL")
download_dir = os.environ.get("DOWNLOAD_DIR")
playlist_offset = int(os.environ.get("PLAYLIST_OFFSET") or 0)

class YTDLPMode(Enum):
    SEARCH = "search"
    DOWNLOAD = "download"

if not shutil.which("ffmpeg"):
    print(f"{WARNING_COLOR}WARNING: FFmpeg is not installed, and yt-dlp may use it.{RESET_COLOR}")

if not shutil.which("yt-dlp"):
    print(f"{ERROR_COLOR}ERROR: yt-dlp is not installed or cannot be found in the system PATH.{RESET_COLOR}")
    sys.exit("yt-dlp not installed")  

def get_user_choice(prompt):
    while True:
        user_input = input(prompt).strip().upper()
        if user_input == "Y":
            return True
        elif user_input == "N":
            return False
        print(f"{ERROR_COLOR}Invalid response. Please enter 'y' or 'n'.{RESET_COLOR}")

download_songs = get_user_choice("Do you want to download the songs (y/n): ")
print(f"Download songs: {MESSAGE_COLOR}{download_songs}{RESET_COLOR}")

# Connect to the user google count credentials
flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
    json_url,
    ["https://www.googleapis.com/auth/youtube.force-ssl"]
)

credentials = flow.run_local_server(port=8080, prompt="consent")

# Get Spotify Playlist
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id, client_secret, redirect_uri, scope="playlist-read-private"))
playlist_sp = sp.playlist_tracks(spoti_playlist_id, limit=100, offset=playlist_offset)
playlist_details = sp.playlist(spoti_playlist_id)

# Create yt playlist
youtube_api = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
playlist_yt_title = playlist_details["name"]
playlist_yt_description = playlist_details["description"]

# Search if the playlist exits
existing_playlists = youtube_api.playlists().list(
    part="snippet",
    mine=True
).execute()

playlist_exists = False
for playlist in existing_playlists.get("items", []):
    if playlist["snippet"]["title"] == playlist_yt_title:
        playlist_exists = True
        playlist_id = playlist["id"]
        break

# Create playlist if not existed
if not playlist_exists:
    playlist_yt = youtube_api.playlists().insert(
        part='snippet,status',
        body={
            'snippet': {
                'title': playlist_yt_title,
                'description': playlist_yt_description
            },
            'status': {
                'privacyStatus': 'private'
            }
        }
    ).execute()
    playlist_id = playlist_yt['id']


def add_song_to_playlist(video_id: str):
    youtube_api.playlistItems().insert(
        part='snippet',
        body={
            'snippet': {
                'playlistId': playlist_id,
                'resourceId': {
                    'kind': 'youtube#video',
                    'videoId': video_id
                }
            }
        }
    ).execute()

def yt_dlp_action(song: str, mode: YTDLPMode, video_id: Optional[str] = None) -> Optional[str]:
    strategies = {
        YTDLPMode.SEARCH: search_strategy,
        YTDLPMode.DOWNLOAD: download_strategy,
    }

    strategy = strategies[mode]
    return strategy(song, video_id)

def search_strategy(song: str, video_id: Optional[str] = None) -> str:
    return run_yt_dlp(["--print", "%(id)s", f"ytsearch1:{song}"])

def download_strategy(song: str, video_id: Optional[str]):
    if not video_id:
        video_id = yt_dlp_action(song, YTDLPMode.SEARCH) 
    
    if video_id:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        run_yt_dlp(["-f", "bestaudio", "-o", f"{download_dir}/%(title)s.%(ext)s", video_url])

def run_yt_dlp(command_args: List[str]) -> Optional[str]:
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

# Read spotify playlist
while playlist_sp["next"]:
    for track in playlist_sp["items"]:
        track_name = track["track"]["name"]
        artists = ", ".join([artist["name"] for artist in track["track"]["artists"]])
        song_query = f"{artists} - {track_name}"
        print(f"Track: {MESSAGE_COLOR}{song_query}{RESET_COLOR}")

        video_id = yt_dlp_action(song_query, YTDLPMode.SEARCH)

        if video_id:
            add_song_to_playlist(video_id)

            if download_songs:
                yt_dlp_action(song_query, YTDLPMode.DOWNLOAD, video_id)  

    playlist_sp = sp.next(playlist_sp)
