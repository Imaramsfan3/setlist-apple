#!/usr/bin/env python3
"""
Script to create Apple Music playlists from setlist.fm URLs
Supports macOS (AppleScript), Windows (COM/iTunes), and M3U export
"""

import sys
import requests
import re
import subprocess
import argparse
from urllib.parse import urlparse
import os
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from pathlib import Path


class SetlistFMClient:
    """Client for interacting with the setlist.fm API"""

    BASE_URL = "https://api.setlist.fm/rest/1.0"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "Accept": "application/json"
        }

    def extract_setlist_id(self, url: str) -> Optional[str]:
        """Extract setlist ID from a setlist.fm URL"""
        # Example URL: https://www.setlist.fm/setlist/artist-name/year/venue-id.html
        pattern = r'setlist\.fm/setlist/[^/]+/\d+/([^/]+)\.html'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None

    def get_setlist(self, setlist_id: str) -> Dict:
        """Fetch setlist data from the API"""
        url = f"{self.BASE_URL}/setlist/{setlist_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def parse_songs(self, setlist_data: Dict) -> tuple[List[Dict[str, str]], str, str]:
        """
        Parse songs from setlist data
        Returns: (songs, artist_name, event_date)
        """
        songs = []
        artist_name = setlist_data.get("artist", {}).get("name", "Unknown Artist")
        event_date = setlist_data.get("eventDate", "")
        venue_name = setlist_data.get("venue", {}).get("name", "")

        # Parse sets
        for set_item in setlist_data.get("sets", {}).get("set", []):
            for song in set_item.get("song", []):
                song_info = {
                    "name": song.get("name", ""),
                    "artist": artist_name
                }

                # Check if it's a cover
                if "cover" in song:
                    song_info["artist"] = song["cover"].get("name", artist_name)

                songs.append(song_info)

        return songs, artist_name, event_date


class MusicController(ABC):
    """Abstract base class for music playlist controllers"""

    @abstractmethod
    def create_playlist(self, name: str) -> None:
        """Create a new playlist"""
        pass

    @abstractmethod
    def search_and_add_song(self, playlist_name: str, song_name: str, artist_name: str) -> bool:
        """Search for and add a song to the playlist"""
        pass


class AppleMusicMacController(MusicController):
    """Controller for Apple Music on macOS via AppleScript"""

    @staticmethod
    def run_applescript(script: str) -> str:
        """Execute an AppleScript command"""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"AppleScript error: {e.stderr}")
            raise

    def create_playlist(self, name: str) -> None:
        """Create a new playlist in Apple Music"""
        script = f'''
        tell application "Music"
            if not (exists playlist "{name}") then
                make new playlist with properties {{name:"{name}"}}
            end if
        end tell
        '''
        self.run_applescript(script)
        print(f"Created playlist: {name}")

    def search_and_add_song(self, playlist_name: str, song_name: str, artist_name: str) -> bool:
        """
        Search for a song in Apple Music and add it to the playlist
        Returns True if successful, False otherwise
        """
        # Escape quotes in song and artist names
        song_name_escaped = song_name.replace('"', '\\"')
        artist_name_escaped = artist_name.replace('"', '\\"')

        script = f'''
        tell application "Music"
            try
                set searchResults to search playlist "Library" for "{song_name_escaped} {artist_name_escaped}"
                if (count of searchResults) > 0 then
                    set theTrack to item 1 of searchResults
                    duplicate theTrack to playlist "{playlist_name}"
                    return "success"
                else
                    return "not found"
                end if
            on error errMsg
                return "error: " & errMsg
            end try
        end tell
        '''

        try:
            result = self.run_applescript(script)
            if result == "success":
                print(f"  ✓ Added: {song_name} - {artist_name}")
                return True
            elif result == "not found":
                print(f"  ✗ Not found: {song_name} - {artist_name}")
                return False
            else:
                print(f"  ✗ Error adding {song_name}: {result}")
                return False
        except Exception as e:
            print(f"  ✗ Failed to add {song_name}: {str(e)}")
            return False


