from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from support import ROOT

from millenium_analyst.env import load_local_env


class LocalEnvironmentTests(unittest.TestCase):
    def test_loads_allowlisted_values_and_strips_matching_quotes(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {}, clear=True):
            Path(temp, ".env.local").write_text(
                "ANALYST_PROVIDER='anthropic'\nANTHROPIC_API_KEY=secret\nUNSAFE_KEY=blocked\n"
            )
            load_local_env(Path(temp))
            self.assertEqual(os.environ["ANALYST_PROVIDER"], "anthropic")
            self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "secret")
            self.assertNotIn("UNSAFE_KEY", os.environ)

    def test_local_file_precedes_env_and_existing_process_values_win(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            os.environ, {"ANALYST_MODEL": "process-model"}, clear=True
        ):
            Path(temp, ".env.local").write_text("ANALYST_MODEL=local-model\n")
            Path(temp, ".env").write_text("ANALYST_MODEL=fallback-model\nOPENAI_API_KEY=fallback-key\n")
            load_local_env(Path(temp))
            self.assertEqual(os.environ["ANALYST_MODEL"], "process-model")
            self.assertEqual(os.environ["OPENAI_API_KEY"], "fallback-key")

    def test_file_contents_are_not_executed_as_shell(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {}, clear=True):
            marker = Path(temp, "should-not-exist")
            Path(temp, ".env.local").write_text(
                f"ANTHROPIC_API_KEY=$(touch {marker})\nexport OPENAI_API_KEY=bad\n"
            )
            load_local_env(Path(temp))
            self.assertFalse(marker.exists())
            self.assertEqual(os.environ["ANTHROPIC_API_KEY"], f"$(touch {marker})")
            self.assertNotIn("OPENAI_API_KEY", os.environ)

    def test_repository_template_contains_no_live_key_prefix(self):
        text = (ROOT / ".env.example").read_text()
        self.assertNotIn("sk-" + "ant-", text)
        self.assertNotIn("sk-" + "proj-", text)


if __name__ == "__main__":
    unittest.main()
