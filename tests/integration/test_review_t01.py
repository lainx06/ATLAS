"""Regression tests for the independent Codex review of T-01 (runs/review-t01/probe.py, results.json).

Each test reproduces one finding through the trusted evaluator. No modified fixture is executed.
"""

import json
import shutil
from pathlib import Path

import pytest

import atlas
from atlas.audit import audit, evaluate, execute
from atlas.contracts import Outcome, Reason, Status
from atlas.reports import sha256_file, write_json
from atlas.runner.trusted import (
    UntrustedFixtureError,
    is_trusted,
    trusted_atlas_parent,
)

FIXTURES = Path(__file__).resolve().parents[2] / "benchmarks" / "t01"
CLEAN = FIXTURES / "s02_clean"
FAULTY = FIXTURES / "s01_faulty"


def _by_id(outcome):
    return {a.assertion_id: a for a in outcome.assertions}


def _rehash(run_dir: Path, name: str) -> None:
    index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    index["artifacts"][name] = sha256_file(run_dir / name)
    write_json(run_dir / "index.json", index)


# --- Finding 1: trusted-fixture import loophole --------------------------------------------


def test_fixture_with_an_extra_file_is_not_trusted_and_does_not_run(tmp_path):
    copy = tmp_path / "s02_with_extra_module"
    shutil.copytree(CLEAN, copy)
    (copy / "atlas.py").write_text("# inert marker; never executed\n", encoding="utf-8")

    assert is_trusted(copy, "evaluate.py") is False
    with pytest.raises(UntrustedFixtureError):
        execute(copy, tmp_path / "runs")
    assert not list((tmp_path / "runs").rglob("provenance.jsonl"))


def test_fixture_child_imports_atlas_from_the_trusted_package_not_the_fixture(tmp_path):
    run_dir = execute(CLEAN, tmp_path)

    runtime = json.loads((run_dir / "runtime.json").read_text(encoding="utf-8"))
    # The trusted root is the package THIS (trusted) process imported: src/atlas normally, the
    # intended temporary copy during the mutation check. It must also be the root the runner
    # selected explicitly, and the child must have imported exactly that package.
    selected = (Path(trusted_atlas_parent()) / "atlas").resolve()
    assert selected == Path(atlas.__file__).resolve().parent
    assert Path(runtime["atlas_origin"]).resolve().parent == selected
    assert runtime["isolated"] == 1
    assert runtime["safe_path"] is True
    assert runtime["project_dir_on_sys_path"] is False


# --- Finding 2: split declarations, predictions and provenance must reconcile ----------------


def test_fold_removed_from_splits_but_present_elsewhere_prevents_complete_coverage(
    tmp_path,
):
    run_dir = execute(CLEAN, tmp_path)
    splits = json.loads((run_dir / "splits.json").read_text(encoding="utf-8"))
    splits.pop(0)
    write_json(run_dir / "splits.json", splits)
    _rehash(run_dir, "splits.json")

    result = evaluate(CLEAN, run_dir)

    by_id = _by_id(result)
    cc = by_id["fit.coverage_complete"]
    assert cc.status is Status.NOT_ASSESSED and cc.reason is Reason.COVERAGE_GAP
    assert by_id["metric.prediction_ids_match_eval_ids"].status is Status.ERROR
    assert result.outcome is Outcome.INCONCLUSIVE


# --- Finding 5: execution evidence is verified and schema-validated ---------------------------


def test_hash_mismatched_execution_record_leaves_no_pass(tmp_path):
    run_dir = execute(CLEAN, tmp_path)
    with (run_dir / "execution.json").open("a", encoding="utf-8") as f:
        f.write("\n")

    result = evaluate(CLEAN, run_dir)

    assert result.outcome is Outcome.INCONCLUSIVE
    assert all(a.status is not Status.PASS for a in result.assertions)


