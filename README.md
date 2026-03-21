# Spotify → YouTube (and MP3) Playlist CLI

Lightweight Python CLI to:

1) mirror a Spotify playlist into a YouTube playlist, and  
2) optionally download each track as a tagged MP3 (via `yt-dlp` + `ffmpeg`).

> Note: due to recent Spotify API changes, this workflow typically requires a **Spotify Premium** account.

## Features

- **Convert mode** (default): processes every playlist item.
- **Sync mode**: only processes tracks added since your last run (snapshot-based).
- **Concurrent workers**: `--workers N` runs track processing in a thread pool (faster on large playlists).
- **Duplicate protection**: prevents adding the same YouTube video ID twice (even with many workers).
- **Resumable downloads**: tracks downloaded items in a local JSON tracker so re-runs don’t re-download.
- **Downloads with metadata**: MP3 conversion + ID3 tags + optional cover art embedding.
- **Spotify offset**: start converting from a specific playlist index via `--playlist-offset` / `PLAYLIST_OFFSET`.
- **Good CLI UX**: progress bar (tqdm), clear logs, optional log file.

## Requirements

- Python **3.10+**
- A Spotify Developer app (client id/secret + redirect URI)
- A Google OAuth client JSON for YouTube Data API v3
- External tools on your `PATH`:
  - `yt-dlp`
  - `ffmpeg`

## Install

```bash
pip install -r requirements.txt
```

For development/tests:

```bash
pip install -r requirements-dev.txt
pytest
```

> **Important**
> `yt-dlp` and `ffmpeg` are **not installed via pip**.  
> You must install them separately and ensure they are available on your system `PATH`.

## Configuration

You can configure everything via **CLI flags** or **environment variables**. A `.env` file is supported.

### Minimal `.env` example

```dotenv
CLIENT_ID=...
CLIENT_SECRET=...
REDIRECT_URI=http://localhost:8888/callback
PLAYLIST_ID=...
JSON_URL=/absolute/path/to/google-oauth-client.json
```

Optional:

```dotenv
DOWNLOAD_DIR=./downloads
PLAYLIST_OFFSET=0
WORKERS=4
TRACKER_FILE=./downloaded_songs.json
SNAPSHOT_FILE=./playlist_snapshot.json
```

### CLI flags (summary)

- Spotify: `--client-id`, `--client-secret`, `--redirect-uri`, `--playlist-id`
- YouTube: `--json-url`
- Downloads: `--download` / `--no-download`, `--download-dir`, `--tracker-file`
- Sync: `sync` subcommand or `--sync`, `--snapshot-file`
- Performance: `--workers`
- Debugging: `--log-level`, `--log-file`
- Pagination: `--playlist-offset`

Run `python main.py --help` for the full help output.

## Usage

### Convert (full conversion)

Convert the playlist to YouTube (no downloads):

```bash
python main.py --no-download
```

Convert + download MP3s (non-interactive):

```bash
python main.py --download --download-dir ./downloads
```

Run with 4 workers (thread pool):

```bash
python main.py --workers 4 --no-download
```

Start converting from a Spotify pagination offset:

```bash
python main.py --playlist-offset 200 --no-download
```

`PLAYLIST_OFFSET` is a **0-based** Spotify API offset (offset 200 starts at the 201st playlist item).  
The progress bar and `ConvertResult.total` reflect the **remaining** items (`total - offset`).

### Sync (incremental updates)

Sync mode only processes tracks that were added since your last sync run. It stores a snapshot of Spotify
track identifiers in `playlist_snapshot.json` (configurable via `--snapshot-file` / `SNAPSHOT_FILE`).

First sync run (no snapshot yet) behaves like a full conversion, then future runs only process additions:

```bash
python main.py sync --no-download
```

Alias flag (equivalent to the `sync` subcommand):

```bash
python main.py --sync --no-download
```

Removals are detected and logged, but the tool currently does not remove videos from the YouTube playlist.

## Output files

- `downloaded_songs.json`: download tracker used to skip already-downloaded tracks on re-runs
  (path configurable via `--tracker-file` / `TRACKER_FILE`).
- `playlist_snapshot.json`: sync snapshot of Spotify track identifiers
  (path configurable via `--snapshot-file` / `SNAPSHOT_FILE`).
- `DOWNLOAD_DIR`: where MP3 files are written when downloads are enabled.

## Troubleshooting

- **YouTube quota exceeded**: the YouTube Data API has daily quotas. If you hit the limit, you’ll need to wait
  for quota reset and re-run.
- **OAuth redirect issues**: ensure your `REDIRECT_URI` matches the value configured in the Spotify Developer dashboard.
- **`yt-dlp` / `ffmpeg` not found**: install them and ensure they’re available on your `PATH`.
- **Matching accuracy**: YouTube matching uses `yt-dlp` search (`ytsearch1:`). Results may vary; retrying with fewer workers
  and `--log-level DEBUG` can help diagnose unexpected matches.

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/Condorbox/SpotifyToYoutube/blob/main/LICENSE) file for more details.