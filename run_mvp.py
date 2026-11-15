#!/usr/bin/env python3
"""Run the MVP from a source checkout without installing a package."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from millenium_analyst.cli import main

raise SystemExit(main())
