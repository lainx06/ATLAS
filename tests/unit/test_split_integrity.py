"""Split-integrity assertions on hand-built tables and splits (SPEC §5, F3, L2)."""

import pandas as pd
import pytest

from atlas.checks.split_integrity import split_assertions
from atlas.contracts import EvidenceRef, Manifest, Outcome, Reason, Status
from atlas.policy import derive_outcome, required_assertions

EVIDENCE = [EvidenceRef(artifact="splits.json", sha256="x")]


def _manifest(columns=None, claim=None, known_duplicates=None):
    base_columns = {
        "row_id": "row_id",
        "target": "y",
        "class_map": {"0": "a", "1": "b"},
        "features": ["f0", "f1"],
        "group_id": "subject",
        "unit_id": "subject",
        "observation_id": "obs",
    }
    base_columns.update(columns or {})
    base_columns = {k: v for k, v in base_columns.items() if v is not None}
    base_claim = {
        "type": "unseen_group",
        "statement": "s",
        "sampling_unit": "subject",
        "dependence": [{"kind": "repeated_measures", "column": "subject"}],
    }
    base_claim.update(claim or {})
    return Manifest.model_validate(
        {
            "schema_version": "0.2",
            "table": {"path": "t.csv", "format": "csv"},
            "columns": base_columns,
            "claim": base_claim,
            "primary_metric": "balanced_accuracy",
            "development_seeds": [0],
            "entry_point": "evaluate.py",
            "known_duplicates": known_duplicates or [],
        }
    )


def _table():
    # Two subjects, two sessions each, two rows per session. Feature values all distinct.
    return pd.DataFrame(
        {
            "row_id": ["r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7"],
            "subject": ["A", "A", "A", "A", "B", "B", "B", "B"],
            "session": ["A1", "A1", "A2", "A2", "B1", "B1", "B2", "B2"],
            "obs": [f"o{i}" for i in range(8)],
            "f0": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            "f1": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7],
            "y": [0, 1, 0, 1, 0, 1, 0, 1],
        }
    ).set_index("row_id")


GROUPED = [
    {
        "fold": "f0",
        "kind": "development_eval",
        "train_ids": ["r0", "r1", "r2", "r3"],
        "eval_ids": ["r4", "r5", "r6", "r7"],
    }
]
MIXED = [
    {
        "fold": "f0",
        "kind": "development_eval",
        "train_ids": ["r0", "r1", "r4", "r5"],
        "eval_ids": ["r2", "r3", "r6", "r7"],
    }
]


def _run(manifest, table, splits, valid=True):
    return split_assertions(manifest, table, splits, EVIDENCE, evidence_valid=valid)


def test_row_overlap_fails_when_a_row_is_in_train_and_eval():
    splits = [
        {
            "fold": "f0",
            "kind": "development_eval",
            "train_ids": ["r0", "r1"],
            "eval_ids": ["r1", "r2"],
        }
    ]

    result = _run(_manifest(), _table(), splits)["split.no_row_overlap"]

    assert result.status is Status.FAIL
    assert result.observed["overlapping_rows"] == {"f0": ["r1"]}


def test_grouped_split_passes_row_group_unit_and_repeated_measures():
    results = _run(_manifest(), _table(), GROUPED)

    for aid in (
        "split.no_row_overlap",
        "split.no_group_overlap",
        "split.sampling_unit_disjoint",
        "split.repeated_measures_rule",
    ):
        assert results[aid].status is Status.PASS, aid


def test_mixed_subjects_fail_group_overlap_with_only_two_groups():
    results = _run(_manifest(), _table(), MIXED)

    assert results["split.no_row_overlap"].status is Status.PASS
    assert results["split.no_group_overlap"].status is Status.FAIL
    assert results["split.no_group_overlap"].observed["overlapping_groups"] == {
        "f0": ["A", "B"]
    }
    assert results["split.sampling_unit_disjoint"].status is Status.FAIL


def test_missing_group_and_unit_roles_are_not_assessed_not_not_applicable():
    m = _manifest(columns={"group_id": None, "unit_id": None})

    results = _run(m, _table(), GROUPED)

    for aid in (
        "split.no_group_overlap",
        "split.sampling_unit_disjoint",
        "split.repeated_measures_rule",
    ):
        assert results[aid].status is Status.NOT_ASSESSED, aid
        assert results[aid].reason is Reason.MISSING_METADATA, aid


