"""Build the report view model and self-contained interactive HTML."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def build_view_model(snapshot: dict, analysis: dict, provider: str) -> dict:
    analyses = {item["pod_id"]: item for item in analysis["pods"]}
    pods = []
    for source in snapshot["pods"]:
        pod = {**source, "analysis": analyses[source["pod_id"]]}
        pod["chart_quadrant"] = chart_quadrant(
            source["performance"]["pnl_percent"],
            source["decision_skill"]["aggregate_percentile"],
        )
        pods.append(pod)
    return {
        "report": {
            "title": "Millenium Pod Risk Review",
            "run_id": snapshot["run_id"],
            "as_of": snapshot["as_of"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "analysis_version": analysis["analysis_version"],
            "schema_version": snapshot["schema_version"],
        },
        "pods": pods,
    }


def chart_quadrant(pnl: float, skill: float) -> str:
    if pnl >= 0 and skill >= 50:
        return "skilled"
    if pnl >= 0 and skill < 50:
        return "lucky"
    if pnl < 0 and skill >= 50:
        return "unlucky"
    return "broken"


def render_html(view_model: dict, template_path: Path, output_path: Path) -> None:
    template = template_path.read_text(encoding="utf-8")
    report_json = json.dumps(view_model, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("__REPORT_DATA__", report_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
