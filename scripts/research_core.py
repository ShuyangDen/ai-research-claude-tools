#!/usr/bin/env python3
"""Run the repo-local research-core CLI without a global installation."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "packages" / "research-core" / "src"
sys.path.insert(0, str(SOURCE))

from research_core.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
