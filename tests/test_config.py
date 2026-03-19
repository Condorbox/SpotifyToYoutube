import pytest

from config import Mode, load_settings


def test_load_settings_reads_cli_args():
    settings = load_settings(
        argv=[
            "--client-id",
            "id",
            "--client-secret",
            "secret",
            "--redirect-uri",
            "http://localhost/",
            "--playlist-id",
            "playlist",
            "--json-url",
            "/tmp/creds.json",
            "--playlist-offset",
            "5",
            "--log-level",
            "DEBUG",
        ]
    )

    assert settings.client_id == "id"
    assert settings.client_secret == "secret"
    assert settings.redirect_uri == "http://localhost/"
    assert settings.playlist_id == "playlist"
    assert settings.json_url == "/tmp/creds.json"
    assert settings.playlist_offset == 5
    assert settings.log_level == "DEBUG"
    assert settings.mode == Mode.CONVERT


def test_load_settings_sync_subcommand_sets_mode():
    settings = load_settings(
        argv=[
            "sync",
            "--client-id",
            "id",
            "--client-secret",
            "secret",
            "--redirect-uri",
            "http://localhost/",
            "--playlist-id",
            "playlist",
            "--json-url",
            "/tmp/creds.json",
        ]
    )

    assert settings.mode == Mode.SYNC


def test_load_settings_sync_flag_sets_mode():
    settings = load_settings(
        argv=[
            "--sync",
            "--client-id",
            "id",
            "--client-secret",
            "secret",
            "--redirect-uri",
            "http://localhost/",
            "--playlist-id",
            "playlist",
            "--json-url",
            "/tmp/creds.json",
        ]
    )

    assert settings.mode == Mode.SYNC


def test_load_settings_requires_required_fields(monkeypatch):
    for var in ("CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI", "PLAYLIST_ID", "JSON_URL"):
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(SystemExit):
        load_settings(argv=[])


def test_load_settings_download_flags_are_mutually_exclusive():
    argv = [
        "--client-id",
        "id",
        "--client-secret",
        "secret",
        "--redirect-uri",
        "http://localhost/",
        "--playlist-id",
        "playlist",
        "--json-url",
        "/tmp/creds.json",
        "--download",
        "--no-download",
    ]
    with pytest.raises(SystemExit):
        load_settings(argv=argv)
