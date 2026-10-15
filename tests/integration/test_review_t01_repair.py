"""Regressions for Codex's verification of the T-01 repair pass (runs/review-t01-repair/).

Evidence-only: runs are produced by unchanged, allowlisted fixtures; afterwards only run artifacts
are altered (and rehashed where the point is semantic validation). No bypass is executed.
"""

import json
from pathlib import Path

from atlas.audit import audit, evaluate, execute
from atlas.contracts import Outcome, Reason, Status
from atlas.reports import sha256_file, write_json

FIXTURES = Path(__file__).resolve().parents[2] / "benchmarks" / "t01"
CLEAN = FIXTURES / "s02_clean"
FAULTY = FIXTURES / "s01_faulty"
PI = "metric.prediction_ids_match_eval_ids"


def _index(run_dir: Path) -> dict:
    return json.loads((run_dir / "index.json").read_text(encoding="utf-8"))


def _rehash(run_dir: Path, name: str) -> None:
    index = _index(run_dir)
    index["artifacts"][name] = sha256_file(run_dir / name)
    write_json(run_dir / "index.json", index)


def _by_id(outcome):
    return {a.assertion_id: a for a in outcome.assertions}


def _assert_outputs_consistent(run_dir: Path) -> dict:
    """Every indexed output exists and hashes correctly; every output file is indexed."""
    outputs = _index(run_dir).get("outputs", {})
    for name, digest in outputs.items():
        assert (run_dir / name).exists(), f"indexed output missing: {name}"
        assert sha256_file(run_dir / name) == digest, f"stale hash for {name}"
    on_disk = {"outcome.json", "report.json"} | {
        f"checks/{p.name}" for p in (run_dir / "checks").glob("*.json")
    }
    assert {n for n in on_disk if (run_dir / n).exists()} == set(outputs)
    return outputs


# --- Blocker 1: invalid orphan artifact must not invent a violation -------------------------------


def test_invalid_orphan_artifact_with_a_colliding_stem_is_an_evidence_error(tmp_path):
    run_dir = execute(CLEAN, tmp_path)
    index = _index(run_dir)
    index["artifacts"]["predictions/orphan/fold0.parquet"] = (
        "0" * 64
    )  # file does not exist
    write_json(run_dir / "index.json", index)

    result = evaluate(CLEAN, run_dir)

    pi = _by_id(result)[PI]
    assert pi.status is Status.ERROR
    assert pi.observed["mismatches"] == {}
    assert pi.observed["unexpected_artifacts"] == ["predictions/orphan/fold0.parquet"]
    assert result.outcome is Outcome.INCONCLUSIVE


def test_provenance_cannot_remap_a_fold_to_another_folds_artifact(tmp_path):
    run_dir = execute(CLEAN, tmp_path)
    path = run_dir / "provenance.jsonl"
    events = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
    ]
    pred = next(
        e for e in events if e["type"] == "predictions" and e["fold"] == "fold1"
    )
    pred["artifact"] = "predictions/fold0.parquet"
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    _rehash(run_dir, "provenance.jsonl")

    result = evaluate(CLEAN, run_dir)

    by_id = _by_id(result)
    assert by_id[PI].status is Status.ERROR
    assert by_id[PI].observed["mismatches"] == {}
    assert by_id["fit.coverage_complete"].reason is Reason.COVERAGE_GAP
    assert result.outcome is Outcome.INCONCLUSIVE


# --- Blocker 3: recovery-path outputs are finalized consistently -----------------------------------


def test_normal_run_outputs_are_all_indexed_with_current_hashes(tmp_path):
    run_dir = audit(CLEAN, tmp_path).run_dir

    outputs = _assert_outputs_consistent(run_dir)

    assert any(n.startswith("checks/") for n in outputs)


def test_unrecoverable_manifest_outputs_have_current_hashes_and_no_stale_check_entries(
    tmp_path,
):
    first = audit(CLEAN, tmp_path)
    (first.run_dir / "manifest.snapshot.json").unlink()
    changed = tmp_path / "changed_project"
    changed.mkdir()
    for name in ("atlas_manifest.json", "evaluate.py", "table.csv"):
        (changed / name).write_bytes((CLEAN / name).read_bytes())
    manifest = json.loads((changed / "atlas_manifest.json").read_text(encoding="utf-8"))
    manifest["claim"]["statement"] = "changed after the recorded run"
    write_json(changed / "atlas_manifest.json", manifest)

    result = evaluate(changed, first.run_dir)

    assert result.outcome is Outcome.INCONCLUSIVE
    outputs = _assert_outputs_consistent(first.run_dir)
    assert set(outputs) == {"outcome.json", "report.json"}


# --- Blocker 4: a missing snapshot stays a visible evidence error ----------------------------------


def test_missing_snapshot_with_matching_fallback_keeps_errors_and_is_inconclusive(
    tmp_path,
):
    run_dir = execute(CLEAN, tmp_path)
    (run_dir / "manifest.snapshot.json").unlink()

    result = evaluate(CLEAN, run_dir)

    assert result.outcome is Outcome.INCONCLUSIVE
    assert "manifest snapshot" in result.reason
    assert result.assertions, "the required set is reconstructed, not dropped"
    for a in result.assertions:
        assert a.status is Status.ERROR, a.assertion_id
        assert a.reason is Reason.EVIDENCE_INVALID
    _assert_outputs_consistent(run_dir)


def test_missing_snapshot_keeps_independent_valid_fails(tmp_path):
    run_dir = execute(FAULTY, tmp_path)
    (run_dir / "manifest.snapshot.json").unlink()

    result = evaluate(FAULTY, run_dir)

    by_id = _by_id(result)
    assert by_id["split.no_group_overlap"].status is Status.FAIL
    assert result.outcome is Outcome.VIOLATION_FOUND
    assert all(a.status is not Status.PASS for a in result.assertions)


# --- Blocker 5: semantic runtime and execution validation (validator tests; nothing executed) -------


def test_rehashed_runtime_record_with_safe_path_false_is_rejected(tmp_path):
    run_dir = execute(CLEAN, tmp_path)
    runtime = json.loads((run_dir / "runtime.json").read_text(encoding="utf-8"))
    runtime["safe_path"] = False
    write_json(run_dir / "runtime.json", runtime)
    _rehash(run_dir, "runtime.json")

    result = evaluate(CLEAN, run_dir)

    assert result.outcome is Outcome.INCONCLUSIVE
    assert all(a.status is not Status.PASS for a in result.assertions)
    assert "controlled launcher" in result.reason


def test_rehashed_execution_record_claiming_another_capability_is_rejected(tmp_path):
    run_dir = execute(CLEAN, tmp_path)
    record = json.loads((run_dir / "execution.json").read_text(encoding="utf-8"))
    record["capability"] = "isolated_available"
    write_json(run_dir / "execution.json", record)
    _rehash(run_dir, "execution.json")

    result = evaluate(CLEAN, run_dir)

    assert result.outcome is Outcome.INCONCLUSIVE
    assert all(a.status is not Status.PASS for a in result.assertions)
