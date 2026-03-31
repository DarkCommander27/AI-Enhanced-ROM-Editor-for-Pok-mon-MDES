"""Undo/redo change history for ROM edits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class ChangeRecord:
    """A single recorded change to a data entry."""

    entity_type: str   # "pokemon", "move", or "dungeon"
    index: int         # entry index in its table
    name: str          # display name of the entry (e.g. "Pikachu")
    old_snapshot: Any  # deep copy of entry BEFORE the change
    new_snapshot: Any  # deep copy of entry AFTER the change


class ChangeHistory:
    """Fixed-capacity undo/redo history for ROM edits.

    Usage::

        history = ChangeHistory(max_size=50)
        history.set_on_change(my_callback)

        # Before modifying an entry:
        old = deepcopy(entry)
        # ...make changes...
        history.push(ChangeRecord("pokemon", entry.index, entry.name, old, deepcopy(entry)))

        # Undo most recent change:
        rec = history.undo()   # returns ChangeRecord or None
        if rec:
            restore_entry(rec.entity_type, rec.index, rec.old_snapshot)
    """

    def __init__(self, max_size: int = 50) -> None:
        self._records: list[ChangeRecord] = []
        # _pos points ONE PAST the last committed record (= len of undo stack)
        self._pos: int = 0
        self._max_size = max_size
        self._on_change: Optional[Callable[[list[ChangeRecord]], None]] = None

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_on_change(
        self, callback: Callable[[list[ChangeRecord]], None]
    ) -> None:
        """Register a callback invoked after every push / undo / redo.

        The callback receives the current committed records list.
        """
        self._on_change = callback

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def records(self) -> list[ChangeRecord]:
        """All committed records in chronological order (up to current pos)."""
        return self._records[: self._pos]

    def has_undo(self) -> bool:
        return self._pos > 0

    def has_redo(self) -> bool:
        return self._pos < len(self._records)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def push(self, record: ChangeRecord) -> None:
        """Commit a new change, discarding any pending redo entries."""
        # Drop the redo branch
        del self._records[self._pos :]
        # Enforce maximum history size by removing the oldest record
        if len(self._records) >= self._max_size:
            self._records.pop(0)
        self._records.append(record)
        self._pos = len(self._records)
        self._notify()

    def undo(self) -> Optional[ChangeRecord]:
        """Move back one step and return the record to reverse, or None."""
        if self._pos == 0:
            return None
        self._pos -= 1
        rec = self._records[self._pos]
        self._notify()
        return rec

    def redo(self) -> Optional[ChangeRecord]:
        """Move forward one step and return the record to reapply, or None."""
        if self._pos >= len(self._records):
            return None
        rec = self._records[self._pos]
        self._pos += 1
        self._notify()
        return rec

    def clear(self) -> None:
        """Discard all history entries."""
        self._records.clear()
        self._pos = 0
        self._notify()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _notify(self) -> None:
        if self._on_change:
            self._on_change(self.records)
