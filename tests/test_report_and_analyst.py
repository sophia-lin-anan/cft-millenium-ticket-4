from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from support import ROOT, clone, snapshot

from millenium_analyst.analyst import PROVIDERS, analyze
from millenium_analyst.providers.mock_provider import MockProvider
from millenium_analyst.report import build_view_model, chart_quadrant, render_html


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = snapshot()
        self.analysis, self.provider = analyze(self.snapshot, "mock")

    def test_quadrant_boundaries_match_verdict_semantics(self):
        cases = [
            ((0, 50), "skilled"),
            ((0, 49.999), "lucky"),
            ((-0.001, 50), "unlucky"),
            ((-0.001, 49.999), "broken"),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(chart_quadrant(*args), expected)

    def test_view_model_joins_analysis_by_pod_id_not_list_order(self):
        reversed_analysis = clone(self.analysis)
        reversed_analysis["pods"].reverse()
        view = build_view_model(self.snapshot, reversed_analysis, self.provider)
        for pod in view["pods"]:
            self.assertEqual(pod["pod_id"], pod["analysis"]["pod_id"])
            self.assertEqual(pod["chart_quadrant"], pod["analysis"]["verdict"]["classification"])

    def test_html_is_self_contained_and_escapes_script_terminator(self):
        view = build_view_model(self.snapshot, self.analysis, self.provider)
        view["pods"][0]["analysis"]["verdict"]["summary"] = "safe </script><script>alert(1)</script>"
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp, "index.html")
            render_html(view, ROOT / "web" / "report_template.html", output)
            html = output.read_text()
        self.assertNotIn("__REPORT_DATA__", html)
        self.assertIn("<\\/script><script>alert(1)<\\/script>", html)
        self.assertEqual(html.count('id="report-data"'), 1)
        self.assertIn("Pod decision memo", html)

    def test_report_metadata_records_provider_and_versions(self):
        view = build_view_model(self.snapshot, self.analysis, "anthropic")
        self.assertEqual(view["report"]["provider"], "anthropic")
        self.assertEqual(view["report"]["run_id"], self.snapshot["run_id"])
        self.assertEqual(view["report"]["analysis_version"], self.analysis["analysis_version"])


class AnalystPromptTests(unittest.TestCase):
    def test_prompt_contains_exact_per_pod_metric_allowlists(self):
        class CaptureProvider:
            name = "capture"
            instructions = ""

            def analyze(self, data, instructions, schema):
                del schema
                type(self).instructions = instructions
                return MockProvider().analyze(data, "", {})

        with patch.dict(PROVIDERS, {"capture": CaptureProvider}):
            analysis, provider = analyze(snapshot(), "capture")
        self.assertEqual(provider, "capture")
        self.assertEqual(len(analysis["pods"]), 4)
        prompt = CaptureProvider.instructions
        self.assertIn("Canonical metric_id allowlist", prompt)
        self.assertIn("- Pod A:", prompt)
        self.assertIn("risk_metrics.hidden_tail_risk", prompt)
        self.assertNotIn("risk_metrics.hidden_tail_risk.score", prompt)


if __name__ == "__main__":
    unittest.main()
