from __future__ import annotations

import unittest

from support import clone, snapshot

from millenium_analyst.analyst import analyze
from millenium_analyst.contracts import ContractError, validate_analysis, validate_snapshot
from millenium_analyst.schemas import metric_ids


class SnapshotContractTests(unittest.TestCase):
    def setUp(self):
        self.data = snapshot()

    def assert_rejected(self, mutate):
        candidate = clone(self.data)
        mutate(candidate)
        with self.assertRaises(ContractError):
            validate_snapshot(candidate)

    def test_valid_snapshot_is_returned_unchanged(self):
        self.assertIs(validate_snapshot(self.data).data, self.data)

    def test_rejects_non_object_empty_pods_and_duplicate_ids(self):
        with self.assertRaises(ContractError):
            validate_snapshot([])
        self.assert_rejected(lambda data: data.__setitem__("pods", []))
        self.assert_rejected(lambda data: data["pods"][1].__setitem__("pod_id", "Pod A"))

    def test_rejects_missing_required_top_level_fields(self):
        for field in ("schema_version", "run_id", "as_of", "pods"):
            with self.subTest(field=field):
                self.assert_rejected(lambda data, field=field: data.pop(field))

    def test_rejects_boolean_or_non_numeric_performance(self):
        for value in (True, "1.2", None):
            with self.subTest(value=value):
                self.assert_rejected(
                    lambda data, value=value: data["pods"][0]["performance"].__setitem__("pnl_percent", value)
                )

    def test_rejects_out_of_range_or_boolean_skill(self):
        for value in (-0.1, 100.1, True):
            with self.subTest(value=value):
                self.assert_rejected(
                    lambda data, value=value: data["pods"][0]["decision_skill"].__setitem__("aggregate_percentile", value)
                )

    def test_rejects_empty_or_invalid_components(self):
        self.assert_rejected(lambda data: data["pods"][0]["decision_skill"].__setitem__("components", {}))
        self.assert_rejected(
            lambda data: data["pods"][0]["decision_skill"]["components"].__setitem__("sizing", 101)
        )

    def test_metric_ids_are_canonical_metric_objects_not_leaf_paths(self):
        ids = metric_ids(self.data, "Pod A")
        self.assertIn("risk_metrics.hidden_tail_risk", ids)
        self.assertNotIn("risk_metrics.hidden_tail_risk.score", ids)
        self.assertIn("decision_skill.components.entry_timing", ids)


class AnalysisContractTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = snapshot()
        self.analysis, _ = analyze(self.snapshot, "mock")

    def assert_rejected(self, mutate):
        candidate = clone(self.analysis)
        mutate(candidate)
        with self.assertRaises(ContractError):
            validate_analysis(self.snapshot, candidate)

    def test_accepts_complete_mock_analysis(self):
        self.assertEqual(validate_analysis(self.snapshot, self.analysis), self.analysis)

    def test_rejects_missing_version_and_mismatched_run(self):
        self.assert_rejected(lambda data: data.__setitem__("analysis_version", ""))
        self.assert_rejected(lambda data: data.__setitem__("run_id", "other-run"))

    def test_rejects_missing_extra_and_duplicate_pod_results(self):
        self.assert_rejected(lambda data: data["pods"].pop())
        self.assert_rejected(lambda data: data["pods"].append(clone(data["pods"][0])))
        self.assert_rejected(lambda data: data["pods"][0].__setitem__("pod_id", "unknown"))

    def test_rejects_invalid_verdict_fields(self):
        cases = {
            "classification": "excellent",
            "confidence": 1.1,
            "confidence_bool": True,
            "gaming_risk": "high",
            "summary": " ",
        }
        for name, value in cases.items():
            field = "confidence" if name == "confidence_bool" else name
            with self.subTest(field=name):
                self.assert_rejected(
                    lambda data, field=field, value=value: data["pods"][0]["verdict"].__setitem__(field, value)
                )

    def test_rejects_missing_or_malformed_evidence(self):
        self.assert_rejected(lambda data: data["pods"][0].__setitem__("evidence", []))
        self.assert_rejected(lambda data: data["pods"][0].__setitem__("counterevidence", "none"))
        self.assert_rejected(
            lambda data: data["pods"][0]["evidence"][0].__setitem__("metric_id", "invented.metric")
        )
        self.assert_rejected(
            lambda data: data["pods"][0]["evidence"][0].__setitem__("direction", "proves")
        )
        self.assert_rejected(
            lambda data: data["pods"][0]["evidence"][0].__setitem__("interpretation", "")
        )

    def test_rejects_invalid_uncertainties(self):
        self.assert_rejected(lambda data: data["pods"][0].__setitem__("uncertainties", "unknown"))
        self.assert_rejected(lambda data: data["pods"][0].__setitem__("uncertainties", [3]))

    def test_rejects_missing_executed_or_invalid_priority_actions(self):
        self.assert_rejected(lambda data: data["pods"][0].__setitem__("recommended_actions", []))
        self.assert_rejected(
            lambda data: data["pods"][0]["recommended_actions"][0].__setitem__("execution_status", "executed")
        )
        self.assert_rejected(
            lambda data: data["pods"][0]["recommended_actions"][0].__setitem__("priority", "urgent")
        )
        self.assert_rejected(lambda data: data["pods"][0]["recommended_actions"][0].pop("why_now"))

    def test_rejects_incomplete_narrative(self):
        for field in (
            "executive_summary",
            "why_this_verdict",
            "alternative_explanation",
            "what_would_change_verdict",
            "performance_analysis",
            "decision_skill_analysis",
            "risk_analysis",
            "conclusion",
        ):
            with self.subTest(field=field):
                self.assert_rejected(
                    lambda data, field=field: data["pods"][0]["narrative"].__setitem__(field, "")
                )


if __name__ == "__main__":
    unittest.main()
