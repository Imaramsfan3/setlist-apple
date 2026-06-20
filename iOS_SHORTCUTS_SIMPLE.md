# iOS Shortcuts - Simple Setup Guide

## What You Need
- iPhone with Apple Music
- The JSON file from the script
- 10 minutes to set up (one-time only)

---

## Part 1: Get the JSON File to Your iPhone

### On Windows:
```powershell
python setlist_to_playlist.py "YOUR_SETLIST_URL" --ios
```
This creates a file like `The Hunna - Peak District - 01-08-2025.json`

### Transfer to iPhone (Pick ONE method):

**Easiest: Email it**
1. Email the `.json` file to yourself
2. Open email on iPhone
3. Tap the attachment to download
4. Tap "Save to Files" → pick a location (Downloads is fine)

---

## Part 2: Create the Shortcut on iPhone

Open the **Shortcuts app** on your iPhone.

### Step 1: Start a New Shortcut
- Tap the **+** button (top right)
- You'll see "New Shortcut" at the top

---

### Step 2: Add Actions (Search for each one)

Tap **"Add Action"** and search for these actions in order:

#### 📁 Action 1: "Select File"
- Search for: **"Select File"**
- Tap it to add
- Leave all settings as default

---

#### 📖 Action 2: "Get Dictionary from Input"  
- Search for: **"Get Dictionary"**
- Tap **"Get Dictionary from Input"**
- Leave all settings as default

---

#### 🔑 Action 3: "Get Dictionary Value" (for playlist name)
- Search for: **"Get Dictionary Value"**
- Tap it to add
- Tap where it says **"Key"**
- Type: **`playlist_name`** (exactly like that)

---

#### 💾 Action 4: "Set Variable" (save the playlist name)
- Search for: **"Set Variable"**
- Tap it to add
- Tap where it says **"Variable Name"**
- Type: **`PlaylistName`**

---

#### 🎵 Action 5: "Create Playlist"
- Search for: **"Create Playlist"**
- Tap **"Create Playlist"** (should have Music icon)
- Tap where it says the playlist name
- Tap **"Select Variable"** → choose **"PlaylistName"**

---

#### 💾 Action 6: "Set Variable" (save the new playlist)
- Search for: **"Set Variable"**
- Tap it to add
- Tap **"Variable Name"**
- Type: **`NewPlaylist`**

---

#### 🔑 Action 7: "Get Dictionary Value" (get songs list)
- Search for: **"Get Dictionary Value"**
- Tap it to add
- Tap **"Key"** → type: **`songs`**
- Tap **"Dictionary"** → Select **"Get Dictionary from Input"** (the one from step 2)

---

#### 🔄 Action 8: "Repeat with Each"
- Search for: **"Repeat"**
- Tap **"Repeat with Each"**
- This creates a loop - you'll see "End Repeat" at the bottom

**IMPORTANT:** The next 4 actions go INSIDE the loop (between "Repeat" and "End Repeat")

---

#### 🔑 Action 9: "Get Dictionary Value" (INSIDE loop - get song search query)
- Search for: **"Get Dictionary Value"**
- Tap it to add (make sure it's INSIDE the Repeat block)
- Tap **"Key"** → type: **`search_query`**
- Tap **"Dictionary"** → Select **"Repeat Item"**

---

#### 🔍 Action 10: "Search" (INSIDE loop - search for song)
- Search for: **"Search"**
- Choose the one that says **"Search Apple Music"** or **"Search Music"**
- Tap where it says what to search for
- Select **"Get Dictionary Value"** (the previous action)
- Make sure **App** is set to **Music**

---

#### 📋 Action 11: "Get Item from List" (INSIDE loop - get first result)
- Search for: **"Get Item from List"**
- Tap it to add (still inside the loop)
- Tap **"First Item"** to make sure it says "First Item"

---

#### ➕ Action 12: "Add to Playlist" (INSIDE loop - add the song)
- Search for: **"Add to Playlist"** or **"Add Music to Playlist"**
- Tap it to add (still inside the loop)
- Tap where it says which playlist
- Select **Variable** → **"NewPlaylist"**

---

#### 🔔 Action 13: "Show Notification" (OUTSIDE loop)
- Drag this action BELOW "End Repeat" (outside the loop)
- Search for: **"Show Notification"**
- Tap it to add
- Tap the notification text
- Type: **"Playlist created!"**

---

### Step 3: Save the Shortcut
- Tap the shortcut name at the top
- Rename it to: **"Create Playlist from JSON"**
- Tap **Done** (top right)

---

## Part 3: Run the Shortcut

1. Open **Shortcuts** app
2. Tap **"Create Playlist from JSON"**
3. Select the `.json` file you saved earlier
4. Wait 1-2 minutes (you'll see it searching for songs)
5. You'll get a notification when it's done!

---

## Check Your Playlist

- Open **Apple Music** on your iPhone
- Go to **Library** → **Playlists**
- Your new playlist should be there!
- On Windows, open Apple Music - it will sync via iCloud (might take a few minutes)

---

## Troubleshooting

### "Can't find [Action Name]"
- Make sure you're typing the exact action name
- Some actions might be under different categories
- Try searching just the first word (e.g., just "Search" instead of "Search Music")

### "Shortcut runs but playlist is empty"
- Make sure actions 9-12 are INSIDE the "Repeat with Each" loop
- Check that you selected the "NewPlaylist" variable in action 12

### "Songs not found"
- Songs might not be available in your region
- Try searching for one song manually in Apple Music first to verify

### "Playlist doesn't appear on Windows"
- Check Settings → Music → Sync Library is ON (on iPhone)
- Sign in with same Apple ID on both devices
- Wait 5-10 minutes for iCloud sync
- Try force-quitting and reopening Apple Music on Windows

---

## Need Help?

If you get stuck, take a screenshot of your shortcut and I can help debug!
