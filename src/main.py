#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# Thermal Printer
# Credits and Acknowledgments
#
# This project builds upon the incredible reverse engineering work of the
# maker and hacker community who cracked the Core Innovation CTP-500
# Bluetooth thermal printer protocol.
#
# ORIGINAL RESEARCH AND DEVELOPMENT
#
#   Mel (ThirtyThreeDown Studio)
#     Primary developer of the original CTP500PrinterApp
#     Bluetooth protocol analysis and GUI implementation
#     https://thirtythreedown.com
#     https://github.com/thirtythreedown/CTP500PrinterApp
#
#   voidsshadows
#     Creator of CorePrint print server
#     Stripped-down Python implementation that formed the foundation
#     https://github.com/voidsshadows/CorePrint-print-server
#
# SECKC CONTRIBUTORS
# Kansas City's Hacker Hive - https://seckc.org
#
#   bitflip
#     Shared critical code resources and collaboration
#
#   Tsathoggualware
#     Research and development support
#
#   Reid
#     Research and development support
#
# COMMUNITY CONTRIBUTORS
#
#   onezeronull, MaikelChan, rbaron, WerWolv
#     Prior thermal printer research and documentation
#
#   Nathaniel (Doodad/Dither Me This)
#     Dithering algorithm inspiration
#
#   Hacking Modern Life (YouTube)
#     Bluetooth reverse engineering tutorials
#
# SPECIAL THANKS
#
# "To all the mad lasses and lads in the maker community whose thermal
# printer research since 2014 made this possible."
#   — Mel, ThirtyThreeDown Studio
#
# ------------------------------------------------------------------------------
# License: This project is open source.
# Original CTP500PrinterApp by ThirtyThreeDown Studio.
# CorePrint by voidsshadows (AGPL-3.0).
# ------------------------------------------------------------------------------
#
# Usage:
#     python -m src.main
#     or
#     python src/main.py
# ------------------------------------------------------------------------------

import sys
from pathlib import Path

# Ensure src directory is in path for imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir.parent))


def main() -> None:
    try:
        from src.gui.app import run_app
        run_app()
    except ImportError as e:
        print(f"Import error: {e}")
        print("\nMake sure all dependencies are installed:")
        print("  pip install customtkinter pillow pyyaml numpy")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
