import os
import stat
import sys
import tomli
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "ss_downloader"
CONFIG_FILE = CONFIG_DIR / "config.toml"
STATE_FILE = CONFIG_DIR / "state.json"
BROWSER_AUTH_FILE = CONFIG_DIR / "browser.json"

DEFAULTS = {
    "output": {"dir": "~/Music/ss_downloader"},
    "slskd": {"host": "localhost", "port": 5030, "api_key": ""},
    "quality": {"formats": ["wav", "mp3"], "min_mp3_bitrate": 320},
    "search": {
        "search_timeout_seconds": 15,
        "download_timeout_seconds": 120,
        "poll_interval_seconds": 2,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _enforce_permissions(path: Path) -> None:
    current = stat.S_IMODE(os.stat(path).st_mode)
    if current & 0o077:
        os.chmod(path, 0o600)


def load() -> dict:
    if not CONFIG_FILE.exists():
        print(f"Config file not found at {CONFIG_FILE}")
        print(f"Copy config.toml.example to {CONFIG_FILE} and fill in your values.")
        sys.exit(1)

    _enforce_permissions(CONFIG_FILE)
    if BROWSER_AUTH_FILE.exists():
        _enforce_permissions(BROWSER_AUTH_FILE)

    with open(CONFIG_FILE, "rb") as f:
        user_config = tomli.load(f)

    config = _deep_merge(DEFAULTS, user_config)
    config["output"]["dir"] = str(Path(config["output"]["dir"]).expanduser())
    return config
