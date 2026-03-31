"""Move data editor tab."""

from __future__ import annotations

import tkinter as tk
from copy import deepcopy
from tkinter import ttk
from typing import Optional, Callable

from rom_editor.games.explorers_sky.moves import MoveEntry, MoveTable
from rom_editor.games.explorers_sky.constants import (
    TYPE_NAMES, MOVE_CATEGORIES,
)

_TARGET_NAMES = [
    "Front enemy", "Self", "All enemies in room",
    "All in room", "Front ally", "Teammates",
    "Entire floor", "User + adjacent", "Line (2 tiles)",
    "Diagonal", "Line (3 tiles)",
]

_RANGE_NAMES = [
    "Front (1 tile)", "Front (2 tiles)", "Room",
    "Front (diagonal OK)", "Entire floor", "Floor (no walls)",
]


class MoveEditorTab(ttk.Frame):
    """Tab widget for editing move data."""

    _NUMERIC_FIELDS = [
        ("base_power", "Base Power", 0, 255),
        ("accuracy",   "Accuracy",   0, 100),
        ("pp",         "PP",         1,  99),
        ("pp2",        "PP (sec.)",  1,  99),
        ("hits_min",   "Min Hits",   1,   9),
        ("hits_max",   "Max Hits",   1,   9),
        ("ai_weight",  "AI Weight",  0, 255),
    ]

    def __init__(
        self,
        parent: ttk.Notebook,
        on_modified: Optional[Callable] = None,
        on_change: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self._table: Optional[MoveTable] = None
        self._on_modified = on_modified
        self._on_change = on_change
        self._current_entry: Optional[MoveEntry] = None
        self._picker_options: list[str] = []
        self._picker_lookup: dict[str, int] = {}
        self._numeric_vars: dict[str, tk.IntVar] = {}
        self._type_var = tk.StringVar()
        self._category_var = tk.StringVar()
        self._target_var = tk.StringVar()
        self._range_var = tk.StringVar()
        self._advanced_widgets: list[tk.Widget] = []
        self._build_ui()

    def load_table(self, table: MoveTable) -> None:
        self._table = table
        self._listbox.delete(0, tk.END)
        self._picker_options = []
        self._picker_lookup = {}
        for entry in table:
            label = f"#{entry.index:03d} {entry.name}"
            self._listbox.insert(tk.END, label)
            self._picker_options.append(label)
            self._picker_lookup[label] = entry.index
        self._picker_cb.configure(values=self._picker_options)
        if self._picker_options:
            self._picker_var.set(self._picker_options[0])

    def get_current_entry(self) -> Optional[MoveEntry]:
        return self._current_entry

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
        self._listbox = tk.Listbox(self._list_frame, width=24, exportselection=False)
        sb = ttk.Scrollbar(self._list_frame, orient="vertical", command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._listbox.pack(side="left", fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # Right: editor
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        right.columnconfigure(1, weight=1)

        row = 0
        # Type
        ttk.Label(right, text="Type:").grid(row=row, column=0, sticky="e", padx=4)
        ttk.Combobox(right, textvariable=self._type_var, values=TYPE_NAMES,
                     state="readonly", width=14).grid(row=row, column=1, sticky="w")
        row += 1

        # Category
        ttk.Label(right, text="Category:").grid(row=row, column=0, sticky="e", padx=4)
        ttk.Combobox(right, textvariable=self._category_var, values=MOVE_CATEGORIES,
                     state="readonly", width=14).grid(row=row, column=1, sticky="w")
        row += 1

        # Target (advanced only)
        lbl_target = ttk.Label(right, text="Target:")
        lbl_target.grid(row=row, column=0, sticky="e", padx=4)
        cb_target = ttk.Combobox(right, textvariable=self._target_var,
                                 values=_TARGET_NAMES, state="readonly", width=22)
        cb_target.grid(row=row, column=1, sticky="w")
        self._advanced_widgets.extend([lbl_target, cb_target])
        row += 1

        # Range (advanced only)
        lbl_range = ttk.Label(right, text="Range:")
        lbl_range.grid(row=row, column=0, sticky="e", padx=4)
        cb_range = ttk.Combobox(right, textvariable=self._range_var,
                                values=_RANGE_NAMES, state="readonly", width=22)
        cb_range.grid(row=row, column=1, sticky="w")
        self._advanced_widgets.extend([lbl_range, cb_range])
        row += 1

        sep = ttk.Separator(right, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=2, sticky="ew", pady=6)
        self._advanced_widgets.append(sep)
        row += 1

        # Simple fields: base_power, accuracy, pp
        _SIMPLE_FIELDS = {"base_power", "accuracy", "pp"}
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

    def _populate(self, e: MoveEntry) -> None:
        self._type_var.set(TYPE_NAMES[e.type_id] if e.type_id < len(TYPE_NAMES) else "???")
        self._category_var.set(
            MOVE_CATEGORIES[e.category] if e.category < len(MOVE_CATEGORIES) else "???"
        )
        target_name = (
            _TARGET_NAMES[e.target] if e.target < len(_TARGET_NAMES) else f"Code {e.target}"
        )
        self._target_var.set(target_name)
        range_name = (
            _RANGE_NAMES[e.range_type] if e.range_type < len(_RANGE_NAMES)
            else f"Code {e.range_type}"
        )
        self._range_var.set(range_name)
        for field, _, _, _ in self._NUMERIC_FIELDS:
            self._numeric_vars[field].set(getattr(e, field))

    def _apply_changes(self) -> None:
        e = self._current_entry
        if e is None:
            return
        old_snapshot = deepcopy(e) if self._on_change else None
        try:
            e.type_id = TYPE_NAMES.index(self._type_var.get())
        except ValueError:
            pass
        try:
            e.category = MOVE_CATEGORIES.index(self._category_var.get())
        except ValueError:
            pass
        try:
            e.target = _TARGET_NAMES.index(self._target_var.get())
        except ValueError:
            pass
        try:
            e.range_type = _RANGE_NAMES.index(self._range_var.get())
        except ValueError:
            pass
        for field, _, lo, hi in self._NUMERIC_FIELDS:
            setattr(e, field, max(lo, min(hi, self._numeric_vars[field].get())))
        if self._on_change and old_snapshot is not None:
            self._on_change("move", e.index, e.name, old_snapshot, deepcopy(e))
        if self._on_modified:
            self._on_modified()
