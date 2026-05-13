import contextlib
import fcntl
import json
import os
from pathlib import Path


@contextlib.contextmanager
def _locked(state_file: Path):
    lock_path = state_file.with_suffix(".lock")
    with open(lock_path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def load(state_file: Path) -> dict:
    if not state_file.exists():
        return {"downloaded": [], "failed": {}}
    with open(state_file, "r") as f:
        data = json.load(f)
    data.setdefault("downloaded", [])
    data.setdefault("failed", {})
    return data


def save(state_file: Path, state: dict) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(state_file)


def mark_downloaded(state_file: Path, video_id: str) -> None:
    with _locked(state_file):
        data = load(state_file)
        downloaded = set(data["downloaded"])
        downloaded.add(video_id)
        data["downloaded"] = list(downloaded)
        data["failed"].pop(video_id, None)
        save(state_file, data)


def mark_failed(state_file: Path, video_id: str, reason: str, artist: str = "", title: str = "") -> None:
    with _locked(state_file):
        data = load(state_file)
        entry = data["failed"].get(video_id, {"reason": reason, "attempts": 0})
        entry["attempts"] += 1
        entry["reason"] = reason
        if artist:
            entry["artist"] = artist
        if title:
            entry["title"] = title
        data["failed"][video_id] = entry
        save(state_file, data)


def is_downloaded(state: dict, video_id: str) -> bool:
    return video_id in state["downloaded"]
