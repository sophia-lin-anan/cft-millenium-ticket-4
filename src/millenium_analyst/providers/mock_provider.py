"""Deterministic local provider used for development, demos, and tests."""

from __future__ import annotations

from .base import AnalystProvider


def _classification(pnl: float, skill: float, has_warnings: bool) -> str:
    if has_warnings:
        return "inconclusive"
    if pnl >= 0 and skill >= 50:
        return "skilled"
    if pnl >= 0 and skill < 50:
        return "lucky"
    if pnl < 0 and skill >= 50:
        return "unlucky"
    return "broken"


class MockProvider(AnalystProvider):
    name = "mock"

    def analyze(self, snapshot: dict, instructions: str, schema: dict) -> dict:
        del instructions, schema
        results = []
        for pod in snapshot["pods"]:
            pnl = float(pod["performance"]["pnl_percent"])
            benchmark = float(pod["performance"]["benchmark_percent"])
            skill = float(pod["decision_skill"]["aggregate_percentile"])
            warnings = pod["data_quality"].get("warnings", [])
            missing = pod["data_quality"].get("missing_metrics", [])
            verdict = _classification(pnl, skill, bool(warnings or missing))
            components = pod["decision_skill"]["components"]
            weakest_name, weakest_value = min(components.items(), key=lambda item: item[1])
            strongest_name, strongest_value = max(components.items(), key=lambda item: item[1])
            tail = pod["risk_metrics"].get("hidden_tail_risk", {})
            gaming = tail.get("gaming_risk", "none")
            if gaming not in {"none", "possible", "likely", "unknown"}:
                gaming = "unknown"
            label = verdict.capitalize()
            if verdict == "skilled":
                summary = "Positive performance is supported by decision skill above the chance baseline."
                action = "Maintain the current mandate and continue monitoring decision quality."
                why_now = "The evidence supports persistence, but a strong recent result should still be tested across another review window."
                next_step = "Keep current limits unchanged and schedule a decision-quality review using the next completed window."
                success_signal = "Aggregate skill remains above the 50th percentile without a material increase in drawdown or tail-risk score."
                alternative = "Recent performance may still be flattered by favorable factor exposures not fully captured in the aggregate skill score."
                change = "A sustained fall in aggregate skill below chance, especially alongside worsening drawdown, would move the verdict toward lucky or broken."
                priority = "low"
            elif verdict == "lucky":
                summary = "Performance is positive, but measured decision skill remains below chance."
                action = "Review whether recent gains are repeatable before increasing risk."
                why_now = "Positive P&L can conceal weak decision quality; increasing risk before confirming repeatability would amplify that uncertainty."
                next_step = "Review the lowest-scoring decisions with the pod and compare them with the supplied random-portfolio baseline."
                success_signal = "Aggregate skill moves above the 50th percentile while P&L remains resilient outside the current factor mix."
                alternative = "The skill framework may be slow to recognize a new edge, so recent gains could be more repeatable than the current percentile suggests."
                change = "Two consecutive windows above the chance baseline would support reclassification toward skilled; fading P&L would reinforce lucky."
                priority = "medium"
            elif verdict == "unlucky":
                summary = "Performance is negative while measured decision skill remains above chance."
                action = "Preserve the mandate while reviewing drawdown and recovery assumptions."
                why_now = "Cutting solely on recent P&L risks removing a process that still shows measurable edge, but the drawdown path needs an explicit recovery test."
                next_step = "Reconcile the largest losing decisions with factor attribution and update the expected recovery window before changing limits."
                success_signal = "Decision skill stays above chance and losses begin to normalize within the risk core's recovery horizon."
                alternative = "The measured edge may be stale or the sample may not yet reflect a structural deterioration in the strategy."
                change = "A drop below the chance baseline, especially in multiple decision components, would move the verdict toward broken."
                priority = "medium"
            elif verdict == "broken":
                summary = "Negative performance coincides with decision skill below the chance baseline."
                action = "Review the mandate and the weakest decision components before restoring risk."
                why_now = "Both outcome and process evidence are weak, making normal variation a less persuasive explanation for the drawdown."
                next_step = "Run a decision review focused on the two weakest components and define a remediation test before any risk restoration."
                success_signal = "The weak components recover toward or above the 50th percentile and drawdown stabilizes without new tail-risk warnings."
                alternative = "A short, unusually adverse regime could depress both realized P&L and measured skill at the same time."
                change = "A recovery in decision skill above chance while P&L remains weak would move the verdict toward unlucky rather than broken."
                priority = "high"
            else:
                summary = "The available evidence is not sufficient for a reliable classification."
                action = "Resolve data-quality gaps and rerun the analysis."
                why_now = "A confident verdict would overstate what the supplied snapshot can support."
                next_step = "Resolve every listed warning or missing metric, then produce a fresh risk-core snapshot."
                success_signal = "All required metrics are present with compatible windows and no material data-quality warning."
                alternative = "The apparent ambiguity may disappear once the missing evidence is restored."
                change = "A complete snapshot with consistent performance and skill evidence would permit a directional verdict."
                priority = "high"
            results.append(
                {
                    "pod_id": pod["pod_id"],
                    "verdict": {
                        "classification": verdict,
                        "confidence": 0.52 if verdict == "inconclusive" else 0.84,
                        "gaming_risk": gaming,
                        "summary": summary,
                    },
                    "evidence": [
                        {
                            "metric_id": "performance.pnl_percent",
                            "direction": "supports",
                            "observation": f"P&L is {pnl:+.1f}% versus a {benchmark:+.1f}% benchmark.",
                            "interpretation": f"This establishes the recent outcome leg of the verdict, but it does not by itself distinguish {'repeatable edge from favorable variation' if pnl >= 0 else 'normal variation from a lost edge'}; the process evidence is needed for that distinction.",
                        },
                        {
                            "metric_id": "decision_skill.aggregate_percentile",
                            "direction": "supports",
                            "observation": f"Aggregate decision skill is at the {_ordinal(skill)} percentile.",
                            "interpretation": f"This is the process leg of the verdict. Being {'above' if skill >= 50 else 'below'} chance changes how the same P&L result should be interpreted and is therefore central to the classification.",
                        },
                        {
                            "metric_id": f"decision_skill.components.{weakest_name}",
                            "direction": "supports",
                            "observation": f"{weakest_name.replace('_', ' ').title()} is the weakest component at the {_ordinal(weakest_value)} percentile.",
                            "interpretation": "Because it is the weakest observed decision dimension, it is the most efficient place to look for a concrete process failure or remediation opportunity.",
                        },
                    ],
                    "counterevidence": [
                        {
                            "metric_id": f"decision_skill.components.{strongest_name}",
                            "direction": "contradicts",
                            "observation": f"{strongest_name.replace('_', ' ').title()} is strongest at the {_ordinal(strongest_value)} percentile.",
                            "interpretation": "This prevents the report from treating decision quality as uniformly strong or weak and limits confidence in an overly broad diagnosis.",
                        }
                    ],
                    "uncertainties": [*warnings, *[f"Missing metric: {item}" for item in missing]],
                    "recommended_actions": [
                        {
                            "action": action,
                            "rationale": summary,
                            "why_now": why_now,
                            "next_step": next_step,
                            "success_signal": success_signal,
                            "review_horizon": "Next completed risk-review window",
                            "priority": priority,
                            "execution_status": "not_executed",
                        },
                        {
                            "action": "Schedule a follow-up review against a predefined evidence checkpoint.",
                            "rationale": "A dated checkpoint keeps the verdict falsifiable and prevents an advisory recommendation from persisting indefinitely.",
                            "why_now": "The current snapshot supports a working conclusion, but the next window is needed to distinguish persistence from a temporary regime effect.",
                            "next_step": "Record the current P&L, aggregate skill, weakest component, drawdown and tail-risk score as the comparison baseline; assign an owner and review date.",
                            "success_signal": "The follow-up uses the same definitions and windows, documents what changed, and explicitly confirms or revises the verdict.",
                            "review_horizon": "At the next completed risk-review window",
                            "priority": "medium",
                            "execution_status": "not_executed",
                        }
                    ],
                    "narrative": {
                        "executive_summary": f"{pod['pod_id']} is classified as {label.lower()} with {pnl:+.1f}% P&L and aggregate skill at the {_ordinal(skill)} percentile.",
                        "why_this_verdict": f"The verdict combines two independent signals: realized P&L is {'positive' if pnl >= 0 else 'negative'}, while measured decision skill is {'above' if skill >= 50 else 'below'} the chance baseline. Together they place the pod in the {label.lower()} regime rather than treating performance alone as proof of edge.",
                        "alternative_explanation": alternative,
                        "what_would_change_verdict": change,
                        "performance_analysis": f"The pod returned {pnl:+.1f}% over {pod['evaluation_window']}, compared with the supplied benchmark of {benchmark:+.1f}%.",
                        "decision_skill_analysis": f"Decision skill is mixed: {strongest_name.replace('_', ' ')} leads at the {_ordinal(strongest_value)} percentile, while {weakest_name.replace('_', ' ')} trails at the {_ordinal(weakest_value)} percentile.",
                        "risk_analysis": _risk_narrative(pod["risk_metrics"]),
                        "conclusion": f"The evidence supports {_article(label.lower())} {label.lower()} verdict. The proposed follow-up is advisory and has not been executed.",
                    },
                }
            )
        return {"analysis_version": "1.0", "run_id": snapshot["run_id"], "pods": results}


def _risk_narrative(metrics: dict) -> str:
    drawdown = metrics.get("drawdown", {})
    var = metrics.get("var", {})
    es = metrics.get("expected_shortfall", {})
    parts = []
    if "value_percent" in drawdown:
        parts.append(f"Maximum drawdown is {drawdown['value_percent']:.1f}%")
    if "value_percent" in var:
        parts.append(f"VaR is {var['value_percent']:.1f}%")
    if "value_percent" in es:
        parts.append(f"expected shortfall is {es['value_percent']:.1f}%")
    return ("; ".join(parts) + ".") if parts else "No summarized risk metrics were supplied."


def _ordinal(value: float) -> str:
    number = round(value)
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"
