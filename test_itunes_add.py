#!/usr/bin/env python3
"""Test adding a track to a playlist in iTunes"""

import win32com.client
import sys

try:
    # Connect to iTunes
    itunes = win32com.client.Dispatch("iTunes.Application")
    print(f"✓ Connected to iTunes {itunes.Version}")

    # Create a test playlist
    test_playlist_name = "TEST_PLAYLIST_DELETE_ME"

    # Delete if exists
    for src in itunes.Sources:
        if src.Kind == 1:
            for pl in src.Playlists:
                if pl.Name == test_playlist_name:
                    pl.Delete()
                    print(f"Deleted existing test playlist")

    # Create new playlist
    test_playlist = itunes.CreatePlaylist(test_playlist_name)
    print(f"✓ Created playlist: {test_playlist_name}")
    print(f"  Playlist type: {type(test_playlist)}")
    print(f"  Playlist Kind: {test_playlist.Kind if hasattr(test_playlist, 'Kind') else 'N/A'}")

    # Search for a common song
    print(f"\nSearching library for 'love'...")
    results = itunes.LibraryPlaylist.Search("love", 0)

    if results and results.Count > 0:
        print(f"✓ Found {results.Count} results")
        track = results.Item(1)
        print(f"  First result: {track.Name} - {track.Artist}")
        print(f"  Track type: {type(track)}")

        # Try different methods to add track
        print(f"\nTrying to add track to playlist...")

        # Method 1: playlist.AddTrack
        try:
            test_playlist.AddTrack(track)
            print(f"  ✓ Method 1 (AddTrack) worked!")
        except Exception as e:
            print(f"  ✗ Method 1 failed: {e}")

        # Check if track was added
        print(f"\nPlaylist now has {test_playlist.Tracks.Count} tracks")

    else:
        print("✗ No songs found in library")
        print("  Add some songs to iTunes first!")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
