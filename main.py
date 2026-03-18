import logging
from tqdm import tqdm

from resume_tracker import ResumeTracker
from youtube_service import YouTubeService
from spotify_service import SpotifyService
from yt_dlp_helper import YTDLPHelper, YTDLPMode

from config import ERROR_COLOR, RESET_COLOR, MESSAGE_COLOR, WARNING_COLOR, setup_logging, args

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
    setup_logging(args.log_level, args.log_file)

    download_songs = get_user_choice("Do you want to download the songs (y/n): ")
    logger.info(f"Download songs: {MESSAGE_COLOR}{download_songs}{RESET_COLOR}")

    # Initialize services
    yt_service = YouTubeService()
    sp_service = SpotifyService()
    tracker = ResumeTracker()

    # Get Spotify playlist details
    playlist_name, playlist_description = sp_service.get_playlist_details()
    sp_playlist = sp_service.get_playlist()
    logger.info(f"Playlist: {MESSAGE_COLOR}'{playlist_name}'{RESET_COLOR}")

    # Get or create YouTube playlist
    yt_playlist_id = yt_service.get_or_create_playlist_id(title=playlist_name, description=playlist_description)
    track_set = yt_service.get_existing_video_ids(playlist_id=yt_playlist_id)
    logger.debug(f"YouTube playlist ID: {yt_playlist_id} ({len(track_set)} existing videos)")

    search_strategy = YTDLPHelper.create_strategy(YTDLPMode.SEARCH)
    download_strategy = YTDLPHelper.create_strategy(YTDLPMode.DOWNLOAD)

    # Count total tracks for the progress bar
    total = sp_playlist.get("total", 0)
    processed = 0

    with tqdm(total=total, desc="Converting playlist", unit="track") as progress:
        # Read Spotify playlist
        while True:
            for track in sp_playlist["items"]:
                track_info = track.get("track")

                if not track_info:
                    logger.warning(f"{WARNING_COLOR}Skipping removed/unavailable track{RESET_COLOR}")
                    progress.update(1)
                    continue

                track_metadata = {
                    "title": track_info["name"],
                    "album": track_info["album"]["name"],
                    "artist": "/".join([artist["name"] for artist in track_info["artists"]]),
                    "cover_url": track_info["album"]["images"][0]["url"] if track_info["album"]["images"] else None,
                }

                song_query = f"{track_metadata['artist']} - {track_metadata['title']}"
                progress.set_postfix_str(song_query[:50])
                logger.debug(f"Processing: {song_query}")

                # print(f"Track: {MESSAGE_COLOR}{song_query}{RESET_COLOR}")

                video_id = search_strategy.execute(song=song_query)

                if video_id and video_id not in track_set:
                    yt_service.add_song_to_playlist(video_id=video_id, playlist_id=yt_playlist_id)
                    track_set.add(video_id)
                    logger.debug(f"Added to YouTube playlist: {video_id}")

                if download_songs:
                    if tracker.is_downloaded(song_query):
                        logger.debug(f"Already downloaded, skipping: {song_query}")
                    else:
                        download_strategy.execute(song=song_query, video_id=video_id, track_metadata=track_metadata)
                        tracker.mark_downloaded(song_query)

                progress.update(1)

            if not sp_playlist["next"]:
                break
            sp_playlist = sp_service.next(sp_playlist)

    logger.info("Done!")