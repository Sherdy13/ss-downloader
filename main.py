import argparse
from pathlib import Path

import config
import state
import ytdlp
import ytmusic
from utils import safe_filename


def file_already_exists(output_dir: Path, artist: str, title: str) -> Path | None:
    stem = safe_filename(f"{artist} - {title}").lower()
    for f in output_dir.iterdir() if output_dir.exists() else []:
        if f.stem.lower() == stem and f.suffix.lower() in {".wav", ".mp3"}:
            return f
    return None


def seed(yt_client, state_file: Path) -> None:
    print("Fetching all liked songs to seed state...")
    all_tracks = ytmusic.get_liked_songs(yt_client)
    current = state.load(state_file)
    existing = set(current["downloaded"])
    new_ids = [t["videoId"] for t in all_tracks if t["videoId"] not in existing]
    current["downloaded"] = list(existing | set(new_ids))
    state.save(state_file, current)
    print(f"Seeded {len(new_ids)} track(s). Future runs will only download new likes.")


def write_failed_report(state_file: Path, output_dir: Path) -> None:
    current = state.load(state_file)
    failed = current.get("failed", {})
    if not failed:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    report = output_dir / "failed.txt"
    lines = []
    for video_id, entry in failed.items():
        artist = entry.get("artist", "Unknown Artist")
        title = entry.get("title", "Unknown Title")
        attempts = entry.get("attempts", 1)
        lines.append(f"{artist} - {title}  (attempts: {attempts}, id: {video_id})")
    lines.sort()
    report.write_text("\n".join(lines) + "\n")
    print(f"--- {len(lines)} track(s) could not be downloaded. See {report} ---")


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Music → yt-dlp batch downloader")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Mark all current likes as seen without downloading. Run once on first setup.",
    )
    parser.add_argument(
        "--unseed",
        action="store_true",
        help="Clear all downloaded IDs so every liked song re-downloads on next run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process at most N new tracks this run (most recently liked first).",
    )
    args = parser.parse_args()

    cfg = config.load()
    output_dir = Path(cfg["output"]["dir"])
    state_file = config.STATE_FILE

    if args.unseed:
        count = state.clear_downloaded(state_file)
        print(f"Cleared {count} ID(s). All liked songs will be downloaded on next run.")
        return

    print("Connecting to YouTube Music...")
    yt_client = ytmusic.build_client(config.BROWSER_AUTH_FILE)
    print("YouTube Music OK")

    if args.seed:
        seed(yt_client, state_file)
        return

    current_state = state.load(state_file)
    downloaded_ids = set(current_state["downloaded"])

    print("Fetching liked songs...")
    tracks = ytmusic.new_tracks(yt_client, downloaded_ids)
    if not tracks:
        print("No new tracks to download.")
        return
    if args.limit:
        tracks = tracks[:args.limit]
    print(f"Found {len(tracks)} new track(s).\n")

    for track in tracks:
        video_id = track["videoId"]
        artist = track["artist"]
        title = track["title"]
        print(f"Processing: {artist} - {title}")

        existing = file_already_exists(output_dir, artist, title)
        if existing:
            print(f"  Already on disk as '{existing.name}' — skipping.\n")
            state.mark_downloaded(state_file, video_id)
            continue

        result = ytdlp.download_track(
            video_id=video_id,
            artist=artist,
            title=title,
            output_dir=output_dir,
        )

        if result:
            state.mark_downloaded(state_file, video_id)
            print(f"  Done: {result.name}\n")
        else:
            state.mark_failed(state_file, video_id, reason="download_failed", artist=artist, title=title)
            print(f"  Failed: {artist} - {title}\n")

    write_failed_report(state_file, output_dir)


if __name__ == "__main__":
    main()
