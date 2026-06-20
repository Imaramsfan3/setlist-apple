#!/usr/bin/env python3
"""Test if iTunes COM interface works"""
import sys

try:
    import win32com.client
    print("✓ pywin32 is installed")
    
    # Try to connect to iTunes
    try:
        itunes = win32com.client.Dispatch("iTunes.Application")
        print(f"✓ Connected to iTunes")
        print(f"  Version: {itunes.Version}")
        
        # List some playlists
        print(f"\nExisting playlists:")
        for src in itunes.Sources:
            if src.Kind == 1:  # Library
                count = 0
                for pl in src.Playlists:
                    print(f"  - {pl.Name}")
                    count += 1
                    if count >= 5:
                        print(f"  ... and more")
                        break
        
        print(f"\n✓ iTunes COM interface is working!")
        
    except Exception as e:
        print(f"✗ Could not connect to iTunes: {e}")
        print(f"\nMake sure:")
        print(f"  1. iTunes is installed")
        print(f"  2. You've launched iTunes at least once")
        print(f"  3. Try restarting your computer")
        sys.exit(1)
        
except ImportError:
    print("✗ pywin32 not installed")
    print("Install with: python -m pip install pywin32")
    sys.exit(1)
