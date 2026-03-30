"""Main application window for the AI-Enhanced ROM Editor."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Optional

from rom_editor.nds.rom import NDSRom
from rom_editor.nds.narc import NARC
from rom_editor.games.explorers_sky.constants import (
    GAME_CODES, POKEMON_DATA_NARC, MOVE_DATA_NARC, DUNGEON_DATA_NARC,
)
from rom_editor.games.explorers_sky.pokemon import PokemonTable
from rom_editor.games.explorers_sky.moves import MoveTable
from rom_editor.games.explorers_sky.dungeons import DungeonTable
from rom_editor.ai.assistant import AIAssistant
from rom_editor.ui.editors.pokemon_editor import PokemonEditorTab
from rom_editor.ui.editors.move_editor import MoveEditorTab
from rom_editor.ui.editors.dungeon_editor import DungeonEditorTab
from rom_editor.ui.editors.ai_panel import AIPanel


APP_TITLE = "AI-Enhanced ROM Editor — Pokémon Mystery Dungeon: Explorers of Sky"
WINDOW_SIZE = "1100x700"


class ROMEditorApp(tk.Tk):
    """The main application window.

    The application window hosts a menu bar and a tabbed notebook containing:
     - Pokémon Stats editor
     - Move editor
     - Dungeon editor
     - AI Assistant panel
    """

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(900, 600)

        self._rom: Optional[NDSRom] = None
        self._pokemon_table: Optional[PokemonTable] = None
        self._move_table: Optional[MoveTable] = None
        self._dungeon_table: Optional[DungeonTable] = None
        self._assistant = AIAssistant()
        self._modified = False

        self._build_menu()
        self._build_toolbar()
        self._build_notebook()
        self._build_statusbar()

        self._update_ui_state()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Open ROM…", accelerator="Ctrl+O",
                              command=self._open_rom)
        file_menu.add_command(label="Save ROM", accelerator="Ctrl+S",
                              command=self._save_rom)
        file_menu.add_command(label="Save ROM As…", accelerator="Ctrl+Shift+S",
                              command=self._save_rom_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.bind("<Control-o>", lambda _e: self._open_rom())
        self.bind("<Control-s>", lambda _e: self._save_rom())
        self.bind("<Control-S>", lambda _e: self._save_rom_as())

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="Reload from ROM",
                              command=self._reload_from_rom)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Configure OpenAI API Key…",
                              command=self._configure_api_key)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, relief="groove")
        bar.pack(side="top", fill="x")

        ttk.Button(bar, text="Open ROM", command=self._open_rom).pack(
            side="left", padx=2, pady=2)
        ttk.Button(bar, text="Save ROM", command=self._save_rom).pack(
            side="left", padx=2, pady=2)

        self._rom_label = ttk.Label(bar, text="No ROM loaded", foreground="grey")
        self._rom_label.pack(side="left", padx=12)

    def _build_notebook(self) -> None:
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=4, pady=4)

        # Pokemon tab
        pokemon_outer = ttk.Frame(self._notebook)
        pokemon_outer.pack(fill="both", expand=True)
        pokemon_outer.columnconfigure(0, weight=3)
        pokemon_outer.columnconfigure(1, weight=1)
        pokemon_outer.rowconfigure(0, weight=1)

        self._pokemon_editor = PokemonEditorTab(
            self._notebook, on_modified=self._on_data_modified
        )
        self._pokemon_editor.grid(row=0, column=0, sticky="nsew", in_=pokemon_outer)

        self._pokemon_ai = AIPanel(
            pokemon_outer,
            assistant=self._assistant,
            on_apply_suggestion=self._apply_pokemon_suggestion,
        )
        self._pokemon_ai.grid(row=0, column=1, sticky="nsew")
        self._notebook.add(pokemon_outer, text="Pokémon Stats")

        # Sync AI panel when selection changes in Pokémon editor
        self._pokemon_editor._listbox.bind(
            "<<ListboxSelect>>",
            lambda _e: self._sync_pokemon_ai(),
        )

        # Move tab
        move_outer = ttk.Frame(self._notebook)
        move_outer.pack(fill="both", expand=True)
        move_outer.columnconfigure(0, weight=3)
        move_outer.columnconfigure(1, weight=1)
        move_outer.rowconfigure(0, weight=1)

        self._move_editor = MoveEditorTab(
            self._notebook, on_modified=self._on_data_modified
        )
        self._move_editor.grid(row=0, column=0, sticky="nsew", in_=move_outer)

        self._move_ai = AIPanel(
            move_outer,
            assistant=self._assistant,
            on_apply_suggestion=self._apply_move_suggestion,
        )
        self._move_ai.grid(row=0, column=1, sticky="nsew")
        self._notebook.add(move_outer, text="Moves")

        self._move_editor._listbox.bind(
            "<<ListboxSelect>>",
            lambda _e: self._sync_move_ai(),
        )

        # Dungeon tab
        dungeon_outer = ttk.Frame(self._notebook)
        dungeon_outer.pack(fill="both", expand=True)
        dungeon_outer.columnconfigure(0, weight=3)
        dungeon_outer.columnconfigure(1, weight=1)
        dungeon_outer.rowconfigure(0, weight=1)

        self._dungeon_editor = DungeonEditorTab(
            self._notebook, on_modified=self._on_data_modified
        )
        self._dungeon_editor.grid(row=0, column=0, sticky="nsew", in_=dungeon_outer)

        self._dungeon_ai = AIPanel(
            dungeon_outer,
            assistant=self._assistant,
            on_apply_suggestion=self._apply_dungeon_suggestion,
        )
        self._dungeon_ai.grid(row=0, column=1, sticky="nsew")
        self._notebook.add(dungeon_outer, text="Dungeons")

        self._dungeon_editor._listbox.bind(
            "<<ListboxSelect>>",
            lambda _e: self._sync_dungeon_ai(),
        )

        # Standalone AI chat tab
        self._ai_chat_panel = AIPanel(self._notebook, assistant=self._assistant)
        self._notebook.add(self._ai_chat_panel, text="AI Assistant")

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self, relief="sunken")
        bar.pack(side="bottom", fill="x")
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(bar, textvariable=self._status_var, anchor="w").pack(
            side="left", padx=6, pady=2)

    # ------------------------------------------------------------------
    # ROM operations
    # ------------------------------------------------------------------

    def _open_rom(self) -> None:
        path = filedialog.askopenfilename(
            title="Open NDS ROM",
            filetypes=[("NDS ROM", "*.nds"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self._status("Loading ROM…")
            self.update_idletasks()
            rom = NDSRom.load(path)
            if rom.header.game_code not in GAME_CODES:
                ok = messagebox.askyesno(
                    "Unknown ROM",
                    f"Game code '{rom.header.game_code}' is not a known "
                    f"Explorers of Sky code ({', '.join(sorted(GAME_CODES))}).\n\n"
                    "The editor may not display data correctly.\n\n"
                    "Continue anyway?",
                )
                if not ok:
                    self._status("Load cancelled.")
                    return
            self._rom = rom
            self._load_game_data()
            self._modified = False
            self._rom_label.configure(
                text=f"{Path(path).name}  [{rom.header.game_code}]",
                foreground="black",
            )
            self._status(f"Loaded: {path}")
        except Exception as exc:
            messagebox.showerror("Error opening ROM", str(exc))
            self._status(f"Error: {exc}")
        self._update_ui_state()

    def _load_game_data(self) -> None:
        assert self._rom is not None
        rom = self._rom

        # Pokémon data
        if rom.has_file(POKEMON_DATA_NARC):
            narc = NARC.from_bytes(rom.read_file(POKEMON_DATA_NARC))
            self._pokemon_table = PokemonTable.from_narc(narc)
            self._pokemon_editor.load_table(self._pokemon_table)
        else:
            self._pokemon_table = None
            self._status("Warning: Pokémon data NARC not found in ROM")

        # Move data
        if rom.has_file(MOVE_DATA_NARC):
            narc = NARC.from_bytes(rom.read_file(MOVE_DATA_NARC))
            self._move_table = MoveTable.from_narc(narc)
            self._move_editor.load_table(self._move_table)
        else:
            self._move_table = None

        # Dungeon data
        if rom.has_file(DUNGEON_DATA_NARC):
            narc = NARC.from_bytes(rom.read_file(DUNGEON_DATA_NARC))
            self._dungeon_table = DungeonTable.from_narc(narc)
            self._dungeon_editor.load_table(self._dungeon_table)
        else:
            self._dungeon_table = None

    def _save_rom(self) -> None:
        if self._rom is None:
            return
        self._write_game_data_to_rom()
        self._rom.save()
        self._modified = False
        self._status(f"Saved: {self._rom.path}")

    def _save_rom_as(self) -> None:
        if self._rom is None:
            return
        path = filedialog.asksaveasfilename(
            title="Save ROM As",
            defaultextension=".nds",
            filetypes=[("NDS ROM", "*.nds"), ("All files", "*.*")],
        )
        if not path:
            return
        self._write_game_data_to_rom()
        self._rom.save(path)
        self._modified = False
        self._status(f"Saved as: {path}")

    def _write_game_data_to_rom(self) -> None:
        assert self._rom is not None
        rom = self._rom

        if self._pokemon_table and rom.has_file(POKEMON_DATA_NARC):
            narc = NARC.from_bytes(rom.read_file(POKEMON_DATA_NARC))
            self._pokemon_table.write_to_narc(narc)
            rom.write_file(POKEMON_DATA_NARC, narc.to_bytes())

        if self._move_table and rom.has_file(MOVE_DATA_NARC):
            narc = NARC.from_bytes(rom.read_file(MOVE_DATA_NARC))
            self._move_table.write_to_narc(narc)
            rom.write_file(MOVE_DATA_NARC, narc.to_bytes())

        if self._dungeon_table and rom.has_file(DUNGEON_DATA_NARC):
            narc = NARC.from_bytes(rom.read_file(DUNGEON_DATA_NARC))
            self._dungeon_table.write_to_narc(narc)
            rom.write_file(DUNGEON_DATA_NARC, narc.to_bytes())

    def _reload_from_rom(self) -> None:
        if self._rom is None:
            return
        if self._modified:
            ok = messagebox.askyesno(
                "Reload",
                "Unsaved changes will be lost. Continue?",
            )
            if not ok:
                return
        self._load_game_data()
        self._modified = False
        self._status("Reloaded data from ROM.")

    # ------------------------------------------------------------------
    # UI state helpers
    # ------------------------------------------------------------------

    def _update_ui_state(self) -> None:
        rom_loaded = self._rom is not None
        state = "normal" if rom_loaded else "disabled"
        # The notebook tabs should be visually accessible even without a ROM
        # (they just show empty lists).  Only save operations are restricted.

    def _on_data_modified(self) -> None:
        self._modified = True
        self._status("Modified (unsaved changes)")

    def _status(self, msg: str) -> None:
        self._status_var.set(msg)

    # ------------------------------------------------------------------
    # AI integration helpers
    # ------------------------------------------------------------------

    def _sync_pokemon_ai(self) -> None:
        entry = self._pokemon_editor.get_current_entry()
        if entry:
            self._pokemon_ai.set_entry(entry)

    def _sync_move_ai(self) -> None:
        entry = self._move_editor.get_current_entry()
        if entry:
            self._move_ai.set_entry(entry)

    def _sync_dungeon_ai(self) -> None:
        entry = self._dungeon_editor.get_current_entry()
        if entry:
            self._dungeon_ai.set_entry(entry)

    def _apply_pokemon_suggestion(self, suggestion) -> None:
        entry = self._pokemon_editor.get_current_entry()
        if entry is None:
            return
        field = suggestion.field
        if hasattr(entry, field):
            old = getattr(entry, field)
            setattr(entry, field, int(suggestion.new_value))
            self._pokemon_editor._populate_fields(entry)
            self._on_data_modified()
            self._status(f"Applied: {entry.name}.{field} {old} → {suggestion.new_value}")

    def _apply_move_suggestion(self, suggestion) -> None:
        entry = self._move_editor.get_current_entry()
        if entry is None:
            return
        field = suggestion.field
        if hasattr(entry, field):
            old = getattr(entry, field)
            setattr(entry, field, int(suggestion.new_value))
            self._move_editor._populate(entry)
            self._on_data_modified()
            self._status(f"Applied: {entry.name}.{field} {old} → {suggestion.new_value}")

    def _apply_dungeon_suggestion(self, suggestion) -> None:
        entry = self._dungeon_editor.get_current_entry()
        if entry is None:
            return
        field = suggestion.field
        if hasattr(entry, field):
            old = getattr(entry, field)
            setattr(entry, field, int(suggestion.new_value))
            self._dungeon_editor._populate(entry)
            self._on_data_modified()
            self._status(f"Applied: {entry.name}.{field} {old} → {suggestion.new_value}")

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _configure_api_key(self) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("Configure OpenAI API Key")
        dlg.grab_set()
        dlg.resizable(False, False)

        ttk.Label(dlg, text="OpenAI API Key:").grid(
            row=0, column=0, sticky="e", padx=8, pady=8)

        var = tk.StringVar(value=self._assistant._api_key)
        entry = ttk.Entry(dlg, textvariable=var, width=50, show="*")
        entry.grid(row=0, column=1, padx=8, pady=8)

        show_var = tk.BooleanVar()
        ttk.Checkbutton(
            dlg, text="Show key", variable=show_var,
            command=lambda: entry.configure(show="" if show_var.get() else "*"),
        ).grid(row=1, column=1, sticky="w", padx=8)

        def save():
            self._assistant._api_key = var.get().strip()
            os.environ["OPENAI_API_KEY"] = self._assistant._api_key
            dlg.destroy()

        ttk.Button(dlg, text="Save", command=save).grid(
            row=2, column=0, columnspan=2, pady=8)

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About",
            "AI-Enhanced ROM Editor\n"
            "Pokémon Mystery Dungeon: Explorers of Sky\n\n"
            "Version 0.1.0\n\n"
            "Supports editing Pokémon base stats, move data, and dungeon\n"
            "parameters in the US, EU, and JP versions of the game.\n\n"
            "AI suggestions are powered by OpenAI (requires API key) or\n"
            "fall back to a built-in rule-based system.",
        )

    def _on_exit(self) -> None:
        if self._modified:
            ok = messagebox.askyesno(
                "Exit",
                "You have unsaved changes. Exit anyway?",
            )
            if not ok:
                return
        self.destroy()
