"""Command line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyst import analyze
from .env import load_local_env
from .report import build_view_model, render_html


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    load_local_env(root)
    parser = argparse.ArgumentParser(description="Generate a pod risk analysis report")
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--provider", choices=["mock", "openai", "anthropic"], default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("output/reports"))
    args = parser.parse_args()

    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    analysis, provider = analyze(snapshot, args.provider)
    view_model = build_view_model(snapshot, analysis, provider)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "analysis.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "report.json").write_text(
        json.dumps(view_model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    template = root / "web" / "report_template.html"
    render_html(view_model, template, args.output_dir / "index.html")
    print(f"Generated {args.output_dir / 'index.html'} using provider={provider}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
