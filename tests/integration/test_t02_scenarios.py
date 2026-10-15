"""T-02 scenarios (policy-v1.3): trusted fixtures under benchmarks/t02/, audited end to end.

Each fixture runs under the fixture hash allowlist (SPEC §10) and is judged by the trusted
evaluator. Expected statuses are listed for every required assertion.
"""

import importlib.util
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from atlas.audit import audit, evaluate, execute
from atlas.contracts import Manifest, Outcome, Reason, Status
from atlas.policy import DESCRIPTIVE, required_assertions

FIXTURES = Path(__file__).resolve().parents[2] / "benchmarks" / "t02"
P, F, N, E = Status.PASS, Status.FAIL, Status.NOT_ASSESSED, Status.ERROR

BASIC = {
    "split.evaluation_folds_nonempty": P,
    "split.no_row_overlap": P,
    "split.no_shared_source_observation": P,
    "fit.state_dependencies_within_fold_train": P,
    "fit.coverage_complete": P,
    "metric.prediction_ids_match_eval_ids": P,
}
FUTURE = {
    "temporal.training_labels_available_by_cutoff": P,
    "temporal.cutoff_precedes_evaluation": P,
    "temporal.features_available_when_used": P,
}
WINDOWS = {"split.no_window_overlap": P, "split.temporal_separation": P}

EXPECTED = {
    "s11a_future_time_label_leak": (
        {**BASIC, **FUTURE, "temporal.training_labels_available_by_cutoff": F},
        Outcome.VIOLATION_FOUND,
    ),
    "s11b_future_time_clean": (
        {**BASIC, **FUTURE, "metric.reported_matches_recomputed": P},
        Outcome.NO_VIOLATION_FOUND,
    ),
    "s11c_reported_metric_mismatch": (
        {**BASIC, **FUTURE, "metric.reported_matches_recomputed": F},
        Outcome.VIOLATION_FOUND,
    ),
    "s12a_same_population_random_windows": (
        {**BASIC, "split.no_window_overlap": F, "split.temporal_separation": F},
        Outcome.VIOLATION_FOUND,
    ),
    "s12b_same_population_blocked_windows": (
        {**BASIC, **WINDOWS},
        Outcome.NO_VIOLATION_FOUND,
    ),
}


def _manifest(name):
    return Manifest.model_validate_json(
        (FIXTURES / name / "atlas_manifest.json").read_text(encoding="utf-8")
    )


def _by_id(outcome):
    return {a.assertion_id: a for a in outcome.assertions}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_scenario_statuses_and_outcome(name, tmp_path):
    statuses, outcome = EXPECTED[name]

    result = audit(FIXTURES / name, tmp_path).outcome

    assert [a.assertion_id for a in result.assertions] == required_assertions(
        _manifest(name)
    )
    assert {a.assertion_id: a.status for a in result.assertions} == statuses
    assert result.outcome is outcome
    assert result.policy_version == "policy-v1.3"


def test_label_leak_witnesses_are_the_last_training_days_of_each_fold(tmp_path):
    result = audit(FIXTURES / "s11a_future_time_label_leak", tmp_path).outcome

    labels = _by_id(result)["temporal.training_labels_available_by_cutoff"]
    assert labels.observed["witness_count"] == 24  # 6 days x 4 folds
    for w in labels.observed["witnesses"]:
        assert w["label_available"] == w["prediction_time"] + 7 > w["cutoff"]


def test_clean_reported_metrics_agree_with_scikit_learn(tmp_path):
    """The manifest values were computed by scikit-learn in generate.py, independently."""
    result = audit(FIXTURES / "s11b_future_time_clean", tmp_path).outcome

    entries = _by_id(result)["metric.reported_matches_recomputed"].observed["entries"]
    assert [e["status"] for e in entries] == [P, P]
    assert all(e["abs_difference"] <= 1e-12 for e in entries)


def test_misreported_metric_fails_and_the_correct_one_still_passes(tmp_path):
    result = audit(FIXTURES / "s11c_reported_metric_mismatch", tmp_path).outcome

    entries = _by_id(result)["metric.reported_matches_recomputed"].observed["entries"]
    assert [e["status"] for e in entries] == [F, P]
    assert entries[0]["abs_difference"] == pytest.approx(0.01, abs=1e-9)


