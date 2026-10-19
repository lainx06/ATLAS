"""T-11 scoring edge cases (SPEC §17 "Finding-level scoring"): empty expected sets, zero
denominators, NOT_ASSESSED as coverage gaps, ERROR apart from misses, and trials without a
valid answer counted but never scored."""

from atlas.evaluation.score import (
    UNDEFINED,
    counts,
    ratio,
    score_atlas,
    score_baseline,
    score_suite,
)

GO, SU, WO = (
    "split.no_group_overlap",
    "split.sampling_unit_disjoint",
    "split.no_window_overlap",
)


def atlas(outcome, **statuses):
    return {
        "available": True,
        "outcome": outcome,
        "assertions": [
            {
                "assertion_id": aid.replace("__", "."),
                "status": s,
                "evidence_valid": True,
            }
            for aid, s in statuses.items()
        ],
    }


def trial(rep, status="VALID", violated=(), code=None):
    t = {"repetition": rep, "status": status, "code": code}
    if status == "VALID":
        t["violated"] = list(violated)
    return t


def test_ratio_is_undefined_for_a_zero_denominator():
    assert ratio(0, 0) == UNDEFINED
    assert ratio(0, 3) == 0.0 and ratio(2, 4) == 0.5


def test_counts():
    assert counts([GO, WO], [GO, SU]) == {"tp": [GO], "fp": [WO], "fn": [SU]}
    assert counts([], []) == {"tp": [], "fp": [], "fn": []}


def test_an_empty_expected_set_with_no_findings_has_undefined_precision_and_recall():
    scores = score_suite(
        {"clean": frozenset()},
        {"clean": atlas("NO_VIOLATION_FOUND", split__no_group_overlap="PASS")},
        {"clean": [trial(1), trial(2)]},
    )
    for leg in ("atlas", "baseline"):
        totals = scores[leg]["totals"]
        assert (totals["tp"], totals["fp"], totals["fn"]) == (0, 0, 0)
        assert totals["precision"] == UNDEFINED and totals["recall"] == UNDEFINED
        assert totals["clean_false_positives"] == 0
        assert totals["clean_false_violation_rate"] == 0.0


def test_a_false_positive_on_a_clean_control():
    scores = score_suite(
        {"clean": frozenset()},
        {"clean": atlas("VIOLATION_FOUND", split__no_group_overlap="FAIL")},
        {"clean": [trial(1, violated=[GO]), trial(2)]},
    )
    a, b = scores["atlas"]["totals"], scores["baseline"]["totals"]
    assert (a["fp"], a["precision"], a["recall"]) == (1, 0.0, UNDEFINED)
    assert a["clean_false_violation_rate"] == 1.0
    assert (b["fp"], b["clean_false_positives"], b["clean_false_violation_rate"]) == (
        1,
        1,
        0.5,
    )


def test_not_assessed_is_a_coverage_gap_not_a_miss():
    row = score_atlas(
        "flawed",
        frozenset({GO, WO}),
        atlas("VIOLATION_FOUND", split__no_group_overlap="FAIL",
              split__no_window_overlap="NOT_ASSESSED"),
    )  # fmt: skip
    assert row["tp"] == [GO] and row["fn"] == [] and row["fp"] == []
    assert row["coverage_gaps"] == [WO] and row["expected_gaps"] == [WO]


def test_error_and_invalid_evidence_are_errors_not_misses_or_detections():
    result = atlas("INCONCLUSIVE", split__no_group_overlap="ERROR")
    result["assertions"].append(
        {"assertion_id": SU, "status": "FAIL", "evidence_valid": False}
    )
    row = score_atlas("flawed", frozenset({GO, SU}), result)
    assert row["tp"] == [] and row["fn"] == [] and row["fp"] == []
    assert row["errors"] == [GO, SU] and row["expected_errors"] == [GO, SU]


def test_a_pass_on_an_expected_id_is_a_miss():
    row = score_atlas(
        "flawed",
        frozenset({GO}),
        atlas("NO_VIOLATION_FOUND", split__no_group_overlap="PASS"),
    )
    assert row["fn"] == [GO]


def test_an_unavailable_atlas_result_is_reported_not_scored():
    scores = score_suite(
        {"flawed": frozenset({GO})},
        {"flawed": {"available": False, "reason": "recorded_changed"}},
        {"flawed": []},
    )
    row = scores["atlas"]["cases"][0]
    assert row["available"] is False and row["reason"] == "recorded_changed"
    totals = scores["atlas"]["totals"]
    assert totals["cases_available"] == 0 and totals["recall"] == UNDEFINED
    assert totals["clean_false_violation_rate"] == UNDEFINED


def test_trials_without_a_valid_answer_are_counted_separately_and_never_scored():
    trials = [
        trial(1, violated=[GO]),
        trial(2, "INVALID_REPLY", code="not_json"),
        trial(3, "NOT_SENT", code="input_over_ceiling"),
        trial(4, "MODEL_ERROR", code="model_timeout"),
    ]
    row = score_baseline("flawed", frozenset({GO, SU}), trials)
    assert row["trials_scheduled"] == 4
    assert (
        row["valid"],
        row["invalid_reply"],
        row["not_sent"],
        row["model_error"],
    ) == (
        1,
        1,
        1,
        1,
    )
    assert (row["tp"], row["fp"], row["fn"]) == (1, 0, 1)  # from the valid trial only
    assert [t["status"] for t in row["trials"]] == [t["status"] for t in trials]
    assert "tp" not in row["trials"][1]


def test_no_valid_trial_means_undefined_rates():
    scores = score_suite(
        {"flawed": frozenset({GO}), "clean": frozenset()},
        {"flawed": atlas("VIOLATION_FOUND", split__no_group_overlap="FAIL"),
         "clean": atlas("NO_VIOLATION_FOUND", split__no_group_overlap="PASS")},
        {"flawed": [trial(1, "NOT_SENT", code="input_over_ceiling")] * 3,
         "clean": [trial(1, "INVALID_REPLY", code="empty")] * 3},
    )  # fmt: skip
    b = scores["baseline"]["totals"]
    assert (b["trials_scheduled"], b["valid"], b["not_sent"], b["invalid_reply"]) == (
        6,
        0,
        3,
        3,
    )
    assert b["precision"] == UNDEFINED and b["recall"] == UNDEFINED
    assert b["clean_false_violation_rate"] == UNDEFINED
    a = scores["atlas"]["totals"]
    assert (a["tp"], a["precision"], a["recall"]) == (1, 1.0, 1.0)
