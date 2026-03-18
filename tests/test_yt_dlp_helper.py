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


def test_download_strategy_converts_and_cleans_up(tmp_path, monkeypatch):
    download_dir = str(tmp_path)
    song = "Artist - Title"
    video_id = "vid123"

    webm_path = tmp_path / sanitize_filename(f"{song}.webm")
    mp3_path = tmp_path / sanitize_filename(f"{song}.mp3")
    cover_path = str(mp3_path).replace(".mp3", "_cover.jpg")

    def fake_run_yt_dlp(command_args):
        out_index = command_args.index("-o") + 1
        out_path = command_args[out_index]
        with open(out_path, "wb") as f:
            f.write(b"webm")
        return ""

    urlretrieve_calls = {"count": 0}

    def fake_urlretrieve(url, filename):
        urlretrieve_calls["count"] += 1
        with open(filename, "wb") as f:
            f.write(b"jpg")
        return (filename, None)

    def fake_ffmpeg(cmd, check):
        out_path = cmd[-1]
        payload = b"tagged" if out_path.endswith("_tmp.mp3") else b"raw"
        with open(cmd[-1], "wb") as f:
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
    assert webm_path.exists() is False
    assert urlretrieve_calls["count"] == 1
    assert tmp_path.joinpath(cover_path).exists() is False
