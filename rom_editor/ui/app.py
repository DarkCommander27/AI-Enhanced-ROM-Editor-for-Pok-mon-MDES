"""Main application window for the AI-Enhanced ROM Editor."""

from __future__ import annotations

import dataclasses
import datetime
import json
import os
import sys
import tkinter as tk
from copy import deepcopy
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Optional

from rom_editor.nds.rom import NDSRom
from rom_editor.nds.narc import NARC
from rom_editor.games.explorers_sky.constants import (
    GAME_CODES, POKEMON_DATA_NARC, MOVE_DATA_NARC, DUNGEON_DATA_NARC,
    PORTRAIT_DATA, MOVE_LEARNSET_NARC,
)
from rom_editor.games.explorers_sky.pokemon import PokemonTable
from rom_editor.games.explorers_sky.moves import MoveTable
from rom_editor.games.explorers_sky.dungeons import DungeonTable
from rom_editor.games.explorers_sky.learnsets import WazaLearnsetTable
from rom_editor.ai.assistant import AIAssistant
from rom_editor.ui.editors.pokemon_editor import PokemonEditorTab
from rom_editor.ui.editors.move_editor import MoveEditorTab
from rom_editor.ui.editors.dungeon_editor import DungeonEditorTab
from rom_editor.ui.editors.ai_panel import AIPanel
from rom_editor.ui.editors.text_editor import TextEditorTab
from rom_editor.ui.editors.learnset_editor import LearnsetEditorTab
from rom_editor.ui.history import ChangeHistory, ChangeRecord


