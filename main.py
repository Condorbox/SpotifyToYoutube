import logging
from tqdm import tqdm

from resume_tracker import ResumeTracker
from playlist_snapshot import PlaylistSnapshot
from youtube_service import YouTubeService
from spotify_service import SpotifyService
from yt_dlp_helper import YTDLPHelper, YTDLPMode
from playlist_converter import convert_playlist
from sync_mode import build_single_page_playlist, collect_playlist_items, diff_playlist_items

from config import ERROR_COLOR, RESET_COLOR, MESSAGE_COLOR, Mode, setup_logging, load_settings

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

    sp_service = SpotifyService(settings)
    snapshot = PlaylistSnapshot.from_settings(settings.snapshot_file)

    sp_playlist = sp_service.get_playlist()
    spotify_playlist_for_convert = sp_playlist
    snapshot_current_ids: set[str] | None = None

    if settings.mode == Mode.SYNC:
        previous = snapshot.get(settings.playlist_id).track_ids if settings.playlist_id else set()
        current_items = collect_playlist_items(sp_service, sp_playlist)
        diff = diff_playlist_items(previous_track_ids=previous, current_items=current_items)
        snapshot_current_ids = diff.current_track_ids

        logger.info(
            "Sync diff: %s%d added%s, %s%d removed%s",
            MESSAGE_COLOR,
            len(diff.added_track_ids),
            RESET_COLOR,
            MESSAGE_COLOR,
            len(diff.removed_track_ids),
            RESET_COLOR,
        )
        if diff.missing_identifier_count:
            logger.warning(
                "Found %d playlist items without a stable Spotify track identifier; they can't be tracked for sync.",
                diff.missing_identifier_count,
            )
        if diff.removed_track_ids:
            logger.info("Removals are detected but not removed from the YouTube playlist.")

        if not diff.items_to_process:
            logger.info("No new tracks to process.")
            if settings.playlist_id and snapshot_current_ids is not None:
                snapshot.set(settings.playlist_id, snapshot_current_ids)
            raise SystemExit(0)

        spotify_playlist_for_convert = build_single_page_playlist(diff.items_to_process)

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
    if settings.playlist_offset:
        logger.info("Spotify playlist offset: %s%d%s", MESSAGE_COLOR, settings.playlist_offset, RESET_COLOR)

    # Initialize services
    yt_service = YouTubeService(settings)
    tracker = ResumeTracker.from_settings(settings.tracker_file)

    search_strategy = YTDLPHelper.create_strategy(YTDLPMode.SEARCH)
    download_strategy = (
        YTDLPHelper.create_strategy(YTDLPMode.DOWNLOAD, download_dir=settings.download_dir)
        if download_songs
        else None
    )

    # Count total tracks for the progress bar
    raw_total = spotify_playlist_for_convert.get("total", 0) or 0
    raw_offset = spotify_playlist_for_convert.get("offset", 0) or 0
    try:
        total_value = int(raw_total)
    except (TypeError, ValueError):
        total_value = 0
    try:
        offset_value = int(raw_offset)
    except (TypeError, ValueError):
        offset_value = 0
    total = max(0, max(0, total_value) - max(0, offset_value))
    desc = "Syncing playlist" if settings.mode == Mode.SYNC else "Converting playlist"

    with tqdm(total=total, desc=desc, unit="track") as progress:
        result = convert_playlist(
            spotify=sp_service,
            youtube=yt_service,
            spotify_playlist=spotify_playlist_for_convert,
            search_strategy=search_strategy,
            download_strategy=download_strategy,
            tracker=tracker if download_songs else None,
            download_songs=download_songs,
            workers=settings.workers,
            progress=progress,
        )

    if settings.mode == Mode.SYNC and settings.playlist_id and snapshot_current_ids is not None:
        snapshot.set(settings.playlist_id, snapshot_current_ids)

    logger.info(f"Playlist: {MESSAGE_COLOR}'{result.playlist_name}'{RESET_COLOR}")
    logger.debug(f"YouTube playlist ID: {result.youtube_playlist_id}")
    logger.info("Done!")