def test_repeated_measures_nested_in_groups_follows_group_overlap():
    m = _manifest(
        claim={"dependence": [{"kind": "repeated_measures", "column": "session"}]}
    )

    results = _run(m, _table(), MIXED)

    rm = results["split.repeated_measures_rule"]
    assert rm.status is Status.FAIL
    assert rm.observed["units"][0]["route"] == "contained_group"
    assert rm.observed["units"][0]["witnesses"]
    assert rm.depends_on == []  # computed from its own witnesses, never inherited


def test_repeated_measures_not_contained_in_groups_has_no_supported_rule():
    table = _table()
    table.loc["r4", "session"] = "A1"  # session A1 now spans subjects A and B
    m = _manifest(
        claim={"dependence": [{"kind": "repeated_measures", "column": "session"}]}
    )

    rm = _run(m, table, GROUPED)["split.repeated_measures_rule"]

    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.NO_SUPPORTED_RULE


def test_same_population_row_sampling_with_repeated_measures_is_not_silently_approved():
    m = _manifest(
        columns={"group_id": None, "unit_id": None},
        claim={"type": "same_population", "sampling_unit": "row"},
    )

    rm = _run(m, _table(), MIXED)["split.repeated_measures_rule"]

    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.NO_SUPPORTED_RULE


def test_identical_values_with_distinct_observation_ids_pass_and_report_candidates():
    table = _table()
    table.loc["r4", ["f0", "f1", "y"]] = table.loc["r0", ["f0", "f1", "y"]].to_numpy()

    so = _run(_manifest(), table, GROUPED)["split.no_shared_source_observation"]

    assert so.status is Status.PASS
    assert so.observed["duplicate_candidates"] == {"f0": [["r0", "r4"]]}


def test_shared_observation_id_across_partitions_fails():
    table = _table()
    table.loc["r4", "obs"] = "o0"

    so = _run(_manifest(), table, GROUPED)["split.no_shared_source_observation"]

    assert so.status is Status.FAIL


def test_identical_values_without_identity_are_unresolved_not_a_violation():
    table = _table().drop(columns=["obs"])
    table.loc["r4", ["f0", "f1", "y"]] = table.loc["r0", ["f0", "f1", "y"]].to_numpy()
    m = _manifest(columns={"observation_id": None})

    so = _run(m, table, GROUPED)["split.no_shared_source_observation"]

    assert so.status is Status.NOT_ASSESSED
    assert so.reason is Reason.UNRESOLVED_DUPLICATE_CANDIDATES


def test_no_candidates_without_identity_passes_as_exact_value_screen():
    m = _manifest(columns={"observation_id": None})

    so = _run(m, _table().drop(columns=["obs"]), GROUPED)[
        "split.no_shared_source_observation"
    ]

    assert so.status is Status.PASS
    assert any("exact-value screen" in lim for lim in so.limitations)


def test_documented_duplicate_across_partitions_fails():
    m = _manifest(columns={"observation_id": None}, known_duplicates=[["r0", "r4"]])

    so = _run(m, _table().drop(columns=["obs"]), GROUPED)[
        "split.no_shared_source_observation"
    ]

    assert so.status is Status.FAIL


def test_invalid_split_evidence_makes_every_split_assertion_error():
    results = _run(_manifest(), _table(), GROUPED, valid=False)

    assert results
    for result in results.values():
        assert result.status is Status.ERROR
        assert result.evidence_valid is False


def test_no_declared_folds_is_not_executed():
    results = _run(_manifest(), _table(), [])

    assert results["split.no_row_overlap"].status is Status.NOT_ASSESSED
    assert results["split.no_row_overlap"].reason is Reason.NOT_EXECUTED


def test_null_group_value_on_a_participating_row_is_not_assessed():
    """Codex probe 'null_group_value': a missing value, not a missing column."""
    table = _table()
    table.loc["r4", "subject"] = float("nan")

    results = _run(_manifest(), table, GROUPED)

    for aid in ("split.no_group_overlap", "split.sampling_unit_disjoint"):
        assert results[aid].status is Status.NOT_ASSESSED, aid
        assert results[aid].reason is Reason.MISSING_METADATA, aid
        assert results[aid].observed["rows_with_unknown_identity"] == {"f0": 1}, aid
    assert results["split.repeated_measures_rule"].status is Status.NOT_ASSESSED


