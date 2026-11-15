"""OpenAI Responses API adapter using strict JSON Schema output."""

from __future__ import annotations

import json
import os

from .base import AnalystProvider, ProviderError, post_json


class OpenAIProvider(AnalystProvider):
    name = "openai"

    def analyze(self, snapshot: dict, instructions: str, schema: dict) -> dict:
        key = os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("ANALYST_MODEL")
        if not key or not model:
            raise ProviderError("OPENAI_API_KEY and ANALYST_MODEL are required for provider=openai")
        payload = {
            "model": model,
            "instructions": instructions,
            "input": json.dumps(snapshot, separators=(",", ":")),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "risk_analysis",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        response = post_json(
            os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1/responses"),
            payload,
            {"Authorization": f"Bearer {key}"},
        )
        for output in response.get("output", []):
            if output.get("type") != "message":
                continue
            for content in output.get("content", []):
                if content.get("type") == "output_text":
                    try:
                        return json.loads(content["text"])
                    except json.JSONDecodeError as exc:
                        raise ProviderError("OpenAI returned non-JSON output text") from exc
        raise ProviderError("OpenAI response did not contain structured output")
