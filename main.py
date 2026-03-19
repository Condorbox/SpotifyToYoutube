import logging
from tqdm import tqdm

from resume_tracker import ResumeTracker
from youtube_service import YouTubeService
from spotify_service import SpotifyService
from yt_dlp_helper import YTDLPHelper, YTDLPMode
from playlist_converter import convert_playlist

from config import ERROR_COLOR, RESET_COLOR, MESSAGE_COLOR, setup_logging, load_settings

logger = logging.getLogger(__name__)

def get_user_choice(prompt):
    while True:
        user_input = input(prompt).strip().upper()
        if user_input == "Y":
            return True
        elif user_input == "N":
            return False
        print(f"{ERROR_COLOR}Invalid response. Please enter 'y' or 'n'.{RESET_COLOR}")

if __name__ == '__main__':
    settings = load_settings()
    setup_logging(settings.log_level, settings.log_file)

    if settings.download:
        download_songs = True
    elif settings.no_download:
        download_songs = False
    else:
        download_songs = get_user_choice("Do you want to download the songs (y/n): ")

    if download_songs and not settings.download_dir:
        raise SystemExit(
            "\n[ERROR] Missing required configuration for downloads. "
            "Provide --download-dir or DOWNLOAD_DIR."
        )

    logger.info(f"Download songs: {MESSAGE_COLOR}{download_songs}{RESET_COLOR}")

    # Initialize services
    yt_service = YouTubeService(settings)
    sp_service = SpotifyService(settings)
    tracker = ResumeTracker.from_settings(settings.tracker_file)

    search_strategy = YTDLPHelper.create_strategy(YTDLPMode.SEARCH)
    download_strategy = (
        YTDLPHelper.create_strategy(YTDLPMode.DOWNLOAD, download_dir=settings.download_dir)
        if download_songs
        else None
    )

    sp_playlist = sp_service.get_playlist()

    # Count total tracks for the progress bar
    total = sp_playlist.get("total", 0)

    with tqdm(total=total, desc="Converting playlist", unit="track") as progress:
        result = convert_playlist(
            spotify=sp_service,
            youtube=yt_service,
            spotify_playlist=sp_playlist,
            search_strategy=search_strategy,
            download_strategy=download_strategy,
            tracker=tracker if download_songs else None,
            download_songs=download_songs,
            progress=progress,
        )

    logger.info(f"Playlist: {MESSAGE_COLOR}'{result.playlist_name}'{RESET_COLOR}")
    logger.debug(f"YouTube playlist ID: {result.youtube_playlist_id}")
    logger.info("Done!")
