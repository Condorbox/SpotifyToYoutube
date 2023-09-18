import http
import os
import spotipy
import time
from spotipy.oauth2 import SpotifyOAuth
import pytube
from pytube.cli import on_progress
from pytube.exceptions import AgeRestrictedError
from pydub import AudioSegment
import urllib.error
import google_auth_oauthlib.flow
import googleapiclient.discovery
from colorama import Fore, Style

SONGS_DIR = ".\songs"
OUTPUT_DIR = ".\ogg_songs"
RESET_COLOR = Style.RESET_ALL
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
MESSAGE_COLOR = Fore.BLUE
MAX_RETRIES = 50

client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
redirect_uri = os.environ.get("REDIRECT_URI")
playlist_id = os.environ.get("PLALIST_ID")
json_url = os.environ.get("JSON_URL")

# Ask the user if want to download songs
dowload_songs = False
while True: 
    user_input = input("Do you want to download the songs(y/n): ")
    if user_input.upper() == "Y":
        dowload_songs = True
        print(f"Dowload songs -> {MESSAGE_COLOR}{dowload_songs}{RESET_COLOR}")
        break
    elif user_input.upper() == "N":
        dowload_songs = False
        print(f"Dowload songs -> {MESSAGE_COLOR}{dowload_songs}{RESET_COLOR}")
        break
    else:
        print("Not valid response, y or n")


# Connect to the user google count credentials
flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
    json_url,
    ["https://www.googleapis.com/auth/youtube.force-ssl"]
)

credentials = None
if not credentials or not credentials.valid:
    credentials = flow.run_local_server(port=8080, prompt="consent")

# Create yt playlist
youtube_api = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
playlist_yt_title = "My Music"
playlist_yt_description = "Favourite song from Spotify"
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

def add_song_to_playlist(video_id):
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

# Get Spotify Playlist
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id, client_secret, redirect_uri, scope="playlist-read-private"))
playlist = sp.playlist_tracks(playlist_id, limit=100)

# Read spotify playlist
while playlist["next"]:  
    for track in playlist["items"]:
        track_name = track["track"]["name"]
        artists = ", ".join([artist["name"] for artist in track["track"]["artists"]])
        print(f"Track: {track_name}, Artist: {artists}")
        search = pytube.Search(f"{artists} - {track_name}")
        video_id = search.results[0].video_id
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        add_song_to_playlist(video_id)
        # Dowload video
        if not dowload_songs:
            continue
        yt = pytube.YouTube(url=video_url, use_oauth=True, allow_oauth_cache=True, on_progress_callback=on_progress)
        retry_count = MAX_RETRIES
        while retry_count > 0:  # Retry loop to attempt to resolve connection issues
            try :
                audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').first()
                audio_stream.download(output_path=SONGS_DIR)
                print(f"Dowload {MESSAGE_COLOR}{track_name}{RESET_COLOR} to {MESSAGE_COLOR}{SONGS_DIR}{RESET_COLOR}")
                break
            except AgeRestrictedError as e:
                print(f"Song {MESSAGE_COLOR}{track_name}{RESET_COLOR} - {WARNING_COLOR}WARNING: {e}{RESET_COLOR}")
                break
            except (pytube.exceptions.PytubeError, http.client.RemoteDisconnected, urllib.error.URLError) as e:
                print(f"Song {track_name} - {ERROR_COLOR}ERROR: {e}{RESET_COLOR} , try: {MESSAGE_COLOR}{retry_count}{RESET_COLOR}")
                retry_count -= 1
                time.sleep(5)
    
    playlist = sp.next(playlist)

if  dowload_songs:
    # Convert from mp4 to ogg
    print("Converting...")

    for file in os.listdir(SONGS_DIR):
        if not file.endswith(".mp4"):
            continue
        input_file = os.path.join(SONGS_DIR, file)
        output_file = os.path.join(OUTPUT_DIR, os.path.splitext(file)[0] + ".ogg")
        audio = AudioSegment.from_file(input_file, format="mp4")
        audio.export(output_file, format="ogg")

    print("The conversion has been successful")