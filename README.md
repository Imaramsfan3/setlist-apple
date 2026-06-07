# Setlist to Apple Music Playlist

Automatically create Apple Music playlists from setlist.fm concert setlists.

Works on **Windows, macOS, and Linux**.

## Quick Start (Windows Users — Easiest Method)

```powershell
# 1. Install dependencies
python -m pip install -r requirements.txt
python -m playwright install chromium

# 2. Get setlist.fm API key (free)
# Visit: https://www.setlist.fm/settings/api

# 3. Run with web automation
$env:SETLISTFM_API_KEY='your-key-here'
python setlist_to_playlist.py "https://www.setlist.fm/setlist/..." --use-web
```

**First run:** A browser opens to music.apple.com — sign in once, session is saved.  
**Subsequent runs:** Fully automatic, no login needed.

---

## How It Works

1. Fetches the setlist from setlist.fm using their API
2. Opens a browser to music.apple.com (or uses saved login session)
3. Creates the playlist automatically
4. Searches for each song and adds it to the playlist

---

## Installation

```powershell
# Windows
python -m pip install -r requirements.txt
python -m playwright install chromium

# macOS / Linux
pip install -r requirements.txt
playwright install chromium
```

> **Windows users:** If `python` is not recognized:
> 1. Download Python from https://www.python.org/downloads/
> 2. During install, check **"Add Python to PATH"**
> 3. Restart PowerShell
> 4. See [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for detailed help

---

## Setup

### Required: setlist.fm API Key

Get a free key at https://www.setlist.fm/settings/api

```powershell
# Windows PowerShell (current session)
$env:SETLISTFM_API_KEY='your-key-here'

# Windows — set permanently
[System.Environment]::SetEnvironmentVariable('SETLISTFM_API_KEY','your-key','User')
```

```bash
# macOS / Linux
export SETLISTFM_API_KEY='your-key-here'
```

---

## Usage

### Method 1: Web Automation (Recommended — Free, Works Everywhere)

```powershell
python setlist_to_playlist.py "URL" --use-web
```

**Pros:**
- ✅ Free — no paid accounts needed
- ✅ Works on Windows, macOS, Linux
- ✅ One-time login, then fully automatic
- ✅ Creates playlists and adds songs automatically

**How it works:**
- Opens Chromium browser
- Navigates to music.apple.com
- Automates playlist creation and song additions
- Session is saved so you only log in once

**First time:**
1. Browser opens to music.apple.com
2. Sign in with your Apple ID
3. Script continues automatically after login
4. Session saved to `~/.setlist_apple_web_session.json`

**After first time:** No login needed — fully automatic.

---

### Method 2: Windows UI Automation (Windows Only — Direct App Control)

```powershell
python setlist_to_playlist.py "URL" --use-windows-ui
```

**Pros:**
- ✅ Free — no paid accounts needed
- ✅ Automates the Apple Music desktop app directly
- ✅ Creates playlists and adds songs automatically
- ✅ No browser needed

**Cons:**
- ❌ Windows only
- ❌ Requires Apple Music app to be installed
- ❌ May be fragile if Apple updates the UI

**How it works:**
- Launches or connects to Apple Music Windows app
- Uses keyboard shortcuts and UI automation
- Creates playlist and searches for songs
- Adds songs to playlist automatically

**Requirements:**
```powershell
python -m pip install pywinauto
```

**Note:** This method automates the Apple Music app using keyboard/mouse automation. It may require the app window to be visible and can be affected by UI changes.

---

### Method 3: M3U Export (Manual Import)

```powershell
python setlist_to_playlist.py "URL" --export-only
```

Creates an `.m3u` playlist file.

**To import:**
1. Open Apple Music
2. **File → Library → Import Playlist**
3. Select the `.m3u` file

---

### Method 4: Apple Music REST API (Advanced)

Requires Apple Developer credentials (£79/year — only needed if you want pure API access).

For most users, **web automation (Method 1) is better** — it's free and just as automatic.

<details>
<summary>Click to see API setup (optional)</summary>

1. Sign in at https://developer.apple.com/account
2. Go to **Certificates, IDs & Profiles → Keys**
3. Create a new key, enable **MusicKit**, download `.p8` file
4. Note your **Team ID** and **Key ID**

```powershell
$env:APPLE_TEAM_ID='XXXXXXXXXX'
$env:APPLE_KEY_ID='XXXXXXXXXX'
$env:APPLE_PRIVATE_KEY='C:\path\to\AuthKey_XXXXXXXXXX.p8'
```

Then run:
```powershell
python setlist_to_playlist.py "URL"
```

</details>

---

## Examples

```powershell
# Basic — web automation (recommended)
python setlist_to_playlist.py "https://www.setlist.fm/setlist/artist/2024/venue-id.html" --use-web

# Custom playlist name
python setlist_to_playlist.py "URL" --use-web --playlist-name "My Concert 2024"

# Windows UI automation (Windows only)
python setlist_to_playlist.py "URL" --use-windows-ui

# M3U export only
python setlist_to_playlist.py "URL" --export-only --output my_playlist.m3u

# Clear saved web session and re-login
python setlist_to_playlist.py "URL" --use-web --re-auth
```

---

## Controller Priority

The script picks the best method automatically:

| Priority | Method | Platform | Free? | Setup |
|----------|--------|----------|-------|-------|
| 1 | **Apple Music API** | All | No (£79/year) | Apple Developer account |
| 2 | **Web automation** (`--use-web`) | All | ✅ Yes | One-time browser login |
| 2b | **Windows UI automation** (`--use-windows-ui`) | Windows only | ✅ Yes | `pip install pywinauto` |
| 3 | **AppleScript** | macOS only | ✅ Yes | None |
| 4 | **COM** | Windows (rarely works) | ✅ Yes | iTunes installed |
| 5 | **M3U export** | All | ✅ Yes | Manual import |

**For Windows:** Use `--use-windows-ui` (automates Apple Music app) or `--ios` (for iPhone Shortcuts). COM doesn't work with Apple Music for Windows.

---

## Troubleshooting

**`python` / `pip` not recognized (Windows)**
- Reinstall Python and tick **"Add Python to PATH"**
- Or use `python -m pip install ...` instead of `pip install ...`

**`No module named 'playwright'`**
```powershell
python -m pip install playwright
python -m playwright install chromium
```

**Web automation: "Login timeout"**
- Make sure to click "Sign In" in the browser window
- You have 5 minutes to log in

**Web automation: Browser doesn't open**
- Check if another browser window opened in the background
- Make sure Chromium installed: `python -m playwright install chromium`

**Web automation: "Failed to create playlist"**
- The music.apple.com interface may have changed
- Try using `--export-only` for M3U export instead
- Or wait for an update to the script

**Songs not found**
- Song may not be available in your region's Apple Music catalog
- Setlist.fm name may differ from Apple Music title

---

## What Gets Installed

- **requests** — HTTP library for setlist.fm API
- **PyJWT** + **cryptography** — JWT tokens (only for API method)
- **playwright** — Browser automation for web method
- **pywin32** — Windows COM (only on Windows)

---

## License

See LICENSE file for details.
