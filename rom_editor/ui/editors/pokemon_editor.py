"""Pokémon stats editor tab."""

from __future__ import annotations

import tkinter as tk
from copy import deepcopy
from tkinter import ttk, messagebox
from typing import Optional, Callable

from rom_editor.games.explorers_sky.pokemon import PokemonEntry, PokemonTable
from rom_editor.games.explorers_sky.constants import (
    POKEMON_NAMES,
    TYPE_NAMES,
    ABILITY_NAMES,
    EXP_GROUP_NAMES,
    EVOLUTION_METHOD_NAMES,
    EVOLUTION_REQUIREMENT_NAMES,
)
from rom_editor.ui.editors.sprite_viewer import SpriteViewer

# Official type colours  (Gen-IV palette — EoS uses exactly these 18 slots)
TYPE_COLORS: dict[str, str] = {
    "Normal":   "#A8A878",
    "Fire":     "#F08030",
    "Water":    "#6890F0",
    "Grass":    "#78C850",
    "Electric": "#F8D030",
    "Ice":      "#98D8D8",
    "Fighting": "#C03028",
    "Poison":   "#A040A0",
    "Ground":   "#E0C068",
    "Flying":   "#A890F0",
    "Psychic":  "#F85888",
    "Bug":      "#A8B820",
    "Rock":     "#B8A038",
    "Ghost":    "#705898",
    "Dragon":   "#7038F8",
    "Dark":     "#705848",
    "Steel":    "#B8B8D0",
    "???":      "#888888",
}

