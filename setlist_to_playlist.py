#!/usr/bin/env python3
"""
Script to create Apple Music playlists from setlist.fm URLs

Platform support:
  - All platforms: Apple Music REST API (recommended, requires Apple Developer credentials)
  - macOS:         AppleScript (fallback if no API credentials)
  - Windows:       COM/iTunes (fallback if no API credentials)
  - Any platform:  M3U export (--export-only flag)
"""

import sys
import requests
import re
import subprocess
import argparse
import os
import time
import json
import http.server
import webbrowser
import urllib.parse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from abc import ABC, abstractmethod


# ---------------------------------------------------------------------------
# setlist.fm client
# ---------------------------------------------------------------------------

class SetlistFMClient:
    BASE_URL = "https://api.setlist.fm/rest/1.0"

    def __init__(self, api_key: str):
        self.headers = {"x-api-key": api_key, "Accept": "application/json"}

    def extract_setlist_id(self, url: str) -> Optional[str]:
        match = re.search(r'setlist\.fm/setlist/[^/]+/\d+/([^/]+)\.html', url)
        return match.group(1) if match else None

    def get_setlist(self, setlist_id: str) -> Dict:
        response = requests.get(f"{self.BASE_URL}/setlist/{setlist_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()

    def parse_songs(self, setlist_data: Dict) -> Tuple[List[Dict[str, str]], str, str]:
        songs = []
        artist_name = setlist_data.get("artist", {}).get("name", "Unknown Artist")
        event_date = setlist_data.get("eventDate", "")

        for set_item in setlist_data.get("sets", {}).get("set", []):
            for song in set_item.get("song", []):
                if not song.get("name"):
                    continue
                song_info = {"name": song["name"], "artist": artist_name}
                if "cover" in song:
                    song_info["artist"] = song["cover"].get("name", artist_name)
                songs.append(song_info)

        return songs, artist_name, event_date


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class MusicController(ABC):
    @abstractmethod
    def create_playlist(self, name: str) -> None:
        pass

    @abstractmethod
    def search_and_add_song(self, playlist_name: str, song_name: str, artist_name: str) -> bool:
        pass


# ---------------------------------------------------------------------------
# Apple Music REST API controller (cross-platform)
# ---------------------------------------------------------------------------

class AppleMusicAPIController(MusicController):
    """
    Uses the official Apple Music REST API.
    Works on macOS, Windows, and Linux.

    Required credentials (set as env vars or pass to constructor):
      APPLE_TEAM_ID        - Your Apple Developer Team ID
      APPLE_KEY_ID         - Your MusicKit Key ID
      APPLE_PRIVATE_KEY    - Path to the .p8 private key file
    """

    BASE_URL = "https://api.music.apple.com/v1"
    TOKEN_CACHE = Path.home() / ".setlist_apple_user_token"
    AUTH_PORT = 8765

    def __init__(self, team_id: str, key_id: str, private_key_path: str):
        self.team_id = team_id
        self.key_id = key_id
        self.private_key_path = private_key_path
        self._developer_token: Optional[str] = None
        self._user_token: Optional[str] = None
        self._storefront: Optional[str] = None
        self._playlist_id: Optional[str] = None

    # --- token generation ---

    def _generate_developer_token(self) -> str:
        if self._developer_token:
            return self._developer_token
        try:
            import jwt
        except ImportError:
            raise ImportError(
                "PyJWT package required for Apple Music API.\n"
                "Install it with: python -m pip install PyJWT cryptography"
            )
        with open(self.private_key_path, "r") as f:
            private_key = f.read()
        now = int(time.time())
        payload = {"iss": self.team_id, "iat": now, "exp": now + 43200}
        self._developer_token = jwt.encode(
            payload, private_key, algorithm="ES256",
            headers={"alg": "ES256", "kid": self.key_id}
        )
        return self._developer_token

    def _get_user_token(self) -> str:
        if self._user_token:
            return self._user_token

        # Try cached token first
        if self.TOKEN_CACHE.exists():
            cached = self.TOKEN_CACHE.read_text().strip()
            if cached:
                self._user_token = cached
                return self._user_token

        # Full browser auth flow
        print("\nNo cached Apple Music user token found.")
        print("A browser window will open for one-time Apple Music authorization.")
        print("This token will be cached so you won't need to do this again.\n")
        self._user_token = self._browser_auth_flow()
        self.TOKEN_CACHE.write_text(self._user_token)
        print("✓ User token cached for future runs.\n")
        return self._user_token

    def _browser_auth_flow(self) -> str:
        dev_token = self._generate_developer_token()
        port = self.AUTH_PORT
        result: Dict = {"token": None}

        auth_html = f"""<!DOCTYPE html>
<html>
<head>
  <title>Apple Music Authorization</title>
  <script src="https://js-cdn.music.apple.com/musickit/v3/musickit.js"></script>
  <style>
    body {{ font-family: -apple-system, sans-serif; max-width: 500px; margin: 60px auto; text-align: center; }}
    button {{ padding: 12px 28px; font-size: 16px; background: #fc3c44; color: white;
              border: none; border-radius: 8px; cursor: pointer; margin-top: 24px; }}
    button:hover {{ background: #d93030; }}
  </style>
</head>
<body>
  <h2>Apple Music Authorization</h2>
  <p id="status">Loading MusicKit...</p>
  <script>
  document.addEventListener('musickitloaded', async function() {{
    document.getElementById('status').textContent = 'Ready. Click below to authorize.';
    try {{
      await MusicKit.configure({{
        developerToken: '{dev_token}',
        app: {{ name: 'Setlist to Apple Music', build: '1.0' }}
      }});
      const music = MusicKit.getInstance();
      const btn = document.createElement('button');
      btn.textContent = 'Authorize Apple Music';
      btn.onclick = async function() {{
        document.getElementById('status').textContent = 'Authorizing...';
        try {{
          await music.authorize();
          const token = music.musicUserToken;
          document.getElementById('status').textContent = 'Done! You can close this tab.';
          fetch('/callback?token=' + encodeURIComponent(token));
        }} catch(e) {{
          document.getElementById('status').textContent = 'Error: ' + e.message;
        }}
      }};
      document.body.appendChild(btn);
    }} catch(e) {{
      document.getElementById('status').textContent = 'Error: ' + e.message;
    }}
  }});
  </script>
</body>
</html>"""

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == "/auth":
                    body = auth_html.encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif parsed.path == "/callback":
                    params = urllib.parse.parse_qs(parsed.query)
                    result["token"] = params.get("token", [None])[0]
                    body = b"<html><body><h2>Done!</h2><p>You can close this tab.</p></body></html>"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):
                pass  # suppress server logs

        server = http.server.HTTPServer(("localhost", port), _Handler)
        url = f"http://localhost:{port}/auth"
        print(f"Opening browser: {url}")
        print("If the browser doesn't open, copy the URL above into your browser.\n")
        webbrowser.open(url)

        while result["token"] is None:
            server.handle_request()
        server.server_close()

        return result["token"]

    # --- API helpers ---

    def _api_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._generate_developer_token()}",
            "Music-User-Token": self._get_user_token(),
            "Content-Type": "application/json",
        }

    def _get_storefront(self) -> str:
        if self._storefront:
            return self._storefront
        resp = requests.get(f"{self.BASE_URL}/me/storefront", headers=self._api_headers())
        if resp.status_code == 401:
            # Cached token expired — clear it and re-auth
            print("Cached user token expired. Re-authorizing...")
            self.TOKEN_CACHE.unlink(missing_ok=True)
            self._user_token = None
            resp = requests.get(f"{self.BASE_URL}/me/storefront", headers=self._api_headers())
        resp.raise_for_status()
        self._storefront = resp.json()["data"][0]["id"]
        return self._storefront

    # --- MusicController interface ---

    def create_playlist(self, name: str) -> None:
        body = {
            "attributes": {
                "name": name,
                "description": "Created from setlist.fm by setlist-apple"
            }
        }
        resp = requests.post(
            f"{self.BASE_URL}/me/library/playlists",
            headers=self._api_headers(),
            json=body
        )
        resp.raise_for_status()
        self._playlist_id = resp.json()["data"][0]["id"]
        print(f"✓ Created playlist: {name}")

    def search_and_add_song(self, playlist_name: str, song_name: str, artist_name: str) -> bool:
        if not self._playlist_id:
            print(f"  ✗ No playlist ID — call create_playlist() first")
            return False

        storefront = self._get_storefront()
        query = f"{song_name} {artist_name}"
        resp = requests.get(
            f"{self.BASE_URL}/catalog/{storefront}/search",
            headers=self._api_headers(),
            params={"term": query, "types": "songs", "limit": 5}
        )
        resp.raise_for_status()

        songs = resp.json().get("results", {}).get("songs", {}).get("data", [])
        if not songs:
            print(f"  ✗ Not found: {song_name} - {artist_name}")
            return False

        song_id = songs[0]["id"]
        add_resp = requests.post(
            f"{self.BASE_URL}/me/library/playlists/{self._playlist_id}/tracks",
            headers=self._api_headers(),
            json={"data": [{"id": song_id, "type": "songs"}]}
        )
        add_resp.raise_for_status()
        print(f"  ✓ Added: {song_name} - {artist_name}")
        # Small delay to avoid hitting rate limits
        time.sleep(0.3)
        return True


