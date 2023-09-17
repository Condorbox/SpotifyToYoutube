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
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
redirect_uri = os.environ.get("REDIRECT_URI")
playlist_id = os.environ.get("PLALIST_ID")
json_url = os.environ.get("JSON_URL")
max_retries = 50

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

def add_song_to_playlist(video_id):
    youtube_api.playlistItems().insert(
        part='snippet',
        body={
            'snippet': {
                'playlistId': playlist_yt['id'],
                'resourceId': {
                    'kind': 'youtube#video',
                    'videoId': video_id
                }
            }
        }
    ).execute()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id, client_secret, redirect_uri, scope="playlist-read-private"))
playlist = sp.playlist_tracks(playlist_id, limit=100)

# Read spotify playlist
while playlist['next']:  
    for track in playlist["items"]:
        track_name = track["track"]["name"]
        artists = ", ".join([artist["name"] for artist in track["track"]["artists"]])
        print(f"Track: {track_name}, Artist: {artists}")
        search = pytube.Search(f"{artists} - {track_name}")
        video_id = search.results[0].video_id
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        add_song_to_playlist(video_id)
        yt = pytube.YouTube(url=video_url, use_oauth=True, allow_oauth_cache=True, on_progress_callback=on_progress)
        retry_count = max_retries
        while retry_count > 0:
            try :
                audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').first()
                output_path = "./songs"
                audio_stream.download(output_path=output_path)
                print(f"Dowload {track_name} to {output_path}")
                break
            except AgeRestrictedError as e:
                print(f"Song {track_name} WARNING: {e}")
                break
            except (pytube.exceptions.PytubeError, http.client.RemoteDisconnected, urllib.error.URLError) as e:
                print(f"Song {track_name} ERROR: {e}")
                retry_count -= 1
                time.sleep(5)
    
    playlist = sp.next(playlist)

SONGS_DIR = ".\songs"
OUTPUT_DIR = ".\ogg_songs"

print("Converting...")
# Convert form mp4 to ogg
for file in os.listdir(SONGS_DIR):
    if(not file.endswith(".mp4")):
        continue
    input_file = os.path.join(SONGS_DIR, file)
    output_file = os.path.join(OUTPUT_DIR, os.path.splitext(file)[0] + '.ogg')
    audio = AudioSegment.from_file(input_file, format="mp4")
    audio.export(output_file, format="ogg")

print("The conversion has been successful")