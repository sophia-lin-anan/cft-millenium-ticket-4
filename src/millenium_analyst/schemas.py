"""JSON Schemas shared by the analyst and provider adapters."""

from __future__ import annotations


ANALYSIS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["analysis_version", "run_id", "pods"],
    "properties": {
        "analysis_version": {"type": "string"},
        "run_id": {"type": "string"},
        "pods": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "pod_id",
                    "verdict",
                    "evidence",
                    "counterevidence",
                    "uncertainties",
                    "recommended_actions",
                    "narrative",
                ],
                "properties": {
                    "pod_id": {"type": "string"},
                    "verdict": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "classification",
                            "confidence",
                            "gaming_risk",
                            "summary",
                        ],
                        "properties": {
                            "classification": {
                                "type": "string",
                                "enum": [
                                    "skilled",
                                    "lucky",
                                    "unlucky",
                                    "broken",
                                    "inconclusive",
                                ],
                            },
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "gaming_risk": {
                                "type": "string",
                                "enum": ["none", "possible", "likely", "unknown"],
                            },
                            "summary": {"type": "string"},
                        },
                    },
                    "evidence": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"$ref": "#/$defs/evidenceItem"},
                    },
                    "counterevidence": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/evidenceItem"},
                    },
                    "uncertainties": {"type": "array", "items": {"type": "string"}},
                    "recommended_actions": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "action",
                                "rationale",
                                "why_now",
                                "next_step",
                                "success_signal",
                                "review_horizon",
                                "priority",
                                "execution_status",
                            ],
                            "properties": {
                                "action": {"type": "string"},
                                "rationale": {"type": "string"},
                                "why_now": {"type": "string"},
                                "next_step": {"type": "string"},
                                "success_signal": {"type": "string"},
                                "review_horizon": {"type": "string"},
                                "priority": {
                                    "type": "string",
                                    "enum": ["low", "medium", "high"],
                                },
                                "execution_status": {
                                    "type": "string",
                                    "enum": ["not_executed"],
                                },
                            },
                        },
                    },
                    "narrative": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "executive_summary",
                            "why_this_verdict",
                            "alternative_explanation",
                            "what_would_change_verdict",
                            "performance_analysis",
                            "decision_skill_analysis",
                            "risk_analysis",
                            "conclusion",
                        ],
                        "properties": {
                            "executive_summary": {"type": "string"},
                            "why_this_verdict": {"type": "string"},
                            "alternative_explanation": {"type": "string"},
                            "what_would_change_verdict": {"type": "string"},
                            "performance_analysis": {"type": "string"},
                            "decision_skill_analysis": {"type": "string"},
                            "risk_analysis": {"type": "string"},
                            "conclusion": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
    "$defs": {
        "evidenceItem": {
            "type": "object",
            "additionalProperties": False,
            "required": ["metric_id", "direction", "observation", "interpretation"],
            "properties": {
                "metric_id": {"type": "string"},
                "direction": {
                    "type": "string",
                    "enum": ["supports", "contradicts", "neutral"],
                },
                "observation": {"type": "string"},
                "interpretation": {"type": "string"},
            },
        }
    },
}


def metric_ids(snapshot: dict, pod_id: str) -> set[str]:
    """Return the stable IDs an analysis may cite for one pod."""
    pod = next(p for p in snapshot["pods"] if p["pod_id"] == pod_id)
    ids = {
        "performance.pnl_percent",
        "performance.benchmark_percent",
        "decision_skill.aggregate_percentile",
    }
    ids.update(f"decision_skill.components.{key}" for key in pod["decision_skill"]["components"])
    ids.update(f"risk_metrics.{key}" for key in pod["risk_metrics"])
    return ids
