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

    def fake_run_yt_dlp(command_args):
        out_index = command_args.index("-o") + 1
        out_path = command_args[out_index]
        with open(out_path, "wb") as f:
            f.write(b"webm")
        return ""

    def fake_ffmpeg(cmd, check):
        with open(cmd[-1], "wb") as f:
            f.write(b"mp3")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(yt_dlp_helper.YTDLPHelper, "_run_yt_dlp", staticmethod(fake_run_yt_dlp))
    monkeypatch.setattr(yt_dlp_helper.subprocess, "run", fake_ffmpeg)

    strategy = yt_dlp_helper.DownloadStrategy(download_dir)
    result = strategy.execute(song=song, video_id=video_id)

    assert result == str(mp3_path)
    assert mp3_path.exists()
    assert webm_path.exists() is False
