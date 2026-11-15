from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def snapshot() -> dict:
    return json.loads((ROOT / "examples" / "risk_core_sample.json").read_text())


def clone(value):
    return copy.deepcopy(value)
