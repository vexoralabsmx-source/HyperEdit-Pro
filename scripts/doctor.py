#!/usr/bin/env python3
"""Standalone script to run HyperEdit Pro diagnostics without installing the package."""

import sys
from pathlib import Path

# Ensure src is on sys.path
root_dir = Path(__file__).resolve().parent.parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from hyperedit.cli.commands.doctor_cmd import doctor_command  # noqa: E402

if __name__ == "__main__":
    doctor_command()

