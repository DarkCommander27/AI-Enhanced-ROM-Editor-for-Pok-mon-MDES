# AI-Enhanced ROM Editor for Pokémon Mystery Dungeon: Explorers of Sky

A cross-platform (Windows & Linux) ROM editing tool for **Pokémon Mystery Dungeon: Explorers of Sky** (NDS), enhanced with AI-powered balance suggestions.

![Python](https://img.shields.io/badge/python-3.9+-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-green)

---

## Features

| Feature | Description |
|---------|-------------|
| 🎮 **ROM loading** | Open and save NDS ROM files (US `YOTE`, EU `YOTJ`, JP `YOTK`) |
| 🐾 **Pokémon Data Editor** | Edit base stats, types, abilities, EXP group, recruit rates, and evolution fields |
| ⚔️ **Move Editor** | Edit move type, category, base power, accuracy, PP, target, range |
| 🏰 **Dungeon Editor** | Edit dungeon parameters and create custom dungeons by cloning existing entries |
| 📘 **Movepool Editor (Experimental)** | Edit WAZA pointer-table level-up movepools/learnsets with size-safe writing |
| 📝 **Text (Raw) Editor** | Edit text-like ROM files (e.g. `/MESSAGE/*`) in size-preserving safe mode |
| ✅ **Validation Warnings** | Detect suspicious values (very high BST/power, invalid ranges, extreme floor counts) before saving |
| 🤖 **AI Suggestions** | Get balance recommendations powered by OpenAI (requires API key) or a built-in rule-based engine |
| 🔍 **Search** | Quickly find any Pokémon, move, or dungeon by name |

---

## Requirements

- Python 3.9 or newer
- tkinter (bundled with most Python distributions)
- Optional: `openai` Python package for AI suggestions via OpenAI

### Linux note

Some Linux Python installs do not ship `tkinter` by default. If launching the app fails with
`ModuleNotFoundError: No module named 'tkinter'`, install your distro package first:

- Debian/Ubuntu: `sudo apt update && sudo apt install -y python3-tk`
- Fedora: `sudo dnf install -y python3-tkinter`
- Arch: `sudo pacman -S tk`

```
pip install -r requirements.txt
```

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/DarkCommander27/AI-Enhanced-ROM-Editor-for-Pok-mon-MDES.git
cd AI-Enhanced-ROM-Editor-for-Pok-mon-MDES

# Install dependencies
pip install -r requirements.txt

# Launch the editor
python main.py
```

---

## Usage

### Opening a ROM

1. Click **File → Open ROM…** or press `Ctrl+O`
2. Select your `*.nds` ROM file (Explorers of Sky US/EU/JP)
3. The editor loads Pokémon stats, move data, and dungeon parameters automatically

### Editing Pokémon Stats

- Select a Pokémon from the left list (use the search box to filter)
- Edit types, abilities, base stats, recruit rates, and evolution fields using the spinboxes and dropdowns
- The **BST** (Base Stat Total) updates live
- Click **Apply Changes** to confirm your edits

### Editing Moves

- Select a move from the left list
- Adjust type, category, base power, accuracy, and PP
- Click **Apply Changes**

### Editing Dungeons

- Select a dungeon from the left list
- Edit floor count, weather, darkness, and spawn/item parameters
- Click **Apply Changes**

### Editing Movepools / Learnsets (Experimental)

- Open the **Movepools (Learnsets)** tab
- Select a Pokémon and edit lines as `move_id,level`
- Click **Apply Learnset**
- Optional: enable **Auto-fit repack on save** to allow encoded list sizes to change
- Save is size-safe: if encoded learnset byte sizes would change, the write is rejected and original data is restored
- With auto-fit enabled, the editor repacks learnset segments and rewrites pointer-table offsets
- If repacked data would overflow the available region, save is rejected and original data is restored

### Editing Text (Raw Mode)

- Open the **Text (Raw)** tab
- Select a text-like file from the left list (supports search)
- Edit content and click **Apply to File**
- Safe mode keeps the file byte size unchanged (shorter text is zero-padded; longer text is rejected)

### AI Suggestions

Each editor tab has an **AI panel** on the right:

1. Select an entry (Pokémon / Move / Dungeon)
2. Click **Get AI Suggestion**
3. The AI analyses the entry and lists recommended changes
4. Select a suggestion and click **Apply Selected Suggestion** to auto-apply it

You can also type free-form questions in the **Ask a question** box.

#### Configuring OpenAI

Go to **Help → Configure OpenAI API Key…** and paste your key.  
Alternatively set the `OPENAI_API_KEY` environment variable before launching.

Without an API key the built-in **rule-based engine** provides useful suggestions
for obvious balance issues (e.g. HP > 200, power > 200, too many floors).

### Saving

- **File → Save ROM** (`Ctrl+S`) — overwrites the original file
- **File → Save ROM As…** (`Ctrl+Shift+S`) — saves to a new path

### Validation Warnings

- Open the **Validation** tab to review warnings across Pokémon, moves, and dungeons
- Click **Refresh Warnings** after major edits
- Use it as a safety pass before saving your ROM

---

## Project Structure

```
rom_editor/
├── __init__.py          # Package metadata
├── __main__.py          # Entry point
├── nds/
│   ├── rom.py           # NDS ROM loading / saving / FAT+FNT parsing
│   └── narc.py          # NARC archive parsing and repacking
├── games/
│   └── explorers_sky/
│       ├── constants.py # Pokémon/move/dungeon/type/ability name lists
│       ├── pokemon.py   # Pokémon base-stats data model
│       ├── moves.py     # Move data model
│       └── dungeons.py  # Dungeon parameter data model
├── ai/
│   └── assistant.py     # AI suggestion engine (OpenAI + rule-based fallback)
└── ui/
    ├── app.py           # Main application window
    └── editors/
        ├── pokemon_editor.py
        ├── move_editor.py
        ├── dungeon_editor.py
        └── ai_panel.py
tests/
├── test_narc.py
├── test_nds_header.py
├── test_pokemon.py
├── test_moves.py
└── test_ai.py
```

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Build Windows EXE

You can package this app for Windows with PyInstaller.

### Local build on Windows

From the repository root in PowerShell:

```powershell
./scripts/build_windows.ps1
```

Or from Command Prompt:

```bat
scripts\build_windows.bat
```

Output:

- `dist/MDES-ROM-Editor.exe`

Build polish included by default:

- Windows version metadata from `scripts/windows_version_info.txt`
- Optional app icon from `assets/app.ico` (if present)

If you want a custom icon, create `assets/app.ico` before running the build script.

### Build on GitHub Actions

A workflow is included at `.github/workflows/build-windows-exe.yml`.

1. Open **Actions** in GitHub
2. Run workflow **Build Windows EXE**
3. Download artifact `MDES-ROM-Editor-windows`

---

## Game Compatibility

| Version | Game Code | Status |
|---------|-----------|--------|
| US      | `YOTE`    | ✅ Primary target |
| EU      | `YOTJ`    | ✅ Supported |
| JP      | `YOTK`    | ✅ Supported |

> **Note:** Editing data outside the known NARC file paths will show a warning.
> The editor will not prevent you from loading other NDS ROMs but data may not
> display correctly.

---

## License

MIT
