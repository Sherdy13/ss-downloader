import subprocess
import tempfile
from pathlib import Path

from utils import safe_filename


def download_track(
    video_id: str,
    artist: str,
    title: str,
    output_dir: Path,
) -> Path | None:
    """
    Download a track via yt-dlp using its YouTube videoId.
    Saves as '{artist} - {title}.ext' in output_dir.
    Returns the output path on success, None on failure.
    """
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        print(f"  [yt-dlp] invalid video_id: {video_id!r}")
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = safe_filename(f"{artist} - {title}")
    url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "320K",
            "--output", str(tmp_path / "%(title)s.%(ext)s"),
            url,
        ]
        print(f"  [yt-dlp] downloading {url}")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )
        except subprocess.TimeoutExpired:
            print("  [yt-dlp] timed out")
            return None
        except FileNotFoundError:
            print("  [yt-dlp] yt-dlp not found — is it installed?")
            return None

        if result.returncode != 0:
            print(f"  [yt-dlp] failed: {result.stderr.strip()}")
            return None

        downloaded = list(tmp_path.glob("*.mp3"))
        if not downloaded:
            print("  [yt-dlp] no output file found")
            return None

        dest = output_dir / f"{clean_name}.mp3"
        downloaded[0].rename(dest)
        print(f"  [yt-dlp] saved to {dest}")
        return dest
