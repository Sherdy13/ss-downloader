import fcntl
import json
from pathlib import Path

_EMPTY = {"downloaded": [], "failed": {}}


def load(state_file: Path) -> dict:
    if not state_file.exists():
        return {"downloaded": [], "failed": {}}
    with open(state_file, "r") as f:
        data = json.load(f)
    # Normalise: older state files may not have all keys
    data.setdefault("downloaded", [])
    data.setdefault("failed", {})
    return data


def save(state_file: Path, state: dict) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_suffix(".tmp")
    with open(tmp, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(state, f, indent=2)
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)
    tmp.replace(state_file)


def mark_downloaded(state_file: Path, video_id: str) -> None:
    state = load(state_file)
    if video_id not in state["downloaded"]:
        state["downloaded"].append(video_id)
    state["failed"].pop(video_id, None)
    save(state_file, state)


def mark_failed(state_file: Path, video_id: str, reason: str, artist: str = "", title: str = "") -> None:
    state = load(state_file)
    entry = state["failed"].get(video_id, {"reason": reason, "attempts": 0})
    entry["attempts"] += 1
    entry["reason"] = reason
    if artist:
        entry["artist"] = artist
    if title:
        entry["title"] = title
    state["failed"][video_id] = entry
    save(state_file, state)


def is_downloaded(state: dict, video_id: str) -> bool:
    return video_id in state["downloaded"]
