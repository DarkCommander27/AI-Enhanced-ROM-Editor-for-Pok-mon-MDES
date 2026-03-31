"""Entry point for the ROM editor."""

import sys


def _format_tkinter_install_help() -> str:
    """Return platform-specific instructions for installing tkinter."""
    if sys.platform.startswith("linux"):
        return (
            "Install your distro's tkinter package, then re-run the app.\n"
            "Debian/Ubuntu: sudo apt update && sudo apt install -y python3-tk\n"
            "Fedora: sudo dnf install -y python3-tkinter\n"
            "Arch: sudo pacman -S tk"
        )

    if sys.platform == "darwin":
        return (
            "Install a Python build that includes Tk support (for example from python.org), "
            "or install Tk via Homebrew and recreate your environment."
        )

    return (
        "Reinstall Python with tkinter/Tk support enabled, then recreate your virtual environment."
    )


def main() -> None:
    """Launch the ROM editor application."""
    try:
        from rom_editor.ui.app import ROMEditorApp
    except ModuleNotFoundError as exc:
        if exc.name == "tkinter":
            print("Error: tkinter is required to run the ROM Editor GUI.", file=sys.stderr)
            print(_format_tkinter_install_help(), file=sys.stderr)
            raise SystemExit(2)
        raise

    app = ROMEditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