def test_violation_among_known_identities_survives_a_null_value():
    table = _table()
    table.loc["r7", "subject"] = None

    result = _run(_manifest(), table, MIXED)["split.no_group_overlap"]

    assert result.status is Status.FAIL
    assert result.observed["overlapping_groups"] == {"f0": ["A", "B"]}


def test_null_observation_id_is_not_assessed():
    table = _table()
    table.loc["r5", "obs"] = None

    so = _run(_manifest(), table, GROUPED)["split.no_shared_source_observation"]

    assert so.status is Status.NOT_ASSESSED
    assert so.reason is Reason.MISSING_METADATA


def test_null_repeated_measures_unit_value_is_not_assessed():
    m = _manifest(
        claim={"dependence": [{"kind": "repeated_measures", "column": "session"}]}
    )
    table = _table()
    table.loc["r1", "session"] = float("nan")

    rm = _run(m, table, GROUPED)["split.repeated_measures_rule"]

    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA


def test_repeated_measures_rule_keeps_a_known_violation_despite_a_null_unit_value():
    """Codex probe 'known_overlap_plus_null': the repeated-measures assertion itself."""
    table = _table()
    table.loc["r7", "subject"] = float("nan")

    rm = _run(_manifest(), table, MIXED)["split.repeated_measures_rule"]

    assert rm.status is Status.FAIL
    assert rm.observed["units"][0]["rows_with_unknown_identity"] == {"f0": 1}
    assert rm.observed["units"][0]["route"] == "sampling_unit"
    assert rm.observed["units"][0]["witnesses"]


def test_nested_unit_with_a_null_value_follows_a_known_group_violation():
    m = _manifest(
        claim={"dependence": [{"kind": "repeated_measures", "column": "session"}]}
    )
    table = _table()
    table.loc["r1", "session"] = None

    rm = _run(m, table, MIXED)["split.repeated_measures_rule"]

    assert rm.status is Status.FAIL
    assert rm.observed["units"][0]["rows_with_unknown_identity"] == {"f0": 1}


def test_nested_unit_with_a_null_value_and_no_known_violation_is_not_assessed():
    m = _manifest(
        claim={"dependence": [{"kind": "repeated_measures", "column": "session"}]}
    )
    table = _table()
    table.loc["r1", "session"] = None

    rm = _run(m, table, GROUPED)["split.repeated_measures_rule"]

    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA


# --- Repeated measures: empty / partial / complete identity (Codex pass-2 'all_null_repeated_unit') --

SESSION_RM = {"dependence": [{"kind": "repeated_measures", "column": "session"}]}


def _outcome(results):
    """Outcome over the split assertions this manifest requires (policy derivation)."""
    required = [
        "split.no_row_overlap",
        "split.no_shared_source_observation",
        "split.no_group_overlap",
        "split.sampling_unit_disjoint",
        "split.repeated_measures_rule",
    ]
    return derive_outcome([results[aid] for aid in required])


def test_all_null_nested_unit_is_not_assessed_while_independent_fails_stand():
    table = _table()
    table["session"] = None

    results = _run(_manifest(claim=SESSION_RM), table, MIXED)

    rm = results["split.repeated_measures_rule"]
    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA
    assert rm.depends_on == []
    assert rm.observed["units"][0]["rows_with_unknown_identity"] == {"f0": 8}
    assert results["split.no_group_overlap"].status is Status.FAIL
    assert results["split.sampling_unit_disjoint"].status is Status.FAIL
    assert _outcome(results) is Outcome.VIOLATION_FOUND


def test_all_null_nested_unit_without_other_violations_is_inconclusive():
    table = _table()
    table["session"] = None

    results = _run(_manifest(claim=SESSION_RM), table, GROUPED)

    rm = results["split.repeated_measures_rule"]
    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA
    assert _outcome(results) is Outcome.INCONCLUSIVE


