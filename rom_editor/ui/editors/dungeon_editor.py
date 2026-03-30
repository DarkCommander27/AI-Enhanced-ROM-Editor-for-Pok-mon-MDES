"""Dungeon parameter editor tab."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from rom_editor.games.explorers_sky.dungeons import DungeonEntry, DungeonTable
from rom_editor.games.explorers_sky.constants import DUNGEON_NAMES


_DARKNESS_OPTIONS = ["Full", "Semi", "None"]
_WEATHER_OPTIONS = ["Clear", "Cloudy", "Sandstorm", "Fog", "Snow", "Random"]


class DungeonEditorTab(ttk.Frame):
    """Tab widget for editing dungeon parameters."""

    _NUMERIC_FIELDS = [
        ("num_floors",            "Floors",            1, 99),
        ("item_density",          "Item Density",       0, 10),
        ("trap_density",          "Trap Density",       0, 99),
        ("floor_connectivity",    "Floor Connectivity", 1, 10),
        ("water_chance",          "Water Chance (%)",   0, 100),
        ("monster_house_chance",  "Monster House (%)",  0, 100),
        ("buried_item_chance",    "Buried Items (%)",   0, 100),
        ("empty_mh_chance",       "Empty MH (%)",       0, 100),
        ("kecleon_shop_chance",   "Kecleon Shop (%)",   0, 100),
        ("music_id",              "Music ID",           0, 255),
        ("fixed_floor_id",        "Fixed Floor ID",     0, 255),
    ]

    def __init__(
        self,
        parent: ttk.Notebook,
        on_modified: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self._table: Optional[DungeonTable] = None
        self._on_modified = on_modified
        self._current_entry: Optional[DungeonEntry] = None
        self._numeric_vars: dict[str, tk.IntVar] = {}
        self._darkness_var = tk.StringVar()
        self._weather_var = tk.StringVar()
        self._rand_start_var = tk.BooleanVar()
        self._build_ui()

    def load_table(self, table: DungeonTable) -> None:
        self._table = table
        self._listbox.delete(0, tk.END)
        for entry in table:
            self._listbox.insert(tk.END, f"#{entry.index:03d} {entry.name}")

    def get_current_entry(self) -> Optional[DungeonEntry]:
        return self._current_entry

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Left: list
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="ns", padx=4, pady=4)

        ttk.Label(left, text="Search:").pack(anchor="w")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ttk.Entry(left, textvariable=self._search_var, width=22).pack(fill="x")

        frame = ttk.Frame(left)
        frame.pack(fill="both", expand=True)
        self._listbox = tk.Listbox(frame, width=26, exportselection=False)
        sb = ttk.Scrollbar(frame, orient="vertical", command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._listbox.pack(side="left", fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # Right: editor
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        right.columnconfigure(1, weight=1)

        row = 0
        # Darkness
        ttk.Label(right, text="Darkness:").grid(row=row, column=0, sticky="e", padx=4)
        ttk.Combobox(right, textvariable=self._darkness_var,
                     values=_DARKNESS_OPTIONS, state="readonly",
                     width=10).grid(row=row, column=1, sticky="w")
        row += 1

        # Weather
        ttk.Label(right, text="Weather:").grid(row=row, column=0, sticky="e", padx=4)
        ttk.Combobox(right, textvariable=self._weather_var,
                     values=_WEATHER_OPTIONS, state="readonly",
                     width=12).grid(row=row, column=1, sticky="w")
        row += 1

        # Random start
        ttk.Label(right, text="Random Start Floor:").grid(
            row=row, column=0, sticky="e", padx=4)
        ttk.Checkbutton(right, variable=self._rand_start_var).grid(
            row=row, column=1, sticky="w")
        row += 1

        ttk.Separator(right, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=6)
        row += 1

        for field, label, lo, hi in self._NUMERIC_FIELDS:
            var = tk.IntVar(value=0)
            self._numeric_vars[field] = var
            ttk.Label(right, text=f"{label}:").grid(
                row=row, column=0, sticky="e", padx=4)
            ttk.Spinbox(right, from_=lo, to=hi, textvariable=var,
                        width=6).grid(row=row, column=1, sticky="w")
            row += 1

        ttk.Button(right, text="Apply Changes",
                   command=self._apply_changes).grid(
            row=row, column=0, columnspan=2, pady=8)

    def _on_search(self, *_args) -> None:
        q = self._search_var.get().lower()
        self._listbox.delete(0, tk.END)
        if self._table is None:
            return
        for e in self._table:
            label = f"#{e.index:03d} {e.name}"
            if q in label.lower():
                self._listbox.insert(tk.END, label)

    def _on_select(self, _event=None) -> None:
        sel = self._listbox.curselection()
        if not sel or self._table is None:
            return
        label = self._listbox.get(sel[0])
        idx = int(label.split()[0].lstrip("#"))
        self._current_entry = self._table[idx]
        self._populate(self._current_entry)

    def _populate(self, e: DungeonEntry) -> None:
        self._darkness_var.set(
            _DARKNESS_OPTIONS[e.darkness]
            if e.darkness < len(_DARKNESS_OPTIONS) else "???"
        )
        self._weather_var.set(
            _WEATHER_OPTIONS[e.weather]
            if e.weather < len(_WEATHER_OPTIONS) else "???"
        )
        self._rand_start_var.set(bool(e.random_start_floor))
        for field, _, _, _ in self._NUMERIC_FIELDS:
            self._numeric_vars[field].set(getattr(e, field))

    def _apply_changes(self) -> None:
        e = self._current_entry
        if e is None:
            return
        try:
            e.darkness = _DARKNESS_OPTIONS.index(self._darkness_var.get())
        except ValueError:
            pass
        try:
            e.weather = _WEATHER_OPTIONS.index(self._weather_var.get())
        except ValueError:
            pass
        e.random_start_floor = int(self._rand_start_var.get())
        for field, _, lo, hi in self._NUMERIC_FIELDS:
            setattr(e, field, max(lo, min(hi, self._numeric_vars[field].get())))
        if self._on_modified:
            self._on_modified()