def test_blocked_windows_pass_at_the_separation_boundary(tmp_path):
    result = audit(FIXTURES / "s12b_same_population_blocked_windows", tmp_path).outcome

    by_id = _by_id(result)
    window = by_id["split.no_window_overlap"]
    assert set(window.observed["established_by"].values()) == {"interval_comparison"}
    separation = by_id["split.temporal_separation"]
    assert [f["smallest_gap"] for f in separation.observed["folds"]] == [5.0] * 4
    for a in (window, separation):
        assert any("not proof of statistical independence" in x for x in a.limitations)


def test_descriptive_results_are_reported_but_do_not_decide_the_outcome(tmp_path):
    run = audit(FIXTURES / "s12b_same_population_blocked_windows", tmp_path)

    ids = {d.result_id for d in run.outcome.descriptive}
    assert ids == set(DESCRIPTIVE)
    assert not ids & {a.assertion_id for a in run.outcome.assertions}
    written = json.loads((run.run_dir / "outcome.json").read_text(encoding="utf-8"))
    assert {d["result_id"] for d in written["descriptive"]} == ids
    checks = json.loads(
        (run.run_dir / "checks" / "independent_metrics.json").read_text(
            encoding="utf-8"
        )
    )
    assert {d["result_id"] for d in checks["descriptive"]} == {
        "metric.recomputed_primary",
        "metric.baselines",
    }
    dummy = next(
        d for d in run.outcome.descriptive if d.result_id == "metric.baselines"
    )
    agg = dummy.observed["dummy"]["aggregates"]["development_eval"]
    assert agg["balanced_accuracy"]["mean_over_folds"]["complete"] is True


def test_corrupted_prediction_artifact_is_an_evidence_error_not_a_rejection(tmp_path):
    """Runtime evidence problems give ERROR; only invalid manifests are NOT_SUPPORTED."""
    project = FIXTURES / "s11b_future_time_clean"
    run_dir = execute(project, tmp_path)
    artifact = run_dir / "predictions" / "fold1.parquet"
    artifact.write_bytes(artifact.read_bytes() + b"tampered")

    result = evaluate(project, run_dir)

    reported = _by_id(result)["metric.reported_matches_recomputed"]
    assert (reported.status, reported.reason) == (E, Reason.EVIDENCE_INVALID)
    assert result.outcome is Outcome.INCONCLUSIVE


def test_invalid_reported_value_is_rejected_at_intake_before_execution(tmp_path):
    copy = tmp_path / "s11b_nan"
    shutil.copytree(FIXTURES / "s11b_future_time_clean", copy)
    manifest = copy / "atlas_manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["reported_metrics"][0]["value"] = float("nan")
    manifest.write_text(json.dumps(data), encoding="utf-8")  # json writes NaN

    run = audit(copy, tmp_path / "runs")

    assert run.outcome.outcome is Outcome.NOT_SUPPORTED
    assert "reported_metrics.0.value" in run.outcome.reason
    assert not (run.run_dir / "provenance.jsonl").exists()


def _generator():
    spec = importlib.util.spec_from_file_location(
        "t02_generate", FIXTURES / "generate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("name", "builder"),
    [
        ("s11b_future_time_clean", "future_table"),
        ("s12b_same_population_blocked_windows", "window_table"),
    ],
)
def test_generator_reproduces_the_committed_tables(name, builder):
    committed = pd.read_csv(FIXTURES / name / "table.csv", dtype={"row_id": str})

    regenerated = getattr(_generator(), builder)()

    pd.testing.assert_frame_equal(committed, regenerated, check_dtype=False)


# --- Codex review of 487664e: full-evaluator regressions --------------------------------------
# Each case executes the trusted s11b fixture, then changes copied evidence (manifest snapshot,
# splits.json, table) and re-hashes it, so evaluator semantics are exercised rather than tamper
# detection. Modified project code is never executed.

CLEAN = FIXTURES / "s11b_future_time_clean"


