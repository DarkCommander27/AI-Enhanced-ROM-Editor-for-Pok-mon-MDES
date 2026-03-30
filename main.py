#!/usr/bin/env python3
"""Launch the AI-Enhanced ROM Editor for Pokémon Mystery Dungeon: Explorers of Sky.

Usage
-----
  python main.py                # open the GUI
  python main.py --help         # show help
"""

import sys


def main() -> None:
    from rom_editor.__main__ import main as _main
    _main()


if __name__ == "__main__":
    main()
