# Smart Rename

Automatically renames image files with descriptive names using local AI — fully private, no internet required, runs in your system tray.

**Before → After**
```
screenshot_48392.png  →  boy_band_singer_posing.png
IMG_20240531.jpg      →  red_race_car_on_track.jpg
download (1).webp     →  golden_retriever_in_grass.webp
```

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed
- The `llava` vision model

---

## Setup

### 1. Install Ollama

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```
**Windows:** Download the installer at [ollama.com](https://ollama.com)

### 2. Pull the llava model
```bash
ollama pull llava
```

### 3. Clone this repo
```bash
git clone https://github.com/YOUR_USERNAME/smart-rename.git
cd smart-rename
```

### 4. Install Python dependencies
```bash
pip install -r requirements.txt
```

---

## Usage

### Step 1 — Start Ollama

**Linux:**
```bash
ollama serve &
```
**Windows:** Ollama starts automatically in the system tray after installation.

### Step 2 — Run Smart Rename
```bash
python watcher.py
```

A green dot appears in your system tray. Drop any image into a watched folder and it gets renamed within a couple of seconds.

**Right-click the tray icon** to:
- Pause / Resume
- Open Settings & Log
- Quit

**Settings window** lets you add or remove watched folders. Your choices are saved automatically.

---

## Default watched folders

On first run, Smart Rename watches whichever of these exist on your system:

| Linux | Windows |
|---|---|
| `~/Downloads` | `C:\Users\YOU\Downloads` |
| `~/Pictures/Screenshots` | `C:\Users\YOU\Pictures\Screenshots` |
| `~/Pictures` | `C:\Users\YOU\Pictures` |

You can add or remove any folder from the Settings window.

---

## Notes

- Works on **Linux** and **Windows**
- Supports `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.tiff`
- `.webp` files are automatically converted before sending to the AI
- Waits for downloads to fully finish before processing
- Will never overwrite an existing file
- Settings saved to `~/.smart-rename-config.json`

---

## Troubleshooting

**Nothing is renaming** — make sure Ollama is running (`ollama serve`) and the llava model is pulled (`ollama pull llava`).

**Tray icon doesn't appear on Linux** — install `libappindicator`: `sudo pacman -S libappindicator-gtk3` (Arch) or `sudo apt install libappindicator3-1` (Ubuntu).

**Slow on first image after startup** — llava loads into VRAM on first use. Every image after that is fast (~1–2s).