# ---------------------------------------------------------------------------
# macOS AppleScript controller
# ---------------------------------------------------------------------------

class AppleMusicMacController(MusicController):
    @staticmethod
    def _osascript(script: str) -> str:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    def create_playlist(self, name: str) -> None:
        self._osascript(f'''
        tell application "Music"
            if not (exists playlist "{name}") then
                make new playlist with properties {{name:"{name}"}}
            end if
        end tell''')
        print(f"✓ Created playlist: {name}")

    def search_and_add_song(self, playlist_name: str, song_name: str, artist_name: str) -> bool:
        sn = song_name.replace('"', '\\"')
        an = artist_name.replace('"', '\\"')
        pn = playlist_name.replace('"', '\\"')
        script = f'''
        tell application "Music"
            try
                set r to search playlist "Library" for "{sn} {an}"
                if (count of r) > 0 then
                    duplicate (item 1 of r) to playlist "{pn}"
                    return "ok"
                else
                    return "not found"
                end if
            on error e
                return "error: " & e
            end try
        end tell'''
        try:
            result = self._osascript(script)
            if result == "ok":
                print(f"  ✓ Added: {song_name} - {artist_name}")
                return True
            print(f"  ✗ {result}: {song_name} - {artist_name}")
            return False
        except Exception as e:
            print(f"  ✗ Failed: {song_name} ({e})")
            return False