def test_schema_invalid_execution_record_is_not_trusted_even_when_rehashed(tmp_path):
    run_dir = execute(CLEAN, tmp_path)
    # Looks like success to a naive reader, but lacks the required execution-record fields.
    write_json(run_dir / "execution.json", {"returncode": 0})
    _rehash(run_dir, "execution.json")

    result = evaluate(CLEAN, run_dir)

    assert result.outcome is Outcome.INCONCLUSIVE
    assert all(a.status is not Status.PASS for a in result.assertions)


def test_corrupted_execution_record_keeps_independent_valid_fails(tmp_path):
    run_dir = execute(FAULTY, tmp_path)
    with (run_dir / "execution.json").open("a", encoding="utf-8") as f:
        f.write("\n")

    result = evaluate(FAULTY, run_dir)

    by_id = _by_id(result)
    assert by_id["split.no_group_overlap"].status is Status.FAIL
    assert by_id["fit.state_dependencies_within_fold_train"].status is Status.FAIL
    assert result.outcome is Outcome.VIOLATION_FOUND
    assert all(a.status is not Status.PASS for a in result.assertions)


# --- Finding 6: missing prediction artifacts are ERROR, not FAIL ---------------------------------


def test_missing_prediction_artifact_is_error_not_fail(tmp_path):
    run_dir = execute(CLEAN, tmp_path)
    index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    name = next(n for n in index["artifacts"] if n.startswith("predictions/"))
    (run_dir / name).unlink()
    del index["artifacts"][name]
    write_json(run_dir / "index.json", index)

    result = evaluate(CLEAN, run_dir)

    pi = _by_id(result)["metric.prediction_ids_match_eval_ids"]
    assert pi.status is Status.ERROR
    assert result.outcome is Outcome.INCONCLUSIVE


# --- Finding 7: missing or unparseable manifest snapshot ------------------------------------------


def test_missing_snapshot_reconstructs_the_required_set_without_crashing(tmp_path):
    """Finding 7 (crash). The outcome expectation was corrected by repair round 2 (blocker 4):
    a missing snapshot stays an evidence error, so the result is not clean."""
    run_dir = execute(CLEAN, tmp_path)
    (run_dir / "manifest.snapshot.json").unlink()

    result = evaluate(CLEAN, run_dir)

    assert result.outcome is Outcome.INCONCLUSIVE
    assert "reconstructed" in (result.reason or "")
    assert len(result.assertions) == 8


def test_unreconstructable_required_set_is_reported_and_replaces_a_stale_clean_outcome(
    tmp_path,
):
    first = audit(CLEAN, tmp_path)
    assert first.outcome.outcome is Outcome.NO_VIOLATION_FOUND
    (first.run_dir / "manifest.snapshot.json").write_text("{not json", encoding="utf-8")
    changed = tmp_path / "project_with_changed_manifest"
    shutil.copytree(CLEAN, changed)
    manifest = json.loads((changed / "atlas_manifest.json").read_text(encoding="utf-8"))
    manifest["claim"]["statement"] = "edited after execution"
    (changed / "atlas_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = evaluate(changed, first.run_dir)

    assert result.outcome is Outcome.INCONCLUSIVE
    assert result.assertions == []
    assert "could not be reconstructed" in result.reason
    written = json.loads((first.run_dir / "outcome.json").read_text(encoding="utf-8"))
    assert written["outcome"] == "INCONCLUSIVE"
    assert not (first.run_dir / "checks").exists()


# --- Reporting improvement: originating fitted state ---------------------------------------------


def test_violation_report_names_the_originating_global_fit_once(tmp_path):
    result = audit(FAULTY, tmp_path).outcome

    sd = _by_id(result)["fit.state_dependencies_within_fold_train"]
    origins = sd.observed["origins"]
    assert len(origins) == 1
    origin = origins[0]
    assert origin["class"] == "SelectKBest"
    assert origin["fit_scope"] == "global"
    assert origin["labels_used"] is True
    assert origin["contributing_rows"] == 160
    assert set(origin["affected_folds"]) == {"fold0", "fold1", "fold2", "fold3"}
    assert sd.status is Status.FAIL