_EVO_METHOD_OPTIONS = [
    f"{i:02d} - {name}" for i, name in enumerate(EVOLUTION_METHOD_NAMES)
]
_EVO_REQUIREMENT_OPTIONS = [
    f"{i:02d} - {name}" for i, name in enumerate(EVOLUTION_REQUIREMENT_NAMES)
]
_PRE_EVO_OPTIONS = [
    f"#{i:04d} {name}" for i, name in enumerate(POKEMON_NAMES)
]


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
        on_change: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self._table: Optional[PokemonTable] = None
        self._on_modified = on_modified
        self._on_change = on_change
        self._current_entry: Optional[PokemonEntry] = None
        self._picker_options: list[str] = []
        self._picker_lookup: dict[str, int] = {}
        self._advanced_widgets: list[tk.Widget] = []
        self._portrait_container = None
        self._sprite_viewer: Optional[SpriteViewer] = None
        self._stat_vars: dict[str, tk.IntVar] = {}
        self._type1_var = tk.StringVar()
        self._type2_var = tk.StringVar()
        self._ability1_var = tk.StringVar()
        self._ability2_var = tk.StringVar()
        self._exp_group_var = tk.StringVar()
        self._pre_evo_var = tk.StringVar()
        self._evo_method_var = tk.StringVar()
        self._evo_param1_var = tk.IntVar()
        self._evo_req_var = tk.StringVar()
        self._recruit_var = tk.IntVar()
        self._recruit2_var = tk.IntVar()
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
        self._picker_options = []
        self._picker_lookup = {}
        for pos, entry in enumerate(table):
            label = f"#{entry.index:03d} {entry.name}"
            if entry.species_index != entry.index:
                label += f" [species {entry.species_index:03d}]"
            self._listbox.insert(tk.END, label)
            self._picker_options.append(label)
            self._picker_lookup[label] = entry.index
            self._colorize_item(pos, entry)
        self._picker_cb.configure(values=self._picker_options)
        if self._picker_options:
            self._picker_var.set(self._picker_options[0])

    def get_current_entry(self) -> Optional[PokemonEntry]:
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

    def _colorize_item(self, pos: int, entry: PokemonEntry) -> None:
        """Set the listbox item foreground to match the Pokémon's primary type."""
        type_name = (
            TYPE_NAMES[entry.type1]
            if 0 <= entry.type1 < len(TYPE_NAMES) else "???"
        )
        color = TYPE_COLORS.get(type_name, "#000000")
        self._listbox.itemconfigure(pos, foreground=color)

    @staticmethod
    def _format_id_option(value: int, options: list[str]) -> str:
        if 0 <= value < len(options):
            return options[value]
        width = 4 if options and options[0].startswith("#") else 2
        return f"{value:0{width}d} - Unknown"

    @staticmethod
    def _parse_id_option(value: str) -> int:
        token = value.strip().split(" ", 1)[0]
        token = token.split("-", 1)[0].strip().lstrip("#")
        try:
            return int(token)
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # --- Left panel: listbox with search ---
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
            width=22,
        )
        self._picker_cb.bind("<<ComboboxSelected>>", self._on_pick)

        ttk.Label(left, text="Search:").pack(anchor="w")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_changed)
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

        # Portrait viewer below listbox
        self._sprite_viewer = SpriteViewer(left)
        self._sprite_viewer.pack(fill="x", pady=(4, 0))
        self._sprite_viewer.on_emotion_changed = lambda _: self._update_portrait()

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

        # Type 1 (shown in simple mode)
        ttk.Label(right, text="Type 1:").grid(row=row, column=0, sticky="e", padx=4)
        cb_type1 = ttk.Combobox(right, textvariable=self._type1_var,
                                values=TYPE_NAMES, state="readonly", width=14)
        cb_type1.grid(row=row, column=1, sticky="w")
        cb_type1.bind("<<ComboboxSelected>>", self._on_field_changed)
        row += 1

        # Type 2 (advanced only)
        lbl_type2 = ttk.Label(right, text="Type 2:")
        lbl_type2.grid(row=row, column=0, sticky="e", padx=4)
        cb_type2 = ttk.Combobox(right, textvariable=self._type2_var,
                                values=TYPE_NAMES, state="readonly", width=14)
        cb_type2.grid(row=row, column=1, sticky="w")
        cb_type2.bind("<<ComboboxSelected>>", self._on_field_changed)
        self._advanced_widgets.extend([lbl_type2, cb_type2])
        row += 1

        # Ability 1 (advanced only)
        lbl_ab1 = ttk.Label(right, text="Ability 1:")
        lbl_ab1.grid(row=row, column=0, sticky="e", padx=4)
        cb_ab1 = ttk.Combobox(right, textvariable=self._ability1_var,
                              values=ABILITY_NAMES, state="readonly", width=20)
        cb_ab1.grid(row=row, column=1, sticky="w")
        cb_ab1.bind("<<ComboboxSelected>>", self._on_field_changed)
        self._advanced_widgets.extend([lbl_ab1, cb_ab1])
        row += 1

        # Ability 2 (advanced only)
        lbl_ab2 = ttk.Label(right, text="Ability 2:")
        lbl_ab2.grid(row=row, column=0, sticky="e", padx=4)
        cb_ab2 = ttk.Combobox(right, textvariable=self._ability2_var,
                              values=ABILITY_NAMES, state="readonly", width=20)
        cb_ab2.grid(row=row, column=1, sticky="w")
        cb_ab2.bind("<<ComboboxSelected>>", self._on_field_changed)
        self._advanced_widgets.extend([lbl_ab2, cb_ab2])
        row += 1

        # EXP Group (advanced only)
        lbl_exp = ttk.Label(right, text="EXP Group:")
        lbl_exp.grid(row=row, column=0, sticky="e", padx=4)
        cb_exp = ttk.Combobox(right, textvariable=self._exp_group_var,
                              values=EXP_GROUP_NAMES, state="readonly", width=14)
        cb_exp.grid(row=row, column=1, sticky="w")
        cb_exp.bind("<<ComboboxSelected>>", self._on_field_changed)
        self._advanced_widgets.extend([lbl_exp, cb_exp])
        row += 1

        # Evolution fields (advanced only)
        lbl_pre = ttk.Label(right, text="Pre-Evolution:")
        lbl_pre.grid(row=row, column=0, sticky="e", padx=4)
        cb_pre = ttk.Combobox(
            right,
            textvariable=self._pre_evo_var,
            values=_PRE_EVO_OPTIONS,
            state="readonly",
            width=22,
        )
        cb_pre.grid(row=row, column=1, sticky="w")
        cb_pre.bind("<<ComboboxSelected>>", self._on_field_changed)
        self._advanced_widgets.extend([lbl_pre, cb_pre])
        row += 1

        lbl_evo_method = ttk.Label(right, text="Evo Method:")
        lbl_evo_method.grid(row=row, column=0, sticky="e", padx=4)
        cb_evo_method = ttk.Combobox(
            right,
            textvariable=self._evo_method_var,
            values=_EVO_METHOD_OPTIONS,
            state="readonly",
            width=20,
        )
        cb_evo_method.grid(row=row, column=1, sticky="w")
        cb_evo_method.bind("<<ComboboxSelected>>", self._on_field_changed)
        self._advanced_widgets.extend([lbl_evo_method, cb_evo_method])
        row += 1

        lbl_evo_param = ttk.Label(right, text="Evo Param 1:")
        lbl_evo_param.grid(row=row, column=0, sticky="e", padx=4)
        sb_evo_param = ttk.Spinbox(
            right,
            from_=0,
            to=65535,
            textvariable=self._evo_param1_var,
            width=8,
        )
        sb_evo_param.grid(row=row, column=1, sticky="w")
        self._advanced_widgets.extend([lbl_evo_param, sb_evo_param])
        row += 1

        lbl_evo_req = ttk.Label(right, text="Evo Requirement:")
        lbl_evo_req.grid(row=row, column=0, sticky="e", padx=4)
        cb_evo_req = ttk.Combobox(
            right,
            textvariable=self._evo_req_var,
            values=_EVO_REQUIREMENT_OPTIONS,
            state="readonly",
            width=20,
        )
        cb_evo_req.grid(row=row, column=1, sticky="w")
        cb_evo_req.bind("<<ComboboxSelected>>", self._on_field_changed)
        self._advanced_widgets.extend([lbl_evo_req, cb_evo_req])
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

        # Recruit Rate (advanced only)
        lbl_rec = ttk.Label(right, text="Recruit Rate:")
        lbl_rec.grid(row=row, column=0, sticky="e", padx=4)
        sb_rec = ttk.Spinbox(right, from_=-100, to=100,
                             textvariable=self._recruit_var, width=6)
        sb_rec.grid(row=row, column=1, sticky="w")
        self._advanced_widgets.extend([lbl_rec, sb_rec])
        row += 1

        # Recruit Rate 2 (advanced only)
        lbl_rec2 = ttk.Label(right, text="Recruit Rate 2:")
        lbl_rec2.grid(row=row, column=0, sticky="e", padx=4)
        sb_rec2 = ttk.Spinbox(right, from_=-100, to=100,
                      textvariable=self._recruit2_var, width=6)
        sb_rec2.grid(row=row, column=1, sticky="w")
        self._advanced_widgets.extend([lbl_rec2, sb_rec2])
        row += 1

        # Size (advanced only)
        lbl_size = ttk.Label(right, text="Size:")
        lbl_size.grid(row=row, column=0, sticky="e", padx=4)
        sb_size = ttk.Spinbox(right, from_=1, to=4,
                              textvariable=self._size_var, width=4)
        sb_size.grid(row=row, column=1, sticky="w")
        self._advanced_widgets.extend([lbl_size, sb_size])
        row += 1

        # Apply button
        ttk.Button(
            right, text="Apply Changes", command=self._apply_changes
        ).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_search_changed(self, *_) -> None:
        query = self._search_var.get().lower()
        self._listbox.delete(0, tk.END)
        if self._table is None:
            return
        pos = 0
        for entry in self._table:
            label = f"#{entry.index:03d} {entry.name}"
            if entry.species_index != entry.index:
                label += f" [species {entry.species_index:03d}]"
            if query in label.lower():
                self._listbox.insert(tk.END, label)
                self._colorize_item(pos, entry)
                pos += 1

    def _on_select(self, _event=None) -> None:
        sel = self._listbox.curselection()
        if not sel or self._table is None:
            return
        label = self._listbox.get(sel[0])
        idx = int(label.split()[0].lstrip("#"))
        self._picker_var.set(label)
        entry = self._table[idx]
        self._current_entry = entry
        self._populate_fields(entry)
        self._update_portrait()

    def _on_pick(self, _event=None) -> None:
        if self._table is None:
            return
        label = self._picker_var.get()
        idx = self._picker_lookup.get(label)
        if idx is None:
            return
        entry = self._table[idx]
        self._current_entry = entry
        self._populate_fields(entry)
        self._update_portrait()

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

    def _on_field_changed(self, _event=None) -> None:
        if self._current_entry is None:
            return
        self._apply_changes(notify=False)

    def _on_stat_changed(self, *_args) -> None:
        if self._current_entry is None:
            return
        self._update_bst()

    def _apply_changes(self, notify: bool = True) -> None:
        entry = self._current_entry
        if entry is None:
            return
        old_snapshot = deepcopy(entry) if (notify and self._on_change) else None
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
        entry.pre_evo_index = max(0, self._parse_id_option(self._pre_evo_var.get()))
        entry.evo_method = max(0, self._parse_id_option(self._evo_method_var.get()))
        entry.evo_param1 = max(0, min(65535, self._evo_param1_var.get()))
        entry.evo_param2 = max(0, self._parse_id_option(self._evo_req_var.get()))
        for field, _ in self._STAT_FIELDS:
            setattr(entry, field, max(1, min(255, self._stat_vars[field].get())))
        entry.recruit_rate1 = max(-128, min(127, self._recruit_var.get()))
        entry.recruit_rate2 = max(-32768, min(32767, self._recruit2_var.get()))
        entry.size = max(1, min(4, self._size_var.get()))
        self._update_bst()
        if notify:
            if self._on_change and old_snapshot is not None:
                self._on_change(
                    "pokemon", entry.index, entry.name,
                    old_snapshot, deepcopy(entry),
                )
            if self._on_modified:
                self._on_modified()

    # ------------------------------------------------------------------
    # Portrait
    # ------------------------------------------------------------------

    def set_portrait_container(self, container) -> None:
        """Provide the kaomado PortraitContainer (or None to clear)."""
        self._portrait_container = container
        self._update_portrait()

    def _update_portrait(self) -> None:
        if self._sprite_viewer is None:
            return
        if self._current_entry is None or self._portrait_container is None:
            self._sprite_viewer.set_portrait(None)
            return
        emotion = self._sprite_viewer.get_emotion()
        img = self._portrait_container.get_portrait(
            self._current_entry.species_index, emotion
        )
        self._sprite_viewer.set_portrait(img)

    # ------------------------------------------------------------------
    # Field population helpers
    # ------------------------------------------------------------------

    def _populate_fields(self, entry: PokemonEntry) -> None:
        self._type1_var.set(
            TYPE_NAMES[entry.type1]
            if 0 <= entry.type1 < len(TYPE_NAMES) else "???"
        )
        self._type2_var.set(
            TYPE_NAMES[entry.type2]
            if 0 <= entry.type2 < len(TYPE_NAMES) else "???"
        )
        self._ability1_var.set(
            ABILITY_NAMES[entry.ability1]
            if 0 <= entry.ability1 < len(ABILITY_NAMES) else ""
        )
        self._ability2_var.set(
            ABILITY_NAMES[entry.ability2]
            if 0 <= entry.ability2 < len(ABILITY_NAMES) else ""
        )
        self._exp_group_var.set(
            EXP_GROUP_NAMES[entry.exp_group]
            if 0 <= entry.exp_group < len(EXP_GROUP_NAMES) else ""
        )
        self._pre_evo_var.set(self._format_id_option(entry.pre_evo_index, _PRE_EVO_OPTIONS))
        self._evo_method_var.set(self._format_id_option(entry.evo_method, _EVO_METHOD_OPTIONS))
        self._evo_param1_var.set(entry.evo_param1)
        self._evo_req_var.set(self._format_id_option(entry.evo_param2, _EVO_REQUIREMENT_OPTIONS))
        self._recruit_var.set(entry.recruit_rate1)
        self._recruit2_var.set(entry.recruit_rate2)
        self._size_var.set(entry.size)
        for field, _ in self._STAT_FIELDS:
            self._stat_vars[field].set(getattr(entry, field, 0))
        self._update_bst()

    def _update_bst(self) -> None:
        total = sum(v.get() for v in self._stat_vars.values())
        self._bst_var.set(f"BST: {total}")

