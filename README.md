# Smart Rename

Automatically renames image files with descriptive names using local AI — fully private, no internet required, runs in your system tray.
What makes this unique compared to other similar projects is the ability to rename images downloaded in realtime.

**Before → After**
```
screenshot_48392.png  →  boy_band_singer_posing.png
IMG_20240531.jpg      →  red_race_car_on_track.jpg
download (1).webp     →  golden_retriever_in_grass.webp
```

---

## Requirements

You need to install these two things manually — everything else is handled by the setup script.

### 1. Python 3.10+

**Linux:** use your package manager
```bash
sudo pacman -S python    # Arch
sudo apt install python3 # Ubuntu/Debian
```

**Windows:** download from [python.org](https://python.org)
> ⚠️ Check **"Add Python to PATH"** during installation.

### 2. Ollama

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:** download the installer from [ollama.com](https://ollama.com)

---

## Installation

```bash
git clone https://github.com/chudweiser/smart-rename.git
cd smart-rename
```

**Linux:**
```bash
bash setup.sh
```

**Windows:** double-click `setup.bat`

The setup script will:
- Check Python and Ollama are installed
- Download the llava AI model (~4GB, one time only)
- Create a virtual environment
- Install all Python dependencies
- Create a `run.sh` / `run.bat` shortcut to launch the app

---

## Usage

**Linux:**
```bash
bash run.sh
```

**Windows:** double-click `run.bat`

A green dot appears in your system tray. Right-click it to open Settings, pause, or quit.

Drop any image into a watched folder and it gets renamed within a couple of seconds.

---

## Default watched folders

On first run, Smart Rename watches whichever of these exist:

| Linux | Windows |
|---|---|
| `~/Downloads` | `C:\Users\YOU\Downloads` |
| `~/Pictures/Screenshots` | `C:\Users\YOU\Pictures\Screenshots` |
| `~/Pictures` | `C:\Users\YOU\Pictures` |

Add or remove folders anytime from the Settings window.

---

## Supported formats

`.jpg` `.jpeg` `.png` `.gif` `.bmp` `.webp` `.tiff`

---

## Troubleshooting

**Nothing is renaming** — make sure Ollama is running. The setup script starts it automatically via `run.sh`/`run.bat`, but if you launched `watcher.py` directly, start Ollama first with `ollama serve`.

**Slow on first image** — llava loads into GPU memory on first use (~1–2s extra). Every image after that is fast.

**Tray icon missing on Linux** — install the appindicator library:
```bash
sudo pacman -S libappindicator-gtk3   # Arch
sudo apt install libappindicator3-1   # Ubuntu
```