# ---------------------------------------------------------------------------
# Windows COM controller
# ---------------------------------------------------------------------------

class AppleMusicWindowsController(MusicController):
    def __init__(self):
        try:
            import win32com.client
            self.win32com = win32com.client
            self._app = None
            self._app_name = None
        except ImportError:
            raise ImportError(
                "pywin32 required for Windows COM support.\n"
                "Install with: python -m pip install pywin32"
            )

    def _get_app(self):
        if self._app:
            return self._app
        for com_id, name in [("AppleMusic.Application", "Apple Music"),
                              ("iTunes.Application", "iTunes")]:
            try:
                self._app = self.win32com.Dispatch(com_id)
                self._app_name = name
                print(f"✓ Connected to {name}")
                return self._app
            except Exception:
                continue
        raise RuntimeError(
            "Could not connect to Apple Music or iTunes.\n\n"
            "Troubleshooting:\n"
            "1. Install Apple Music or iTunes\n"
            "2. Launch the app at least once\n"
            "3. Restart your computer\n"
            "4. Try running as Administrator\n\n"
            "Or use --export-only for an M3U file instead.\n"
            "Or set up Apple Music API credentials for full cross-platform support."
        )

    def create_playlist(self, name: str) -> None:
        app = self._get_app()
        for src in app.Sources:
            if src.Kind == 1:
                for pl in src.Playlists:
                    if pl.Name == name:
                        print(f"Playlist already exists: {name}")
                        return
        app.CreatePlaylist(name)
        print(f"✓ Created playlist: {name}")

    def search_and_add_song(self, playlist_name: str, song_name: str, artist_name: str) -> bool:
        try:
            app = self._get_app()
            target = None
            for src in app.Sources:
                if src.Kind == 1:
                    for pl in src.Playlists:
                        if pl.Name == playlist_name:
                            target = pl
                            break
            if not target:
                print(f"  ✗ Playlist not found: {playlist_name}")
                return False
            results = app.LibraryPlaylist.Search(f"{song_name} {artist_name}", 0)
            if results and results.Count > 0:
                results.Item(1).AddToPlaylist(target)
                print(f"  ✓ Added: {song_name} - {artist_name}")
                return True
            print(f"  ✗ Not found: {song_name} - {artist_name}")
            return False
        except Exception as e:
            print(f"  ✗ Error: {song_name} ({e})")
            return False


