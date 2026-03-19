import json
import logging

from config import TRACKER_FILE
from resume_tracker import ResumeTracker


def test_resume_tracker_persists_downloads(tmp_path):
    tracker_path = tmp_path / "downloaded_songs.json"

    tracker = ResumeTracker(filepath=str(tracker_path))
    assert tracker.is_downloaded("a - b") is False

    tracker.mark_downloaded("a - b")
    assert tracker.is_downloaded("a - b") is True
    assert tracker_path.exists()

    data = json.loads(tracker_path.read_text(encoding="utf-8"))
    assert data["downloaded"] == ["a - b"]

    tracker2 = ResumeTracker(filepath=str(tracker_path))
    assert tracker2.is_downloaded("a - b") is True


def test_resume_tracker_reset_clears_file(tmp_path):
    tracker_path = tmp_path / "downloaded_songs.json"

    tracker = ResumeTracker(filepath=str(tracker_path))
    tracker.mark_downloaded("x - y")
    assert tracker_path.exists()

    tracker.reset()
    assert tracker_path.exists() is False
    assert tracker.is_downloaded("x - y") is False


def test_resume_tracker_from_settings_uses_custom_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tracker_path = tmp_path / "custom_tracker.json"
    tracker_path.write_text(json.dumps({"downloaded": ["a - b"]}), encoding="utf-8")

    tracker = ResumeTracker.from_settings(str(tracker_path))

    assert tracker.filepath == str(tracker_path)
    assert tracker.is_downloaded("a - b") is True


def test_resume_tracker_from_settings_falls_back_when_missing(tmp_path, caplog, monkeypatch):
    monkeypatch.chdir(tmp_path)
    missing_path = tmp_path / "missing_tracker.json"

    caplog.set_level(logging.WARNING, logger="resume_tracker")
    tracker = ResumeTracker.from_settings(str(missing_path))

    assert tracker.filepath == TRACKER_FILE
    assert "does not exist" in caplog.text
    assert str(missing_path) in caplog.text


def test_resume_tracker_from_settings_falls_back_when_not_a_file(tmp_path, caplog, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tracker_dir = tmp_path / "tracker_dir"
    tracker_dir.mkdir()

    caplog.set_level(logging.WARNING, logger="resume_tracker")
    tracker = ResumeTracker.from_settings(str(tracker_dir))

    assert tracker.filepath == TRACKER_FILE
    assert "is not a file" in caplog.text
    assert str(tracker_dir) in caplog.text
