# ss-downloader

Watches your YouTube Music liked songs and downloads them automatically via yt-dlp as 320kbps MP3.

> **Note on audio quality:** YouTube streams are typically 160kbps Opus. yt-dlp re-encodes these to 320kbps MP3, so the file bitrate is 320k but the source quality is capped at whatever YouTube provides. In practice the quality is good — 160kbps Opus is comparable to a higher-bitrate MP3.

## Requirements

- Python 3.10+
- yt-dlp installed: `brew install yt-dlp` or `pip install yt-dlp`

## Installation

```bash
pip install -r requirements.txt
```

## Setup

**1. YouTube Music auth**

Open Firefox, go to `music.youtube.com` (logged in), open DevTools (`Cmd+Option+I`) → Network tab, click anything to trigger a request, filter by `browse`, right-click the request headers → Copy All. Then:

```bash
ytmusicapi browser
# or if Ctrl+D doesn't work in your terminal:
pbpaste | ytmusicapi browser
```

Move the generated file to the config directory:

```bash
mkdir -p ~/.config/ss_downloader
mv browser.json ~/.config/ss_downloader/
chmod 600 ~/.config/ss_downloader/browser.json
```

**2. Config file**

```bash
cp config.toml.example ~/.config/ss_downloader/config.toml
```

Edit it and set `dir` to where you want music saved.

## Usage

**First time — seed your existing likes so they aren't all downloaded:**
```bash
python main.py --seed
```

> If you accidentally ran `--seed` before you were ready (or want to re-download everything), run `--unseed` to reset and start fresh:
> ```bash
> python main.py --unseed
> ```

**Download a batch of your most recent likes:**
```bash
python main.py --limit 250
```

**Subsequent runs — picks up anything liked since last run:**
```bash
python main.py
```

Any tracks that couldn't be downloaded are saved to `failed.txt` in your output directory.

## CLI reference

| Flag | Description |
|------|-------------|
| *(none)* | Download all new liked songs |
| `--limit N` | Process at most N new tracks this run |
| `--seed` | Mark all current likes as seen without downloading (use on first setup) |
| `--unseed` | Clear all downloaded IDs so every liked song re-downloads on next run |

## Config reference

```toml
[output]
dir = "~/Music/ss_downloader"   # where files are saved
```
