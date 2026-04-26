# iOS Shortcuts Setup Guide

Use your iPhone to create playlists that sync back to Windows!

## Step 1: Export the Playlist

On your Windows PC:

```powershell
git pull
python setlist_to_playlist.py "https://www.setlist.fm/setlist/..." --ios
```

This creates a `.json` file (e.g., `The Hunna - Peak District - 01-08-2025.json`)

---

## Step 2: Get the File to Your iPhone

**Option A: AirDrop** (if you have a Mac nearby)
- Right-click the JSON file → Share → AirDrop to iPhone

**Option B: Email**
- Email the JSON file to yourself
- Open on iPhone, tap to download

**Option C: Cloud Storage**
- Upload to iCloud Drive, Dropbox, or Google Drive
- Download on iPhone

---

## Step 3: Create the Shortcut (One-Time Setup)

On your iPhone:

1. **Open the Shortcuts app** (built into iOS)

2. **Tap the + button** (top right) to create a new shortcut

3. **Tap "Add Action"** and build this sequence:

   | Step | Action | Settings |
   |------|--------|----------|
   | 1 | **Select File** | Leave default |
   | 2 | **Get Dictionary from Input** | |
   | 3 | **Get Dictionary Value** | Key: `playlist_name` |
   | 4 | **Set Variable** | Variable Name: `PlaylistName` |
   | 5 | **Create Playlist** | Name: tap variable icon → select `PlaylistName` |
   | 6 | **Set Variable** | Variable Name: `NewPlaylist` |
   | 7 | **Get Dictionary Value** | Key: `songs`, Dictionary: tap "Dictionary" → select first action result |
   | 8 | **Repeat with Each** | (this creates a loop) |
   | 9 | *Inside the loop:* **Get Dictionary Value** | Key: `search_query`, Dictionary: tap → select "Repeat Item" |
   | 10 | *Inside the loop:* **Search** | Search for: tap → select previous result, App: Music |
   | 11 | *Inside the loop:* **Get Item from List** | Index: First Item |
   | 12 | *Inside the loop:* **Add Music to Playlist** | Playlist: tap variable → select `NewPlaylist` |
   | 13 | *Outside loop:* **Show Notification** | Text: "Playlist created!" |

4. **Tap the shortcut name** at the top and rename it to **"Create Playlist from JSON"**

5. **Tap Done**

---

## Step 4: Run the Shortcut

1. **Open Shortcuts app**
2. **Tap your "Create Playlist from JSON" shortcut**
3. **Select the JSON file** you copied earlier
4. **Wait ~1-2 minutes** while it creates the playlist

You'll see a notification when done!

---

## Step 5: Check Windows

Open Apple Music on Windows — your new playlist should appear (synced via iCloud).

---

## Troubleshooting

**"No actions found"**
- Make sure you're searching for the right action names
- "Create Playlist" is under Music actions
- "Search" needs to have App set to Music

**"Can't find songs"**
- Songs might not be available in your region
- Try searching manually in Apple Music first

**Shortcut runs but no songs added**
- Check that "Add Music to Playlist" is INSIDE the repeat loop
- Make sure you selected the `NewPlaylist` variable

**Playlist doesn't sync to Windows**
- Make sure you're signed in with the same Apple ID on both devices
- Check Settings → Music → Sync Library is ON
- Wait a few minutes for iCloud to sync

---

## Alternative: Download a Pre-Made Shortcut

Search "playlist creator" or "JSON to playlist" on:
- https://www.icloud.com/shortcuts/
- https://shortcutsgallery.com/

Look for shortcuts that can read JSON and create Apple Music playlists.

---

## Need Help?

The inline instructions when you run `--ios` show the full step-by-step.
