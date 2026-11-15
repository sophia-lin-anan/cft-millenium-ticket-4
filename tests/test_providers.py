from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from support import snapshot

from millenium_analyst.providers.anthropic_provider import AnthropicProvider
from millenium_analyst.providers.base import ProviderError
from millenium_analyst.providers.openai_provider import OpenAIProvider


SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}}


class AnthropicProviderTests(unittest.TestCase):
    def test_requires_non_placeholder_key(self):
        for env in ({}, {"ANTHROPIC_API_KEY": "replace-with-key"}):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ProviderError):
                    AnthropicProvider().analyze(snapshot(), "instructions", SCHEMA)

    @patch("millenium_analyst.providers.anthropic_provider.post_json")
    def test_uses_default_model_for_missing_or_placeholder_configuration(self, post):
        post.return_value = {
            "content": [{"type": "tool_use", "name": "submit_risk_analysis", "input": {"ok": True}}]
        }
        for configured in (None, "replace-with-model-id"):
            env = {"ANTHROPIC_API_KEY": "test-key"}
            if configured is not None:
                env["ANALYST_MODEL"] = configured
            with self.subTest(configured=configured), patch.dict(os.environ, env, clear=True):
                result = AnthropicProvider().analyze(snapshot(), "instructions", SCHEMA)
                self.assertEqual(result, {"ok": True})
                payload = post.call_args.args[1]
                self.assertEqual(payload["model"], AnthropicProvider.default_model)
                self.assertEqual(payload["tool_choice"], {"type": "tool", "name": "submit_risk_analysis"})
                self.assertEqual(payload["tools"][0]["input_schema"], SCHEMA)

    @patch("millenium_analyst.providers.anthropic_provider.post_json")
    def test_honors_custom_model_and_headers(self, post):
        post.return_value = {
            "content": [{"type": "tool_use", "name": "submit_risk_analysis", "input": {"ok": True}}]
        }
        env = {
            "ANTHROPIC_API_KEY": "test-key",
            "ANALYST_MODEL": "custom-model",
            "ANTHROPIC_VERSION": "test-version",
            "ANTHROPIC_BASE_URL": "https://example.invalid/messages",
        }
        with patch.dict(os.environ, env, clear=True):
            AnthropicProvider().analyze(snapshot(), "instructions", SCHEMA)
        url, payload, headers = post.call_args.args
        self.assertEqual(url, env["ANTHROPIC_BASE_URL"])
        self.assertEqual(payload["model"], "custom-model")
        self.assertEqual(headers["x-api-key"], "test-key")
        self.assertEqual(headers["anthropic-version"], "test-version")

    @patch("millenium_analyst.providers.anthropic_provider.post_json", return_value={"content": []})
    def test_rejects_response_without_required_tool_payload(self, _post):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True):
            with self.assertRaises(ProviderError):
                AnthropicProvider().analyze(snapshot(), "instructions", SCHEMA)


class OpenAIProviderTests(unittest.TestCase):
    def test_requires_key_and_model(self):
        for env in ({}, {"OPENAI_API_KEY": "key"}, {"ANALYST_MODEL": "model"}):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ProviderError):
                    OpenAIProvider().analyze(snapshot(), "instructions", SCHEMA)

    @patch("millenium_analyst.providers.openai_provider.post_json")
    def test_builds_strict_schema_request_and_parses_output(self, post):
        post.return_value = {
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": json.dumps({"ok": True})}]}
            ]
        }
        env = {"OPENAI_API_KEY": "test-key", "ANALYST_MODEL": "test-model"}
        with patch.dict(os.environ, env, clear=True):
            result = OpenAIProvider().analyze(snapshot(), "instructions", SCHEMA)
        self.assertEqual(result, {"ok": True})
        _url, payload, headers = post.call_args.args
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertEqual(payload["text"]["format"]["schema"], SCHEMA)
        self.assertEqual(headers["Authorization"], "Bearer test-key")

    @patch("millenium_analyst.providers.openai_provider.post_json")
    def test_rejects_non_json_or_missing_output(self, post):
        env = {"OPENAI_API_KEY": "test-key", "ANALYST_MODEL": "test-model"}
        with patch.dict(os.environ, env, clear=True):
            post.return_value = {
                "output": [{"type": "message", "content": [{"type": "output_text", "text": "not-json"}]}]
            }
            with self.assertRaises(ProviderError):
                OpenAIProvider().analyze(snapshot(), "instructions", SCHEMA)
            post.return_value = {"output": []}
            with self.assertRaises(ProviderError):
                OpenAIProvider().analyze(snapshot(), "instructions", SCHEMA)


if __name__ == "__main__":
    unittest.main()