APP_TITLE = "AI-Enhanced ROM Editor — Pokémon Mystery Dungeon: Explorers of Sky"
WINDOW_SIZE = "1100x700"
SETTINGS_FILE = Path.home() / ".ai_enhanced_rom_editor_settings.json"


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

        self._settings = self._load_settings()
        self._style = ttk.Style(self)
        self._theme_mode = tk.StringVar(
            value=self._settings.get("theme", "dark")
            if self._settings.get("theme", "dark") in {"light", "dark"}
            else "dark"
        )
        self._theme_colors: dict[str, str] = {}
        self._apply_theme(self._theme_mode.get())

        self._rom: Optional[NDSRom] = None
        self._pokemon_table: Optional[PokemonTable] = None
        self._move_table: Optional[MoveTable] = None
        self._dungeon_table: Optional[DungeonTable] = None
        self._learnset_table: Optional[WazaLearnsetTable] = None
        self._move_data_is_narc = True
        self._dungeon_data_is_narc = True
        self._assistant = AIAssistant()
        self._modified = False
        self._autosave_job: Optional[str] = None
        self._history = ChangeHistory(max_size=50)
        self._history.set_on_change(self._on_history_changed)
        self._simple_mode = tk.BooleanVar(value=False)
        self._focus_assist = tk.BooleanVar(value=False)
        self._neuro_mode = tk.BooleanVar(
            value=self._get_setting_bool("neuro_mode", default=True)
        )
        self._portrait_container = None

        self._build_menu()
        self._build_toolbar()
        self._build_guidance_bar()
        self._build_statusbar()
        self._build_changes_panel()
        self._build_notebook()

        # Start in a calmer layout by default.
        self._apply_neuro_mode(initial=True)
        self._refresh_theme_dependent_widgets()

        self._update_ui_state()

    def _apply_theme(self, mode: str) -> None:
        """Apply app theme palette and ttk/tk styling."""
        try:
            if "clam" in self._style.theme_names():
                self._style.theme_use("clam")
        except Exception:
            pass

        palettes = {
            "dark": {
                "bg": "#09090d",
                "surface": "#12121a",
                "panel": "#171725",
                "panel_soft": "#23233a",
                "panel_soft_2": "#2d2d4a",
                "text": "#f4f1ff",
                "text_muted": "#b0abd0",
                "accent": "#8b5cf6",
                "accent_active": "#a78bfa",
                "menu_bg": "#101017",
                "guide_text": "#ddd3ff",
                "warning_text": "#f4c27a",
                "status_dim": "#c3bfe1",
                "entry_fg": "#f4f1ff",
                "entry_bg": "#141421",
                "canvas_bg": "#101018",
            },
            "light": {
                "bg": "#f4f6fb",
                "surface": "#e8ecf7",
                "panel": "#ffffff",
                "panel_soft": "#d2daf0",
                "panel_soft_2": "#c3ccee",
                "text": "#1f2340",
                "text_muted": "#596089",
                "accent": "#6a4dff",
                "accent_active": "#7b63ff",
                "menu_bg": "#e8ecf7",
                "guide_text": "#4c2ec9",
                "warning_text": "#8a4f12",
                "status_dim": "#6b7398",
                "entry_fg": "#1f2340",
                "entry_bg": "#ffffff",
                "canvas_bg": "#eef2ff",
            },
        }
        colors = palettes["light" if mode == "light" else "dark"]
        self._theme_colors = colors

        bg = colors["bg"]
        surface = colors["surface"]
        panel = colors["panel"]
        panel_soft = colors["panel_soft"]
        panel_soft_2 = colors["panel_soft_2"]
        text = colors["text"]
        text_muted = colors["text_muted"]
        accent = colors["accent"]
        accent_active = colors["accent_active"]

        self.configure(bg=bg)
        base_font = ("Segoe UI", 10) if sys.platform.startswith("win") else ("TkDefaultFont", 10)
        small_font = ("Segoe UI", 9) if sys.platform.startswith("win") else ("TkDefaultFont", 9)
        heading_font = ("Segoe UI Semibold", 10) if sys.platform.startswith("win") else ("TkDefaultFont", 10, "bold")

        self._style.configure("TFrame", background=bg)
        self._style.configure("TLabel", background=bg, foreground=text)
        self._style.configure(
            "TLabelframe",
            background=bg,
            bordercolor=panel_soft_2,
            relief="flat",
            borderwidth=1,
            padding=10,
        )
        self._style.configure("TLabelframe.Label", background=bg, foreground=text)
        self._style.configure("Hint.TLabel", background=bg, foreground=colors["guide_text"])
        self._style.configure("Muted.TLabel", background=bg, foreground=text_muted)
        self._style.configure("Toolbar.TFrame", background=surface)
        self._style.configure("ToolbarGroup.TFrame", background=surface)
        self._style.configure("Guide.TFrame", background=panel)
        self._style.configure("Status.TFrame", background=surface)
        self._style.configure("Changes.TFrame", background=surface)
        self._style.configure("Panel.TFrame", background=panel)
        self._style.configure("TSeparator", background=panel_soft_2)

        self._style.configure(
            "TButton",
            padding=(14, 9),
            background=panel,
            foreground=text,
            bordercolor=panel_soft_2,
            relief="flat",
            borderwidth=1,
            lightcolor=panel,
            darkcolor=panel,
            focuscolor=accent,
        )
        self._style.map(
            "TButton",
            background=[("active", panel_soft), ("pressed", accent)],
            foreground=[("disabled", text_muted), ("!disabled", text)],
            bordercolor=[("focus", accent), ("!focus", panel_soft_2)],
        )

        self._style.configure(
            "Accent.TButton",
            padding=(16, 10),
            background=accent,
            bordercolor=accent,
            relief="flat",
        )
        self._style.map(
            "Accent.TButton",
            background=[("active", accent_active), ("!active", accent)],
            foreground=[("!disabled", "#ffffff")],
        )

        self._style.configure(
            "TCheckbutton",
            background=bg,
            foreground=text,
            padding=(4, 4),
            font=base_font,
        )
        self._style.map(
            "TCheckbutton",
            foreground=[("disabled", text_muted), ("!disabled", text)],
            indicatorcolor=[("selected", accent), ("!selected", panel_soft)],
        )

        self._style.configure(
            "TEntry",
            fieldbackground=panel,
            background=panel,
            foreground=colors["entry_fg"],
            insertcolor=accent,
            bordercolor=panel_soft_2,
            relief="flat",
            padding=7,
        )
        self._style.map(
            "TEntry",
            bordercolor=[("focus", accent), ("!focus", panel_soft_2)],
        )

        self._style.configure(
            "TCombobox",
            fieldbackground=panel,
            background=panel,
            foreground=colors["entry_fg"],
            arrowcolor=text,
            bordercolor=panel_soft_2,
            relief="flat",
            padding=6,
        )
        self._style.map(
            "TCombobox",
            fieldbackground=[("readonly", panel), ("focus", panel_soft)],
            bordercolor=[("focus", accent), ("!focus", panel_soft_2)],
        )

        self._style.configure(
            "TSpinbox",
            fieldbackground=panel,
            background=panel,
            foreground=colors["entry_fg"],
            arrowcolor=text,
            bordercolor=panel_soft_2,
            relief="flat",
            padding=4,
        )
        self._style.map(
            "TSpinbox",
            fieldbackground=[("focus", panel_soft), ("!focus", panel)],
            bordercolor=[("focus", accent), ("!focus", panel_soft_2)],
        )

        self._style.configure(
            "Treeview",
            background=panel,
            fieldbackground=panel,
            foreground=text,
            bordercolor=panel_soft_2,
            rowheight=28,
        )
        self._style.map(
            "Treeview",
            background=[("selected", accent)],
            foreground=[("selected", "#ffffff")],
        )
        self._style.configure(
            "Treeview.Heading",
            background=panel_soft,
            foreground=text,
            bordercolor=panel_soft_2,
            relief="flat",
            padding=(8, 8),
            font=heading_font,
        )

        self._style.configure("TNotebook", background=bg, borderwidth=0)
        self._style.configure(
            "TNotebook.Tab",
            padding=(16, 10),
            background=surface,
            foreground=text_muted,
            font=base_font,
        )
        self._style.map(
            "TNotebook.Tab",
            background=[("selected", panel_soft), ("active", panel)],
            foreground=[("selected", "#ffffff"), ("active", text)],
        )

        self._style.configure(
            "TScrollbar",
            background=panel_soft,
            troughcolor=surface,
            arrowcolor=text,
            bordercolor=surface,
        )

        self.option_add("*Font", base_font)
        self.option_add("*Menu.font", base_font)
        self.option_add("*Listbox.font", base_font)
        self.option_add("*Listbox.background", colors["entry_bg"])
        self.option_add("*Listbox.foreground", colors["entry_fg"])
        self.option_add("*Listbox.selectBackground", accent)
        self.option_add("*Listbox.selectForeground", "#ffffff")
        self.option_add("*Listbox.highlightBackground", panel_soft_2)
        self.option_add("*Listbox.highlightColor", accent)
        self.option_add("*Listbox.borderWidth", 0)

        self.option_add("*Text.background", colors["entry_bg"])
        self.option_add("*Text.foreground", colors["entry_fg"])
        self.option_add("*Text.insertBackground", accent)
        self.option_add("*Text.selectBackground", accent)
        self.option_add("*Text.selectForeground", "#ffffff")
        self.option_add("*Text.highlightBackground", panel_soft_2)
        self.option_add("*Text.highlightColor", accent)
        self.option_add("*Text.font", small_font)

        self._apply_menu_theme()

    def _apply_menu_theme(self) -> None:
        """Update menu colors if menus have already been built."""
        if not hasattr(self, "_menubar"):
            return
        menu_bg = self._theme_colors["menu_bg"]
        text = self._theme_colors["text"]
        accent = self._theme_colors["accent"]
        for menu in (
            self._menubar,
            getattr(self, "_file_menu", None),
            getattr(self, "_edit_menu", None),
            getattr(self, "_settings_menu", None),
            getattr(self, "_help_menu", None),
            getattr(self, "_theme_submenu", None),
        ):
            if menu is None:
                continue
            menu.configure(
                bg=menu_bg,
                fg=text,
                activebackground=accent,
                activeforeground="#ffffff",
            )

    def _refresh_theme_dependent_widgets(self) -> None:
        """Refresh colors for widgets that use explicit foreground/background."""
        if not self._theme_colors:
            return
        guide_text = self._theme_colors["guide_text"]
        warning_text = self._theme_colors["warning_text"]
        panel = self._theme_colors["panel"]
        status_dim = self._theme_colors["status_dim"]

        if hasattr(self, "_rom_label"):
            self._rom_label.configure(foreground=status_dim)
        if hasattr(self, "_guide_label"):
            self._guide_label.configure(foreground=guide_text, background=panel)
        if hasattr(self, "_validation_hint"):
            self._validation_hint.configure(foreground=warning_text)
        self._refresh_plain_tk_widgets(self)
        self._apply_menu_theme()

    def _refresh_plain_tk_widgets(self, widget: tk.Misc) -> None:
        """Apply theme colors to classic Tk widgets after creation."""
        if not self._theme_colors:
            return
        colors = self._theme_colors
        panel_soft_2 = colors["panel_soft_2"]
        accent = colors["accent"]

        for child in widget.winfo_children():
            try:
                if isinstance(child, tk.Listbox):
                    child.configure(
                        bg=colors["entry_bg"],
                        fg=colors["entry_fg"],
                        selectbackground=accent,
                        selectforeground="#ffffff",
                        highlightbackground=panel_soft_2,
                        highlightcolor=accent,
                        activestyle="none",
                        bd=0,
                        relief="flat",
                    )
                elif isinstance(child, tk.Text):
                    child.configure(
                        bg=colors["entry_bg"],
                        fg=colors["entry_fg"],
                        insertbackground=accent,
                        selectbackground=accent,
                        selectforeground="#ffffff",
                        highlightbackground=panel_soft_2,
                        highlightcolor=accent,
                        bd=0,
                        relief="flat",
                    )
                elif isinstance(child, tk.Canvas):
                    child.configure(
                        bg=colors["canvas_bg"],
                        highlightbackground=panel_soft_2,
                        highlightcolor=accent,
                    )
                else:
                    set_theme = getattr(child, "set_theme", None)
                    if callable(set_theme):
                        set_theme(colors)
            except Exception:
                pass
            self._refresh_plain_tk_widgets(child)

    def _on_theme_changed(self) -> None:
        """Apply and persist theme choice from Settings menu."""
        mode = self._theme_mode.get()
        self._settings["theme"] = mode
        self._save_settings()
        self._apply_theme(mode)
        self._refresh_theme_dependent_widgets()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _load_settings(self) -> dict:
        if not SETTINGS_FILE.exists():
            return {}
        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, dict):
                return raw
        except Exception:
            pass
        return {}

    def _save_settings(self) -> None:
        try:
            with SETTINGS_FILE.open("w", encoding="utf-8") as fh:
                json.dump(self._settings, fh, indent=2)
        except Exception:
            # Failing to save preferences should never block editing.
            self._status("Warning: Could not save editor preferences.")

    def _get_setting_bool(self, key: str, default: bool) -> bool:
        value = self._settings.get(key, default)
        return value if isinstance(value, bool) else default

    def _build_menu(self) -> None:
        self._menubar = tk.Menu(self)

        # File menu
        self._file_menu = tk.Menu(self._menubar, tearoff=False)
        self._file_menu.add_command(label="Open ROM…", accelerator="Ctrl+O",
                                    command=self._open_rom)
        self._file_menu.add_command(label="Save ROM", accelerator="Ctrl+S",
                                    command=self._save_rom)
        self._file_menu.add_command(label="Save ROM As…", accelerator="Ctrl+Shift+S",
                                    command=self._save_rom_as)
        self._file_menu.add_separator()
        self._file_menu.add_command(label="Exit", command=self._on_exit)
        self._menubar.add_cascade(label="File", menu=self._file_menu)
        self.bind("<Control-o>", lambda _e: self._open_rom())
        self.bind("<Control-s>", lambda _e: self._save_rom())
        self.bind("<Control-S>", lambda _e: self._save_rom_as())

        # Edit menu
        self._edit_menu = tk.Menu(self._menubar, tearoff=False)
        self._edit_menu.add_command(
            label="Undo", accelerator="Ctrl+Z",
            command=self._undo, state="disabled")
        self._edit_menu.add_command(
            label="Redo", accelerator="Ctrl+Y",
            command=self._redo, state="disabled")
        self._edit_menu.add_separator()
        self._edit_menu.add_command(label="Reload from ROM",
                                    command=self._reload_from_rom)
        self._menubar.add_cascade(label="Edit", menu=self._edit_menu)
        self.bind("<Control-z>", lambda _e: self._undo())
        self.bind("<Control-y>", lambda _e: self._redo())

        # Settings menu
        self._settings_menu = tk.Menu(self._menubar, tearoff=False)
        self._theme_submenu = tk.Menu(self._settings_menu, tearoff=False)
        self._theme_submenu.add_radiobutton(
            label="Dark",
            variable=self._theme_mode,
            value="dark",
            command=self._on_theme_changed,
        )
        self._theme_submenu.add_radiobutton(
            label="Light",
            variable=self._theme_mode,
            value="light",
            command=self._on_theme_changed,
        )
        self._settings_menu.add_cascade(label="Theme", menu=self._theme_submenu)
        self._menubar.add_cascade(label="Settings", menu=self._settings_menu)

        # Help menu
        self._help_menu = tk.Menu(self._menubar, tearoff=False)
        self._help_menu.add_command(label="About", command=self._show_about)
        self._help_menu.add_command(label="Configure OpenAI API Key…",
                                    command=self._configure_api_key)
        self._menubar.add_cascade(label="Help", menu=self._help_menu)

        self.config(menu=self._menubar)
        self._apply_menu_theme()

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, relief="groove", style="Toolbar.TFrame")
        bar.pack(side="top", fill="x", padx=10, pady=(10, 6))

        left = ttk.Frame(bar, style="ToolbarGroup.TFrame")
        left.pack(side="left", fill="x", expand=True, padx=8, pady=8)

        ttk.Button(left, text="Open ROM", command=self._open_rom, style="Accent.TButton").pack(
            side="left", padx=(0, 8))
        ttk.Button(left, text="Save ROM", command=self._save_rom, style="Accent.TButton").pack(
            side="left", padx=(0, 18))

        self._mode_btn = ttk.Button(left, text="Simple Mode", command=self._toggle_mode)
        self._mode_btn.pack(side="left", padx=(0, 8))

        self._neuro_btn = ttk.Button(left, text="Neuro Mode: On", command=self._toggle_neuro_mode)
        self._neuro_btn.pack(side="left", padx=(0, 8))

        self._focus_btn = ttk.Button(left, text="Focus Assist: Off", command=self._toggle_focus_assist)
        self._focus_btn.pack(side="left")

        right = ttk.Frame(bar, style="ToolbarGroup.TFrame")
        right.pack(side="right", padx=10, pady=8)
        self._rom_label = ttk.Label(right, text="No ROM loaded", style="Muted.TLabel")
        self._rom_label.pack(side="right")

    def _build_guidance_bar(self) -> None:
        """A low-pressure, step-by-step hint bar for the current workflow."""
        bar = ttk.Frame(self, relief="ridge", style="Guide.TFrame")
        bar.pack(side="top", fill="x", padx=10, pady=(0, 8))
        self._guide_var = tk.StringVar()
        self._guide_label = ttk.Label(
            bar,
            textvariable=self._guide_var,
            anchor="w",
            style="Hint.TLabel",
        )
        self._guide_label.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        self._update_guidance()

    def _build_notebook(self) -> None:
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Pokémon tab
        self._pokemon_outer = ttk.Frame(self._notebook)
        self._pokemon_outer.pack(fill="both", expand=True)
        self._pokemon_outer.columnconfigure(0, weight=3)
        self._pokemon_outer.columnconfigure(1, weight=1)
        self._pokemon_outer.rowconfigure(0, weight=1)

        self._pokemon_editor = PokemonEditorTab(
            self._notebook,
            on_modified=self._on_data_modified,
            on_change=self._on_entry_changed,
        )
        self._pokemon_editor.grid(row=0, column=0, sticky="nsew", in_=self._pokemon_outer)

        self._pokemon_ai = AIPanel(
            self._pokemon_outer,
            assistant=self._assistant,
            on_apply_suggestion=self._apply_pokemon_suggestion,
        )
        self._pokemon_ai.grid(row=0, column=1, sticky="nsew")
        self._notebook.add(self._pokemon_outer, text="Pokémon Stats")

        self._pokemon_editor._listbox.bind(
            "<<ListboxSelect>>",
            lambda _e: self._sync_pokemon_ai(),
        )

        # Move tab
        self._move_outer = ttk.Frame(self._notebook)
        self._move_outer.pack(fill="both", expand=True)
        self._move_outer.columnconfigure(0, weight=3)
        self._move_outer.columnconfigure(1, weight=1)
        self._move_outer.rowconfigure(0, weight=1)

        self._move_editor = MoveEditorTab(
            self._notebook,
            on_modified=self._on_data_modified,
            on_change=self._on_entry_changed,
        )
        self._move_editor.grid(row=0, column=0, sticky="nsew", in_=self._move_outer)

        self._move_ai = AIPanel(
            self._move_outer,
            assistant=self._assistant,
            on_apply_suggestion=self._apply_move_suggestion,
        )
        self._move_ai.grid(row=0, column=1, sticky="nsew")
        self._notebook.add(self._move_outer, text="Moves")

        self._move_editor._listbox.bind(
            "<<ListboxSelect>>",
            lambda _e: self._sync_move_ai(),
        )

        # Learnset tab (experimental)
        self._learnset_editor = LearnsetEditorTab(
            self._notebook,
            on_modified=self._on_data_modified,
        )
        self._notebook.add(self._learnset_editor, text="Movepools (Learnsets)")

        # Dungeon tab
        self._dungeon_outer = ttk.Frame(self._notebook)
        self._dungeon_outer.pack(fill="both", expand=True)
        self._dungeon_outer.columnconfigure(0, weight=3)
        self._dungeon_outer.columnconfigure(1, weight=1)
        self._dungeon_outer.rowconfigure(0, weight=1)

        self._dungeon_editor = DungeonEditorTab(
            self._notebook,
            on_modified=self._on_data_modified,
            on_change=self._on_entry_changed,
        )
        self._dungeon_editor.grid(row=0, column=0, sticky="nsew", in_=self._dungeon_outer)

        self._dungeon_ai = AIPanel(
            self._dungeon_outer,
            assistant=self._assistant,
            on_apply_suggestion=self._apply_dungeon_suggestion,
        )
        self._dungeon_ai.grid(row=0, column=1, sticky="nsew")
        self._notebook.add(self._dungeon_outer, text="Dungeons")

        self._dungeon_editor._listbox.bind(
            "<<ListboxSelect>>",
            lambda _e: self._sync_dungeon_ai(),
        )

        # Standalone AI chat tab
        self._ai_chat_panel = AIPanel(self._notebook, assistant=self._assistant)
        self._notebook.add(self._ai_chat_panel, text="AI Assistant")

        # Raw text/localization-like files (safe, size-preserving mode)
        self._text_editor = TextEditorTab(
            self._notebook,
            on_modified=self._on_data_modified,
        )
        self._notebook.add(self._text_editor, text="Text (Raw)")

        # Validation warnings tab
        self._validation_tab = ttk.Frame(self._notebook)
        self._validation_tab.columnconfigure(0, weight=1)
        self._validation_tab.rowconfigure(1, weight=1)
        top = ttk.Frame(self._validation_tab)
        top.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        self._validation_hint = ttk.Label(
            top,
            text="Warnings help catch risky values before saving.",
        )
        self._validation_hint.pack(side="left")
        ttk.Button(
            top,
            text="Refresh Warnings",
            command=self._refresh_validation_warnings,
        ).pack(side="right")

        self._validation_tree = ttk.Treeview(
            self._validation_tab,
            columns=("kind", "name", "warning"),
            show="headings",
            height=14,
        )
        self._validation_tree.heading("kind", text="Type")
        self._validation_tree.heading("name", text="Entry")
        self._validation_tree.heading("warning", text="Warning")
        self._validation_tree.column("kind", width=90, stretch=False)
        self._validation_tree.column("name", width=220, stretch=False)
        self._validation_tree.column("warning", width=620, stretch=True)
        self._validation_tree.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        self._notebook.add(self._validation_tab, text="Validation")

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self, relief="sunken", style="Status.TFrame")
        bar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(bar, textvariable=self._status_var, anchor="w").pack(
            side="left", padx=12, pady=8)

    def _build_changes_panel(self) -> None:
        """Collapsible panel at the bottom showing a log of all edits."""
        self._changes_outer = ttk.Frame(self, relief="groove", style="Changes.TFrame")
        self._changes_outer.pack(side="bottom", fill="x", padx=10, pady=(0, 8))

        header = ttk.Frame(self._changes_outer)
        header.pack(fill="x")
        self._changes_toggle_btn = ttk.Button(
            header, text="\u25be Changes (0)",
            command=self._toggle_changes_panel, width=18,
        )
        self._changes_toggle_btn.pack(side="left", padx=2, pady=1)

        self._changes_body = ttk.Frame(self._changes_outer)
        self._changes_body.pack(fill="x")

        cols = ("entity", "change")
        self._changes_tree = ttk.Treeview(
            self._changes_body, columns=cols,
            show="headings", height=4, selectmode="none",
        )
        self._changes_tree.heading("entity", text="What")
        self._changes_tree.heading("change", text="Change")
        self._changes_tree.column("entity", width=200, stretch=False)
        self._changes_tree.column("change", width=400, stretch=True)
        self._changes_tree.pack(side="left", fill="x", expand=True)

        sb = ttk.Scrollbar(
            self._changes_body, orient="vertical",
            command=self._changes_tree.yview,
        )
        self._changes_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self._changes_visible = True

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
                foreground=self._theme_colors.get("text", "black"),
            )
            self._status(f"Loaded: {path}")
            self._schedule_autosave()
            self._update_guidance()
        except Exception as exc:
            messagebox.showerror("Error opening ROM", str(exc))
            self._status(f"Error: {exc}")
        self._update_ui_state()

    def _load_game_data(self) -> None:
        assert self._rom is not None
        rom = self._rom

        # Clear history whenever new ROM data is loaded
        self._history.clear()

        # Reset portrait container
        self._portrait_container = None
        self._pokemon_editor.set_portrait_container(None)

        # Pokémon data
        if rom.has_file(POKEMON_DATA_NARC):
            pkmn_raw = rom.read_file(POKEMON_DATA_NARC)
            if pkmn_raw[:4] == b"NARC":
                narc = NARC.from_bytes(pkmn_raw)
                self._pokemon_table = PokemonTable.from_narc(narc)
            elif pkmn_raw[:4] == b"MD\x00\x00":
                self._pokemon_table = PokemonTable.from_md_bytes(pkmn_raw)
            else:
                raise ValueError(
                    f"Unsupported Pokémon data format at {POKEMON_DATA_NARC}"
                )
            self._pokemon_editor.load_table(self._pokemon_table)
        else:
            self._pokemon_table = None
            self._status("Warning: Pokémon data NARC not found in ROM")

        # Move data
        if rom.has_file(MOVE_DATA_NARC):
            move_raw = rom.read_file(MOVE_DATA_NARC)
            if move_raw[:4] == b"NARC":
                narc = NARC.from_bytes(move_raw)
                self._move_table = MoveTable.from_narc(narc)
                self._move_data_is_narc = True
                self._move_editor.load_table(self._move_table)
            else:
                # Some EoS variants store this as a flat table blob.
                self._move_table = MoveTable.from_bytes(move_raw)
                self._move_data_is_narc = False
                self._move_editor.load_table(self._move_table)
                self._status(
                    f"Loaded {MOVE_DATA_NARC} as raw move table (non-NARC format)."
                )
        else:
            self._move_table = None
            self._move_data_is_narc = True

        # Dungeon data
        if rom.has_file(DUNGEON_DATA_NARC):
            dungeon_raw = rom.read_file(DUNGEON_DATA_NARC)
            if dungeon_raw[:4] == b"NARC":
                narc = NARC.from_bytes(dungeon_raw)
                self._dungeon_table = DungeonTable.from_narc(narc)
                self._dungeon_data_is_narc = True
                self._dungeon_editor.load_table(self._dungeon_table)
            else:
                self._dungeon_table = DungeonTable.from_flat_bytes(dungeon_raw)
                self._dungeon_data_is_narc = False
                self._dungeon_editor.load_table(self._dungeon_table)
                self._status(
                    f"Loaded {DUNGEON_DATA_NARC} as flat dungeon table (non-NARC format)."
                )
        else:
            self._dungeon_table = None
            self._dungeon_data_is_narc = True

        # Portrait data (kaomado.bin) — optional, fails gracefully
        if rom.has_file(PORTRAIT_DATA):
            try:
                from rom_editor.nds.portrait import PortraitContainer
                self._portrait_container = PortraitContainer(
                    rom.read_file(PORTRAIT_DATA)
                )
                self._pokemon_editor.set_portrait_container(self._portrait_container)
            except Exception as exc:
                self._status(f"Portraits unavailable: {exc}")

        # Text-like files (message/str/msg/txt) in conservative raw mode
        self._text_editor.load_rom(rom)

        # Learnset data (WAZA pointer-table format)
        if rom.has_file(MOVE_LEARNSET_NARC):
            try:
                self._learnset_table = WazaLearnsetTable.from_bytes(
                    rom.read_file(MOVE_LEARNSET_NARC)
                )
                self._learnset_editor.load_table(self._learnset_table)
            except Exception as exc:
                self._learnset_table = None
                self._status(f"Learnsets unavailable: {exc}")
        else:
            self._learnset_table = None
        self._refresh_validation_warnings()

    def _save_rom(self) -> None:
        if self._rom is None:
            return
        try:
            self._write_game_data_to_rom()
            self._rom.save()
            self._modified = False
            self._status(f"Saved: {self._rom.path}")
            self._update_guidance()
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            self._status(f"Save failed: {exc}")

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
        try:
            self._write_game_data_to_rom()
            self._rom.save(path)
            self._modified = False
            self._status(f"Saved as: {path}")
            self._update_guidance()
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            self._status(f"Save failed: {exc}")

    def _write_game_data_to_rom(self) -> None:
        assert self._rom is not None
        rom = self._rom

        if self._pokemon_table and rom.has_file(POKEMON_DATA_NARC):
            if self._pokemon_table.source_format == "md":
                rom.write_file(POKEMON_DATA_NARC, self._pokemon_table.to_md_bytes())
            else:
                narc = NARC.from_bytes(rom.read_file(POKEMON_DATA_NARC))
                self._pokemon_table.write_to_narc(narc)
                rom.write_file(POKEMON_DATA_NARC, narc.to_bytes())

        if self._move_table and rom.has_file(MOVE_DATA_NARC):
            if self._move_data_is_narc:
                narc = NARC.from_bytes(rom.read_file(MOVE_DATA_NARC))
                self._move_table.write_to_narc(narc)
                rom.write_file(MOVE_DATA_NARC, narc.to_bytes())
            else:
                rom.write_file(MOVE_DATA_NARC, self._move_table.to_bytes())

        if self._dungeon_table and rom.has_file(DUNGEON_DATA_NARC):
            if self._dungeon_data_is_narc:
                narc = NARC.from_bytes(rom.read_file(DUNGEON_DATA_NARC))
                self._dungeon_table.write_to_narc(narc)
                rom.write_file(DUNGEON_DATA_NARC, narc.to_bytes())
            else:
                rom.write_file(DUNGEON_DATA_NARC, self._dungeon_table.to_flat_bytes())

        if self._learnset_table and rom.has_file(MOVE_LEARNSET_NARC):
            # Safe path: keep a backup and restore if writing learnsets fails.
            old_data = rom.read_file(MOVE_LEARNSET_NARC)
            try:
                new_data = self._learnset_table.to_bytes(
                    auto_fit=self._learnset_editor.auto_fit_enabled()
                )
                rom.write_file(MOVE_LEARNSET_NARC, new_data)
            except Exception:
                try:
                    rom.write_file(MOVE_LEARNSET_NARC, old_data)
                except Exception:
                    pass
                raise

        for path, data in self._text_editor.get_modified_files().items():
            if rom.has_file(path):
                rom.write_file(path, data)

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
        self._update_guidance()

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
        self._update_guidance()
        self._refresh_validation_warnings()

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
            old_snapshot = deepcopy(entry)
            old = getattr(entry, field)
            setattr(entry, field, int(suggestion.new_value))
            self._history.push(ChangeRecord(
                entity_type="pokemon", index=entry.index, name=entry.name,
                old_snapshot=old_snapshot, new_snapshot=deepcopy(entry),
            ))
            self._pokemon_editor._populate_fields(entry)
            self._on_data_modified()
            self._status(f"Applied: {entry.name}.{field} {old} \u2192 {suggestion.new_value}")

    def _apply_move_suggestion(self, suggestion) -> None:
        entry = self._move_editor.get_current_entry()
        if entry is None:
            return
        field = suggestion.field
        if hasattr(entry, field):
            old_snapshot = deepcopy(entry)
            old = getattr(entry, field)
            setattr(entry, field, int(suggestion.new_value))
            self._history.push(ChangeRecord(
                entity_type="move", index=entry.index, name=entry.name,
                old_snapshot=old_snapshot, new_snapshot=deepcopy(entry),
            ))
            self._move_editor._populate(entry)
            self._on_data_modified()
            self._status(f"Applied: {entry.name}.{field} {old} \u2192 {suggestion.new_value}")

    def _apply_dungeon_suggestion(self, suggestion) -> None:
        entry = self._dungeon_editor.get_current_entry()
        if entry is None:
            return
        field = suggestion.field
        if hasattr(entry, field):
            old_snapshot = deepcopy(entry)
            old = getattr(entry, field)
            setattr(entry, field, int(suggestion.new_value))
            self._history.push(ChangeRecord(
                entity_type="dungeon", index=entry.index, name=entry.name,
                old_snapshot=old_snapshot, new_snapshot=deepcopy(entry),
            ))
            self._dungeon_editor._populate(entry)
            self._on_data_modified()
            self._status(f"Applied: {entry.name}.{field} {old} \u2192 {suggestion.new_value}")

    # ------------------------------------------------------------------
    # Auto-save
    # ------------------------------------------------------------------

    def _schedule_autosave(self) -> None:
        """Start (or restart) the 3-minute auto-save timer."""
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(180_000, self._autosave)

    def _autosave(self) -> None:
        if self._rom is not None and self._modified:
            try:
                sidecar = str(self._rom.path) + ".autosave.nds"
                self._write_game_data_to_rom()
                self._rom.save(sidecar)
                now = datetime.datetime.now().strftime("%H:%M")
                self._status(
                    f"Auto-saved at {now}  \u2192  {Path(sidecar).name}"
                )
            except Exception as exc:
                self._status(f"Auto-save failed: {exc}")
        # Always reschedule
        self._autosave_job = self.after(180_000, self._autosave)

    # ------------------------------------------------------------------
    # Simple / Advanced mode toggle
    # ------------------------------------------------------------------

    def _toggle_mode(self) -> None:
        simple = not self._simple_mode.get()
        self._simple_mode.set(simple)
        label = "Advanced Mode" if simple else "Simple Mode"
        self._mode_btn.configure(text=label)
        self._pokemon_editor.set_simple_mode(simple)
        self._move_editor.set_simple_mode(simple)
        self._dungeon_editor.set_simple_mode(simple)
        self._update_guidance()

    def _toggle_focus_assist(self) -> None:
        enabled = not self._focus_assist.get()
        self._focus_assist.set(enabled)
        self._set_focus_assist(enabled)

    def _set_focus_assist(self, enabled: bool) -> None:
        """Hide side AI panels to reduce visual/cognitive load."""
        if enabled:
            self._pokemon_ai.grid_remove()
            self._move_ai.grid_remove()
            self._dungeon_ai.grid_remove()
            self._pokemon_outer.columnconfigure(0, weight=1)
            self._move_outer.columnconfigure(0, weight=1)
            self._dungeon_outer.columnconfigure(0, weight=1)
            self._focus_btn.configure(text="Focus Assist: On")
        else:
            self._pokemon_ai.grid(row=0, column=1, sticky="nsew")
            self._move_ai.grid(row=0, column=1, sticky="nsew")
            self._dungeon_ai.grid(row=0, column=1, sticky="nsew")
            self._pokemon_outer.columnconfigure(0, weight=3)
            self._move_outer.columnconfigure(0, weight=3)
            self._dungeon_outer.columnconfigure(0, weight=3)
            self._focus_btn.configure(text="Focus Assist: Off")
        self._update_guidance()

    def _toggle_neuro_mode(self) -> None:
        enabled = not self._neuro_mode.get()
        self._neuro_mode.set(enabled)
        self._settings["neuro_mode"] = enabled
        self._save_settings()
        self._apply_neuro_mode()

    def _apply_neuro_mode(self, initial: bool = False) -> None:
        enabled = self._neuro_mode.get()
        self._neuro_btn.configure(
            text="Neuro Mode: On" if enabled else "Neuro Mode: Off"
        )
        if enabled:
            self._pokemon_editor.set_dropdown_picker_mode(True)
            self._move_editor.set_dropdown_picker_mode(True)
            self._dungeon_editor.set_dropdown_picker_mode(True)
            self._learnset_editor.set_dropdown_picker_mode(True)
            if not self._simple_mode.get():
                self._toggle_mode()
            if not self._focus_assist.get():
                self._focus_assist.set(True)
                self._set_focus_assist(True)
        elif not initial:
            # Turning neuro mode off does not force advanced mode back on.
            self._update_guidance()

    def _update_guidance(self) -> None:
        if self._rom is None:
            self._guide_var.set(
                "Step 1: Open a ROM. Then pick one tab, make one small change, and save."
            )
            return
        if self._modified:
            self._guide_var.set(
                "You have unsaved changes. Step 4: Save ROM now (Ctrl+S)."
            )
            return
        if not self._history.has_undo():
            self._guide_var.set(
                "Step 2: Select a Pokémon, move, or dungeon entry and edit one field at a time."
            )
            return
        self._guide_var.set(
            "Great progress. Continue with one small edit, then Save ROM when ready."
        )

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def _on_entry_changed(
        self,
        entity_type: str,
        index: int,
        name: str,
        old_snapshot,
        new_snapshot,
    ) -> None:
        """Called by each editor's Apply Changes; pushes a history record."""
        self._history.push(ChangeRecord(
            entity_type=entity_type,
            index=index,
            name=name,
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
        ))

    def _on_history_changed(self, records) -> None:
        """Refresh changes panel and update Edit menu state."""
        self._refresh_changes_panel(records)
        undo_state = "normal" if self._history.has_undo() else "disabled"
        redo_state = "normal" if self._history.has_redo() else "disabled"
        self._edit_menu.entryconfigure("Undo", state=undo_state)
        self._edit_menu.entryconfigure("Redo", state=redo_state)

    def _undo(self) -> None:
        rec = self._history.undo()
        if rec is None:
            self._status("Nothing to undo.")
            return
        self._restore_snapshot(rec.entity_type, rec.index, rec.old_snapshot)
        self._status(f"Undid: {rec.name}")
        self._update_guidance()
        self._refresh_validation_warnings()

    def _redo(self) -> None:
        rec = self._history.redo()
        if rec is None:
            self._status("Nothing to redo.")
            return
        self._restore_snapshot(rec.entity_type, rec.index, rec.new_snapshot)
        self._status(f"Redid: {rec.name}")
        self._update_guidance()
        self._refresh_validation_warnings()

    def _refresh_validation_warnings(self) -> None:
        self._validation_tree.delete(*self._validation_tree.get_children())
        warnings = self._collect_validation_warnings()
        if not warnings:
            self._validation_tree.insert(
                "", "end", values=("Info", "All", "No warnings detected.")
            )
            return
        for kind, name, msg in warnings:
            self._validation_tree.insert("", "end", values=(kind, name, msg))

    def _collect_validation_warnings(self) -> list[tuple[str, str, str]]:
        out: list[tuple[str, str, str]] = []

        if self._pokemon_table:
            for e in self._pokemon_table:
                if e.base_hp <= 1 or e.base_hp > 255:
                    out.append(("Pokemon", e.name, f"Base HP looks invalid: {e.base_hp}"))
                if e.bst > 700:
                    out.append(("Pokemon", e.name, f"Very high BST: {e.bst}"))
                if e.base_spd <= 0:
                    out.append(("Pokemon", e.name, f"Speed is non-positive: {e.base_spd}"))

        if self._move_table:
            for m in self._move_table:
                if m.base_power > 250:
                    out.append(("Move", m.name, f"Very high base power: {m.base_power}"))
                if m.accuracy > 100:
                    out.append(("Move", m.name, f"Accuracy over 100: {m.accuracy}"))
                if m.hits_min > m.hits_max:
                    out.append(("Move", m.name, "Min hits is greater than max hits"))

        if self._dungeon_table:
            for d in self._dungeon_table:
                if d.num_floors <= 0:
                    out.append(("Dungeon", d.name, "Floor count must be at least 1"))
                if d.num_floors > 99:
                    out.append(("Dungeon", d.name, f"Very high floor count: {d.num_floors}"))
                if d.item_density > 100:
                    out.append(("Dungeon", d.name, f"Item density over 100: {d.item_density}"))
                if d.trap_density > 100:
                    out.append(("Dungeon", d.name, f"Trap density over 100: {d.trap_density}"))

        return out

    def _restore_snapshot(self, entity_type: str, index: int, snapshot) -> None:
        """Copy all dataclass fields from *snapshot* into the live table entry."""
        if entity_type == "pokemon" and self._pokemon_table:
            target = self._pokemon_table[index]
            for f in dataclasses.fields(target):
                setattr(target, f.name, getattr(snapshot, f.name))
            cur = self._pokemon_editor.get_current_entry()
            if cur is not None and cur.index == index:
                self._pokemon_editor._populate_fields(target)
        elif entity_type == "move" and self._move_table:
            target = self._move_table[index]
            for f in dataclasses.fields(target):
                setattr(target, f.name, getattr(snapshot, f.name))
            cur = self._move_editor.get_current_entry()
            if cur is not None and cur.index == index:
                self._move_editor._populate(target)
        elif entity_type == "dungeon" and self._dungeon_table:
            target = self._dungeon_table[index]
            for f in dataclasses.fields(target):
                setattr(target, f.name, getattr(snapshot, f.name))
            cur = self._dungeon_editor.get_current_entry()
            if cur is not None and cur.index == index:
                self._dungeon_editor._populate(target)

    # ------------------------------------------------------------------
    # Changes panel
    # ------------------------------------------------------------------

    def _toggle_changes_panel(self) -> None:
        if self._changes_visible:
            self._changes_body.pack_forget()
            count = len(self._history.records)
            self._changes_toggle_btn.configure(
                text=f"\u25b8 Changes ({count})")
        else:
            self._changes_body.pack(fill="x")
            count = len(self._history.records)
            self._changes_toggle_btn.configure(
                text=f"\u25be Changes ({count})")
        self._changes_visible = not self._changes_visible

    def _refresh_changes_panel(self, records) -> None:
        """Repopulate the changes treeview with the current history records."""
        self._changes_tree.delete(*self._changes_tree.get_children())
        count = len(records)
        label = f"\u25be Changes ({count})" if self._changes_visible \
            else f"\u25b8 Changes ({count})"
        self._changes_toggle_btn.configure(text=label)
        # Show newest first
        for rec in reversed(records):
            kind = rec.entity_type.capitalize()
            diff = self._describe_diff(rec.old_snapshot, rec.new_snapshot)
            self._changes_tree.insert(
                "", "end",
                values=(f"[{kind}] {rec.name}", diff),
            )

    @staticmethod
    def _describe_diff(old, new) -> str:
        """Return a short human-readable summary of changed fields."""
        changes = []
        for f in dataclasses.fields(old):
            if f.name == "index":
                continue
            ov = getattr(old, f.name)
            nv = getattr(new, f.name)
            if ov != nv:
                changes.append(f"{f.name}: {ov}\u2192{nv}")
        if not changes:
            return "no changes"
        summary = ", ".join(changes[:3])
        return summary + ("\u2026" if len(changes) > 3 else "")

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
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self.destroy()
