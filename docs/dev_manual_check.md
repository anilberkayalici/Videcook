# Videcook — Manual Visual QA Checklist

## How to Run

```bash
python -m videcook.main
```

## What to Check

### General
- [ ] Dark theme loads correctly (not a plain default Qt look).
- [ ] Window title shows "Videcook".
- [ ] Minimum size feels usable (around 1000x650).
- [ ] Resizing the window does not break layout.

### Language Toggle
- [ ] Default language is Turkish: navigation shows "İndir / Nasıl Kullanırım? / Ayarlar".
- [ ] Clicking "EN" button switches navigation to "Download / Help / Settings".
- [ ] Clicking "TR" switches back without restarting.
- [ ] No mixed-language UI (e.g., Turkish nav with English page text).

### Download Page
- [ ] Layout has three clear cards/sections:
  - Source (URL, Cookie, Output, Quality)
  - Progress & Status (progress bar + buttons)
  - Operation Log (titled log area)
- [ ] Inputs are readable with clear borders.
- [ ] "Browse" buttons are styled as primary.
- [ ] "Download" button stands out (blue primary).
- [ ] "Cancel" button is styled as danger/secondary.
- [ ] Progress bar is visible and updates when download runs.
- [ ] Status label is centered and readable.
- [ ] Log area uses monospace font and looks like a console.

### Help Page
- [ ] Integrated inside main window (not a separate dialog).
- [ ] 7 numbered steps are clearly readable.
- [ ] Cookie warning appears in a styled callout box.
- [ ] Text is natural in Turkish, clear in English.

### Settings Page
- [ ] Shows binary status:
  - yt-dlp.exe — OK (green) or MISSING (red)
  - ffmpeg.exe — OK (green) or MISSING (red)
  - ffprobe.exe — OK (green) or MISSING (red)
- [ ] If binaries are missing, the note text explains they belong in `bin/`.
- [ ] Page does not crash.

### Cookie Safety
- [ ] Select a cookies.txt file.
- [ ] Click Download (with missing binaries is fine — just check log).
- [ ] Confirm only the **filename** (not full path) appears in the log.
- [ ] Confirm no cookie contents are ever shown.

### Missing Binaries
- [ ] With `bin/` empty, click Download after filling all fields.
- [ ] A friendly translated message should appear:
  - TR: "Gerekli yardımcı dosyalar bulunamadı..."
  - EN: "Required helper binaries not found..."
- [ ] App does not crash.