class AppleMusicWindowsController(MusicController):
    """Controller for Apple Music/iTunes on Windows via COM"""

    def __init__(self):
        try:
            import win32com.client
            self.win32com = win32com.client
            self.itunes = None
        except ImportError:
            raise ImportError(
                "pywin32 package required for Windows support.\n"
                "Install it with: pip install pywin32"
            )

    def _get_itunes(self):
        """Get Apple Music/iTunes COM object"""
        if self.itunes is None:
            try:
                # Try Apple Music first, then iTunes as fallback
                try:
                    self.itunes = self.win32com.Dispatch("AppleMusic.Application")
                    print("Connected to Apple Music")
                except:
                    self.itunes = self.win32com.Dispatch("iTunes.Application")
                    print("Connected to iTunes")
            except Exception as e:
                raise RuntimeError(
                    f"Could not connect to Apple Music/iTunes: {e}\n"
                    "Make sure Apple Music or iTunes is installed."
                )
        return self.itunes

    def create_playlist(self, name: str) -> None:
        """Create a new playlist in Apple Music/iTunes"""
        app = self._get_itunes()

        # Check if playlist exists
        sources = app.Sources
        for source in sources:
            if source.Kind == 1:  # Library
                playlists = source.Playlists
                for playlist in playlists:
                    if playlist.Name == name:
                        print(f"Playlist already exists: {name}")
                        return

        # Create new playlist
        app.CreatePlaylist(name)
        print(f"Created playlist: {name}")

    def search_and_add_song(self, playlist_name: str, song_name: str, artist_name: str) -> bool:
        """
        Search for a song and add it to the playlist
        Returns True if successful, False otherwise
        """
        try:
            app = self._get_itunes()

            # Find the playlist
            target_playlist = None
            sources = app.Sources
            for source in sources:
                if source.Kind == 1:  # Library
                    playlists = source.Playlists
                    for playlist in playlists:
                        if playlist.Name == playlist_name:
                            target_playlist = playlist
                            break
                if target_playlist:
                    break

            if not target_playlist:
                print(f"  ✗ Playlist not found: {playlist_name}")
                return False

            # Search for the track
            search_query = f"{song_name} {artist_name}"
            library_playlist = app.LibraryPlaylist
            search_results = library_playlist.Search(search_query, 0)  # 0 = search all fields

            if search_results and search_results.Count > 0:
                track = search_results.Item(1)  # Get first result (COM uses 1-based indexing)
                track.AddToPlaylist(target_playlist)
                print(f"  ✓ Added: {song_name} - {artist_name}")
                return True
            else:
                print(f"  ✗ Not found: {song_name} - {artist_name}")
                return False

        except Exception as e:
            print(f"  ✗ Error adding {song_name}: {str(e)}")
            return False


class M3UExporter:
    """Export playlist as M3U file for manual import"""

    @staticmethod
    def export_playlist(playlist_name: str, songs: List[Dict[str, str]], output_path: str = None) -> str:
        """
        Export songs to M3U playlist file
        Returns the path to the created file
        """
        if output_path is None:
            # Create safe filename
            safe_name = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_path = f"{safe_name}.m3u"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for song in songs:
                # M3U format: #EXTINF:duration,artist - title
                # Duration is unknown, so use -1
                f.write(f"#EXTINF:-1,{song['artist']} - {song['name']}\n")
                # We don't have actual file paths, so just write the search query
                # This serves as a reference list
                f.write(f"# Search: {song['name']} by {song['artist']}\n")

        return output_path


def get_music_controller(export_only: bool = False) -> Optional[MusicController]:
    """
    Get the appropriate music controller for the current platform
    Returns None if export_only is True
    """
    if export_only:
        return None

    if sys.platform == "darwin":
        # macOS - use AppleScript
        return AppleMusicMacController()
    elif sys.platform == "win32":
        # Windows - use COM
        try:
            return AppleMusicWindowsController()
        except ImportError as e:
            print(f"Warning: {e}")
            print("Falling back to M3U export mode.")
            return None
        except RuntimeError as e:
            print(f"Warning: {e}")
            print("Falling back to M3U export mode.")
            return None
    else:
        # Unsupported platform
        print(f"Warning: Platform '{sys.platform}' not supported for direct playlist creation.")
        print("Falling back to M3U export mode.")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Create an Apple Music playlist from a setlist.fm URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://www.setlist.fm/setlist/artist/2024/venue-id.html"
  %(prog)s "URL" --playlist-name "My Custom Playlist"
  %(prog)s "URL" --export-only --output myplaylist.m3u

