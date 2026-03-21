from types import SimpleNamespace

import yt_dlp_helper
from utils import sanitize_filename


def test_run_yt_dlp_success(monkeypatch):
    def fake_run(cmd, capture_output, text):
        assert cmd[0] == "yt-dlp"
        return SimpleNamespace(returncode=0, stdout="abc\n", stderr="")

    monkeypatch.setattr(yt_dlp_helper.subprocess, "run", fake_run)
    assert yt_dlp_helper.YTDLPHelper._run_yt_dlp(["--version"]) == "abc"


def test_run_yt_dlp_error_returns_none(monkeypatch):
    def fake_run(cmd, capture_output, text):
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(yt_dlp_helper.subprocess, "run", fake_run)
    assert yt_dlp_helper.YTDLPHelper._run_yt_dlp(["--version"]) is None


def test_run_yt_dlp_missing_binary_returns_none(monkeypatch):
    def fake_run(cmd, capture_output, text):
        raise FileNotFoundError

    monkeypatch.setattr(yt_dlp_helper.subprocess, "run", fake_run)
    assert yt_dlp_helper.YTDLPHelper._run_yt_dlp(["--version"]) is None


def test_download_strategy_converts_and_cleans_up(tmp_path, monkeypatch):
    download_dir = str(tmp_path)
    song = "Artist - Title"
    video_id = "vid123"

    # yt-dlp resolves %(ext)s to "webm" at runtime; simulate that here.
    actual_audio_path = tmp_path / (sanitize_filename(song) + ".webm")
    mp3_path = tmp_path / sanitize_filename(f"{song}.mp3")
    cover_path = str(mp3_path).replace(".mp3", "_cover.jpg")

    def fake_run_yt_dlp(command_args):
        # Verify the output template uses %(ext)s, not a hardcoded extension.
        out_index = command_args.index("-o") + 1
        out_tpl = command_args[out_index]
        assert "%(ext)s" in out_tpl, "output template must contain %(ext)s"

        # Verify --print after_move:filepath is present so the real path is captured.
        assert "--print" in command_args
        print_index = command_args.index("--print") + 1
        assert command_args[print_index] == "after_move:filepath"

        # Simulate yt-dlp writing the file with a resolved extension and
        # printing its path as stdout (what _run_yt_dlp returns).
        resolved_path = out_tpl.replace("%(ext)s", "webm")
        with open(resolved_path, "wb") as f:
            f.write(b"webm")
        return resolved_path  # _run_yt_dlp strips stdout → this is the path

    urlretrieve_calls = {"count": 0}

    def fake_urlretrieve(url, filename):
        urlretrieve_calls["count"] += 1
        with open(filename, "wb") as f:
            f.write(b"jpg")
        return (filename, None)

    def fake_ffmpeg(cmd, check):
        # ffmpeg input (-i) must be the resolved audio path, not a guessed one.
        i_index = cmd.index("-i") + 1
        assert cmd[i_index] == str(actual_audio_path), (
            f"ffmpeg must receive the real downloaded path; got {cmd[i_index]}"
        )
        out_path = cmd[-1]
        payload = b"tagged" if out_path.endswith("_tmp.mp3") else b"raw"
        with open(out_path, "wb") as f:
            f.write(payload)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(yt_dlp_helper.YTDLPHelper, "_run_yt_dlp", staticmethod(fake_run_yt_dlp))
    monkeypatch.setattr(yt_dlp_helper.urllib.request, "urlretrieve", fake_urlretrieve)
    monkeypatch.setattr(yt_dlp_helper.subprocess, "run", fake_ffmpeg)

    strategy = yt_dlp_helper.DownloadStrategy(download_dir)
    result = strategy.execute(
        song=song,
        video_id=video_id,
        track_metadata={"title": "Title", "artist": "Artist", "album": "Album", "cover_url": "https://example/1.jpg"},
    )

    assert result == str(mp3_path)
    assert mp3_path.exists()
    assert mp3_path.read_bytes() == b"tagged"
    # yt-dlp's actual download must be cleaned up, whatever extension it chose.
    assert actual_audio_path.exists() is False
    assert urlretrieve_calls["count"] == 1
    assert tmp_path.joinpath(cover_path).exists() is False


def test_download_strategy_returns_none_when_yt_dlp_prints_nothing(tmp_path, monkeypatch):
    """
    If yt-dlp exits successfully but prints no path (e.g. format unavailable),
    the strategy must return None without touching ffmpeg.
    """
    def fake_run_yt_dlp(_command_args):
        return None  # _run_yt_dlp returns None on failure / empty stdout

    ffmpeg_called = {"value": False}

    def fake_ffmpeg(cmd, check):
        ffmpeg_called["value"] = True
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(yt_dlp_helper.YTDLPHelper, "_run_yt_dlp", staticmethod(fake_run_yt_dlp))
    monkeypatch.setattr(yt_dlp_helper.subprocess, "run", fake_ffmpeg)

    strategy = yt_dlp_helper.DownloadStrategy(str(tmp_path))
    result = strategy.execute(song="Ghost - Song", video_id="vid999", track_metadata={})

    assert result is None
    assert ffmpeg_called["value"] is False


def test_download_strategy_returns_none_when_reported_file_missing(tmp_path, monkeypatch):
    """
    If yt-dlp prints a path but that file doesn't actually exist on disk,
    the strategy must return None (guards against yt-dlp lying or partial writes).
    """
    phantom_path = str(tmp_path / "ghost.opus")

    def fake_run_yt_dlp(_command_args):
        # Reports a path but never creates the file.
        return phantom_path

    monkeypatch.setattr(yt_dlp_helper.YTDLPHelper, "_run_yt_dlp", staticmethod(fake_run_yt_dlp))

    strategy = yt_dlp_helper.DownloadStrategy(str(tmp_path))
    result = strategy.execute(song="Ghost - Song", video_id="vid999", track_metadata={})

    assert result is None
