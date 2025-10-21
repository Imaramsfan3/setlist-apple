#!/usr/bin/env python3
"""
Script to create Apple Music playlists from setlist.fm URLs
"""

import sys
import requests
import re
import subprocess
import argparse
from urllib.parse import urlparse
import os
from typing import List, Dict, Optional


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


class AppleMusicController:
    """Controller for interacting with Apple Music via AppleScript"""

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


def main():
    parser = argparse.ArgumentParser(
        description="Create an Apple Music playlist from a setlist.fm URL"
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

    args = parser.parse_args()

    if not args.api_key:
        print("Error: setlist.fm API key required.")
        print("Set SETLISTFM_API_KEY environment variable or use --api-key flag")
        print("\nGet your API key at: https://www.setlist.fm/settings/api")
        sys.exit(1)

    # Check if running on macOS
    if sys.platform != "darwin":
        print("Error: This script requires macOS to control Apple Music")
        sys.exit(1)

    print(f"Fetching setlist from: {args.url}\n")

    # Initialize clients
    setlist_client = SetlistFMClient(args.api_key)
    music_controller = AppleMusicController()

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

    print(f"Creating playlist: {playlist_name}\n")

    # Create playlist
    try:
        music_controller.create_playlist(playlist_name)
    except Exception as e:
        print(f"Error creating playlist: {e}")
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
