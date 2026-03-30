# AI-Enhanced ROM Editor for Pokémon Mystery Dungeon: Explorers of Sky

A cross-platform (Windows & Linux) ROM editing tool for **Pokémon Mystery Dungeon: Explorers of Sky** (NDS), enhanced with AI-powered balance suggestions.

![Python](https://img.shields.io/badge/python-3.9+-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-green)

---

## Features

| Feature | Description |
|---------|-------------|
| 🎮 **ROM loading** | Open and save NDS ROM files (US `YOTE`, EU `YOTJ`, JP `YOTK`) |
| 🐾 **Pokémon Stats Editor** | Edit base HP, Attack, Sp. Atk, Defense, Sp. Def, Speed, types, abilities, EXP group |
| ⚔️ **Move Editor** | Edit move type, category, base power, accuracy, PP, target, range |
| 🏰 **Dungeon Editor** | Edit floor count, weather, darkness, item density, trap density, Kecleon shop chance, and more |
| 🤖 **AI Suggestions** | Get balance recommendations powered by OpenAI (requires API key) or a built-in rule-based engine |
| 🔍 **Search** | Quickly find any Pokémon, move, or dungeon by name |

---

## Requirements

- Python 3.9 or newer
- tkinter (bundled with most Python distributions)
- Optional: `openai` Python package for AI suggestions via OpenAI

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
- Edit types, abilities, and base stats using the spinboxes and dropdowns
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
