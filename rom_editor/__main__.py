"""Entry point for the ROM editor."""

import sys


def main() -> None:
    """Launch the ROM editor application."""
    from rom_editor.ui.app import ROMEditorApp

    app = ROMEditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
