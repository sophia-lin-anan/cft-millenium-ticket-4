from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import ROOT, snapshot

from millenium_analyst.analyst import analyze
from millenium_analyst.pdf_report import render_pdf
from millenium_analyst.report import build_view_model


class CliIntegrationTests(unittest.TestCase):
    def test_mock_cli_generates_all_report_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp, "reports")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "run_mvp.py"),
                    str(ROOT / "examples" / "risk_core_sample.json"),
                    "--provider",
                    "mock",
                    "--output-dir",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("provider=mock", completed.stdout)
            self.assertEqual({path.name for path in output.iterdir()}, {"analysis.json", "report.json", "index.html"})
            analysis = json.loads((output / "analysis.json").read_text())
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(len(analysis["pods"]), 4)
            self.assertEqual(report["report"]["provider"], "mock")
            self.assertIn("Pod decision memo", (output / "index.html").read_text())


@unittest.skipUnless(shutil.which("pdftotext") and shutil.which("pdfinfo"), "Poppler tools required")
class PdfIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import reportlab  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest("reportlab required") from exc

    def test_pdf_contains_every_html_narrative_field_and_paginates_actions(self):
        source = snapshot()
        analysis, provider = analyze(source, "mock")
        view = build_view_model(source, analysis, provider)
        expected_pages = 1 + sum(
            2 + max(0, len(pod["analysis"]["recommended_actions"]) - 1) for pod in view["pods"]
        )
        pdf_temp_root = ROOT / "tmp" / "pdfs"
        pdf_temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=pdf_temp_root) as temp:
            pdf = Path(temp, "report.pdf")
            text_file = Path(temp, "report.txt")
            render_pdf(view, pdf)
            self.assertGreater(pdf.stat().st_size, 10_000)
            info = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True).stdout
            pages = int(re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE).group(1))
            self.assertEqual(pages, expected_pages)
            subprocess.run(["pdftotext", str(pdf), str(text_file)], check=True)
            pdf_text = _normalize(text_file.read_text())

        for pod in view["pods"]:
            analysis = pod["analysis"]
            expected = [
                analysis["verdict"]["summary"],
                analysis["narrative"]["why_this_verdict"],
                analysis["narrative"]["alternative_explanation"],
                analysis["narrative"]["what_would_change_verdict"],
                analysis["narrative"]["decision_skill_analysis"],
                analysis["narrative"]["risk_analysis"],
                analysis["narrative"]["conclusion"],
            ]
            expected.extend(
                value
                for item in analysis["evidence"] + analysis["counterevidence"]
                for value in (item["metric_id"], item["observation"], item["interpretation"])
            )
            expected.extend(
                value
                for action in analysis["recommended_actions"]
                for value in (
                    action["action"],
                    action["rationale"],
                    action["why_now"],
                    action["next_step"],
                    action["success_signal"],
                    action["review_horizon"],
                )
            )
            for value in expected:
                with self.subTest(pod=pod["pod_id"], value=value[:40]):
                    self.assertIn(_normalize(value), pdf_text)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


if __name__ == "__main__":
    unittest.main()
