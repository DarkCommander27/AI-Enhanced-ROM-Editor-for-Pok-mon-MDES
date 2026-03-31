"""Entry point for the ROM editor."""

import sys


def _set_windows_dpi_awareness() -> None:
    """Enable per-monitor DPI awareness on Windows before any Tk window is created.

    Without this the OS bitmap-scales the window, producing a blurry UI on
    HiDPI / 4K monitors.  The call is a no-op on non-Windows platforms.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # SetProcessDpiAwareness(2) = PROCESS_PER_MONITOR_DPI_AWARE (Win 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Fallback: SetProcessDPIAware() (Vista+)
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _set_appusermodelid() -> None:
    """Set Windows taskbar / ALT+TAB app identity so the icon groups correctly."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "MDESRomEditor.ExplSkySuite.v1"
        )
    except Exception:
        pass


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
    # Windows-specific setup: must run before any Tk window is created.
    _set_windows_dpi_awareness()
    _set_appusermodelid()

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
