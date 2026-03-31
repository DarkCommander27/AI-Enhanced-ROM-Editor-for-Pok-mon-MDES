# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for AI-Enhanced ROM Editor (Windows EXE).

Run from the repository root:
    pyinstaller --noconfirm --clean MDES-ROM-Editor.spec

The spec handles:
- All rom_editor sub-packages (every editor tab)
- Pillow (portrait/sprite viewer)
- openai (AI Assistant panel)
- skytemple-files (portrait KAO handler, optional)
- Windows DPI-aware + visual-styles manifest
- Version metadata embedded in the EXE
- Single-file (--onefile equivalent) output
"""

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
SPEC_ROOT = os.path.abspath(SPECPATH)  # directory containing this spec file
ICON_PATH = os.path.join(SPEC_ROOT, "assets", "app.ico")
MANIFEST_PATH = os.path.join(SPEC_ROOT, "scripts", "app.manifest")
VERSION_PATH = os.path.join(SPEC_ROOT, "scripts", "windows_version_info.txt")

# ------------------------------------------------------------------
# Collect data/binary/hidden-import lists from third-party packages
# ------------------------------------------------------------------
datas = []
binaries = []
hiddenimports = []

# Pillow — sprite viewer and portrait rendering
_pil = collect_all("PIL")
datas     += _pil[0]
binaries  += _pil[1]
hiddenimports += _pil[2]

# openai — AI Assistant panel
_openai = collect_all("openai")
datas     += _openai[0]
binaries  += _openai[1]
hiddenimports += _openai[2]

# httpx / anyio / pydantic — pulled in by openai at runtime
for _pkg in ("httpx", "anyio", "pydantic", "certifi", "charset_normalizer", "idna", "sniffio"):
    try:
        _r = collect_all(_pkg)
        datas     += _r[0]
        binaries  += _r[1]
        hiddenimports += _r[2]
    except Exception:
        pass

# skytemple-files — optional; used for accurate KAO portrait handling
try:
    _sky = collect_all("skytemple_files")
    datas     += _sky[0]
    binaries  += _sky[1]
    hiddenimports += _sky[2]
    hiddenimports += collect_submodules("skytemple_files")
except Exception:
    pass

# All rom_editor sub-packages (ensures every editor tab is bundled)
hiddenimports += collect_submodules("rom_editor")

# tkinter extras that PyInstaller sometimes misses
hiddenimports += [
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.simpledialog",
    "tkinter.colorchooser",
    "tkinter.font",
    "tkinter.scrolledtext",
    "_tkinter",
]

# Explicit rom_editor module list (belt-and-suspenders)
hiddenimports += [
    "rom_editor",
    "rom_editor.__main__",
    "rom_editor.ai",
    "rom_editor.ai.assistant",
    "rom_editor.games",
    "rom_editor.games.explorers_sky",
    "rom_editor.games.explorers_sky.constants",
    "rom_editor.games.explorers_sky.pokemon",
    "rom_editor.games.explorers_sky.moves",
    "rom_editor.games.explorers_sky.dungeons",
    "rom_editor.games.explorers_sky.learnsets",
    "rom_editor.nds",
    "rom_editor.nds.rom",
    "rom_editor.nds.narc",
    "rom_editor.nds.portrait",
    "rom_editor.ui",
    "rom_editor.ui.app",
    "rom_editor.ui.history",
    "rom_editor.ui.editors",
    "rom_editor.ui.editors.pokemon_editor",
    "rom_editor.ui.editors.move_editor",
    "rom_editor.ui.editors.dungeon_editor",
    "rom_editor.ui.editors.learnset_editor",
    "rom_editor.ui.editors.text_editor",
    "rom_editor.ui.editors.ai_panel",
    "rom_editor.ui.editors.sprite_viewer",
    # Standard library extras
    "json",
    "pathlib",
    "copy",
    "dataclasses",
    "struct",
    "ctypes",
    "ctypes.wintypes",
]

# ------------------------------------------------------------------
# Analysis
# ------------------------------------------------------------------
a = Analysis(
    ["main.py"],
    pathex=[SPEC_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=list(dict.fromkeys(hiddenimports)),  # deduplicate
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy test/dev packages from the bundle
        "pytest",
        "pytest_cov",
        "_pytest",
        "setuptools",
        "pkg_resources",
        "pip",
        "wheel",
    ],
    noarchive=False,
)

# ------------------------------------------------------------------
# Archive
# ------------------------------------------------------------------
pyz = PYZ(a.pure)

# ------------------------------------------------------------------
# Executable  (onefile: binaries + datas embedded directly into EXE)
# ------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MDES-ROM-Editor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX disabled: UPX-compressed Windows EXEs often trigger antivirus false positives.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    # No console window — windowed GUI application.
    console=False,
    # Embed Windows DPI-aware + visual-styles manifest.
    manifest=MANIFEST_PATH if os.path.exists(MANIFEST_PATH) else None,
    # Embed version metadata (visible in Properties → Details).
    version=VERSION_PATH if os.path.exists(VERSION_PATH) else None,
    # Taskbar / Explorer icon.
    icon=ICON_PATH if os.path.exists(ICON_PATH) else None,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