def _evaluate_changed(tmp_path, change):
    from atlas.reports import sha256_file

    run_dir = execute(CLEAN, tmp_path / "runs")
    project = tmp_path / "project"
    shutil.copytree(CLEAN, project)
    manifest = json.loads(
        (run_dir / "manifest.snapshot.json").read_text(encoding="utf-8")
    )
    splits = json.loads((run_dir / "splits.json").read_text(encoding="utf-8"))
    table = pd.read_csv(project / "table.csv", dtype={"row_id": str})
    changed = change(manifest, splits, table)
    table = table if changed is None else changed
    table.to_csv(project / "table.csv", index=False)
    for path in (run_dir / "manifest.snapshot.json", project / "atlas_manifest.json"):
        path.write_text(json.dumps(manifest), encoding="utf-8")
    (run_dir / "splits.json").write_text(json.dumps(splits), encoding="utf-8")
    index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    for name in ("manifest.snapshot.json", "splits.json"):
        index["artifacts"][name] = sha256_file(run_dir / name)
    index["table"]["sha256"] = sha256_file(project / "table.csv")
    (run_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return evaluate(project, run_dir), run_dir


def _late_training_row(manifest, splits, table, pred_day, label_day, column=True):
    """Fold 0's first training row gets the given prediction day and label day."""
    manifest["label_availability"] = {"column": "label_day"}
    if column:
        table["label_day"] = (table["pred_day"] + 7).astype(float)
    row = table["row_id"] == splits[0]["train_ids"][0]
    table["pred_day"] = table["pred_day"].astype(float)
    table.loc[row, "pred_day"] = pred_day
    if column:
        table.loc[row, "label_day"] = label_day
    return table


@pytest.mark.parametrize(
    ("pred_day", "label_day", "column"),
    [(61.0, None, True), (None, 61.0, True), (61.0, None, False)],
    ids=[
        "late_prediction_label_missing",
        "late_label_prediction_missing",
        "no_label_column",
    ],
)
def test_known_cutoff_violation_with_a_missing_value_is_violation_found(
    tmp_path, pred_day, label_day, column
):
    """Finding 1: fold 0's cutoff is 60; one known value of the row is after it."""

    def change(manifest, splits, table):
        return _late_training_row(manifest, splits, table, pred_day, label_day, column)

    result, _ = _evaluate_changed(tmp_path, change)

    labels = _by_id(result)["temporal.training_labels_available_by_cutoff"]
    assert labels.status is F
    assert result.outcome is Outcome.VIOLATION_FOUND


@pytest.mark.parametrize(
    "containment",
    [
        None,
        {"within": "group_id", "source": "doc", "statement": "one stream per group"},
    ],
    ids=["undeclared", "declared"],
)
def test_shared_stream_group_column_writes_an_outcome(tmp_path, containment):
    """Finding 2: stream_id and group_id name one column; route D is incomplete."""

    def change(manifest, splits, table):
        manifest["columns"].update(
            stream_id="stream",
            group_id="stream",
            window_start="start",
            window_end="end",
        )
        manifest["claim"]["dependence"].append({"kind": "overlapping_windows"})
        if containment:
            manifest["window_containment"] = containment
        table["stream"] = "S"
        table["start"] = float("nan")
        table["end"] = 10
        return table

    result, run_dir = _evaluate_changed(tmp_path, change)

    window = _by_id(result)["split.no_window_overlap"]
    assert (window.status, window.reason) == (N, Reason.MISSING_METADATA)
    assert (run_dir / "outcome.json").exists()


def test_oversized_cutoff_is_recorded_and_a_supported_fail_is_preserved(tmp_path):
    """Finding 3: fold 0's cutoff is beyond float64; fold 1's cutoff exposes a late label."""

    def change(manifest, splits, table):
        splits[0]["training_cutoff"] = 10**400
        splits[1]["training_cutoff"] -= (
            1  # its last training day's label now arrives late
        )

    result, run_dir = _evaluate_changed(tmp_path, change)

    by_id = _by_id(result)
    labels = by_id["temporal.training_labels_available_by_cutoff"]
    assert labels.status is F and labels.observed["invalid_cutoff_folds"] == ["fold0"]
    precedes = by_id["temporal.cutoff_precedes_evaluation"]
    assert (precedes.status, precedes.reason) == (E, Reason.EVIDENCE_INVALID)
    assert result.outcome is Outcome.VIOLATION_FOUND
    assert (run_dir / "outcome.json").exists()


def test_oversized_reported_value_is_not_supported_with_the_field_named(tmp_path):
    copy = tmp_path / "s11b_huge"
    shutil.copytree(CLEAN, copy)
    manifest = copy / "atlas_manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["reported_metrics"][0]["value"] = 10**400
    manifest.write_text(json.dumps(data), encoding="utf-8")

    run = audit(copy, tmp_path / "runs")

    assert run.outcome.outcome is Outcome.NOT_SUPPORTED
    assert "reported_metrics.0.value" in run.outcome.reason
    assert not (run.run_dir / "provenance.jsonl").exists()


@pytest.mark.parametrize("order", ["invalid_first", "valid_first"])
def test_duplicate_fold_identifier_is_an_evidence_error(tmp_path, order):
    """Finding 4: a second 'fold3' whose evaluation rows are fold 2's (no matching predictions)."""

    def change(manifest, splits, table):
        duplicate = {**splits[3], "eval_ids": splits[2]["eval_ids"]}
        splits.insert(3 if order == "invalid_first" else 4, duplicate)

    result, _ = _evaluate_changed(tmp_path, change)

    reported = _by_id(result)["metric.reported_matches_recomputed"]
    assert (reported.status, reported.reason) == (E, Reason.EVIDENCE_INVALID)
    assert reported.observed["duplicate_fold_identifiers"] == ["fold3"]
    for entry in reported.observed["entries"]:
        assert entry["recomputed"]["complete"] is False
    assert result.outcome is not Outcome.NO_VIOLATION_FOUND


# --- Codex verification of 0cf955d: undecodable split evidence -----------------------------------


def _undecodable(case: str, splits: list) -> bytes:
    """Bytes that are not decodable split evidence; the index is re-hashed to match them."""
    if (
        case == "integer_5000_digits"
    ):  # the demonstrated case: beyond the int-from-str limit
        splits[1]["training_cutoff"] = "BIG"
        raw = json.dumps(splits).replace('"BIG"', "1" + "0" * 4999)
        return raw.encode("utf-8")
    if case == "malformed_json":
        return json.dumps(splits)[:-1].encode("utf-8")
    if case == "invalid_utf8":
        return b"\xff" + json.dumps(splits).encode("utf-8")
    return ("[" * 100_000 + "]" * 100_000).encode("utf-8")  # deep_nesting


@pytest.mark.parametrize(
    "case", ["integer_5000_digits", "malformed_json", "invalid_utf8", "deep_nesting"]
)
def test_undecodable_hash_matching_splits_is_an_evidence_error(tmp_path, case):
    from atlas.reports import sha256_file

    run_dir = execute(CLEAN, tmp_path / "runs")
    evaluate(
        CLEAN, run_dir
    )  # earlier outputs exist and must be replaced, not left stale
    splits = json.loads((run_dir / "splits.json").read_text(encoding="utf-8"))
    (run_dir / "splits.json").write_bytes(_undecodable(case, splits))
    index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    index["artifacts"]["splits.json"] = sha256_file(run_dir / "splits.json")
    (run_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")

    result = evaluate(CLEAN, run_dir)  # returns; no uncaught decoder exception

    required = required_assertions(_manifest("s11b_future_time_clean"))
    assert [a.assertion_id for a in result.assertions] == required
    for (
        a
    ) in result.assertions:  # every required assertion depends on the split evidence
        assert (a.status, a.reason) == (E, Reason.EVIDENCE_INVALID), a.assertion_id
    assert result.outcome is Outcome.INCONCLUSIVE  # no clean outcome is possible
    assert "splits.json could not be decoded" in result.reason
    assert not any(d.available for d in result.descriptive)
    written = json.loads((run_dir / "outcome.json").read_text(encoding="utf-8"))
    assert written["outcome"] == "INCONCLUSIVE"
    assert [a["assertion_id"] for a in written["assertions"]] == required
    outputs = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))[
        "outputs"
    ]
    on_disk = {"outcome.json", "report.json"} | {
        f"checks/{p.name}" for p in (run_dir / "checks").glob("*.json")
    }
    assert set(outputs) == on_disk
    for name, digest in outputs.items():
        assert sha256_file(run_dir / name) == digest, name


