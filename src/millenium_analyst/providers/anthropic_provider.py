"""Anthropic Messages API adapter using a forced schema-backed tool call."""

from __future__ import annotations

import json
import os

from .base import AnalystProvider, ProviderError, post_json


class AnthropicProvider(AnalystProvider):
    name = "anthropic"
    default_model = "claude-sonnet-5"

    def analyze(self, snapshot: dict, instructions: str, schema: dict) -> dict:
        key = os.environ.get("ANTHROPIC_API_KEY")
        configured_model = os.environ.get("ANALYST_MODEL", "")
        model = (
            self.default_model
            if not configured_model or configured_model.startswith("replace-")
            else configured_model
        )
        if not key or key.startswith("replace-"):
            raise ProviderError("ANTHROPIC_API_KEY is required for provider=anthropic")
        payload = {
            "model": model,
            "max_tokens": 8000,
            "system": instructions,
            "messages": [
                {
                    "role": "user",
                    "content": "Analyze this risk-core snapshot:\n" + json.dumps(snapshot),
                }
            ],
            "tools": [
                {
                    "name": "submit_risk_analysis",
                    "description": "Submit the complete risk analysis and final report content.",
                    "input_schema": schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": "submit_risk_analysis"},
        }
        response = post_json(
            os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/messages"),
            payload,
            {
                "x-api-key": key,
                "anthropic-version": os.environ.get("ANTHROPIC_VERSION", "2023-06-01"),
            },
        )
        for block in response.get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "submit_risk_analysis":
                if isinstance(block.get("input"), dict):
                    return block["input"]
        raise ProviderError("Anthropic response did not contain the required tool payload")