# ---------------------------------------------------------------------------
# M3U exporter
# ---------------------------------------------------------------------------

class M3UExporter:
    @staticmethod
    def export(playlist_name: str, songs: List[Dict[str, str]], output_path: Optional[str] = None) -> str:
        if output_path is None:
            safe = "".join(c for c in playlist_name if c.isalnum() or c in " -_").strip()
            output_path = f"{safe}.m3u"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for song in songs:
                f.write(f"#EXTINF:-1,{song['artist']} - {song['name']}\n")
                f.write(f"# Search in Apple Music: {song['name']} by {song['artist']}\n")
        return output_path


# ---------------------------------------------------------------------------
# Controller selection
# ---------------------------------------------------------------------------

def get_controller(args) -> Optional[MusicController]:
    """
    Priority:
      1. Apple Music REST API  — if APPLE_TEAM_ID / APPLE_KEY_ID / APPLE_PRIVATE_KEY are set
      2. macOS AppleScript     — on darwin
      3. Windows COM           — on win32
      4. None → M3U export
    """
    if args.export_only:
        return None

    # 1. Apple Music REST API
    team_id = args.apple_team_id or os.environ.get("APPLE_TEAM_ID")
    key_id = args.apple_key_id or os.environ.get("APPLE_KEY_ID")
    key_path = args.apple_private_key or os.environ.get("APPLE_PRIVATE_KEY")

    if team_id and key_id and key_path:
        if not Path(key_path).exists():
            print(f"Error: Private key file not found: {key_path}")
            sys.exit(1)
        print("Using Apple Music REST API (cross-platform)\n")
        return AppleMusicAPIController(team_id, key_id, key_path)

    # 2. macOS AppleScript
    if sys.platform == "darwin":
        print("Using AppleScript (macOS)\n")
        return AppleMusicMacController()

    # 3. Windows COM
    if sys.platform == "win32":
        try:
            return AppleMusicWindowsController()
        except (ImportError, RuntimeError) as e:
            print(f"Warning: {e}\nFalling back to M3U export.\n")
            return None

    # 4. Fallback
    print(f"Platform '{sys.platform}' not supported for direct playlist creation.")
    print("Falling back to M3U export.\n")
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Create an Apple Music playlist from a setlist.fm URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Apple Music API setup (recommended — works on Windows, macOS, Linux):
  1. Sign in at https://developer.apple.com/account
  2. Go to Certificates, IDs & Profiles > Keys > Create a new key
  3. Enable MusicKit, download the .p8 file
  4. Note your Team ID (top-right of developer account page) and Key ID
  5. Set environment variables:
       APPLE_TEAM_ID=XXXXXXXXXX
       APPLE_KEY_ID=XXXXXXXXXX
       APPLE_PRIVATE_KEY=C:\\path\\to\\AuthKey_XXXXXXXXXX.p8

