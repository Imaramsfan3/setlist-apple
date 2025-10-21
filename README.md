# Setlist to Apple Music Playlist

Automatically create Apple Music playlists from setlist.fm concert setlists.

**Cross-platform support:** Works on macOS, Windows, and Linux!

## Features

- Fetch setlist data from any setlist.fm URL
- **Cross-platform support:**
  - **macOS**: Automatically create playlists via AppleScript
  - **Windows**: Automatically create playlists via COM (iTunes/Apple Music)
  - **Linux/Other**: Export M3U playlists for manual import
- Search and add songs to the playlist
- Support for cover songs (uses the original artist)
- M3U export option for all platforms
- Detailed progress reporting

## Requirements

- Python 3.7 or higher
- Apple Music or iTunes (for automatic playlist creation)
- setlist.fm API key (free)

### Platform-Specific Requirements

- **macOS**: Apple Music app (uses AppleScript)
- **Windows**: iTunes or Apple Music for Windows (uses COM interface)
- **Linux/Other**: Any music player that supports M3U playlists

## Installation

### Windows Users - Quick Start

**Option 1: Automated Setup (Recommended)**
1. Download this repository
2. Double-click `setup.bat` to install dependencies automatically
3. See [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for detailed instructions

**Option 2: Manual Setup**
```powershell
# Navigate to the folder
cd setlist-apple

# Install dependencies
python -m pip install -r requirements.txt

# If 'python' doesn't work, try:
py -m pip install -r requirements.txt
```

### macOS/Linux Users

```bash
# Clone the repository
git clone https://github.com/yourusername/setlist-apple.git
cd setlist-apple

# Install dependencies
pip install -r requirements.txt
```

### Get API Key

1. Get a setlist.fm API key:
   - Go to https://www.setlist.fm/settings/api
   - Sign in or create an account
   - Request an API key (it's free!)

2. Set your API key as an environment variable:

   **macOS/Linux:**
   ```bash
   export SETLISTFM_API_KEY='your-api-key-here'
   ```

   Or add it to your `~/.zshrc` or `~/.bash_profile`:
   ```bash
   echo 'export SETLISTFM_API_KEY="your-api-key-here"' >> ~/.zshrc
   ```

   **Windows (PowerShell):**
   ```powershell
   $env:SETLISTFM_API_KEY='your-api-key-here'
   ```

   Or set it permanently via System Properties > Environment Variables

## Usage

Basic usage:
```bash
python setlist_to_playlist.py "https://www.setlist.fm/setlist/artist/year/venue-id.html"
```

With custom playlist name:
```bash
python setlist_to_playlist.py "https://www.setlist.fm/setlist/artist/year/venue-id.html" --playlist-name "My Custom Playlist"
```

With API key as argument:
```bash
python setlist_to_playlist.py "https://www.setlist.fm/setlist/artist/year/venue-id.html" --api-key "your-api-key"
```

Export to M3U file (for manual import):
```bash
python setlist_to_playlist.py "https://www.setlist.fm/setlist/artist/year/venue-id.html" --export-only --output "my_playlist.m3u"
```

### Example

```bash
python setlist_to_playlist.py "https://www.setlist.fm/setlist/taylor-swift/2024/madison-square-garden-new-york-ny-12345678.html"
```

This will:
1. Fetch the setlist from setlist.fm
2. Create a playlist named "Taylor Swift - Madison Square Garden - 2024-XX-XX"
3. Search Apple Music for each song
4. Add found songs to the playlist

## How It Works

1. **Fetch**: The script uses the setlist.fm API to retrieve setlist data
2. **Parse**: Extracts song names and artist information (including cover songs)
3. **Create**: Creates a new playlist using the appropriate method:
   - **macOS**: AppleScript automation
   - **Windows**: COM interface (iTunes/Apple Music)
   - **Other/Fallback**: M3U file export
4. **Search**: Searches Apple Music's library for each song
5. **Add**: Adds found songs to the playlist

## Notes

- The script searches your Apple Music library and the Apple Music catalog
- Songs not found in Apple Music will be skipped (you'll see which ones)
- For best results, make sure you have an Apple Music subscription
- The playlist name defaults to: "Artist - Venue - Date"
- Cover songs will search for the original artist's version

## Troubleshooting

**"Error: setlist.fm API key required"**
- Make sure you've set the `SETLISTFM_API_KEY` environment variable
- Or pass the API key using the `--api-key` flag

**Windows: "pywin32 package required"**
- Install pywin32: `pip install pywin32`
- Or reinstall all requirements: `pip install -r requirements.txt`

**Windows: "Could not connect to Apple Music/iTunes"**
- Make sure iTunes or Apple Music for Windows is installed
- Try launching the application manually first
- If issues persist, use `--export-only` to create an M3U file instead

**macOS: "AppleScript error"**
- Make sure Apple Music is installed and accessible
- Grant Terminal/your IDE permission to control Apple Music (System Settings > Privacy & Security > Automation)
- Try running Apple Music manually first

**"Songs not found"**
- Some songs may not be available in Apple Music
- Song names from setlist.fm might not exactly match Apple Music's catalog
- Try searching manually in Apple Music to verify availability

**Platform not supported / Automatic fallback to M3U**
- The script will automatically export an M3U file
- Import it manually: Apple Music > File > Library > Import Playlist
- You can also force M3U export with the `--export-only` flag

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.