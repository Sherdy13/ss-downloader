"""
One-off script to check the ordering of get_liked_songs().
Like a song on YouTube Music, then run this to see if it appears first or last.
"""
import sys
from pathlib import Path

import config
import ytmusic

auth_file = config.BROWSER_AUTH_FILE
if not auth_file.exists():
    print(f"Auth file not found at {auth_file}")
    print("Run: ytmusicapi browser")
    print(f"Then move browser.json to {auth_file}")
    sys.exit(1)

client = ytmusic.build_client(auth_file)
tracks = ytmusic.get_liked_songs(client, limit=2000)

print(f"Total liked songs fetched: {len(tracks)}\n")
print("--- First 5 ---")
for t in tracks[:5]:
    print(f"  {t['artist']} - {t['title']}")

print("\n--- Last 5 ---")
for t in tracks[-5:]:
    print(f"  {t['artist']} - {t['title']}")