# --- Codex verification of bb9bac8: provenance and index decoding boundaries -------------------

FIT = ("fit.state_dependencies_within_fold_train", "fit.coverage_complete")
LABELS_ID = "temporal.training_labels_available_by_cutoff"


def _undecodable_line(case: str) -> bytes:
    if case == "integer_5000_digits":
        return ('{"type": "load", "n_rows": ' + "1" + "0" * 4999 + "}").encode("utf-8")
    if case == "malformed_json":
        return b'{"type": "load", "n_rows":'
    if case == "invalid_utf8":
        return b"\xff"
    return ("[" * 100_000 + "]" * 100_000).encode("utf-8")  # deep_nesting


def _late_prediction(manifest, splits, table):
    """Separate valid split/table evidence: a training row predicted after its fold's cutoff."""
    return _late_training_row(manifest, splits, table, 61.0, None)


@pytest.mark.parametrize(
    "case", ["integer_5000_digits", "malformed_json", "invalid_utf8", "deep_nesting"]
)
def test_undecodable_provenance_is_wholly_invalid_and_independent_fail_stands(
    tmp_path, case
):
    from atlas.reports import sha256_file

    control, run_dir = _evaluate_changed(tmp_path, _late_prediction)
    assert control.outcome is Outcome.VIOLATION_FOUND
    provenance = run_dir / "provenance.jsonl"
    valid_events = provenance.read_bytes()
    assert valid_events.count(b"\n") > 10  # a decodable prefix precedes the bad line
    provenance.write_bytes(valid_events + _undecodable_line(case) + b"\n")
    index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    index["artifacts"]["provenance.jsonl"] = sha256_file(provenance)
    (run_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")

    result = evaluate(
        tmp_path / "project", run_dir
    )  # returns; no uncaught decoder error

    by_id, before = _by_id(result), _by_id(control)
    for aid in FIT:  # the decoded prefix is not used: provenance is wholly invalid
        assert (by_id[aid].status, by_id[aid].reason) == (E, Reason.EVIDENCE_INVALID)
    assert by_id[LABELS_ID].status is F and by_id[LABELS_ID].evidence_valid
    for aid, a in by_id.items():  # only provenance-dependent assertions changed
        if aid not in FIT:
            assert (a.status, a.reason) == (before[aid].status, before[aid].reason), aid
    assert result.outcome is Outcome.VIOLATION_FOUND
    assert "provenance.jsonl could not be decoded" in result.reason
    outputs = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))[
        "outputs"
    ]
    on_disk = {"outcome.json", "report.json"} | {
        f"checks/{p.name}" for p in (run_dir / "checks").glob("*.json")
    }
    assert set(outputs) == on_disk
    for name, digest in outputs.items():
        assert sha256_file(run_dir / name) == digest, name


def test_index_recursion_uses_the_index_unavailable_recovery_path(tmp_path):
    control, run_dir = _evaluate_changed(tmp_path, _late_prediction)
    assert control.outcome is Outcome.VIOLATION_FOUND
    deep = ("[" * 100_000 + "]" * 100_000).encode("utf-8")
    (run_dir / "index.json").write_bytes(deep)

    result = evaluate(
        tmp_path / "project", run_dir
    )  # returns; no uncaught RecursionError

    # Existing recovery contract: no trusted manifest, so no assertion set is invented, and the
    # run is INCONCLUSIVE. Stale outputs are replaced by fresh ones; the index is not rebuilt.
    assert result.outcome is Outcome.INCONCLUSIVE
    assert result.assertions == []
    assert "run index missing or unparseable" in result.reason
    written = json.loads((run_dir / "outcome.json").read_text(encoding="utf-8"))
    assert written["outcome"] == "INCONCLUSIVE" and written["assertions"] == []
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    assert report["outcome"] == "INCONCLUSIVE"
    assert not (run_dir / "checks").exists()  # the stale check files were cleared
    assert (run_dir / "index.json").read_bytes() == deep
