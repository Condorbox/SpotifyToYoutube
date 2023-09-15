import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pytube
import os

client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
redirect_uri = os.environ.get("REDIRECT_URI")

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id, client_secret, redirect_uri, scope="playlist-read-private"))

playlist_id = os.environ.get("PLALIST_ID")
playlist = sp.playlist_tracks(playlist_id)

for track in playlist["items"]:
    track_name = track["track"]["name"]
    artists = ", ".join([artist["name"] for artist in track["track"]["artists"]])
    print(f"Track: {track_name}, Artist: {artists}")

first_track = playlist["items"][0]["track"]
first_track_name = first_track["name"]
first_track_artist = ", ".join([artist['name'] for artist in first_track['artists']])
s = pytube.Search(f"{first_track_name}, {first_track_artist}")

yt = s.results[0]
print("___________________________________________")
print(f"song: {yt.title} , channel: {yt.author}")

audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').first()

output_path = "./songs"
audio_stream.download(output_path=output_path)
print(f"Descarga completa: {output_path}")