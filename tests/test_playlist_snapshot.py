import json

from playlist_snapshot import PlaylistSnapshot


def test_playlist_snapshot_persists_track_ids_per_playlist(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    playlist_id = "pl_123"

    snap = PlaylistSnapshot(filepath=str(snapshot_path))
    assert snap.get(playlist_id).track_ids == set()

    snap.set(playlist_id, {"t2", "t1"})
    assert snapshot_path.exists()

    raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert raw["playlists"][playlist_id]["track_ids"] == ["t1", "t2"]

    snap2 = PlaylistSnapshot(filepath=str(snapshot_path))
    assert snap2.get(playlist_id).track_ids == {"t1", "t2"}

