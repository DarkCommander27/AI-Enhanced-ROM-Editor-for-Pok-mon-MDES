"""Experimental Pokemon learnset editor tab."""

from __future__ import annotations

import tkinter as tk
from copy import deepcopy
from tkinter import messagebox, ttk
from typing import Callable, Optional

from rom_editor.games.explorers_sky.constants import MOVE_NAMES, POKEMON_NAMES
from rom_editor.games.explorers_sky.learnsets import LearnsetEntry, WazaLearnsetTable


class LearnsetEditorTab(ttk.Frame):
    """Editor for WAZA level-up learnsets (experimental, size-safe writes)."""

    def __init__(
        self,
        parent: ttk.Notebook,
        on_modified: Optional[Callable] = None,
        on_change: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self._table: Optional[WazaLearnsetTable] = None
        self._on_modified = on_modified
        self._on_change = on_change
        self._current_entry: Optional[LearnsetEntry] = None
        self._draft_level_up: list[tuple[int, int]] = []
        self._pokemon_options: list[str] = []
        self._pokemon_lookup: dict[str, int] = {}
        self._move_options = [f"{i:03d} - {name}" for i, name in enumerate(MOVE_NAMES)]
        self._move_lookup = {opt: i for i, opt in enumerate(self._move_options)}
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="ns", padx=4, pady=4)

        self._dropdown_picker_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            left,
            text="Pure dropdown picker",
            variable=self._dropdown_picker_var,
            command=self._toggle_pokemon_picker_mode,
        ).pack(anchor="w", pady=(0, 4))

        self._pokemon_picker_var = tk.StringVar()
        self._pokemon_picker = ttk.Combobox(
            left,
            textvariable=self._pokemon_picker_var,
            values=[],
            state="readonly",
            width=28,
        )
        self._pokemon_picker.bind("<<ComboboxSelected>>", self._on_pokemon_pick)

        ttk.Label(left, text="Search Pokemon:").pack(anchor="w")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        self._search_entry = ttk.Entry(left, textvariable=self._search_var, width=24)
        self._search_entry.pack(fill="x")

        lframe = ttk.Frame(left)
        lframe.pack(fill="both", expand=True)
        self._listbox = tk.Listbox(lframe, width=28, exportselection=False)
        sb = ttk.Scrollbar(lframe, orient="vertical", command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._listbox.pack(side="left", fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)
        self._listbox_frame = lframe

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        self._title_var = tk.StringVar(value="Select a Pokemon")
        ttk.Label(right, textvariable=self._title_var).grid(row=0, column=0, sticky="w")

        ttk.Label(
            right,
            text="Use dropdowns to add or edit level-up moves.",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(0, 4))

        edit_row = ttk.Frame(right)
        edit_row.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(edit_row, text="Move:").pack(side="left")
        self._move_var = tk.StringVar(value=self._move_options[0] if self._move_options else "")
        self._move_cb = ttk.Combobox(
            edit_row,
            textvariable=self._move_var,
            values=self._move_options,
            state="readonly",
            width=34,
        )
        self._move_cb.pack(side="left", padx=(4, 8))

        ttk.Label(edit_row, text="Level:").pack(side="left")
        self._level_var = tk.StringVar(value="1")
        self._level_cb = ttk.Combobox(
            edit_row,
            textvariable=self._level_var,
            values=[str(i) for i in range(1, 101)],
            state="readonly",
            width=4,
        )
        self._level_cb.pack(side="left", padx=(4, 8))

        ttk.Button(edit_row, text="Add", command=self._add_move).pack(side="left", padx=(0, 4))
        ttk.Button(edit_row, text="Update", command=self._update_selected).pack(side="left", padx=(0, 4))
        ttk.Button(edit_row, text="Remove", command=self._remove_selected).pack(side="left")

        list_frame = ttk.Frame(right)
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self._tree = ttk.Treeview(
            list_frame,
            columns=("idx", "move", "level"),
            show="headings",
            height=14,
        )
        self._tree.heading("idx", text="#")
        self._tree.heading("move", text="Move")
        self._tree.heading("level", text="Level")
        self._tree.column("idx", width=45, stretch=False)
        self._tree.column("move", width=420, stretch=True)
        self._tree.column("level", width=80, stretch=False)
        self._tree.grid(row=0, column=0, sticky="nsew")
        ysb = ttk.Scrollbar(list_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=ysb.set)
        ysb.grid(row=0, column=1, sticky="ns")
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        btns = ttk.Frame(right)
        btns.grid(row=4, column=0, sticky="ew", pady=6)
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        btns.columnconfigure(2, weight=1)
        btns.columnconfigure(3, weight=1)
        ttk.Button(btns, text="Move Up", command=self._move_selected_up).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(btns, text="Move Down", command=self._move_selected_down).grid(
            row=0, column=1, sticky="ew", padx=(0, 8)
        )
        ttk.Button(btns, text="Apply Learnset", command=self._apply).grid(
            row=0, column=2, sticky="ew", padx=(0, 6)
        )
        ttk.Button(btns, text="Reload Entry", command=self._reload_current).grid(
            row=0, column=3, sticky="ew"
        )

        self._auto_fit_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            right,
            text="Auto-fit repack on save (experimental)",
            variable=self._auto_fit_var,
        ).grid(row=5, column=0, sticky="w")

    def auto_fit_enabled(self) -> bool:
        return self._auto_fit_var.get()

    def set_dropdown_picker_mode(self, enabled: bool) -> None:
        """Enable or disable no-typing dropdown picker mode."""
        if self._dropdown_picker_var.get() != enabled:
            self._dropdown_picker_var.set(enabled)
            self._toggle_pokemon_picker_mode()

    def load_table(self, table: WazaLearnsetTable) -> None:
        self._table = table
        self._listbox.delete(0, tk.END)
        self._pokemon_options = []
        self._pokemon_lookup = {}
        for e in table:
            name = POKEMON_NAMES[e.index] if e.index < len(POKEMON_NAMES) else f"#{e.index}"
            label = f"#{e.index:04d} {name}"
            self._listbox.insert(tk.END, label)
            self._pokemon_options.append(label)
            self._pokemon_lookup[label] = e.index
        self._pokemon_picker.configure(values=self._pokemon_options)
        if self._pokemon_options:
            self._pokemon_picker_var.set(self._pokemon_options[0])

    def _on_search(self, *_args) -> None:
        q = self._search_var.get().lower().strip()
        self._listbox.delete(0, tk.END)
        if self._table is None:
            return
        for e in self._table:
            name = POKEMON_NAMES[e.index] if e.index < len(POKEMON_NAMES) else f"#{e.index}"
            label = f"#{e.index:04d} {name}"
            if q in label.lower():
                self._listbox.insert(tk.END, label)

    def _on_select(self, _event=None) -> None:
        sel = self._listbox.curselection()
        if not sel or self._table is None:
            return
        label = self._listbox.get(sel[0])
        idx = int(label.split()[0].lstrip("#"))
        self._current_entry = self._table[idx]
        self._pokemon_picker_var.set(label)
        self._populate(self._current_entry)

    def _on_pokemon_pick(self, _event=None) -> None:
        if self._table is None:
            return
        label = self._pokemon_picker_var.get()
        idx = self._pokemon_lookup.get(label)
        if idx is None:
            return
        self._current_entry = self._table[idx]
        self._populate(self._current_entry)

        # Keep listbox in sync when using dropdown mode.
        for i in range(self._listbox.size()):
            if self._listbox.get(i).startswith(f"#{idx:04d} "):
                self._listbox.selection_clear(0, tk.END)
                self._listbox.selection_set(i)
                self._listbox.see(i)
                break

    def _toggle_pokemon_picker_mode(self) -> None:
        dropdown = self._dropdown_picker_var.get()
        if dropdown:
            self._pokemon_picker.pack(fill="x", pady=(0, 4))
            self._search_entry.pack_forget()
            self._listbox_frame.pack_forget()
        else:
            self._pokemon_picker.pack_forget()
            self._search_entry.pack(fill="x")
            self._listbox_frame.pack(fill="both", expand=True)

    def _populate(self, entry: LearnsetEntry) -> None:
        name = POKEMON_NAMES[entry.index] if entry.index < len(POKEMON_NAMES) else f"#{entry.index}"
        self._title_var.set(f"{name} (#{entry.index:04d})")
        self._draft_level_up = list(entry.level_up)
        self._refresh_tree()

    def _reload_current(self) -> None:
        if self._current_entry is not None:
            self._populate(self._current_entry)

    def _refresh_tree(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for i, (move_id, level) in enumerate(self._draft_level_up, start=1):
            move_name = MOVE_NAMES[move_id] if 0 <= move_id < len(MOVE_NAMES) else f"Unknown {move_id}"
            self._tree.insert("", "end", iid=str(i - 1), values=(i, f"{move_id:03d} - {move_name}", level))

    def _current_selection_index(self) -> Optional[int]:
        sel = self._tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def _selected_move_level(self) -> tuple[int, int]:
        move_label = self._move_var.get()
        if move_label not in self._move_lookup:
            raise ValueError("Select a valid move from the dropdown")
        move_id = self._move_lookup[move_label]
        level = int(self._level_var.get())
        if not (1 <= level <= 100):
            raise ValueError("Level must be between 1 and 100")
        return move_id, level

    def _on_tree_select(self, _event=None) -> None:
        idx = self._current_selection_index()
        if idx is None or idx >= len(self._draft_level_up):
            return
        move_id, level = self._draft_level_up[idx]
        if 0 <= move_id < len(self._move_options):
            self._move_var.set(self._move_options[move_id])
        self._level_var.set(str(level))

    def _add_move(self) -> None:
        if self._current_entry is None:
            return
        try:
            move_id, level = self._selected_move_level()
        except Exception as exc:
            messagebox.showerror("Invalid selection", str(exc))
            return
        self._draft_level_up.append((move_id, level))
        self._refresh_tree()

    def _update_selected(self) -> None:
        idx = self._current_selection_index()
        if idx is None:
            return
        try:
            move_id, level = self._selected_move_level()
        except Exception as exc:
            messagebox.showerror("Invalid selection", str(exc))
            return
        if 0 <= idx < len(self._draft_level_up):
            self._draft_level_up[idx] = (move_id, level)
            self._refresh_tree()
            self._tree.selection_set(str(idx))

    def _remove_selected(self) -> None:
        idx = self._current_selection_index()
        if idx is None:
            return
        if 0 <= idx < len(self._draft_level_up):
            del self._draft_level_up[idx]
            self._refresh_tree()

    def _move_selected_up(self) -> None:
        idx = self._current_selection_index()
        if idx is None or idx <= 0 or idx >= len(self._draft_level_up):
            return
        self._draft_level_up[idx - 1], self._draft_level_up[idx] = (
            self._draft_level_up[idx],
            self._draft_level_up[idx - 1],
        )
        self._refresh_tree()
        self._tree.selection_set(str(idx - 1))

    def _move_selected_down(self) -> None:
        idx = self._current_selection_index()
        if idx is None or idx < 0 or idx >= len(self._draft_level_up) - 1:
            return
        self._draft_level_up[idx + 1], self._draft_level_up[idx] = (
            self._draft_level_up[idx],
            self._draft_level_up[idx + 1],
        )
        self._refresh_tree()
        self._tree.selection_set(str(idx + 1))

    def _apply(self) -> None:
        e = self._current_entry
        if e is None:
            return

        old = deepcopy(e.level_up)
        e.level_up = list(self._draft_level_up)
        if self._on_change is not None:
            self._on_change("learnset", e.index, f"Learnset #{e.index}", old, deepcopy(e.level_up))
        if self._on_modified is not None:
            self._on_modified()
