"""Raw text-like file editor tab.

This is a conservative editor intended for localization exploration and quick
string tweaks in ROM files that appear text-oriented (for example /MESSAGE/*).
Writes are size-preserving to avoid breaking ROM file layout.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from rom_editor.nds.rom import NDSRom


class TextEditorTab(ttk.Frame):
    """Tab for editing text-like ROM files with strict size preservation."""

    def __init__(
        self,
        parent: ttk.Notebook,
        on_modified: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent)
        self._on_modified = on_modified

        self._rom: Optional[NDSRom] = None
        self._current_path: Optional[str] = None
        self._raw_by_path: dict[str, bytes] = {}
        self._modified_by_path: dict[str, bytes] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="ns", padx=4, pady=4)

        ttk.Label(left, text="Search files:").pack(anchor="w")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ttk.Entry(left, textvariable=self._search_var, width=28).pack(fill="x")

        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True)
        self._listbox = tk.Listbox(list_frame, width=34, exportselection=False)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._listbox.pack(side="left", fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        self._path_var = tk.StringVar(value="No file selected")
        ttk.Label(right, textvariable=self._path_var).grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )

        ttk.Label(
            right,
            text=(
                "Raw mode: saves with latin-1 and keeps original byte size. "
                "Longer text is rejected."
            ),
            foreground="#7a4f1f",
        ).grid(row=1, column=0, sticky="w", pady=(0, 4))

        text_frame = ttk.Frame(right)
        text_frame.grid(row=2, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self._text = tk.Text(text_frame, wrap="word", undo=True)
        text_sb = ttk.Scrollbar(text_frame, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=text_sb.set)
        self._text.grid(row=0, column=0, sticky="nsew")
        text_sb.grid(row=0, column=1, sticky="ns")

        btn_row = ttk.Frame(right)
        btn_row.grid(row=3, column=0, sticky="ew", pady=6)
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        ttk.Button(btn_row, text="Apply to File", command=self._apply_current).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(btn_row, text="Revert File", command=self._revert_current).grid(
            row=0, column=1, sticky="ew"
        )

    def load_rom(self, rom: NDSRom) -> None:
        self._rom = rom
        self._current_path = None
        self._raw_by_path.clear()
        self._modified_by_path.clear()

        paths = [p for p in rom.list_files() if self._is_text_candidate(p)]
        for path in paths:
            self._raw_by_path[path] = rom.read_file(path)

        self._refresh_list(paths)
        self._path_var.set(
            "No text-like files found" if not paths else "Select a file to edit"
        )
        self._text.delete("1.0", tk.END)

    def get_modified_files(self) -> dict[str, bytes]:
        return dict(self._modified_by_path)

    @staticmethod
    def _is_text_candidate(path: str) -> bool:
        up = path.upper()
        return (
            "/MESSAGE/" in up
            or up.endswith(".STR")
            or up.endswith(".MSG")
            or up.endswith(".TXT")
            or "MESSAGE" in up
        )

    def _refresh_list(self, paths: list[str]) -> None:
        self._listbox.delete(0, tk.END)
        for path in paths:
            marker = "* " if path in self._modified_by_path else "  "
            self._listbox.insert(tk.END, f"{marker}{path}")

    def _on_search(self, *_args) -> None:
        q = self._search_var.get().strip().lower()
        paths = sorted(self._raw_by_path.keys())
        if q:
            paths = [p for p in paths if q in p.lower()]
        self._refresh_list(paths)

    def _on_select(self, _event=None) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        line = self._listbox.get(sel[0])
        path = line[2:]
        self._current_path = path
        self._path_var.set(path)

        data = self._modified_by_path.get(path, self._raw_by_path.get(path, b""))
        text = data.rstrip(b"\x00").decode("latin-1", errors="replace")
        self._text.delete("1.0", tk.END)
        self._text.insert("1.0", text)

    def _apply_current(self) -> None:
        path = self._current_path
        if not path:
            return
        original = self._raw_by_path.get(path)
        if original is None:
            return

        edited_text = self._text.get("1.0", tk.END).rstrip("\n")
        try:
            encoded = edited_text.encode("latin-1", errors="strict")
        except UnicodeEncodeError:
            messagebox.showerror(
                "Encoding error",
                "This file is in raw latin-1 mode. Use only latin-1 characters.",
            )
            return

        if len(encoded) > len(original):
            messagebox.showerror(
                "Too long",
                (
                    f"Edited content is {len(encoded)} bytes, but this file allows "
                    f"at most {len(original)} bytes in safe mode."
                ),
            )
            return

        new_data = encoded + (b"\x00" * (len(original) - len(encoded)))
        if new_data == original:
            self._modified_by_path.pop(path, None)
        else:
            self._modified_by_path[path] = new_data

        self._on_search()
        if self._on_modified:
            self._on_modified()

    def _revert_current(self) -> None:
        path = self._current_path
        if not path:
            return
        self._modified_by_path.pop(path, None)
        data = self._raw_by_path.get(path, b"")
        text = data.rstrip(b"\x00").decode("latin-1", errors="replace")
        self._text.delete("1.0", tk.END)
        self._text.insert("1.0", text)
        self._on_search()
