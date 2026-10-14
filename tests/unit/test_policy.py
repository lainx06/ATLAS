"""policy-v1: required assertion sets, materialization, outcome derivation (SPEC §5, §6)."""

from atlas.contracts import AssertionResult, Manifest, Outcome, Reason, Status
from atlas.policy import (
    derive_outcome,
    materialize,
    required_assertions,
    supported_claim,
)


def _manifest(**claim_overrides):
    claim = {
        "type": "unseen_group",
        "statement": "works on people absent from training",
        "sampling_unit": "subject",
        "dependence": [{"kind": "repeated_measures", "column": "subject_id"}],
    }
    claim.update(claim_overrides)
    return Manifest.model_validate(
        {
            "schema_version": "0.2",
            "table": {"path": "table.csv", "format": "csv"},
            "columns": {
                "row_id": "row_id",
                "target": "label",
                "class_map": {"0": "a", "1": "b"},
                "features": ["f0"],
                "group_id": "subject_id",
                "unit_id": "subject_id",
            },
            "claim": claim,
            "primary_metric": "balanced_accuracy",
            "development_seeds": [0],
            "entry_point": "evaluate.py",
        }
    )


def _result(aid, status, reason=None, valid=True):
    return AssertionResult(
        assertion_id=aid, status=status, reason=reason, evidence_valid=valid
    )


def test_unseen_group_subject_unit_with_repeated_measures_requires_eight_assertions():
    required = required_assertions(_manifest())

    assert set(required) == {
        "split.no_row_overlap",
        "split.no_shared_source_observation",
        "split.no_group_overlap",
        "split.sampling_unit_disjoint",
        "split.repeated_measures_rule",
        "fit.state_dependencies_within_fold_train",
        "fit.coverage_complete",
        "metric.prediction_ids_match_eval_ids",
    }


def test_overlapping_windows_declaration_adds_window_assertion():
    m = _manifest(
        dependence=[
            {"kind": "repeated_measures", "column": "subject_id"},
            {"kind": "overlapping_windows"},
        ]
    )

    assert "split.no_window_overlap" in required_assertions(m)


def test_future_time_requires_three_temporal_assertions_and_no_group_overlap():
    required = required_assertions(
        _manifest(type="future_time", sampling_unit="row", dependence=[])
    )

    assert {
        "temporal.training_labels_available_by_cutoff",
        "temporal.cutoff_precedes_evaluation",
        "temporal.features_available_when_used",
    } <= set(required)
    assert "split.no_group_overlap" not in required
    assert "split.sampling_unit_disjoint" not in required


def test_combined_or_unknown_claim_type_is_not_supported():
    assert not supported_claim("unseen_group+future_time")
    assert not supported_claim(["unseen_group", "future_time"])
    assert supported_claim("same_population")


def test_materialize_marks_missing_required_result_unimplemented():
    required = ["split.no_row_overlap", "split.no_window_overlap"]
    computed = {"split.no_row_overlap": _result("split.no_row_overlap", Status.PASS)}

    results = materialize(required, computed)

    by_id = {r.assertion_id: r for r in results}
    assert by_id["split.no_window_overlap"].status is Status.NOT_ASSESSED
    assert by_id["split.no_window_overlap"].reason is Reason.UNIMPLEMENTED_ASSERTION
    assert len(results) == 2


def test_materialize_never_drops_required_assertions_or_adds_unrequired_ones():
    computed = {
        "split.no_row_overlap": _result("split.no_row_overlap", Status.PASS),
        "split.extra": _result("split.extra", Status.FAIL),
    }

    results = materialize(["split.no_row_overlap"], computed)

    assert [r.assertion_id for r in results] == ["split.no_row_overlap"]


def test_valid_fail_gives_violation_found_even_with_errors_elsewhere():
    results = [
        _result("a", Status.FAIL),
        _result("b", Status.ERROR),
        _result("c", Status.NOT_ASSESSED, Reason.UNKNOWN_ANCESTRY),
    ]

    assert derive_outcome(results) is Outcome.VIOLATION_FOUND


def test_fail_with_invalid_evidence_is_not_an_established_violation():
    results = [_result("a", Status.FAIL, valid=False), _result("b", Status.PASS)]

    assert derive_outcome(results) is Outcome.INCONCLUSIVE


def test_all_valid_pass_gives_no_violation_found():
    results = [_result("a", Status.PASS), _result("b", Status.PASS)]

    assert derive_outcome(results) is Outcome.NO_VIOLATION_FOUND


def test_pass_with_invalid_evidence_is_not_counted_as_pass():
    results = [_result("a", Status.PASS), _result("b", Status.PASS, valid=False)]

    assert derive_outcome(results) is Outcome.INCONCLUSIVE


def test_any_not_assessed_without_fail_is_inconclusive():
    results = [
        _result("a", Status.PASS),
        _result("b", Status.NOT_ASSESSED, Reason.MISSING_METADATA),
    ]

    assert derive_outcome(results) is Outcome.INCONCLUSIVE


def test_empty_required_set_is_never_no_violation_found():
    assert derive_outcome([]) is Outcome.INCONCLUSIVE


def test_all_not_assessed_is_inconclusive():
    results = [_result("a", Status.NOT_ASSESSED, Reason.UNIMPLEMENTED_ASSERTION)]

    assert derive_outcome(results) is Outcome.INCONCLUSIVE
