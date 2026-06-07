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
        # Extract the hex ID from the end of the URL
        # Format: .../artist/year/venue-name-HEXID.html
        # We want just the HEXID part (8 hex characters at the end)
        match = re.search(r'-([0-9a-f]{8})\.html', url)
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
# Apple Music Windows UI Automation Controller
# ---------------------------------------------------------------------------

class AppleMusicWindowsUIController(MusicController):
    """
    Automates the Apple Music for Windows desktop app using UI automation.
    Works on Windows only.

    Reads JSON files exported with --ios flag and creates playlists directly
    in the Apple Music Windows app using keyboard/mouse automation.
    """

    def __init__(self):
        try:
            from pywinauto.application import Application
            from pywinauto import Desktop
            import pywinauto.keyboard as keyboard
            self.Application = Application
            self.Desktop = Desktop
            self.keyboard = keyboard
        except ImportError:
            raise ImportError(
                "pywinauto required for Windows UI automation.\n"
                "Install with: python -m pip install pywinauto"
            )

        self._app = None
        self._main_window = None
        self._playlist_name = None

    def _launch_or_connect(self):
        """Launch Apple Music or connect to existing instance"""
        if self._app:
            return

        try:
            # Try to connect to running instance first
            self._app = self.Application(backend="uia").connect(title_re=".*Apple Music.*", timeout=5)
            print("✓ Connected to running Apple Music")
        except Exception:
            # Launch if not running
            print("Launching Apple Music...")
            try:
                # Common install locations
                paths = [
                    r"C:\Program Files\WindowsApps\AppleInc.AppleMusic_*\AppleMusic.exe",
                    r"C:\Program Files (x86)\Apple Music\AppleMusic.exe"
                ]

                import glob
                exe_path = None
                for pattern in paths:
                    matches = glob.glob(pattern)
                    if matches:
                        exe_path = matches[0]
                        break

                if not exe_path:
                    # Try to find via Start Menu shortcut
                    import subprocess
                    subprocess.Popen("start applemusicapp:", shell=True)
                    time.sleep(5)
                else:
                    self._app = self.Application(backend="uia").start(exe_path)
                    time.sleep(5)

                self._app = self.Application(backend="uia").connect(title_re=".*Apple Music.*", timeout=10)
                print("✓ Launched Apple Music")
            except Exception as e:
                raise RuntimeError(
                    f"Could not launch Apple Music: {e}\n\n"
                    "Please launch Apple Music manually and try again."
                )

        # Get main window
        self._main_window = self._app.window(title_re=".*Apple Music.*")
        self._main_window.set_focus()
        time.sleep(1)

    def create_playlist(self, name: str) -> None:
        """Create a new playlist using File menu"""
        self._launch_or_connect()
        self._playlist_name = name

        print(f"Creating playlist: {name}")
        print("  → Opening File menu...")

        try:
            self._main_window.set_focus()
            time.sleep(0.5)

            # Use File menu: Alt, F, N, P (File > New > Playlist)
            self.keyboard.send_keys('%')  # Alt (opens menu bar)
            time.sleep(0.3)
            self.keyboard.send_keys('f')  # File
            time.sleep(0.3)
            self.keyboard.send_keys('n')  # New
            time.sleep(0.3)
            self.keyboard.send_keys('p')  # Playlist
            time.sleep(1)

            # A dialog or input should appear for the playlist name
            # Type the name
            self.keyboard.send_keys(name, with_spaces=True)
            time.sleep(0.5)

            # Press Enter to confirm
            self.keyboard.send_keys('{ENTER}')
            time.sleep(1)

            print(f"  ✓ Created playlist: {name}")

        except Exception as e:
            raise RuntimeError(f"Failed to create playlist: {e}")

    def search_and_add_song(self, playlist_name: str, song_name: str, artist_name: str) -> bool:
        """Search for a song and add it to the playlist"""
        try:
            self._main_window.set_focus()
            time.sleep(0.3)

            # Focus search box (Ctrl+F)
            self.keyboard.send_keys('^f')  # Ctrl+F for search
            time.sleep(0.5)

            # Clear any existing text in search box
            self.keyboard.send_keys('^a')  # Ctrl+A to select all
            time.sleep(0.2)

            # Type search query (this replaces the selected text)
            query = f"{song_name} {artist_name}"
            self.keyboard.send_keys(query, with_spaces=True)
            time.sleep(0.5)

            # Press Enter to search
            self.keyboard.send_keys('{ENTER}')
            time.sleep(2.5)  # Wait for search results to load

            # Escape out of search box to get to results
            self.keyboard.send_keys('{ESC}')
            time.sleep(0.3)

            # Tab to results area
            self.keyboard.send_keys('{TAB}')
            time.sleep(0.5)

            # Select first song (should already be highlighted, but ensure it)
            self.keyboard.send_keys('{DOWN}')
            time.sleep(0.3)

            # Right-click using keyboard (Applications/Menu key or Shift+F10)
            self.keyboard.send_keys('+{F10}')  # Shift+F10 = context menu
            time.sleep(1)

            # Press 'A' for "Add to Playlist"
            self.keyboard.send_keys('a')
            time.sleep(0.8)

            # Now we should be in the "Add to Playlist" submenu
            # Type the playlist name to search for it
            # Most apps let you type to search in menus
            for char in playlist_name[:20]:  # Limit to first 20 chars
                self.keyboard.send_keys(char)
                time.sleep(0.05)

            time.sleep(0.5)

            # Press Enter to select the playlist
            self.keyboard.send_keys('{ENTER}')
            time.sleep(0.8)

            print(f"  ✓ Added: {song_name} - {artist_name}")
            return True

        except Exception as e:
            print(f"  ✗ Error adding {song_name}: {e}")
            # Try to close any open menus
            try:
                self.keyboard.send_keys('{ESC}')
                self.keyboard.send_keys('{ESC}')
            except:
                pass
            return False


