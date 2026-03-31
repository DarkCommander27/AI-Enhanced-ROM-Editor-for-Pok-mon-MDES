"""Portrait preview widget for the Pokémon editor.

Shows a 40×40 portrait portrait scaled to 80×80 on a dark canvas, an emotion
spinner (0–39), and an "Export PNG" button that saves at 4× resolution.

Requires Pillow (``pillow >= 10.0.0``).  If Pillow is absent the widget
degrades gracefully to a plain text placeholder.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk
from typing import Optional

try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except ImportError:  # pragma: no cover
    _HAS_PIL = False

_CANVAS_SIZE = 80   # display size in pixels (2× the 40×40 source)


class SpriteViewer(ttk.LabelFrame):
    """A compact portrait preview widget.

    Attributes
    ----------
    on_emotion_changed : optional callable(emotion: int)
        Called whenever the emotion spinner changes value.
    """

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, text="Portrait", **kwargs)

        self._photo: Optional["ImageTk.PhotoImage"] = None
        self._image: Optional["Image.Image"] = None
        self._theme_colors = {
            "canvas_bg": "#2a2a2a",
            "panel_soft_2": "#555",
            "text_muted": "#666",
            "text": "#f0f0f0",
        }

        # Canvas (or fallback label)
        if _HAS_PIL:
            self._canvas = tk.Canvas(
                self,
                width=_CANVAS_SIZE,
                height=_CANVAS_SIZE,
                bg=self._theme_colors["canvas_bg"],
                highlightthickness=1,
                highlightbackground=self._theme_colors["panel_soft_2"],
            )
            self._canvas.pack(padx=4, pady=(4, 2))
            self._set_placeholder()
        else:
            ttk.Label(
                self, text="Pillow\nnot installed",
                anchor="center", width=12,
            ).pack(padx=4, pady=4)

        # Controls row
        ctrl = ttk.Frame(self)
        ctrl.pack(fill="x", padx=4, pady=(0, 4))

        ttk.Label(ctrl, text="Emo:").pack(side="left")
        self._emotion_var = tk.IntVar(value=0)
        ttk.Spinbox(
            ctrl, from_=0, to=39, width=4,
            textvariable=self._emotion_var,
            command=self._on_spin,
        ).pack(side="left", padx=(2, 6))

        ttk.Button(ctrl, text="Export PNG", command=self._export).pack(
            side="left")

        self.on_emotion_changed: Optional[callable] = None   # type: ignore[type-arg]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_portrait(self, img: Optional["Image.Image"]) -> None:
        """Display *img* (40×40 PIL Image) or a "no portrait" placeholder."""
        self._image = img
        if not _HAS_PIL:
            return
        self._canvas.delete("all")
        if img is None:
            self._set_placeholder()
        else:
            scaled = img.resize((_CANVAS_SIZE, _CANVAS_SIZE),
                                Image.Resampling.NEAREST)
            self._photo = ImageTk.PhotoImage(scaled)
            self._canvas.create_image(0, 0, anchor="nw", image=self._photo)

    def get_emotion(self) -> int:
        """Return the currently selected emotion index."""
        return self._emotion_var.get()

    def set_theme(self, colors: dict[str, str]) -> None:
        """Apply app theme colors to the preview widget."""
        self._theme_colors.update(colors)
        if not _HAS_PIL:
            return
        self._canvas.configure(
            bg=self._theme_colors.get("canvas_bg", "#2a2a2a"),
            highlightbackground=self._theme_colors.get("panel_soft_2", "#555"),
            highlightcolor=self._theme_colors.get("accent", "#8e6bff"),
        )
        self.set_portrait(self._image)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_placeholder(self) -> None:
        self._canvas.create_text(
            _CANVAS_SIZE // 2, _CANVAS_SIZE // 2,
            text="No portrait",
            fill=self._theme_colors.get("text_muted", "#666"),
            font=("TkDefaultFont", 8),
        )
        self._photo = None

    def _on_spin(self) -> None:
        if self.on_emotion_changed:
            self.on_emotion_changed(self._emotion_var.get())

    def _export(self) -> None:
        if self._image is None:
            return
        path = filedialog.asksaveasfilename(
            title="Export Portrait as PNG",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
        )
        if not path:
            return
        # Save at 4× (160×160) for usable resolution
        big = self._image.resize((160, 160), Image.Resampling.NEAREST)
        big.save(path)
