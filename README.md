# Spotify to YouTube Playlist Converter

This is a Python program that allows you to create a YouTube playlist from songs in a Spotify playlist and optionally download the songs in mp3 format.

## Prerequisites

Before running this program, make sure you have the following installed:

- Python 3.x
- [Spotipy](https://github.com/plamere/spotipy): A Python library for interacting with the Spotify API.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp): A Python library for downloading YouTube videos and audio.
- [Google APIs Client Library](https://developers.google.com/api-client-library/python/start/installation): For interacting with the YouTube API.
- [colorama](https://pypi.org/project/colorama/): For formatting text in the console.
- [FFmpeg](https://ffmpeg.org/): Used by yt-dlp to properly download and process audio. The program automatically converts downloaded songs to MP3 format and embeds useful metadata (such as artist, album, and title).

Also, make sure to set up your Spotify and YouTube API credentials before running the program. You can find more information in the configuration section below.

> **Warning**
> Due to recent Spotify API changes, this project requires a **Spotify Premium** account for the Spotify side of the workflow.

## Configuration

You can provide configuration via **CLI flags** or **environment variables** (including a `.env` file).

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
   DOWNLOAD_DIR=<Path to the directory where downloaded audio files will be saved (required only when downloading)>
   PLAYLIST_OFFSET=<Offset for Spotify playlist pagination (default: 0)>
   TRACKER_FILE=<Path to the download tracker JSON file (optional, defaults to ./downloaded_songs.json)>
   ```

2. Install program dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   **Note**: `yt-dlp` and `ffmpeg` must be installed separately and available on your `PATH`.

## Usage

Run the program from the command line:

```bash
python main.py --help
```

Common CLI options:

- Spotify: `--client-id`, `--client-secret`, `--redirect-uri`, `--playlist-id` (or `CLIENT_ID`, `CLIENT_SECRET`, `REDIRECT_URI`, `PLAYLIST_ID`)
- YouTube: `--json-url` (or `JSON_URL`)
- Downloading: `--download` / `--no-download`, `--download-dir` (or `DOWNLOAD_DIR`), `--tracker-file`
- Other: `--playlist-offset`, `--log-level`, `--log-file`

By default, the program will prompt you whether to download songs. You can skip the prompt with:

- `--download` (download without prompting; requires `--download-dir` or `DOWNLOAD_DIR`)
- `--no-download` (skip downloads without prompting)

Example: convert playlist only (no downloads):

```bash
python main.py --no-download
```

Example: convert playlist + download audio:

```bash
python main.py --download --download-dir ./downloads
```

The program performs the following steps:
1. Authenticates with the Spotify and YouTube APIs.
2. Retrieves the playlist name and description from Spotify.
3. Creates or retrieves a corresponding YouTube playlist.
4. Searches for each song from the Spotify playlist on YouTube.
5. Adds the found videos to the YouTube playlist.
6. Optionally downloads the songs as audio files.
7. Change the video format to mp3 and add metadata.

## Features
+ **Spotify to YouTube Playlist Conversion**: Converts a Spotify playlist into a YouTube playlist.
+ **YouTube Playlist Management**: Creates a new YouTube playlist if it doesn't exist or update if it exist.
+ **Duplicate Video Prevention**: Ensures that a song is not added to the YouTube playlist more than once.
+ **Song Downloading with Metadata**: Downloads songs in mp3 format and automatically embeds artist, album, and title metadata using yt-dlp and FFmpeg.

## Development

Run the test suite:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest
```

## License
This project is licensed under the MIT License. See the [LICENSE](https://github.com/Condorbox/SpotifyToYoutube/blob/main/LICENSE) file for more details.