# ---------------------------------------------------------------------------
# Apple Music Web Controller (cross-platform browser automation)
# ---------------------------------------------------------------------------

class AppleMusicWebController(MusicController):
    """
    Automates music.apple.com using Playwright browser automation.
    Works on Windows, macOS, and Linux.

    First run: Opens browser for you to log in, saves session.
    Subsequent runs: Uses saved session (no login needed).
    """

    SESSION_FILE = Path.home() / ".setlist_apple_web_session.json"

    def __init__(self):
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
            self.PlaywrightTimeout = PlaywrightTimeout
        except ImportError:
            raise ImportError(
                "Playwright required for web automation.\n"
                "Install with:\n"
                "  python -m pip install playwright\n"
                "  python -m playwright install chromium"
            )

        print("Starting browser automation...")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=False)

        # Load saved session if exists
        storage_state = str(self.SESSION_FILE) if self.SESSION_FILE.exists() else None
        self._context = self._browser.new_context(storage_state=storage_state)
        self._page = self._context.new_page()

        # Set longer timeout and use 'load' instead of 'networkidle' (Apple Music keeps making requests)
        self._page.set_default_timeout(60000)  # 60 seconds
        self._page.goto("https://music.apple.com", wait_until="load")
        time.sleep(3)  # Give UI time to render

        # Extract the storefront (region) from the redirected URL
        # e.g., https://music.apple.com/us/ -> 'us'
        current_url = self._page.url
        storefront_match = re.search(r'music\.apple\.com/([a-z]{2})/', current_url)
        self._storefront = storefront_match.group(1) if storefront_match else 'us'
        print(f"Detected region: {self._storefront}")

        # Check if logged in
        if not self._is_logged_in():
            print("\n" + "="*60)
            print("PLEASE LOG IN TO APPLE MUSIC")
            print("="*60)
            print("A browser window has opened to music.apple.com")
            print("Please sign in with your Apple ID")
            print("The script will continue automatically after login...\n")
            self._wait_for_login()
            # Save session
            self._context.storage_state(path=str(self.SESSION_FILE))
            print("✓ Login saved — you won't need to log in again\n")
        else:
            print("✓ Using saved login session")

        self._playlist_url = None
        print()  # Blank line for readability

    def _is_logged_in(self) -> bool:
        try:
            # Try multiple possible selectors for logged-in state
            selectors = [
                'button[data-testid="account-button"]',
                '[aria-label="Account"]',
                'button[aria-label="Account menu"]',
                '[class*="account"]',
                'nav a[href*="account"]',
                # Check if we can access library (only works when logged in)
                'a[href*="library"]',
                '[href="/library"]'
            ]

            for selector in selectors:
                try:
                    self._page.wait_for_selector(selector, timeout=2000)
                    return True
                except:
                    continue

            return False
        except:
            return False

    def _wait_for_login(self):
        print("Waiting for login... (or press Enter if you're already logged in)")

        import threading
        login_detected = {'done': False}

        # Thread to wait for Enter key
        def wait_for_enter():
            input()  # Wait for user to press Enter
            login_detected['done'] = True

        enter_thread = threading.Thread(target=wait_for_enter, daemon=True)
        enter_thread.start()

        # Try to detect login automatically
        start_time = time.time()
        while not login_detected['done'] and (time.time() - start_time) < 300:  # 5 min timeout
            if self._is_logged_in():
                login_detected['done'] = True
                print("\n✓ Login detected!")
                break
            time.sleep(2)

        if not login_detected['done']:
            raise RuntimeError("Login timeout — please try again")

    def create_playlist(self, name: str) -> None:
        print(f"Creating playlist via web: {name}")

        try:
            # Navigate to Library (use storefront-specific URL)
            library_url = f"https://music.apple.com/{self._storefront}/library/playlists"
            self._page.goto(library_url, wait_until="load")
            time.sleep(3)

            # Look for "New Playlist" button
            # Try multiple possible selectors
            new_playlist_selectors = [
                'button:has-text("New Playlist")',
                'button[aria-label="New Playlist"]',
                '[data-testid="new-playlist-button"]',
                'button:has-text("Create")'
            ]

            clicked = False
            for selector in new_playlist_selectors:
                try:
                    self._page.click(selector, timeout=3000)
                    clicked = True
                    break
                except:
                    continue

            if not clicked:
                # Fallback: try keyboard shortcut (Cmd+N / Ctrl+N)
                print("  Trying keyboard shortcut to create playlist...")
                self._page.keyboard.press("Control+N" if sys.platform == "win32" else "Meta+N")
                time.sleep(1)

            # Enter playlist name
            time.sleep(1)
            # The name input should be focused, just type
            self._page.keyboard.type(name)
            self._page.keyboard.press("Enter")
            time.sleep(2)

            # Store the playlist URL for adding songs
            self._playlist_url = self._page.url
            print(f"✓ Created playlist: {name}")

        except Exception as e:
            raise RuntimeError(f"Failed to create playlist: {e}\n"
                             "The web interface may have changed. Try the M3U export instead.")

    def search_and_add_song(self, playlist_name: str, song_name: str, artist_name: str) -> bool:
        try:
            # Try searching with both song and artist first
            query = f"{song_name} {artist_name}"

            # Navigate to search by typing in URL (include storefront/region)
            search_url = f"https://music.apple.com/{self._storefront}/search?term={urllib.parse.quote(query)}"
            self._page.goto(search_url, wait_until="load")
            time.sleep(3)

            # Check for "No Results" message first
            no_results_selectors = [
                'text="No Results"',
                'text="No results found"',
                '[class*="no-results"]',
                '[class*="empty-state"]'
            ]

            has_no_results = False
            for selector in no_results_selectors:
                try:
                    if self._page.query_selector(selector):
                        has_no_results = True
                        break
                except:
                    continue

            if has_no_results:
                # Try again with just the song name
                print(f"  ⟳ No results with artist, trying just song name...")
                search_url = f"https://music.apple.com/{self._storefront}/search?term={urllib.parse.quote(song_name)}"
                self._page.goto(search_url, wait_until="load")
                time.sleep(3)

                # Check again for no results
                for selector in no_results_selectors:
                    try:
                        if self._page.query_selector(selector):
                            print(f"  ✗ Not found: {song_name} - {artist_name}")
                            return False
                    except:
                        continue

            # Look for song results with timeout
            result_found = False
            result_selectors = [
                '[data-testid="track-lockup"]',
                '.songs-list-row',
                '[role="row"]',
                '.lockup--song',
                'div[class*="song"]',
                'div[class*="track"]',
                'music-card-lockup[type="song"]'
            ]

            result_element = None
            for selector in result_selectors:
                try:
                    # Use wait_for_selector with short timeout instead of query_selector_all
                    elem = self._page.wait_for_selector(selector, timeout=5000)
                    if elem:
                        result_element = elem
                        result_found = True
                        break
                except:
                    continue

            if not result_found:
                print(f"  ✗ No results found for: {song_name} - {artist_name}")
                return False

            # Try different methods to add the song
            added = False

            # Method 1: Hover and click the "add" button
            try:
                result_element.hover()
                time.sleep(0.5)

                # Look for add button
                add_buttons = [
                    'button[aria-label*="Add"]',
                    'button[title*="Add"]',
                    '[data-testid="add-button"]',
                    'button[class*="add"]'
                ]

                for btn_selector in add_buttons:
                    try:
                        add_btn = result_element.query_selector(btn_selector)
                        if not add_btn:
                            add_btn = self._page.query_selector(btn_selector)
                        if add_btn:
                            add_btn.click()
                            time.sleep(1)

                            # Look for playlist selector in dropdown
                            try:
                                self._page.click(f'text="{playlist_name}"', timeout=3000)
                                print(f"  ✓ Added: {song_name} - {artist_name}")
                                return True
                            except:
                                # Try clicking "Add to a Playlist" option
                                try:
                                    self._page.click('text="Add to a Playlist"', timeout=2000)
                                    time.sleep(1)
                                    self._page.click(f'text="{playlist_name}"', timeout=3000)
                                    print(f"  ✓ Added: {song_name} - {artist_name}")
                                    return True
                                except:
                                    pass
                    except:
                        continue
            except Exception as e:
                pass

            # Method 2: Right-click context menu
            try:
                result_element.click(button="right")
                time.sleep(1)

                # Look for "Add to Playlist" in context menu
                add_menu_texts = [
                    'text="Add to Playlist"',
                    'text="Add to a Playlist"',
                    '[role="menuitem"]:has-text("Playlist")'
                ]

                for menu_selector in add_menu_texts:
                    try:
                        self._page.click(menu_selector, timeout=2000)
                        time.sleep(1)
                        self._page.click(f'text="{playlist_name}"', timeout=3000)
                        print(f"  ✓ Added: {song_name} - {artist_name}")
                        return True
                    except:
                        continue
            except:
                pass

            # Method 3: Click the song to open details, then add
            try:
                result_element.click()
                time.sleep(2)

                # Look for add/more button in detail view
                self._page.click('button[aria-label*="More"]', timeout=3000)
                time.sleep(1)
                self._page.click('text="Add to Playlist"', timeout=2000)
                time.sleep(1)
                self._page.click(f'text="{playlist_name}"', timeout=3000)
                print(f"  ✓ Added: {song_name} - {artist_name}")
                return True
            except:
                pass

            print(f"  ✗ Could not add: {song_name} - {artist_name} (found result but couldn't click add)")
            return False

        except Exception as e:
            print(f"  ✗ Error: {song_name} - {str(e)}")
            return False

    def __del__(self):
        try:
            if hasattr(self, '_browser'):
                self._browser.close()
            if hasattr(self, '_playwright'):
                self._playwright.stop()
        except:
            pass


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
# iOS Shortcuts exporter
# ---------------------------------------------------------------------------

