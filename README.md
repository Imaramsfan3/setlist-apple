# Setlist to Apple Music Playlist

Automatically create Apple Music playlists from setlist.fm concert setlists.

## Features

- Fetch setlist data from any setlist.fm URL
- Automatically create a playlist in Apple Music
- Search and add songs to the playlist
- Support for cover songs (uses the original artist)
- Detailed progress reporting

## Requirements

- macOS (required for Apple Music integration via AppleScript)
- Python 3.7 or higher
- Apple Music app
- setlist.fm API key

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/setlist-apple.git
cd setlist-apple
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Get a setlist.fm API key:
   - Go to https://www.setlist.fm/settings/api
   - Sign in or create an account
   - Request an API key (it's free!)

4. Set your API key as an environment variable:
```bash
export SETLISTFM_API_KEY='your-api-key-here'
```

Or add it to your `~/.zshrc` or `~/.bash_profile`:
```bash
echo 'export SETLISTFM_API_KEY="your-api-key-here"' >> ~/.zshrc
```

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
3. **Create**: Creates a new playlist in Apple Music via AppleScript
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

**"Error: This script requires macOS"**
- This script uses AppleScript to control Apple Music, which only works on macOS

**"AppleScript error"**
- Make sure Apple Music is installed and accessible
- Try running Apple Music manually first

**"Songs not found"**
- Some songs may not be available in Apple Music
- Song names from setlist.fm might not exactly match Apple Music's catalog
- Try searching manually in Apple Music to verify availability

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.