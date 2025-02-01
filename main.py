import os
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import google_auth_oauthlib.flow
import googleapiclient.discovery
from colorama import Fore, Style

RESET_COLOR = Style.RESET_ALL
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
MESSAGE_COLOR = Fore.BLUE

client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
redirect_uri = os.environ.get("REDIRECT_URI")
spoti_playlist_id = os.environ.get("PLALIST_ID")
json_url = os.environ.get("JSON_URL")
yt_playlits_name = os.environ.get("PLAYLIST_NAME")
download_dir = os.environ.get("DOWNLOAD_DIR")

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
playlist_yt_title = yt_playlits_name
playlist_yt_description = "Song from Spotify"
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

def search_song(song):
    command = [
        "yt-dlp",
        "--print", "%(id)s",
        f"ytsearch1:{song}" 
    ]
    
    resultado = subprocess.run(command, capture_output=True, text=True)

    if resultado.stderr:
        print(f"Error searching song: {song}\n error: {resultado.stderr}")
        #exit(-1)

    video_id = resultado.stdout.strip()
    
    return video_id

def download_song(video_url):
    command = [
        "yt-dlp", 
        "-f", "bestaudio", 
        "-o", f"{download_dir}/%(title)s.%(ext)s", 
        video_url
    ]

    subprocess.run(command)


# Get Spotify Playlist
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id, client_secret, redirect_uri, scope="playlist-read-private"))
playlist = sp.playlist_tracks(spoti_playlist_id, limit=100)

# Read spotify playlist
while playlist["next"]:
    for track in playlist["items"]:
        track_name = track["track"]["name"]
        artists = ", ".join([artist["name"] for artist in track["track"]["artists"]])
        print(f"Track: {track_name}, Artist: {artists}")
        video_id = search_song(f"{artists} - {track_name}")
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        add_song_to_playlist(video_id)
        if not dowload_songs:
            continue
        download_song(video_url)

    playlist = sp.next(playlist)
