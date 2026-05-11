# ss-downloader

Watches your YouTube Music liked songs and downloads them automatically — via Soulseek first (WAV or 320kbps MP3), falling back to yt-dlp if nothing is found.

## How it works

1. Fetches your liked songs from YouTube Music
2. For each new track, searches Soulseek (via slskd) using a query ladder of variants
3. Picks the best quality result (WAV preferred, 320kbps MP3 as fallback)
4. If Soulseek can't find it, falls back to yt-dlp
5. Saves the file as `Artist - Title.ext` and records it in a local state file so it's never downloaded twice

## Requirements

- Python 3.10+
- [slskd](https://github.com/slskd/slskd) running locally (Docker recommended)
- A free [Soulseek](https://www.slsknet.org) account
- yt-dlp installed and on your PATH

## Installation

```bash
pip install -r requirements.txt
```

## Setup

**1. YouTube Music auth**

```bash
ytmusicapi browser
mkdir -p ~/.config/ss_downloader
mv browser.json ~/.config/ss_downloader/
chmod 600 ~/.config/ss_downloader/browser.json
```

Open Firefox, go to `music.youtube.com`, open DevTools (`Cmd+Option+I`) → Network tab, click anything to trigger a request, filter by `browse`, right-click the request headers → Copy All. Then:

```bash
pbpaste | ytmusicapi browser
```

**2. Config file**

```bash
cp config.toml.example ~/.config/ss_downloader/config.toml
chmod 600 ~/.config/ss_downloader/config.toml
```

Edit `~/.config/ss_downloader/config.toml` and fill in:
- `dir` — where downloaded music should be saved
- `api_key` — your slskd API key (see below)

**3. slskd (Docker)**

```bash
docker run -d \
  --name slskd \
  --restart unless-stopped \
  -p 5030:5030 \
  -p 50300:50300 \
  -v ~/Music/slskd:/app \
  slskd/slskd
```

Create `~/Music/slskd/slskd.yml`:

```yaml
soulseek:
  username: your-soulseek-username
  password: your-soulseek-password

web:
  authentication:
    api_keys:
      script:
        key: "your-generated-api-key"

directories:
  downloads: /app/downloads
  incomplete: /app/incomplete
```

Generate an API key with:
```bash
openssl rand -base64 32
```

Then restart slskd:
```bash
docker restart slskd
```

## Usage

**First time — seed your existing likes so they aren't all downloaded:**
```bash
python main.py --seed
```

**Or download a batch of your most recent likes:**
```bash
python main.py --limit 250
```

**Subsequent runs — picks up anything liked since last run:**
```bash
python main.py
```

Any tracks that couldn't be downloaded are saved to `failed.txt` in your output directory.

## Config reference

```toml
[output]
dir = "~/Music/ss_downloader"      # where files are saved

[slskd]
host = "localhost"
port = 5030
api_key = "your-api-key"

[quality]
formats = ["wav", "mp3"]           # preference order
min_mp3_bitrate = 320              # reject MP3s below this bitrate

[search]
search_timeout_seconds = 15        # how long to wait for Soulseek results per query
download_timeout_seconds = 120     # how long to wait for a download to complete
poll_interval_seconds = 2          # how often to check status
```
