"""Pokémon stats editor tab."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable

from rom_editor.games.explorers_sky.pokemon import PokemonEntry, PokemonTable
from rom_editor.games.explorers_sky.constants import (
    POKEMON_NAMES, TYPE_NAMES, ABILITY_NAMES, EXP_GROUP_NAMES,
)


class PokemonEditorTab(ttk.Frame):
    """A tab widget for editing Pokémon base statistics."""

    _STAT_FIELDS = [
        ("base_hp",    "HP"),
        ("base_atk",   "Attack"),
        ("base_spatk", "Sp. Atk"),
        ("base_def",   "Defense"),
        ("base_spdef", "Sp. Def"),
        ("base_spd",   "Speed"),
    ]

    def __init__(
        self,
        parent: ttk.Notebook,
        on_modified: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self._table: Optional[PokemonTable] = None
        self._on_modified = on_modified
        self._current_entry: Optional[PokemonEntry] = None
        self._stat_vars: dict[str, tk.IntVar] = {}
        self._type1_var = tk.StringVar()
        self._type2_var = tk.StringVar()
        self._ability1_var = tk.StringVar()
        self._ability2_var = tk.StringVar()
        self._exp_group_var = tk.StringVar()
        self._recruit_var = tk.IntVar()
        self._size_var = tk.IntVar()
        self._bst_var = tk.StringVar(value="BST: —")
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_table(self, table: PokemonTable) -> None:
        """Populate the listbox with all Pokémon from *table*."""
        self._table = table
        self._listbox.delete(0, tk.END)
        for entry in table:
            label = f"#{entry.index:03d} {entry.name}"
            self._listbox.insert(tk.END, label)

    def get_current_entry(self) -> Optional[PokemonEntry]:
        return self._current_entry

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # --- Left panel: listbox with search ---
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="ns", padx=4, pady=4)

        ttk.Label(left, text="Search:").pack(anchor="w")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_changed)
        ttk.Entry(left, textvariable=self._search_var, width=22).pack(fill="x")

        self._listbox = tk.Listbox(left, width=24, exportselection=False)
        self._listbox.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(left, orient="vertical", command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._listbox.pack(side="left", fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # --- Right panel: stat editor ---
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        right.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(right, textvariable=self._bst_var,
                  font=("TkDefaultFont", 11, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        row += 1

        # Type selectors
        for label_text, var, options in [
            ("Type 1:", self._type1_var, TYPE_NAMES),
            ("Type 2:", self._type2_var, TYPE_NAMES),
        ]:
            ttk.Label(right, text=label_text).grid(row=row, column=0, sticky="e", padx=4)
            cb = ttk.Combobox(right, textvariable=var, values=options,
                              state="readonly", width=14)
            cb.grid(row=row, column=1, sticky="w")
            cb.bind("<<ComboboxSelected>>", self._on_field_changed)
            row += 1

        # Ability selectors
        for label_text, var in [
            ("Ability 1:", self._ability1_var),
            ("Ability 2:", self._ability2_var),
        ]:
            ttk.Label(right, text=label_text).grid(row=row, column=0, sticky="e", padx=4)
            cb = ttk.Combobox(right, textvariable=var, values=ABILITY_NAMES,
                              state="readonly", width=20)
            cb.grid(row=row, column=1, sticky="w")
            cb.bind("<<ComboboxSelected>>", self._on_field_changed)
            row += 1

        # EXP Group
        ttk.Label(right, text="EXP Group:").grid(row=row, column=0, sticky="e", padx=4)
        cb = ttk.Combobox(right, textvariable=self._exp_group_var,
                          values=EXP_GROUP_NAMES, state="readonly", width=14)
        cb.grid(row=row, column=1, sticky="w")
        cb.bind("<<ComboboxSelected>>", self._on_field_changed)
        row += 1

        # Stat spinboxes
        ttk.Separator(right, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=6)
        row += 1

        for field, label in self._STAT_FIELDS:
            var = tk.IntVar(value=0)
            self._stat_vars[field] = var
            ttk.Label(right, text=f"{label}:").grid(
                row=row, column=0, sticky="e", padx=4)
            sb = ttk.Spinbox(
                right, from_=1, to=255, textvariable=var, width=6,
                command=self._on_stat_changed
            )
            sb.grid(row=row, column=1, sticky="w")
            sb.bind("<FocusOut>", self._on_stat_changed)
            row += 1

        # Recruit / Size
        ttk.Label(right, text="Recruit Rate:").grid(row=row, column=0, sticky="e", padx=4)
        ttk.Spinbox(right, from_=-100, to=100, textvariable=self._recruit_var,
                    width=6).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(right, text="Size:").grid(row=row, column=0, sticky="e", padx=4)
        ttk.Spinbox(right, from_=1, to=4, textvariable=self._size_var,
                    width=4).grid(row=row, column=1, sticky="w")
        row += 1

        # Apply button
        ttk.Button(
            right, text="Apply Changes", command=self._apply_changes
        ).grid(row=row, column=0, columnspan=2, pady=8)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_search_changed(self, *_args) -> None:
        query = self._search_var.get().lower()
        self._listbox.delete(0, tk.END)
        if self._table is None:
            return
        for entry in self._table:
            label = f"#{entry.index:03d} {entry.name}"
            if query in label.lower():
                self._listbox.insert(tk.END, label)

    def _on_select(self, _event=None) -> None:
        sel = self._listbox.curselection()
        if not sel or self._table is None:
            return
        label = self._listbox.get(sel[0])
        idx = int(label.split()[0].lstrip("#"))
        entry = self._table[idx]
        self._current_entry = entry
        self._populate_fields(entry)

    def _on_field_changed(self, _event=None) -> None:
        if self._current_entry is None:
            return
        self._apply_changes(notify=False)

    def _on_stat_changed(self, *_args) -> None:
        if self._current_entry is None:
            return
        self._update_bst()

    def _populate_fields(self, entry: PokemonEntry) -> None:
        """Fill UI fields with data from *entry*."""
        self._type1_var.set(TYPE_NAMES[entry.type1] if entry.type1 < len(TYPE_NAMES) else "???")
        self._type2_var.set(TYPE_NAMES[entry.type2] if entry.type2 < len(TYPE_NAMES) else "???")
        ab1 = ABILITY_NAMES[entry.ability1] if entry.ability1 < len(ABILITY_NAMES) else "???"
        ab2 = ABILITY_NAMES[entry.ability2] if entry.ability2 < len(ABILITY_NAMES) else "???"
        self._ability1_var.set(ab1)
        self._ability2_var.set(ab2)
        exp = EXP_GROUP_NAMES[entry.exp_group] if entry.exp_group < len(EXP_GROUP_NAMES) else "???"
        self._exp_group_var.set(exp)
        for field, _ in self._STAT_FIELDS:
            self._stat_vars[field].set(getattr(entry, field))
        self._recruit_var.set(entry.recruit_rate1)
        self._size_var.set(entry.size)
        self._update_bst()

    def _update_bst(self) -> None:
        try:
            total = sum(self._stat_vars[f].get() for f, _ in self._STAT_FIELDS)
            name = self._current_entry.name if self._current_entry else "—"
            self._bst_var.set(f"{name}  —  BST: {total}")
        except Exception:
            pass

    def _apply_changes(self, notify: bool = True) -> None:
        entry = self._current_entry
        if entry is None:
            return
        try:
            entry.type1 = TYPE_NAMES.index(self._type1_var.get())
        except ValueError:
            pass
        try:
            entry.type2 = TYPE_NAMES.index(self._type2_var.get())
        except ValueError:
            pass
        try:
            entry.ability1 = ABILITY_NAMES.index(self._ability1_var.get())
        except ValueError:
            pass
        try:
            entry.ability2 = ABILITY_NAMES.index(self._ability2_var.get())
        except ValueError:
            pass
        try:
            entry.exp_group = EXP_GROUP_NAMES.index(self._exp_group_var.get())
        except ValueError:
            pass
        for field, _ in self._STAT_FIELDS:
            setattr(entry, field, max(1, min(255, self._stat_vars[field].get())))
        entry.recruit_rate1 = max(-128, min(127, self._recruit_var.get()))
        entry.size = max(1, min(4, self._size_var.get()))
        self._update_bst()
        if notify and self._on_modified:
            self._on_modified()
