import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pytube
from pytube.cli import on_progress
from pytube.exceptions import AgeRestrictedError
from pydub import AudioSegment

client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
redirect_uri = os.environ.get("REDIRECT_URI")
playlist_id = os.environ.get("PLALIST_ID")

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id, client_secret, redirect_uri, scope="playlist-read-private"))
playlist = sp.playlist_tracks(playlist_id, limit=100)

while playlist['next']:  
    for track in playlist["items"]:
        track_name = track["track"]["name"]
        artists = ", ".join([artist["name"] for artist in track["track"]["artists"]])
        print(f"Track: {track_name}, Artist: {artists}")

        search = pytube.Search(f"{artists} - {track_name}")
        video_url = f"https://www.youtube.com/watch?v={search.results[0].video_id}"
        yt = pytube.YouTube(url=video_url, use_oauth=True, allow_oauth_cache=True, on_progress_callback=on_progress)
        try :
            audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').first()
            output_path = "./songs"
            audio_stream.download(output_path=output_path)
            print(f"Dowload {track_name} to {output_path}")
        except AgeRestrictedError as e:
            print(f"{track_name} ERROR: age restricted -> {e}")
    
    playlist = sp.next(playlist)

SONGS_DIR = ".\songs"
OUTPUT_DIR = ".\ogg_songs"

print("Converting...")

for file in os.listdir(SONGS_DIR):
    if(not file.endswith(".mp4")):
        continue
    input_file = os.path.join(SONGS_DIR, file)
    output_file = os.path.join(OUTPUT_DIR, os.path.splitext(file)[0] + '.ogg')
    audio = AudioSegment.from_file(input_file, format="mp4")
    audio.export(output_file, format="ogg")

print("The conversion has been successful")