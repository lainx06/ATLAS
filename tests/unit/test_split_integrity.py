"""Split-integrity assertions on hand-built tables and splits (SPEC §5, F3, L2)."""

import pandas as pd

from atlas.checks.split_integrity import split_assertions
from atlas.contracts import EvidenceRef, Manifest, Reason, Status

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
    assert "split.no_group_overlap" in rm.depends_on


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
