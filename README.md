# Spotify to YouTube Playlist Converter

This is a Python program that allows you to create a YouTube playlist from songs in a Spotify playlist and optionally download the songs in audio format.

## Prerequisites

Before running this program, make sure you have the following installed:

- Python 3.x
- [Spotipy](https://github.com/plamere/spotipy): A Python library for interacting with the Spotify API.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp): A Python library for downloading YouTube videos and audio.
- [Google APIs Client Library](https://developers.google.com/api-client-library/python/start/installation): For interacting with the YouTube API.
- [colorama](https://pypi.org/project/colorama/): For formatting text in the console.
- [FFmpeg](https://ffmpeg.org/): Although not mandatory, yt-dlp may not work properly without it.

Also, make sure to set up your Spotify and YouTube API credentials before running the program. You can find more information in the configuration section below.

## Configuration

1. Set up your Spotify and YouTube API credentials:

   - Get a `client_id`, `client_secret`, and `redirect_uri` from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications).
   - Download the JSON credentials file from the [Google Developer Console](https://console.developers.google.com/), which will be used for authentication with the YouTube API.
   - Define the following environment variables on your system or create a `.env` file in the project's root directory:

   ```plaintext
   CLIENT_ID=<Your Spotify client_id>
   CLIENT_SECRET=<Your Spotify client_secret>
   REDIRECT_URI=<Your Spotify redirect_uri>
   JSON_URL=<Path to your Google credentials JSON file>
   PLAYLIST_ID=<The ID of the Spotify playlist you want to convert>
   DOWNLOAD_DIR=<Path to the directory where downloaded audio files will be saved>
   ```
2. Install program dependencies by running
    ```plaintext
    pip install spotipy yt-dlp google-auth-oauthlib google-api-python-client colorama
     ```
## Usage

Run the program from the command line. The program will ask if you want to download the songs.
Respond "y" to download them or "n" to skip the download.
The program will search for songs from your Spotify playlist, add them to a YouTube playlist (created automatically if it doesn't exist),
and download the songs in the best available audio format if you selected the option.

## License
This project is licensed under the MIT License. See the [LICENSE](https://github.com/Condorbox/SpotifyToYoutube/blob/main/LICENSE) file for more details.