Examples:
  %(prog)s "https://www.setlist.fm/setlist/artist/2024/venue-id.html"
  %(prog)s "URL" --playlist-name "My Playlist"
  %(prog)s "URL" --export-only --output playlist.m3u
  %(prog)s "URL" --re-auth   (clear cached user token and re-authorize)
        """
    )
    parser.add_argument("url", help="setlist.fm URL")
    parser.add_argument("--api-key", default=os.environ.get("SETLISTFM_API_KEY"),
                        help="setlist.fm API key (or set SETLISTFM_API_KEY)")
    parser.add_argument("--playlist-name", help="Override playlist name")
    parser.add_argument("--export-only", action="store_true",
                        help="Export M3U file only, don't create playlist in Apple Music")
    parser.add_argument("--output", help="Output path for M3U file")
    parser.add_argument("--re-auth", action="store_true",
                        help="Clear cached Apple Music user token and re-authorize")
    # Apple Music API credentials (can also be set via env vars)
    parser.add_argument("--apple-team-id", default=None, help="Apple Developer Team ID")
    parser.add_argument("--apple-key-id", default=None, help="MusicKit Key ID")
    parser.add_argument("--apple-private-key", default=None, help="Path to .p8 private key file")

    args = parser.parse_args()

    if not args.api_key:
        print("Error: setlist.fm API key required.")
        print("Set SETLISTFM_API_KEY or use --api-key")
        print("Get your key at: https://www.setlist.fm/settings/api")
        sys.exit(1)

    if args.re_auth:
        cache = Path.home() / ".setlist_apple_user_token"
        if cache.exists():
            cache.unlink()
            print("✓ Cleared cached user token. Will re-authorize on next run.\n")
        else:
            print("No cached token found.\n")
        sys.exit(0)

    # --- Fetch setlist ---
    print(f"Fetching setlist: {args.url}\n")
    client = SetlistFMClient(args.api_key)

    setlist_id = client.extract_setlist_id(args.url)
    if not setlist_id:
        print("Error: Could not parse setlist ID from URL.")
        print("Expected: https://www.setlist.fm/setlist/artist/year/venue-id.html")
        sys.exit(1)

    try:
        data = client.get_setlist(setlist_id)
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching setlist: {e}")
        if e.response.status_code == 401:
            print("Invalid setlist.fm API key.")
        sys.exit(1)

    songs, artist_name, event_date = client.parse_songs(data)
    if not songs:
        print("No songs found in setlist.")
        sys.exit(1)

    venue = data.get("venue", {}).get("name", "Unknown Venue")
    playlist_name = args.playlist_name or f"{artist_name} - {venue} - {event_date}"

    print(f"Artist:   {artist_name}")
    print(f"Venue:    {venue}")
    print(f"Date:     {event_date}")
    print(f"Songs:    {len(songs)}")
    print(f"Playlist: {playlist_name}\n")

    # --- Get controller ---
    controller = get_controller(args)

    if controller is None:
        path = M3UExporter.export(playlist_name, songs, args.output)
        print(f"\n{'='*50}")
        print("M3U playlist exported!")
        print(f"{'='*50}")
        print(f"File:  {path}")
        print(f"Songs: {len(songs)}")
        print("\nTo import: Apple Music > File > Library > Import Playlist")
        return

    # --- Create playlist and add songs ---
    try:
        controller.create_playlist(playlist_name)
    except Exception as e:
        print(f"\nError: {e}")
        print("\nFalling back to M3U export...\n")
        path = M3UExporter.export(playlist_name, songs, args.output)
        print(f"M3U file saved: {path}")
        print("To import: Apple Music > File > Library > Import Playlist")
        return

    print("\nAdding songs:")
    ok = fail = 0
    for song in songs:
        if controller.search_and_add_song(playlist_name, song["name"], song["artist"]):
            ok += 1
        else:
            fail += 1

    print(f"\n{'='*50}")
    print("Done!")
    print(f"{'='*50}")
    print(f"Playlist: {playlist_name}")
    print(f"Added:    {ok}/{len(songs)}")
    if fail:
        print(f"Skipped:  {fail} (not found in Apple Music catalog)")
    print("\nOpen Apple Music to view your playlist.")


if __name__ == "__main__":
    main()
