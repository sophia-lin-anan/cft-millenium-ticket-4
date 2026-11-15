"""Lightweight runtime contract checks with no third-party dependency."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schemas import metric_ids


class ContractError(ValueError):
    """Raised when a boundary payload violates the MVP contract."""


@dataclass(frozen=True)
class ValidatedSnapshot:
    data: dict[str, Any]


def _require(obj: dict, key: str, expected: type, path: str) -> Any:
    if key not in obj:
        raise ContractError(f"Missing {path}.{key}")
    value = obj[key]
    if not isinstance(value, expected):
        raise ContractError(f"{path}.{key} must be {expected.__name__}")
    return value


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_snapshot(data: dict[str, Any]) -> ValidatedSnapshot:
    if not isinstance(data, dict):
        raise ContractError("Snapshot must be an object")
    for key in ("schema_version", "run_id", "as_of"):
        _require(data, key, str, "snapshot")
    pods = _require(data, "pods", list, "snapshot")
    if not pods:
        raise ContractError("snapshot.pods must not be empty")
    seen: set[str] = set()
    for index, pod in enumerate(pods):
        path = f"snapshot.pods[{index}]"
        if not isinstance(pod, dict):
            raise ContractError(f"{path} must be an object")
        pod_id = _require(pod, "pod_id", str, path)
        if pod_id in seen:
            raise ContractError(f"Duplicate pod_id: {pod_id}")
        seen.add(pod_id)
        _require(pod, "evaluation_window", str, path)
        performance = _require(pod, "performance", dict, path)
        skill = _require(pod, "decision_skill", dict, path)
        _require(pod, "risk_metrics", dict, path)
        _require(pod, "data_quality", dict, path)
        _require(pod, "provenance", dict, path)
        for key in ("pnl_percent", "benchmark_percent"):
            if not _is_number(performance.get(key)):
                raise ContractError(f"{path}.performance.{key} must be numeric")
        aggregate = skill.get("aggregate_percentile")
        if not _is_number(aggregate) or not 0 <= aggregate <= 100:
            raise ContractError(f"{path}.decision_skill.aggregate_percentile must be 0..100")
        components = _require(skill, "components", dict, f"{path}.decision_skill")
        if not components:
            raise ContractError(f"{path}.decision_skill.components must not be empty")
        for name, value in components.items():
            if not _is_number(value) or not 0 <= value <= 100:
                raise ContractError(f"{path}.decision_skill.components.{name} must be 0..100")
    return ValidatedSnapshot(data=data)


def validate_analysis(snapshot: dict, analysis: dict) -> dict:
    """Check semantic invariants not guaranteed by provider JSON syntax."""
    if not isinstance(analysis, dict):
        raise ContractError("Analysis must be an object")
    if not isinstance(analysis.get("analysis_version"), str) or not analysis["analysis_version"].strip():
        raise ContractError("Analysis must include a non-empty analysis_version")
    if analysis.get("run_id") != snapshot["run_id"]:
        raise ContractError("Analysis run_id does not match snapshot")
    expected_pods = {pod["pod_id"] for pod in snapshot["pods"]}
    results = analysis.get("pods")
    if not isinstance(results, list):
        raise ContractError("analysis.pods must be an array")
    if len(results) != len(expected_pods) or any(not isinstance(pod, dict) for pod in results):
        raise ContractError("Analysis must contain exactly one result for each input pod")
    actual_pods = {pod.get("pod_id") for pod in results if isinstance(pod, dict)}
    if actual_pods != expected_pods:
        raise ContractError("Analysis must contain exactly one result for each input pod")
    verdicts = {"skilled", "lucky", "unlucky", "broken", "inconclusive"}
    gaming = {"none", "possible", "likely", "unknown"}
    for result in results:
        pod_id = result["pod_id"]
        verdict = result.get("verdict", {})
        if not isinstance(verdict, dict):
            raise ContractError(f"Invalid verdict for {pod_id}")
        if verdict.get("classification") not in verdicts:
            raise ContractError(f"Invalid verdict for {pod_id}")
        confidence = verdict.get("confidence")
        if not _is_number(confidence) or not 0 <= confidence <= 1:
            raise ContractError(f"Invalid confidence for {pod_id}")
        if verdict.get("gaming_risk") not in gaming:
            raise ContractError(f"Invalid gaming risk for {pod_id}")
        if not isinstance(verdict.get("summary"), str) or not verdict["summary"].strip():
            raise ContractError(f"Verdict summary for {pod_id} is required")
        allowed_ids = metric_ids(snapshot, pod_id)
        evidence = result.get("evidence")
        counterevidence = result.get("counterevidence")
        if not isinstance(evidence, list) or not evidence:
            raise ContractError(f"Analysis for {pod_id} must include evidence")
        if not isinstance(counterevidence, list):
            raise ContractError(f"Counterevidence for {pod_id} must be an array")
        for item in evidence + counterevidence:
            if not isinstance(item, dict):
                raise ContractError(f"Evidence for {pod_id} must contain objects")
            if item.get("metric_id") not in allowed_ids:
                raise ContractError(
                    f"Analysis for {pod_id} cites unknown metric_id {item.get('metric_id')!r}"
                )
            if item.get("direction") not in {"supports", "contradicts", "neutral"}:
                raise ContractError(f"Analysis for {pod_id} contains an invalid evidence direction")
            for field in ("observation", "interpretation"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise ContractError(f"Evidence for {pod_id} is missing {field}")
        uncertainties = result.get("uncertainties")
        if not isinstance(uncertainties, list) or any(not isinstance(item, str) for item in uncertainties):
            raise ContractError(f"Uncertainties for {pod_id} must be an array of strings")
        actions = result.get("recommended_actions", [])
        if not actions:
            raise ContractError(f"Analysis for {pod_id} must include a recommendation")
        required_action_fields = {
            "action",
            "rationale",
            "why_now",
            "next_step",
            "success_signal",
            "review_horizon",
        }
        for action in actions:
            if not isinstance(action, dict):
                raise ContractError(f"Action for {pod_id} must be an object")
            if action.get("execution_status") != "not_executed":
                raise ContractError(f"Action for {pod_id} must be marked not_executed")
            if action.get("priority") not in {"low", "medium", "high"}:
                raise ContractError(f"Action for {pod_id} has an invalid priority")
            if any(not isinstance(action.get(key), str) or not action[key].strip() for key in required_action_fields):
                raise ContractError(f"Action for {pod_id} is missing explanatory fields")
        narrative = result.get("narrative", {})
        required_narrative_fields = {
            "executive_summary",
            "why_this_verdict",
            "alternative_explanation",
            "what_would_change_verdict",
            "performance_analysis",
            "decision_skill_analysis",
            "risk_analysis",
            "conclusion",
        }
        if any(not isinstance(narrative.get(key), str) or not narrative[key].strip() for key in required_narrative_fields):
            raise ContractError(f"Narrative for {pod_id} is incomplete")
    return analysis
