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