class iOSShortcutsExporter:
    @staticmethod
    def export(playlist_name: str, songs: List[Dict[str, str]], output_path: Optional[str] = None) -> str:
        """
        Export playlist in iOS Shortcuts-friendly JSON format.
        Returns the path to the created file.
        """
        if output_path is None:
            safe = "".join(c for c in playlist_name if c.isalnum() or c in " -_").strip()
            output_path = f"{safe}.json"

        data = {
            "playlist_name": playlist_name,
            "song_count": len(songs),
            "songs": [
                {
                    "title": song["name"],
                    "artist": song["artist"],
                    "search_query": f"{song['name']} {song['artist']}"
                }
                for song in songs
            ]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_path


# ---------------------------------------------------------------------------
# Controller selection
# ---------------------------------------------------------------------------

def get_controller(args) -> Optional[MusicController]:
    """
    Priority:
      1. Apple Music REST API   — if APPLE_TEAM_ID / APPLE_KEY_ID / APPLE_PRIVATE_KEY are set
      2. Web automation         — if --use-web flag
      2b. Windows UI automation — if --use-windows-ui flag (Windows only)
      3. macOS AppleScript      — on darwin
      4. Windows COM            — on win32 (rarely works)
      5. Web automation         — fallback for Windows if COM fails
      6. None → M3U export
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

    # 2. Web automation (if explicitly requested)
    if args.use_web:
        try:
            return AppleMusicWebController()
        except ImportError as e:
            print(f"Error: {e}")
            sys.exit(1)

    # 2b. Windows UI automation (if explicitly requested)
    if args.use_windows_ui:
        if sys.platform != "win32":
            print("Error: --use-windows-ui only works on Windows")
            sys.exit(1)
        try:
            print("Using Windows UI automation (Apple Music desktop app)\n")
            return AppleMusicWindowsUIController()
        except ImportError as e:
            print(f"Error: {e}")
            sys.exit(1)

    # 3. macOS AppleScript
    if sys.platform == "darwin":
        print("Using AppleScript (macOS)\n")
        return AppleMusicMacController()

    # 4. Windows COM
    if sys.platform == "win32":
        try:
            return AppleMusicWindowsController()
        except (ImportError, RuntimeError) as e:
            print(f"Windows COM not available: {e}")
            print("\nTrying web automation instead...\n")
            # 5. Fallback to web automation
            try:
                return AppleMusicWebController()
            except ImportError:
                print("Web automation not available. Install with:")
                print("  python -m pip install playwright")
                print("  python -m playwright install chromium\n")
                print("Falling back to M3U export.\n")
                return None

    # 6. Fallback
    print(f"Platform '{sys.platform}' not supported for direct playlist creation.")
    print("Use --use-web for browser automation, or --export-only for M3U file.\n")
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

Windows UI automation (Windows only — automates Apple Music app):
  %(prog)s "URL" --use-windows-ui
  (Automates the Apple Music desktop app on Windows)
  Requires: pip install pywinauto

iOS Shortcuts (recommended for Windows users without automation):
  %(prog)s "URL" --ios
  (Exports JSON for iPhone/iPad Shortcuts automation)
  Creates playlist on iOS, syncs to Windows via iCloud

Web automation (limited — music.apple.com web player):
  %(prog)s "URL" --use-web
  (Opens a browser, automates music.apple.com — no API keys needed)
  Note: Web player has limited features, may not support playlist creation

Examples:
  %(prog)s "https://www.setlist.fm/setlist/artist/2024/venue-id.html"
  %(prog)s "URL" --use-web --playlist-name "My Playlist"
  %(prog)s "URL" --export-only --output playlist.m3u
  %(prog)s "URL" --ios --output myplaylist.json
  %(prog)s "URL" --re-auth   (clear cached user token and re-authorize)
        """
    )
    parser.add_argument("url", help="setlist.fm URL")
    parser.add_argument("--api-key", default=os.environ.get("SETLISTFM_API_KEY"),
                        help="setlist.fm API key (or set SETLISTFM_API_KEY)")
    parser.add_argument("--playlist-name", help="Override playlist name")
    parser.add_argument("--export-only", action="store_true",
                        help="Export M3U file only, don't create playlist in Apple Music")
    parser.add_argument("--ios", action="store_true",
                        help="Export for iOS Shortcuts automation (creates JSON file)")
    parser.add_argument("--output", help="Output path for M3U or JSON file")
    parser.add_argument("--re-auth", action="store_true",
                        help="Clear cached Apple Music user token and re-authorize")
    parser.add_argument("--use-web", action="store_true",
                        help="Use web browser automation (music.apple.com) - works on all platforms")
    parser.add_argument("--use-windows-ui", action="store_true",
                        help="Use Windows UI automation (Apple Music desktop app) - Windows only")
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

    # --- iOS Shortcuts export ---
    if args.ios:
        path = iOSShortcutsExporter.export(playlist_name, songs, args.output)
        print(f"\n{'='*50}")
        print("iOS Shortcuts JSON exported!")
        print(f"{'='*50}")
        print(f"File:  {path}")
        print(f"Songs: {len(songs)}")
        print(f"\nNext steps:")
        print(f"1. AirDrop or copy '{path}' to your iPhone/iPad")
        print(f"2. Install the Apple Shortcut (see instructions below)")
        print(f"3. Run the Shortcut and select this JSON file")
        print(f"4. Playlist will be created and synced to your Windows via iCloud")
        print(f"\n{'='*50}")
        print(f"APPLE SHORTCUT SETUP")
        print(f"{'='*50}")
        print(f"1. On your iPhone, open the Shortcuts app")
        print(f"2. Tap + to create a new shortcut")
        print(f"3. Add these actions (tap + between each):")
        print(f"")
        print(f"   a. 'Select File' (to pick the JSON)")
        print(f"   b. 'Get Dictionary from Input'")
        print(f"   c. 'Get Dictionary Value' - Key: playlist_name")
        print(f"   d. 'Set Variable' - Name: PlaylistName")
        print(f"   e. 'Create Playlist' - Name: PlaylistName variable")
        print(f"   f. 'Set Variable' - Name: NewPlaylist")
        print(f"   g. 'Get Dictionary Value' - Key: songs (from Dictionary)")
        print(f"   h. 'Repeat with Each' (loops through songs)")
        print(f"      Inside the repeat:")
        print(f"      - 'Get Dictionary Value' - Key: search_query")
        print(f"      - 'Search Apple Music' - Search term: (result from above)")
        print(f"      - 'Get Item from List' - First Item")
        print(f"      - 'Add to Playlist' - Playlist: NewPlaylist variable")
        print(f"   i. 'Show Notification' - Text: 'Playlist created!'")
        print(f"")
        print(f"4. Name the shortcut 'Create Playlist from JSON'")
        print(f"5. Run it and select your JSON file!")
        print(f"\nOr download a pre-made shortcut:")
        print(f"https://www.icloud.com/shortcuts/ (search for playlist creators)")
        return

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
