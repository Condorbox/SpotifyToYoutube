import json

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

