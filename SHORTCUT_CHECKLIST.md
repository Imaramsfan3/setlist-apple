# iOS Shortcut Checklist

Use this to verify your shortcut is set up correctly!

---

## Visual Structure Check

Your shortcut should look like this:

```
1. Select File
2. Get Dictionary from Input
3. Get Dictionary Value (Key: playlist_name)
4. Set Variable (PlaylistName)
5. Create Playlist (using PlaylistName variable)
6. Set Variable (NewPlaylist)
7. Get Dictionary Value (Key: songs, Dictionary: Get Dictionary from Input)
8. Repeat with Each (Loop starts here)
   ├─ 9. Get Dictionary Value (Key: search_query, Dictionary: Repeat Item)
   ├─ 10. Search Music (search for: previous result)
   ├─ 11. Get Item from List (First Item)
   └─ 12. Add to Playlist (Playlist: NewPlaylist variable)
   End Repeat (Loop ends here)
13. Show Notification ("Playlist created!")
```

---

## Quick Checks

### ✅ Action 3 Settings:
- [ ] Key is set to: **playlist_name** (all lowercase, underscore)

### ✅ Action 4 Settings:
- [ ] Variable name is: **PlaylistName** (no spaces)

### ✅ Action 5 Settings:
- [ ] Playlist name is set to the **PlaylistName** variable (not typed text)
- [ ] Should show: "📄 PlaylistName" (with a document icon)

### ✅ Action 6 Settings:
- [ ] Variable name is: **NewPlaylist** (no spaces)

### ✅ Action 7 Settings:
- [ ] Key is set to: **songs** (all lowercase)
- [ ] Dictionary is set to: **Get Dictionary from Input** (from action 2)

### ✅ Actions 9-12 are INSIDE the loop:
- [ ] They should be indented/inside the "Repeat with Each" block
- [ ] You should see them between "Repeat with Each" and "End Repeat"

### ✅ Action 9 Settings (INSIDE loop):
- [ ] Key is set to: **search_query** (all lowercase, underscore)
- [ ] Dictionary is set to: **Repeat Item** (not Get Dictionary from Input)

### ✅ Action 10 Settings (INSIDE loop):
- [ ] Search for is set to the previous "Get Dictionary Value" result
- [ ] App is set to: **Music**

### ✅ Action 11 Settings (INSIDE loop):
- [ ] Get is set to: **First Item**

### ✅ Action 12 Settings (INSIDE loop):
- [ ] Playlist is set to: **NewPlaylist** variable
- [ ] Should show: "📄 NewPlaylist" (with a document icon)

### ✅ Action 13 is OUTSIDE the loop:
- [ ] Should be below "End Repeat"
- [ ] Should not be indented inside the loop

---

## Common Mistakes

### ❌ Wrong: Actions 9-12 are outside the loop
**Fix:** Drag them into the "Repeat with Each" block

### ❌ Wrong: Action 12 uses typed playlist name instead of variable
**Fix:** Tap the playlist name → Select Variable → Choose "NewPlaylist"

### ❌ Wrong: Action 7 Dictionary is set to "Repeat Item"
**Fix:** Tap Dictionary → Select "Get Dictionary from Input"

### ❌ Wrong: Action 9 Dictionary is set to "Get Dictionary from Input"
**Fix:** Tap Dictionary → Select "Repeat Item"

---

## Test Your Shortcut

### Quick Test with Sample JSON:

Create a file called `test.json` with this content:

```json
{
  "playlist_name": "Test Playlist",
  "song_count": 2,
  "songs": [
    {
      "title": "Love Story",
      "artist": "Taylor Swift",
      "search_query": "Love Story Taylor Swift"
    },
    {
      "title": "Shape of You",
      "artist": "Ed Sheeran",
      "search_query": "Shape of You Ed Sheeran"
    }
  ]
}
```

1. Save this to your iPhone (Files app)
2. Run your shortcut
3. Select the test.json file
4. If it works, you'll get a playlist with those 2 songs!

---

## Still Not Working?

Take a screenshot of your shortcut (showing all the actions) and send it to me!
