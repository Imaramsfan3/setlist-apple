# Windows Setup Guide

## Step 1: Install Python

1. Download Python from https://www.python.org/downloads/
2. **IMPORTANT**: During installation, check "Add Python to PATH"
3. Click "Install Now"
4. Restart PowerShell after installation

## Step 2: Verify Python Installation

Open a new PowerShell window and run:

```powershell
python --version
```

If that doesn't work, try:
```powershell
py --version
```

## Step 3: Install Dependencies

Navigate to the project folder:
```powershell
cd path\to\setlist-apple
```

Install required packages using one of these commands:

```powershell
# Try this first
python -m pip install -r requirements.txt

# Or if using py launcher
py -m pip install -r requirements.txt

# Or if pip is in PATH
pip install -r requirements.txt
```

## Step 4: Set Your API Key

Get your API key from: https://www.setlist.fm/settings/api

Set it as an environment variable (temporary - for current session only):
```powershell
$env:SETLISTFM_API_KEY='your-api-key-here'
```

Or set it permanently:
```powershell
[System.Environment]::SetEnvironmentVariable('SETLISTFM_API_KEY', 'your-api-key-here', 'User')
```

Then restart PowerShell to use the permanent variable.

## Step 5: Run the Script

```powershell
# Using python command
python setlist_to_playlist.py "https://www.setlist.fm/setlist/artist/2024/venue-id.html"

# Or using py launcher
py setlist_to_playlist.py "https://www.setlist.fm/setlist/artist/2024/venue-id.html"

# Or pass API key directly
python setlist_to_playlist.py "URL" --api-key "your-api-key"
```

## Troubleshooting

### "pip is not recognized"
- Python is not installed or not in PATH
- Reinstall Python and make sure to check "Add Python to PATH"
- Use `python -m pip` instead of `pip`

### "python is not recognized"
- Try using `py` instead of `python`
- Reinstall Python with PATH option enabled

### "Could not connect to Apple Music/iTunes"
- Make sure iTunes or Apple Music for Windows is installed
- Download from: https://www.apple.com/itunes/download/
- Launch the application at least once before running the script

### pywin32 Installation Issues
If you get errors about pywin32, install it separately:
```powershell
python -m pip install pywin32
```

Then run the post-install script:
```powershell
python Scripts/pywin32_postinstall.py -install
```

## Alternative: M3U Export (No iTunes Required)

If you don't have iTunes/Apple Music, or if automation doesn't work, export an M3U file:

```powershell
python setlist_to_playlist.py "URL" --export-only --output "my_playlist.m3u"
```

Then import the M3U file manually into your music player.