def test_partially_null_nested_unit_still_follows_a_demonstrated_group_violation():
    table = _table()
    table.loc[["r0", "r1"], "session"] = None  # session A1 unknown; A2, B1, B2 known

    results = _run(_manifest(claim=SESSION_RM), table, MIXED)

    rm = results["split.repeated_measures_rule"]
    assert rm.status is Status.FAIL
    assert rm.observed["units"][0]["route"] == "contained_group"
    assert rm.observed["units"][0]["witnesses"]
    assert rm.observed["units"][0]["rows_with_unknown_identity"] == {"f0": 2}
    assert _outcome(results) is Outcome.VIOLATION_FOUND


def test_complete_nested_unit_on_a_grouped_split_passes():
    results = _run(_manifest(claim=SESSION_RM), _table(), GROUPED)

    rm = results["split.repeated_measures_rule"]
    assert rm.status is Status.PASS
    assert rm.observed["units"][0]["route"] == "contained_group"
    assert rm.observed["units"][0]["complete"] is True
    assert _outcome(results) is Outcome.NO_VIOLATION_FOUND


def test_nested_unit_null_only_on_a_non_participating_row_does_not_matter():
    table = _table()
    table.loc["r7", "session"] = None
    splits = [
        {
            "fold": "f0",
            "kind": "development_eval",
            "train_ids": ["r0", "r1", "r2", "r3"],
            "eval_ids": ["r4", "r5", "r6"],  # r7 does not participate
        }
    ]

    rm = _run(_manifest(claim=SESSION_RM), table, splits)[
        "split.repeated_measures_rule"
    ]

    assert rm.status is Status.PASS


def test_nested_unit_whose_group_values_are_all_unknown_does_not_establish_containment():
    table = _table()
    table["subject"] = None  # groups unknown: containment cannot be shown

    rm = _run(_manifest(claim=SESSION_RM), table, MIXED)["split.repeated_measures_rule"]

    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA


# --- policy-v1.1: explicit routes and witnesses for repeated measures ------------------------------


def _rm(manifest, table, splits):
    return _run(manifest, table, splits)["split.repeated_measures_rule"]


def test_overlap_only_through_unknown_unit_rows_has_no_witness():
    """Codex containment probe 'partly_null_unrelated_overlap' (unit level)."""
    table = _table()
    table["session"] = None
    table.loc[["r0", "r1"], "session"] = (
        "A1"  # known sessions only for subject A in train
    )
    table.loc[["r6", "r7"], "session"] = "B2"  # and subject B in eval
    splits = [
        {
            "fold": "f0",
            "kind": "development_eval",
            "train_ids": ["r0", "r1", "r4", "r5"],
            "eval_ids": ["r2", "r3", "r6", "r7"],
        }
    ]

    results = _run(_manifest(claim=SESSION_RM), table, splits)

    rm = results["split.repeated_measures_rule"]
    assert (
        results["split.no_group_overlap"].status is Status.FAIL
    )  # via unknown-session rows
    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA
    assert rm.observed["units"][0]["witnesses"] == []
    assert _outcome(results) is Outcome.VIOLATION_FOUND


def test_group_overlap_with_different_session_ids_is_a_group_separation_witness():
    rm = _rm(_manifest(claim=SESSION_RM), _table(), MIXED)

    assert rm.status is Status.FAIL
    witness = next(
        w for w in rm.observed["units"][0]["witnesses"] if w["group_id"] == "A"
    )
    assert witness["kind"] == "group_separation"
    assert witness["fold"] == "f0"
    assert witness["train_row_ids"] == ["r0", "r1"]
    assert witness["eval_row_ids"] == ["r2", "r3"]
    assert witness["train_unit_ids"] == ["A1"]
    assert witness["eval_unit_ids"] == [
        "A2"
    ]  # different sessions: not same-session overlap


def test_known_plus_missing_group_assignments_with_a_valid_witness_fail():
    table = _table()
    table.loc["r0", "subject"] = None

    rm = _rm(_manifest(claim=SESSION_RM), table, MIXED)

    assert rm.status is Status.FAIL
    assert rm.observed["units"][0]["rows_missing_group"] == {"f0": 1}
    assert rm.observed["units"][0]["complete"] is False


def test_known_plus_missing_group_assignments_without_a_witness_are_not_assessed():
    table = _table()
    table.loc["r0", "subject"] = None

    rm = _rm(_manifest(claim=SESSION_RM), table, GROUPED)

    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA


def test_complete_overlapping_sampling_units_fail_with_unit_witnesses():
    rm = _rm(_manifest(), _table(), MIXED)

    assert rm.status is Status.FAIL
    unit = rm.observed["units"][0]
    assert unit["route"] == "sampling_unit"
    assert {w["unit_id"] for w in unit["witnesses"]} == {"A", "B"}
    assert all(w["kind"] == "sampling_unit_overlap" for w in unit["witnesses"])


def test_complete_disjoint_sampling_units_pass():
    rm = _rm(_manifest(), _table(), GROUPED)

    assert rm.status is Status.PASS
    assert rm.observed["units"][0]["complete"] is True


def test_empty_participation_is_not_executed_never_pass():
    splits = [
        {"fold": "f0", "kind": "development_eval", "train_ids": [], "eval_ids": []}
    ]

    rm = _rm(_manifest(claim=SESSION_RM), _table(), splits)

    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.NOT_EXECUTED


def test_cross_fold_only_overlap_is_not_combined_into_a_witness():
    splits = [
        {
            "fold": "f0",
            "kind": "development_eval",
            "train_ids": ["r0", "r1", "r2", "r3"],
            "eval_ids": ["r4", "r5", "r6", "r7"],
        },
        {
            "fold": "f1",
            "kind": "development_eval",
            "train_ids": ["r4", "r5", "r6", "r7"],
            "eval_ids": ["r0", "r1", "r2", "r3"],
        },
    ]

    for manifest in (_manifest(), _manifest(claim=SESSION_RM)):
        rm = _rm(manifest, _table(), splits)
        assert rm.status is Status.PASS
        assert rm.observed["units"][0]["witnesses"] == []


def test_observed_multi_group_mapping_blocks_the_contained_group_route_even_with_a_witness():
    table = _table()
    table.loc["r4", "session"] = "A1"  # session A1 now observed in subjects A and B

    rm = _rm(_manifest(claim=SESSION_RM), table, MIXED)

    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.NO_SUPPORTED_RULE
    assert rm.observed["units"][0]["mapping_contradictions"] == [
        {"unit_id": "A1", "group_ids": ["A", "B"]}
    ]


def test_sampling_unit_route_does_not_need_group_assignments():
    table = _table()
    table["site"] = None  # declared group column, entirely unknown
    manifest = _manifest(columns={"group_id": "site"})

    assert _rm(manifest, table, MIXED).status is Status.FAIL
    passing = _rm(manifest, table, GROUPED)
    assert passing.status is Status.PASS
    assert passing.observed["units"][0]["route"] == "sampling_unit"


def test_multiple_declared_units_keep_a_valid_fail_and_disclose_incomplete_coverage():
    table = _table()
    table["session"] = None
    m = _manifest(
        claim={
            "dependence": [
                {"kind": "repeated_measures", "column": "subject"},
                {"kind": "repeated_measures", "column": "session"},
            ]
        }
    )

    rm = _rm(m, table, MIXED)

    assert rm.status is Status.FAIL
    statuses = {u["column"]: (u["status"], u["reason"]) for u in rm.observed["units"]}
    assert statuses == {
        "subject": (Status.FAIL, None),
        "session": (Status.NOT_ASSESSED, Reason.MISSING_METADATA),
    }


# --- Route B with the repeated unit and the group on the SAME column (rm-v11 'group_equals_repeated') -


def _same_column_manifest(sampling):
    """Repeated measures and group both reference `subject`; route B (unit is not the sampling unit)."""
    return _manifest(
        columns={"unit_id": None if sampling == "row" else "session"},
        claim={
            "sampling_unit": sampling,
            "dependence": [{"kind": "repeated_measures", "column": "subject"}],
        },
    )


@pytest.mark.parametrize("sampling", ["row", "session"])
def test_same_column_complete_disjoint_values_pass(sampling):
    rm = _rm(_same_column_manifest(sampling), _table(), GROUPED)

    assert rm.status is Status.PASS
    assert rm.observed["units"][0]["route"] == "contained_group"
    assert rm.observed["units"][0]["mapping_contradictions"] == []


