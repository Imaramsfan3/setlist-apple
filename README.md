# Setlist to Apple Music Playlist

Automatically create Apple Music playlists from setlist.fm concert setlists.

Works on **Windows, macOS, and Linux** via the official Apple Music REST API.

## How It Works

1. Fetches the setlist from setlist.fm using their API
2. Authenticates with Apple Music (one-time browser login, token cached after)
3. Searches the Apple Music catalog for each song
4. Creates the playlist and adds the songs automatically

## Controller Priority

The script picks the best available method automatically:

| Priority | Method | Platform | Requires |
|----------|--------|----------|---------|
| 1 | **Apple Music REST API** | All platforms | Apple Developer credentials (one-time setup) |
| 2 | **AppleScript** | macOS only | Apple Music app |
| 3 | **COM interface** | Windows only | iTunes or Apple Music for Windows |
| 4 | **M3U export** | Any | Nothing — manual import |

## Installation

```powershell
# Windows
python -m pip install -r requirements.txt

# macOS / Linux
pip install -r requirements.txt
```

> **Windows users:** If `python` is not recognised, download Python from
> https://www.python.org/downloads/ — check **"Add Python to PATH"** during install,
> then restart PowerShell. See [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for details.

## Setup

### 1. setlist.fm API Key (required)

Get a free key at https://www.setlist.fm/settings/api

```powershell
# Windows PowerShell (current session)
$env:SETLISTFM_API_KEY='your-key'

# Windows — set permanently
[System.Environment]::SetEnvironmentVariable('SETLISTFM_API_KEY','your-key','User')
```

```bash
# macOS / Linux
export SETLISTFM_API_KEY='your-key'
```

---

### 2. Apple Music API Credentials (recommended — works on all platforms)

This is a one-time setup that takes about 10 minutes.

**Step 1 — Create a MusicKit key**

1. Sign in at https://developer.apple.com/account *(free account works)*
2. Go to **Certificates, IDs & Profiles → Keys**
3. Click **+** to create a new key
4. Name it anything (e.g. "Setlist Playlist"), enable **MusicKit**
5. Click **Continue → Register → Download** — save the `.p8` file somewhere safe
6. Note the **Key ID** shown on the download page

**Step 2 — Find your Team ID**

Your Team ID is shown in the top-right corner of your Apple Developer account page
(e.g. `ABC123DEFG`).

**Step 3 — Set environment variables**

```powershell
# Windows PowerShell (current session)
$env:APPLE_TEAM_ID='XXXXXXXXXX'
$env:APPLE_KEY_ID='XXXXXXXXXX'
$env:APPLE_PRIVATE_KEY='C:\Users\you\AuthKey_XXXXXXXXXX.p8'

# Windows — set permanently
[System.Environment]::SetEnvironmentVariable('APPLE_TEAM_ID','XXXXXXXXXX','User')
[System.Environment]::SetEnvironmentVariable('APPLE_KEY_ID','XXXXXXXXXX','User')
[System.Environment]::SetEnvironmentVariable('APPLE_PRIVATE_KEY','C:\path\to\key.p8','User')
```

```bash
# macOS / Linux
export APPLE_TEAM_ID='XXXXXXXXXX'
export APPLE_KEY_ID='XXXXXXXXXX'
export APPLE_PRIVATE_KEY='/path/to/AuthKey_XXXXXXXXXX.p8'
```

---

## Usage

```powershell
# Basic — creates playlist in Apple Music
python setlist_to_playlist.py "https://www.setlist.fm/setlist/artist/2024/venue-id.html"

# Custom playlist name
python setlist_to_playlist.py "URL" --playlist-name "My Playlist"

# Export M3U file only (no Apple Music account needed)
python setlist_to_playlist.py "URL" --export-only --output my_playlist.m3u

# Clear cached user token and re-authorize
python setlist_to_playlist.py "URL" --re-auth
```

**First run with Apple Music API:** A browser window will open asking you to sign in to
Apple Music and grant access. After that, the token is cached at `~/.setlist_apple_user_token`
and you won't be asked again (token lasts ~6 months).

## Troubleshooting

**`python` / `pip` not recognised (Windows)**
- Reinstall Python and tick **"Add Python to PATH"**
- Use `python -m pip` instead of `pip`

**`No module named 'jwt'`**
```powershell
python -m pip install PyJWT cryptography
```

**Apple Music API — `401 Unauthorized`**
- Your cached user token may have expired. Run with `--re-auth` to re-authorize.
- Double-check `APPLE_TEAM_ID`, `APPLE_KEY_ID`, and `APPLE_PRIVATE_KEY` are set correctly.

**Apple Music API — `invalid_client` in browser**
- Make sure MusicKit is enabled on the key in your Apple Developer account.
- Regenerate the key if needed.

**Windows COM — `Invalid class string`**
- Apple Music for Windows does not expose a COM interface.
- Set up Apple Music API credentials (see above) for full Windows support.

**Songs not found**
- The song may not be available in your region's Apple Music catalog.
- The setlist.fm name may differ from the Apple Music title (e.g. live edits, alternate titles).

## License

See LICENSE file for details.
