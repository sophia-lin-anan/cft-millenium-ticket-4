"""Application service for provider selection and analyst execution."""

from __future__ import annotations

import os
from pathlib import Path

from .contracts import validate_analysis, validate_snapshot
from .providers import AnthropicProvider, MockProvider, OpenAIProvider
from .schemas import ANALYSIS_SCHEMA, metric_ids


PROVIDERS = {
    "mock": MockProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def analyze(snapshot: dict, provider_name: str | None = None) -> tuple[dict, str]:
    validated = validate_snapshot(snapshot).data
    selected = (provider_name or os.environ.get("ANALYST_PROVIDER", "mock")).lower()
    try:
        provider = PROVIDERS[selected]()
    except KeyError as exc:
        raise ValueError(f"Unknown provider {selected!r}; choose mock, openai, or anthropic") from exc
    prompt_path = Path(__file__).resolve().parents[2] / "config" / "analyst_prompt.txt"
    instructions = prompt_path.read_text(encoding="utf-8")
    citation_allowlist = "\n\nCanonical metric_id allowlist (use these exact strings; do not append leaf fields):\n"
    for pod in validated["pods"]:
        allowed = ", ".join(sorted(metric_ids(validated, pod["pod_id"])))
        citation_allowlist += f"- {pod['pod_id']}: {allowed}\n"
    instructions += citation_allowlist
    result = provider.analyze(validated, instructions, ANALYSIS_SCHEMA)
    return validate_analysis(validated, result), provider.name
