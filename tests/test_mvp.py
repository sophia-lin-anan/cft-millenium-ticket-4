from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from millenium_analyst.analyst import analyze
from millenium_analyst.contracts import ContractError, validate_analysis, validate_snapshot
from millenium_analyst.report import build_view_model, chart_quadrant, render_html


class MvpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads((ROOT / "examples/risk_core_sample.json").read_text())

    def test_sample_contract(self):
        self.assertEqual(validate_snapshot(self.snapshot).data["schema_version"], "1.0")

    def test_quadrants(self):
        self.assertEqual(chart_quadrant(1, 51), "skilled")
        self.assertEqual(chart_quadrant(1, 49), "lucky")
        self.assertEqual(chart_quadrant(-1, 51), "unlucky")
        self.assertEqual(chart_quadrant(-1, 49), "broken")

    def test_mock_provider_covers_all_quadrants(self):
        analysis, provider = analyze(self.snapshot, "mock")
        actual = {item["pod_id"]: item["verdict"]["classification"] for item in analysis["pods"]}
        self.assertEqual(provider, "mock")
        self.assertEqual(
            actual,
            {"Pod A": "unlucky", "Pod B": "broken", "Pod C": "lucky", "Pod D": "skilled"},
        )

    def test_unknown_metric_citation_is_rejected(self):
        analysis, _ = analyze(self.snapshot, "mock")
        analysis["pods"][0]["evidence"][0]["metric_id"] = "invented.metric"
        with self.assertRaises(ContractError):
            validate_analysis(self.snapshot, analysis)

    def test_incomplete_recommendation_is_rejected(self):
        analysis, _ = analyze(self.snapshot, "mock")
        del analysis["pods"][0]["recommended_actions"][0]["why_now"]
        with self.assertRaises(ContractError):
            validate_analysis(self.snapshot, analysis)

    def test_report_is_self_contained(self):
        analysis, provider = analyze(self.snapshot, "mock")
        first = analysis["pods"][0]
        self.assertTrue(first["narrative"]["why_this_verdict"])
        self.assertTrue(first["recommended_actions"][0]["next_step"])
        view = build_view_model(self.snapshot, analysis, provider)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "index.html"
            render_html(view, ROOT / "web/report_template.html", output)
            html = output.read_text()
        self.assertIn("Pod decision memo", html)
        self.assertIn("demo-2026-11-15", html)
        self.assertNotIn("__REPORT_DATA__", html)


if __name__ == "__main__":
    unittest.main()
