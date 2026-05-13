import re
import shutil
import time
from pathlib import Path

import slskd_api

from utils import safe_filename

ACCEPTED_EXTENSIONS = {".wav", ".mp3"}


def build_client(host: str, port: int, api_key: str) -> slskd_api.SlskdClient:
    return slskd_api.SlskdClient(host=f"http://{host}:{port}", api_key=api_key)


# --- Query ladder ---

def _clean_token(s: str) -> str:
    """Strip common noise tokens from artist/title strings."""
    noise = re.compile(
        r"\(feat\..*?\)|\(ft\..*?\)|\[feat\..*?\]|\[ft\..*?\]"
        r"|\(official.*?\)|\(audio.*?\)|\(video.*?\)|\(remaster.*?\)"
        r"|\[.*?kbps.*?\]|\[.*?flac.*?\]|\bHD\b|\bHQ\b",
        re.IGNORECASE,
    )
    return noise.sub("", s).strip(" -–—")


def _strip_parens(s: str) -> str:
    """Strip all parenthetical and bracketed content from a string."""
    return re.sub(r"[\(\[].*?[\)\]]", "", s).strip(" -–—")


def query_variants(artist: str, title: str) -> list[str]:
    a, t = artist.strip(), title.strip()
    ac, tc = _clean_token(a), _clean_token(t)
    tb = _strip_parens(t)
    variants = [
        f"{a} {t}",
        f"{a} - {t}",
        f"{t} {a}",
    ]
    if ac != a or tc != t:
        variants += [
            f"{ac} {tc}",
            f"{ac} - {tc}",
        ]
    if tb != t and tb != tc:
        variants += [
            f"{a} {tb}",
            f"{a} - {tb}",
        ]
    seen = set()
    result = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


# --- Quality filtering ---

def _ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def _is_acceptable(f: dict, min_mp3_bitrate: int) -> bool:
    ext = _ext(f.get("filename", ""))
    if ext not in ACCEPTED_EXTENSIONS:
        return False
    if ext == ".mp3":
        bitrate = f.get("bitRate") or 0
        return bitrate >= min_mp3_bitrate
    return True


def _rank(f: dict, formats: list[str]) -> tuple:
    """Lower score = more preferred. Rank by format preference order, then bitrate descending."""
    ext = _ext(f.get("filename", "")).lstrip(".")
    try:
        format_rank = formats.index(ext)
    except ValueError:
        format_rank = len(formats)
    bitrate = f.get("bitRate") or 0
    return (format_rank, -bitrate)


def _filename_matches_track(filename: str, artist: str, title: str) -> bool:
    """Loose sanity check: both artist and title words appear in the filename."""
    name = Path(filename).stem.lower()
    artist_words = [w for w in re.split(r"\W+", artist.lower()) if len(w) > 2]
    title_words = [w for w in re.split(r"\W+", title.lower()) if len(w) > 2]
    artist_match = any(w in name for w in artist_words) if artist_words else True
    title_match = any(w in name for w in title_words) if title_words else True
    return artist_match and title_match


# --- Search + download ---

def _wait_for_search(client: slskd_api.SlskdClient, search_id: str,
                     timeout: int, poll: float) -> list[dict]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = client.searches.state(search_id)
        if result.get("state") == "Completed":
            return result.get("responses", [])
        time.sleep(poll)
    return []


def _best_result(responses: list[dict], artist: str, title: str,
                 min_mp3_bitrate: int, formats: list[str]) -> tuple[str, dict] | None:
    """Return (username, file_dict) for the best qualifying result, or None."""
    candidates = []
    for response in responses:
        username = response.get("username", "")
        for f in response.get("files", []):
            if (
                _is_acceptable(f, min_mp3_bitrate)
                and _filename_matches_track(f.get("filename", ""), artist, title)
            ):
                candidates.append((username, f))
    if not candidates:
        return None
    candidates.sort(key=lambda x: _rank(x[1], formats))
    return candidates[0]


def _wait_for_download(client: slskd_api.SlskdClient, username: str,
                       filename: str, timeout: int, poll: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        transfers = client.transfers.get_downloads(username)
        for t in transfers:
            if t.get("filename") == filename:
                state = t.get("state", "")
                if "Completed" in state:
                    return True
                if "Errored" in state or "Rejected" in state or "Cancelled" in state:
                    return False
        time.sleep(poll)
    return False


def _find_slskd_file(client: slskd_api.SlskdClient, filename: str) -> Path | None:
    """Ask slskd where it saved the file, searching recursively under the download dir."""
    try:
        app_info = client.application.state()
        dl_dir = app_info.get("options", {}).get("directories", {}).get("downloads", "")
        if dl_dir:
            matches = list(Path(dl_dir).rglob(Path(filename).name))
            return matches[0] if matches else None
    except Exception:
        pass
    return None


def download_track(
    client: slskd_api.SlskdClient,
    artist: str,
    title: str,
    output_dir: Path,
    search_timeout: int,
    download_timeout: int,
    poll_interval: float,
    min_mp3_bitrate: int,
    formats: list[str],
) -> Path | None:
    """
    Try each query variant in order. For each, search slskd, pick the best
    qualifying result, download it, rename to clean format, and return the path.
    Returns None if nothing worked.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for query in query_variants(artist, title):
        print(f"  [slskd] searching: '{query}'")
        search = client.searches.search_text(query)
        search_id = search.get("id")
        if not search_id:
            continue

        responses = _wait_for_search(client, search_id, search_timeout, poll_interval)
        best = _best_result(responses, artist, title, min_mp3_bitrate, formats)

        if not best:
            print(f"  [slskd] no qualifying results for '{query}'")
            try:
                client.searches.delete(search_id)
            except Exception:
                pass
            continue

        username, file_info = best
        remote_filename = file_info["filename"]
        ext = _ext(remote_filename)
        clean_name = safe_filename(f"{artist} - {title}") + ext
        dest = output_dir / clean_name

        print(f"  [slskd] downloading '{remote_filename}' from {username}")
        try:
            client.transfers.enqueue(username=username, files=[file_info])
        except Exception as e:
            print(f"  [slskd] enqueue failed: {e}")
            try:
                client.searches.delete(search_id)
            except Exception:
                pass
            continue

        success = _wait_for_download(
            client, username, remote_filename, download_timeout, poll_interval
        )
        if not success:
            print(f"  [slskd] download timed out or failed")
            try:
                client.searches.delete(search_id)
            except Exception:
                pass
            continue

        slskd_downloads = _find_slskd_file(client, remote_filename)
        try:
            client.searches.delete(search_id)
        except Exception:
            pass

        if slskd_downloads and slskd_downloads.exists():
            shutil.move(str(slskd_downloads), str(dest))
            print(f"  [slskd] saved to {dest}")
            return dest

        print(f"  [slskd] could not locate downloaded file")

    return None
