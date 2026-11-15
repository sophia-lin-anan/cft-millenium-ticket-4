#!/usr/bin/env python3
"""Generate the printable report from output/reports/report.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from millenium_analyst.pdf_report import render_pdf

view = json.loads((ROOT / "output/reports/report.json").read_text(encoding="utf-8"))
output = ROOT / "output/pdf/millenium_pod_risk_review.pdf"
render_pdf(view, output)
print(f"Generated {output}")
