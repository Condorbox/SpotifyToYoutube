import os
import argparse
from colorama import Fore, Style
import logging
from dotenv import load_dotenv
from dataclasses import dataclass

RESET_COLOR = Style.RESET_ALL
WARNING_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
MESSAGE_COLOR = Fore.BLUE

load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    client_id: str | None
    client_secret: str | None
    redirect_uri: str | None
    playlist_id: str | None
    json_url: str | None
    download_dir: str | None
    playlist_offset: int
    download: bool
    no_download: bool
    log_level: str
    log_file: str | None


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a Spotify playlist to YouTube and optionally download songs."
    )
    parser.add_argument("--client-id", default=os.environ.get("CLIENT_ID"), help="Spotify client ID")
    parser.add_argument("--client-secret", default=os.environ.get("CLIENT_SECRET"), help="Spotify client secret")
    parser.add_argument("--redirect-uri", default=os.environ.get("REDIRECT_URI"), help="Spotify redirect URI")
    parser.add_argument("--playlist-id", default=os.environ.get("PLAYLIST_ID"), help="Spotify playlist ID to convert")
    parser.add_argument("--json-url", default=os.environ.get("JSON_URL"), help="Path to Google credentials JSON file")
    parser.add_argument("--download-dir", default=os.environ.get("DOWNLOAD_DIR"), help="Directory to save downloaded songs")
    parser.add_argument(
        "--playlist-offset",
        default=int(os.environ.get("PLAYLIST_OFFSET") or 0),
        type=int,
        help="Offset for Spotify playlist pagination (default: 0)",
    )

    download_group = parser.add_mutually_exclusive_group()
    download_group.add_argument("--download", action="store_true", default=False, help="Download songs without prompting")
    download_group.add_argument("--no-download", action="store_true", help="Skip download without prompting")

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    parser.add_argument("--log-file", default=None, help="Optional path to write logs to a file")
    return parser


def load_settings(argv: list[str] | None = None) -> Settings:
    args = build_arg_parser().parse_args(argv)
    settings = Settings(
        client_id=args.client_id,
        client_secret=args.client_secret,
        redirect_uri=args.redirect_uri,
        playlist_id=args.playlist_id,
        json_url=args.json_url,
        download_dir=args.download_dir,
        playlist_offset=args.playlist_offset,
        download=args.download,
        no_download=args.no_download,
        log_level=args.log_level,
        log_file=args.log_file,
    )
    _validate(settings)
    return settings

_REQUIRED_ALWAYS: list[tuple[str, str]] = [
    ("client_id", "--client-id        / CLIENT_ID"),
    ("client_secret", "--client-secret    / CLIENT_SECRET"),
    ("redirect_uri", "--redirect-uri     / REDIRECT_URI"),
    ("playlist_id", "--playlist-id      / PLAYLIST_ID"),
    ("json_url", "--json-url         / JSON_URL"),
]

def _validate(settings: Settings) -> None:
    missing = [hint for attr, hint in _REQUIRED_ALWAYS if not getattr(settings, attr, None)]
    if missing:
        lines = "\n  ".join(missing)
        raise SystemExit(
            f"\n[ERROR] Missing required configuration. "
            f"Provide each value via CLI argument or environment variable:\n  {lines}"
        )

# Set up logging
def setup_logging(log_level: str, log_file: str | None = None):
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers
    )
