from youtube_service import YouTubeService
from spotify_service import SpotifyService
from yt_dlp_helper import YTDLPHelper, YTDLPMode

from config import ERROR_COLOR, RESET_COLOR, MESSAGE_COLOR

def get_user_choice(prompt):
    while True:
        user_input = input(prompt).strip().upper()
        if user_input == "Y":
            return True
        elif user_input == "N":
            return False
        print(f"{ERROR_COLOR}Invalid response. Please enter 'y' or 'n'.{RESET_COLOR}")

if __name__ == '__main__':
    download_songs = get_user_choice("Do you want to download the songs (y/n): ")
    print(f"Download songs: {MESSAGE_COLOR}{download_songs}{RESET_COLOR}")

    # Initialize services
    yt_service = YouTubeService()
    sp_service = SpotifyService()

    # Get Spotify playlist details
    playlist_name, playlist_description = sp_service.get_playlist_details()
    sp_playlist = sp_service.get_playlist()

    # Get or create YouTube playlist
    yt_playlist_id = yt_service.get_or_create_playlist_id(title=playlist_name, description=playlist_description)
    track_set = yt_service.get_existing_video_ids(playlist_id=yt_playlist_id)

    search_strategy = YTDLPHelper.create_strategy(YTDLPMode.SEARCH)
    download_strategy = YTDLPHelper.create_strategy(YTDLPMode.DOWNLOAD)

    # Read spotify playlist
    while sp_playlist["next"]:
        for track in sp_playlist["items"]:
            track_info = track["track"]
            track_metadata = {
                "title": track_info["name"],
                "album": track_info["album"]["name"],
                "artist": ", ".join([artist["name"] for artist in track_info["artists"]]),
                "cover_url": track_info["album"]["images"][0]["url"] if track_info["album"]["images"] else None,
            }

            song_query = f"{track_metadata['artist']} - {track_metadata['title']}"
            print(f"Track: {MESSAGE_COLOR}{song_query}{RESET_COLOR}")

            video_id = search_strategy.execute(song=song_query)

            if video_id and video_id not in track_set:
                yt_service.add_song_to_playlist(video_id=video_id, playlist_id=yt_playlist_id)
                track_set.add(video_id)

            if download_songs:
                download_strategy.execute(song=song_query, video_id=video_id, track_metadata=track_metadata)

        sp_playlist = sp_service.next(sp_playlist)