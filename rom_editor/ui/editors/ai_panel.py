"""AI assistant panel."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from rom_editor.ai.assistant import AIAssistant, AssistantResponse, Suggestion


class AIPanel(ttk.Frame):
    """A panel that shows AI suggestions for the currently selected entry.

    The panel can be used stand-alone or embedded inside another editor tab.
    It accepts any of ``PokemonEntry``, ``MoveEntry`` or ``DungeonEntry`` and
    dispatches to the appropriate assistant method.
    """

    def __init__(
        self,
        parent,
        assistant: Optional[AIAssistant] = None,
        on_apply_suggestion: Optional[Callable[[Suggestion], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._assistant = assistant or AIAssistant()
        self._on_apply = on_apply_suggestion
        self._current_entry = None
        self._suggestions: list[Suggestion] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_entry(self, entry) -> None:
        """Set the entry to analyse when the user clicks 'Get AI Suggestion'."""
        self._current_entry = entry
        self._refresh_status()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # --- Top bar ---
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        self._status_label = ttk.Label(top, text="Select an entry and click 'Get Suggestion'")
        self._status_label.pack(side="left", fill="x", expand=True)

        self._suggest_btn = ttk.Button(
            top, text="Get AI Suggestion", command=self._run_suggestion
        )
        self._suggest_btn.pack(side="right")

        # Free-form question input
        ask_frame = ttk.LabelFrame(self, text="Ask a question")
        ask_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 4))
        ask_frame.columnconfigure(0, weight=1)

        self._question_var = tk.StringVar()
        ttk.Entry(ask_frame, textvariable=self._question_var).grid(
            row=0, column=0, sticky="ew", padx=4, pady=4)
        ttk.Button(ask_frame, text="Ask", command=self._run_ask).grid(
            row=0, column=1, padx=4, pady=4)

        # --- Response text area ---
        resp_frame = ttk.LabelFrame(self, text="AI Response")
        resp_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)
        resp_frame.columnconfigure(0, weight=1)
        resp_frame.rowconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._response_text = tk.Text(resp_frame, wrap="word", state="disabled",
                                      height=12, font=("TkDefaultFont", 9))
        sb = ttk.Scrollbar(resp_frame, orient="vertical",
                           command=self._response_text.yview)
        self._response_text.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")
        self._response_text.grid(row=0, column=0, sticky="nsew")

        # --- Suggestions list ---
        sugg_frame = ttk.LabelFrame(self, text="Suggestions")
        sugg_frame.grid(row=3, column=0, sticky="ew", padx=4, pady=(0, 4))
        sugg_frame.columnconfigure(0, weight=1)

        self._sugg_list = ttk.Treeview(
            sugg_frame,
            columns=("field", "old", "new", "reason"),
            show="headings",
            height=5,
        )
        self._sugg_list.heading("field",  text="Field")
        self._sugg_list.heading("old",    text="Old")
        self._sugg_list.heading("new",    text="New")
        self._sugg_list.heading("reason", text="Reason")
        self._sugg_list.column("field",  width=100)
        self._sugg_list.column("old",    width=50)
        self._sugg_list.column("new",    width=50)
        self._sugg_list.column("reason", width=300)
        self._sugg_list.grid(row=0, column=0, sticky="ew")

        ttk.Button(
            sugg_frame,
            text="Apply Selected Suggestion",
            command=self._apply_selected,
        ).grid(row=1, column=0, pady=4)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_status(self) -> None:
        if self._current_entry is None:
            msg = "No entry selected"
        else:
            name = getattr(self._current_entry, "name", repr(self._current_entry))
            src = "OpenAI" if self._assistant.is_openai_available() else "rule-based"
            msg = f"Selected: {name}  (AI source: {src})"
        self._status_label.configure(text=msg)

    def _run_suggestion(self) -> None:
        if self._current_entry is None:
            self._show_text("Please select an entry first.")
            return
        self._suggest_btn.configure(state="disabled", text="Thinking…")
        thread = threading.Thread(
            target=self._fetch_suggestion, daemon=True
        )
        thread.start()

    def _fetch_suggestion(self) -> None:
        try:
            entry = self._current_entry
            # Detect entry type by presence of characteristic attributes
            if hasattr(entry, "base_hp"):
                resp = self._assistant.suggest_pokemon_changes(entry)
            elif hasattr(entry, "base_power"):
                resp = self._assistant.suggest_move_changes(entry)
            elif hasattr(entry, "num_floors"):
                resp = self._assistant.suggest_dungeon_changes(entry)
            else:
                resp = self._assistant.ask(repr(entry))
        except Exception as exc:
            resp = AssistantResponse(
                message=f"Error: {exc}",
                suggestions=[],
                source="error",
            )
        # Must update GUI from main thread
        self.after(0, lambda: self._show_response(resp))

    def _run_ask(self) -> None:
        question = self._question_var.get().strip()
        if not question:
            return
        self._suggest_btn.configure(state="disabled", text="Thinking…")
        thread = threading.Thread(
            target=lambda: self.after(
                0,
                lambda: self._show_response(self._assistant.ask(question)),
            ),
            daemon=True,
        )
        thread.start()

    def _show_response(self, resp: AssistantResponse) -> None:
        self._suggest_btn.configure(state="normal", text="Get AI Suggestion")
        self._show_text(resp.message)
        self._suggestions = resp.suggestions
        self._sugg_list.delete(*self._sugg_list.get_children())
        for s in resp.suggestions:
            self._sugg_list.insert("", "end", values=(
                s.field, s.old_value, s.new_value, s.reason
            ))

    def _show_text(self, text: str) -> None:
        self._response_text.configure(state="normal")
        self._response_text.delete("1.0", "end")
        self._response_text.insert("end", text)
        self._response_text.configure(state="disabled")

    def _apply_selected(self) -> None:
        sel = self._sugg_list.selection()
        if not sel:
            return
        item = self._sugg_list.item(sel[0])
        field, _, new_val, _ = item["values"]
        # Find matching suggestion
        for s in self._suggestions:
            if s.field == field:
                if self._on_apply:
                    self._on_apply(s)
                break