Platform Support:
  macOS:   Uses AppleScript to control Apple Music
  Windows: Uses COM interface (requires iTunes or Apple Music for Windows)
  Other:   Exports M3U file for manual import
        """
    )
    parser.add_argument(
        "url",
        help="The setlist.fm URL"
    )
    parser.add_argument(
        "--api-key",
        help="setlist.fm API key (or set SETLISTFM_API_KEY environment variable)",
        default=os.environ.get("SETLISTFM_API_KEY")
    )
    parser.add_argument(
        "--playlist-name",
        help="Custom playlist name (default: 'Artist - Venue - Date')"
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Only export M3U file, don't create playlist in Apple Music"
    )
    parser.add_argument(
        "--output",
        help="Output path for M3U file (only used with --export-only)"
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: setlist.fm API key required.")
        print("Set SETLISTFM_API_KEY environment variable or use --api-key flag")
        print("\nGet your API key at: https://www.setlist.fm/settings/api")
        sys.exit(1)

    print(f"Fetching setlist from: {args.url}\n")

    # Initialize setlist client
    setlist_client = SetlistFMClient(args.api_key)

    # Extract setlist ID from URL
    setlist_id = setlist_client.extract_setlist_id(args.url)
    if not setlist_id:
        print("Error: Could not extract setlist ID from URL")
        print("Expected format: https://www.setlist.fm/setlist/artist/year/venue-id.html")
        sys.exit(1)

    print(f"Setlist ID: {setlist_id}")

    # Fetch setlist data
    try:
        setlist_data = setlist_client.get_setlist(setlist_id)
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching setlist: {e}")
        if e.response.status_code == 401:
            print("Invalid API key. Get your key at: https://www.setlist.fm/settings/api")
        sys.exit(1)

    # Parse songs
    songs, artist_name, event_date = setlist_client.parse_songs(setlist_data)

    if not songs:
        print("No songs found in setlist")
        sys.exit(1)

    print(f"Artist: {artist_name}")
    print(f"Date: {event_date}")
    print(f"Songs found: {len(songs)}\n")

    # Generate playlist name
    if args.playlist_name:
        playlist_name = args.playlist_name
    else:
        venue = setlist_data.get("venue", {}).get("name", "Unknown Venue")
        playlist_name = f"{artist_name} - {venue} - {event_date}"

    # Get music controller
    music_controller = get_music_controller(export_only=args.export_only)

    if music_controller is None:
        # Export to M3U file
        print(f"Exporting playlist to M3U file: {playlist_name}\n")
        output_path = M3UExporter.export_playlist(playlist_name, songs, args.output)
        print(f"\n{'='*50}")
        print(f"M3U playlist exported successfully!")
        print(f"{'='*50}")
        print(f"File: {output_path}")
        print(f"Songs: {len(songs)}")
        print(f"\nTo import into Apple Music:")
        print(f"1. Open Apple Music")
        print(f"2. Go to File > Library > Import Playlist")
        print(f"3. Select the M3U file: {output_path}")
        print(f"\nNote: You'll need to manually search and add songs in Apple Music")
        return

    # Create playlist directly
    print(f"Creating playlist: {playlist_name}\n")

    try:
        music_controller.create_playlist(playlist_name)
    except Exception as e:
        print(f"Error creating playlist: {e}")
        print("\nTrying M3U export as fallback...")
        output_path = M3UExporter.export_playlist(playlist_name, songs, args.output)
        print(f"M3U file created: {output_path}")
        sys.exit(1)

    # Add songs to playlist
    print("\nAdding songs to playlist:")
    successful = 0
    failed = 0

    for song in songs:
        if music_controller.search_and_add_song(playlist_name, song["name"], song["artist"]):
            successful += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"Playlist creation complete!")
    print(f"{'='*50}")
    print(f"Playlist name: {playlist_name}")
    print(f"Total songs: {len(songs)}")
    print(f"Successfully added: {successful}")
    print(f"Not found/failed: {failed}")
    print(f"\nOpen Apple Music to view your playlist!")


if __name__ == "__main__":
    main()
