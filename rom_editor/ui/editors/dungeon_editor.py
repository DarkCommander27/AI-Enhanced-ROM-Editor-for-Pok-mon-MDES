"""Dungeon parameter editor tab."""

from __future__ import annotations

import tkinter as tk
from copy import deepcopy
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
        on_change: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self._table: Optional[DungeonTable] = None
        self._on_modified = on_modified
        self._on_change = on_change
        self._current_entry: Optional[DungeonEntry] = None
        self._picker_options: list[str] = []
        self._picker_lookup: dict[str, int] = {}
        self._numeric_vars: dict[str, tk.IntVar] = {}
        self._darkness_var = tk.StringVar()
        self._weather_var = tk.StringVar()
        self._rand_start_var = tk.BooleanVar()
        self._advanced_widgets: list[tk.Widget] = []
        self._build_ui()

    def load_table(self, table: DungeonTable) -> None:
        self._table = table
        self._listbox.delete(0, tk.END)
        self._picker_options = []
        self._picker_lookup = {}
        self._refresh_picker_and_list()
        if self._picker_options:
            self._picker_var.set(self._picker_options[0])

    def set_simple_mode(self, simple: bool) -> None:
        """Show or hide advanced fields depending on *simple*."""
        for widget in self._advanced_widgets:
            if simple:
                widget.grid_remove()
            else:
                widget.grid()

    def set_dropdown_picker_mode(self, enabled: bool) -> None:
        """Enable or disable no-typing dropdown picker mode."""
        if self._dropdown_picker_var.get() != enabled:
            self._dropdown_picker_var.set(enabled)
            self._toggle_picker_mode()

    def get_current_entry(self) -> Optional[DungeonEntry]:
        return self._current_entry

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Left: list
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="ns", padx=4, pady=4)

        self._dropdown_picker_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            left,
            text="Pure dropdown picker",
            variable=self._dropdown_picker_var,
            command=self._toggle_picker_mode,
        ).pack(anchor="w", pady=(0, 4))

        self._picker_var = tk.StringVar()
        self._picker_cb = ttk.Combobox(
            left,
            textvariable=self._picker_var,
            values=[],
            state="readonly",
            width=24,
        )
        self._picker_cb.bind("<<ComboboxSelected>>", self._on_pick)

        ttk.Label(left, text="Search:").pack(anchor="w")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        self._search_entry = ttk.Entry(left, textvariable=self._search_var, width=22)
        self._search_entry.pack(fill="x")

        self._list_frame = ttk.Frame(left)
        self._list_frame.pack(fill="both", expand=True)
        self._listbox = tk.Listbox(self._list_frame, width=26, exportselection=False)
        sb = ttk.Scrollbar(self._list_frame, orient="vertical", command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._listbox.pack(side="left", fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        ttk.Button(
            left,
            text="Create Custom from Selected",
            command=self._create_custom_from_selected,
        ).pack(fill="x", pady=(4, 0))

        # Right: editor
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        right.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(right, text="Darkness:").grid(row=row, column=0, sticky="e", padx=4)
        ttk.Combobox(right, textvariable=self._darkness_var,
                     values=_DARKNESS_OPTIONS, state="readonly",
                     width=10).grid(row=row, column=1, sticky="w")
        row += 1

        # Weather (simple)
        ttk.Label(right, text="Weather:").grid(row=row, column=0, sticky="e", padx=4)
        ttk.Combobox(right, textvariable=self._weather_var,
                     values=_WEATHER_OPTIONS, state="readonly",
                     width=12).grid(row=row, column=1, sticky="w")
        row += 1

        # Random start (advanced only)
        lbl_rand = ttk.Label(right, text="Random Start Floor:")
        lbl_rand.grid(row=row, column=0, sticky="e", padx=4)
        cb_rand = ttk.Checkbutton(right, variable=self._rand_start_var)
        cb_rand.grid(row=row, column=1, sticky="w")
        self._advanced_widgets.extend([lbl_rand, cb_rand])
        row += 1

        sep = ttk.Separator(right, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=2, sticky="ew", pady=6)
        self._advanced_widgets.append(sep)
        row += 1

        # Simple numeric fields
        _SIMPLE_FIELDS = {"num_floors", "trap_density", "monster_house_chance"}
        for field, label, lo, hi in self._NUMERIC_FIELDS:
            var = tk.IntVar(value=0)
            self._numeric_vars[field] = var
            lbl = ttk.Label(right, text=f"{label}:")
            lbl.grid(row=row, column=0, sticky="e", padx=4)
            sb = ttk.Spinbox(right, from_=lo, to=hi, textvariable=var, width=6)
            sb.grid(row=row, column=1, sticky="w")
            if field not in _SIMPLE_FIELDS:
                self._advanced_widgets.extend([lbl, sb])
            row += 1

        ttk.Button(right, text="Apply Changes",
                   command=self._apply_changes).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=8)

    def _on_search(self, *_args) -> None:
        q = self._search_var.get().lower()
        self._listbox.delete(0, tk.END)
        if self._table is None:
            return
        for e in self._table:
            label = f"#{e.index:03d} {e.name}"
            if q in label.lower():
                self._listbox.insert(tk.END, label)

    def _refresh_picker_and_list(self) -> None:
        self._listbox.delete(0, tk.END)
        self._picker_options = []
        self._picker_lookup = {}
        if self._table is None:
            self._picker_cb.configure(values=[])
            return
        for entry in self._table:
            label = f"#{entry.index:03d} {entry.name}"
            self._listbox.insert(tk.END, label)
            self._picker_options.append(label)
            self._picker_lookup[label] = entry.index
        self._picker_cb.configure(values=self._picker_options)

    def _create_custom_from_selected(self) -> None:
        if self._table is None or self._current_entry is None:
            return
        source = self._current_entry
        custom = self._table.create_custom_dungeon(source.index)
        self._refresh_picker_and_list()

        label = f"#{custom.index:03d} {custom.name}"
        self._picker_var.set(label)
        self._current_entry = custom
        self._populate(custom)
        for i in range(self._listbox.size()):
            if self._listbox.get(i).startswith(f"#{custom.index:03d} "):
                self._listbox.selection_clear(0, tk.END)
                self._listbox.selection_set(i)
                self._listbox.see(i)
                break
        if self._on_modified:
            self._on_modified()

    def _on_select(self, _event=None) -> None:
        sel = self._listbox.curselection()
        if not sel or self._table is None:
            return
        label = self._listbox.get(sel[0])
        idx = int(label.split()[0].lstrip("#"))
        self._picker_var.set(label)
        self._current_entry = self._table[idx]
        self._populate(self._current_entry)

    def _on_pick(self, _event=None) -> None:
        if self._table is None:
            return
        label = self._picker_var.get()
        idx = self._picker_lookup.get(label)
        if idx is None:
            return
        self._current_entry = self._table[idx]
        self._populate(self._current_entry)

        for i in range(self._listbox.size()):
            if self._listbox.get(i).startswith(f"#{idx:03d} "):
                self._listbox.selection_clear(0, tk.END)
                self._listbox.selection_set(i)
                self._listbox.see(i)
                break

    def _toggle_picker_mode(self) -> None:
        dropdown = self._dropdown_picker_var.get()
        if dropdown:
            self._picker_cb.pack(fill="x", pady=(0, 4))
            self._search_entry.pack_forget()
            self._list_frame.pack_forget()
        else:
            self._picker_cb.pack_forget()
            self._search_entry.pack(fill="x")
            self._list_frame.pack(fill="both", expand=True)

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
        old_snapshot = deepcopy(e) if self._on_change else None
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
        if self._on_change and old_snapshot is not None:
            self._on_change("dungeon", e.index, e.name, old_snapshot, deepcopy(e))
        if self._on_modified:
            self._on_modified()