@pytest.mark.parametrize("sampling", ["row", "session"])
def test_same_column_known_overlap_fails_with_a_witness(sampling):
    rm = _rm(_same_column_manifest(sampling), _table(), MIXED)

    assert rm.status is Status.FAIL
    witness = next(
        w for w in rm.observed["units"][0]["witnesses"] if w["group_id"] == "A"
    )
    assert witness["train_unit_ids"] == ["A"] and witness["eval_unit_ids"] == ["A"]


@pytest.mark.parametrize("sampling", ["row", "session"])
def test_same_column_all_missing_is_not_assessed(sampling):
    table = _table()
    table["subject"] = None

    rm = _rm(_same_column_manifest(sampling), table, MIXED)

    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA


@pytest.mark.parametrize("sampling", ["row", "session"])
def test_same_column_partial_missing_with_a_witness_fails(sampling):
    table = _table()
    table.loc["r0", "subject"] = None

    rm = _rm(_same_column_manifest(sampling), table, MIXED)

    assert rm.status is Status.FAIL
    assert rm.observed["units"][0]["rows_with_unknown_identity"] == {"f0": 1}
    assert rm.observed["units"][0]["rows_missing_group"] == {"f0": 1}


@pytest.mark.parametrize("sampling", ["row", "session"])
def test_same_column_partial_missing_without_a_witness_is_not_assessed(sampling):
    table = _table()
    table.loc["r0", "subject"] = None

    rm = _rm(_same_column_manifest(sampling), table, GROUPED)

    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA


# --- policy-v1.2: every declared evaluation fold must contain at least one evaluation row ----------

EF = "split.evaluation_folds_nonempty"


def test_zero_evaluation_rows_is_not_assessed_empty_evaluation():
    splits = [
        {
            "fold": "f0",
            "kind": "development_eval",
            "train_ids": ["r0", "r1"],
            "eval_ids": [],
        }
    ]

    ef = _run(_manifest(), _table(), splits)[EF]

    assert ef.status is Status.NOT_ASSESSED
    assert ef.reason is Reason.EMPTY_EVALUATION
    assert ef.observed["empty_evaluation_folds"] == ["f0"]


def test_mix_of_empty_and_nonempty_evaluation_folds_is_not_assessed():
    splits = [
        GROUPED[0],
        {"fold": "f1", "kind": "development_eval", "train_ids": ["r0"], "eval_ids": []},
    ]

    results = _run(_manifest(), _table(), splits)

    assert results[EF].status is Status.NOT_ASSESSED
    assert results[EF].reason is Reason.EMPTY_EVALUATION
    assert results[EF].observed["empty_evaluation_folds"] == ["f1"]
    assert _outcome_with_ef(results) is Outcome.INCONCLUSIVE


def test_empty_evaluation_fold_does_not_hide_an_independent_valid_fail():
    splits = [
        MIXED[0],
        {"fold": "f1", "kind": "development_eval", "train_ids": ["r0"], "eval_ids": []},
    ]

    results = _run(_manifest(), _table(), splits)

    assert results[EF].status is Status.NOT_ASSESSED
    assert results["split.no_group_overlap"].status is Status.FAIL
    assert _outcome_with_ef(results) is Outcome.VIOLATION_FOUND


def test_all_evaluation_folds_nonempty_passes():
    assert _run(_manifest(), _table(), GROUPED)[EF].status is Status.PASS


def test_zero_declared_folds_is_not_executed_for_the_prerequisite():
    ef = _run(_manifest(), _table(), [])[EF]

    assert ef.status is Status.NOT_ASSESSED
    assert ef.reason is Reason.NOT_EXECUTED


def test_invalid_split_evidence_makes_the_prerequisite_error():
    ef = _run(_manifest(), _table(), GROUPED, valid=False)[EF]

    assert ef.status is Status.ERROR


def test_prerequisite_is_required_for_every_claim_type():
    for claim_type in ("same_population", "unseen_group", "future_time"):
        m = _manifest(
            claim={"type": claim_type, "sampling_unit": "row", "dependence": []}
        )
        assert EF in required_assertions(m), claim_type


def _outcome_with_ef(results):
    required = [
        "split.no_row_overlap",
        "split.no_shared_source_observation",
        "split.no_group_overlap",
        "split.sampling_unit_disjoint",
        "split.repeated_measures_rule",
        EF,
    ]
    return derive_outcome([results[aid] for aid in required])
