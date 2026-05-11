from pathlib import Path
from ytmusicapi import YTMusic


def build_client(auth_file: Path) -> YTMusic:
    if not auth_file.exists():
        print(f"YouTube Music auth file not found at {auth_file}")
        print("Run: ytmusicapi browser")
        print(f"Then move the generated browser.json to {auth_file}")
        raise SystemExit(1)
    return YTMusic(str(auth_file))


def get_liked_songs(client: YTMusic, limit: int = 2000) -> list[dict]:
    result = client.get_liked_songs(limit=limit)
    tracks = result.get("tracks", [])
    cleaned = []
    for t in tracks:
        video_id = t.get("videoId")
        title = t.get("title", "").strip()
        # artists is a list of dicts with a "name" key
        artists = t.get("artists") or []
        artist = artists[0].get("name", "").strip() if artists else ""
        if video_id and title and artist:
            cleaned.append({"videoId": video_id, "title": title, "artist": artist})
    return cleaned


def new_tracks(client: YTMusic, downloaded_ids: set[str]) -> list[dict]:
    all_tracks = get_liked_songs(client)
    return [t for t in all_tracks if t["videoId"] not in downloaded_ids]
