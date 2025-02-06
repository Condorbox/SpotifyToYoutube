import os
from colorama import Fore, Style

RESET_COLOR = Style.RESET_ALL
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
MESSAGE_COLOR = Fore.BLUE

client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
redirect_uri = os.environ.get("REDIRECT_URI")
spoti_playlist_id = os.environ.get("PLALIST_ID")
json_url = os.environ.get("JSON_URL")
download_dir = os.environ.get("DOWNLOAD_DIR")
playlist_offset = int(os.environ.get("PLAYLIST_OFFSET") or 0)