"""Regressions for Codex's verification of the T-01 repair pass (runs/review-t01-repair/).

Evidence-only: runs are produced by unchanged, allowlisted fixtures; afterwards only run artifacts
are altered (and rehashed where the point is semantic validation). No bypass is executed.
"""

import json
from pathlib import Path

from atlas.audit import audit, evaluate, execute
from atlas.checks.split_integrity import split_assertions
from atlas.contracts import Manifest, Outcome, Reason, Status
from atlas.intake import read_table
from atlas.policy import derive_outcome, required_assertions
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


# --- Codex pass-2 verification: all-null repeated-measures unit (verify_pass2.py) -------------------


def test_all_null_session_ids_with_shared_subjects_mirror_of_codex_reproduction():
    manifest = Manifest.model_validate_json(
        (CLEAN / "atlas_manifest.json").read_text(encoding="utf-8")
    )
    manifest.claim.dependence = [
        d for d in manifest.claim.dependence if d.column == "session_id"
    ]
    table = read_table(CLEAN, manifest)
    table["session_id"] = None
    ids = list(table.index)
    splits = [
        {
            "fold": "mixed",
            "kind": "development_eval",
            "train_ids": ids[::2],
            "eval_ids": ids[1::2],
        }
    ]

    results = split_assertions(manifest, table, splits, [])

    rm = results["split.repeated_measures_rule"]
    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA
    assert results["split.no_group_overlap"].status is Status.FAIL
    assert results["split.sampling_unit_disjoint"].status is Status.FAIL
    split_required = [
        a for a in required_assertions(manifest) if a.startswith("split.")
    ]
    assert (
        derive_outcome([results[a] for a in split_required]) is Outcome.VIOLATION_FOUND
    )


# --- Codex containment probe (runs/review-t01-containment/probe.py) ---------------------------------


def _session_only_manifest():
    manifest = Manifest.model_validate_json(
        (CLEAN / "atlas_manifest.json").read_text(encoding="utf-8")
    )
    manifest.claim.dependence = [
        d for d in manifest.claim.dependence if d.column == "session_id"
    ]
    return manifest


def test_partly_null_unrelated_overlap_mirror_of_codex_containment_probe():
    """Known sessions only in disjoint groups across partitions; overlap only via unknown sessions."""
    manifest = _session_only_manifest()
    base = read_table(CLEAN, manifest)
    ids = list(base.index)
    mixed = [
        {
            "fold": "mixed",
            "kind": "development_eval",
            "train_ids": ids[::2],
            "eval_ids": ids[1::2],
        }
    ]
    table = base.copy()
    table["session_id"] = None
    known_train = [
        r for r in mixed[0]["train_ids"] if base.loc[r, "subject_id"] == "S01"
    ]
    known_eval = [r for r in mixed[0]["eval_ids"] if base.loc[r, "subject_id"] == "S02"]
    known = known_train + known_eval
    table.loc[known, "session_id"] = base.loc[known, "session_id"]

    results = split_assertions(manifest, table, mixed, [])

    rm = results["split.repeated_measures_rule"]
    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA
    assert rm.observed["units"][0]["witnesses"] == []
    split_required = [
        a for a in required_assertions(manifest) if a.startswith("split.")
    ]
    assert (
        derive_outcome([results[a] for a in split_required]) is Outcome.VIOLATION_FOUND
    )


def test_one_missing_group_never_yields_complete_containment_or_pass():
    """Codex boundary 'one_unknown_group_with_known_group_for_same_unit' on grouped folds."""
    manifest = _session_only_manifest()
    table = read_table(CLEAN, manifest)
    run_dir_splits = []
    subjects = sorted(table["subject_id"].unique())
    for k, ev_subjects in enumerate([subjects[:4], subjects[4:]]):
        ev = list(table.index[table["subject_id"].isin(ev_subjects)])
        tr = [r for r in table.index if r not in set(ev)]
        run_dir_splits.append(
            {
                "fold": f"fold{k}",
                "kind": "development_eval",
                "train_ids": tr,
                "eval_ids": ev,
            }
        )
    table.loc[table.index[0], "subject_id"] = None

    rm = split_assertions(manifest, table, run_dir_splits, [])[
        "split.repeated_measures_rule"
    ]

    assert rm.status is Status.NOT_ASSESSED
    assert rm.reason is Reason.MISSING_METADATA
    assert rm.observed["units"][0]["complete"] is False


# --- rm-v11 'empty_eval_evaluator_boundary', through the deterministic evaluator -------------------


def test_empty_evaluation_partitions_cannot_produce_a_clean_outcome(tmp_path):
    """Recorded evidence altered (and rehashed) to empty evaluation partitions, as in Codex's
    synthetic boundary input; this is not an executed empty-evaluation run."""
    import pandas as pd

    from atlas.reports import ids_sha256

    run_dir = execute(CLEAN, tmp_path)
    splits = json.loads((run_dir / "splits.json").read_text(encoding="utf-8"))
    prov = run_dir / "provenance.jsonl"
    events = [
        json.loads(line) for line in prov.read_text(encoding="utf-8").splitlines()
    ]
    for s in splits:
        old = set(s["eval_ids"])
        s["eval_ids"] = []
        for e in events:
            if e.get("fold") == s["fold"] and e["type"] == "split":
                e["eval_sha256"] = ids_sha256([])
            if (
                e.get("rows")
                and set(e["rows"]).issubset(old)
                and e["type"] in ("take", "use", "predictions")
            ):
                e["rows"] = []
    for e in events:
        if e["type"] == "predictions":
            e["rows"] = []
            path = run_dir / e["artifact"]
            pd.DataFrame(
                {"row_id": pd.Series(dtype=str), "y_pred": pd.Series(dtype=int)}
            ).to_parquet(path, index=False)
            e["artifact_sha256"] = sha256_file(path)
            _rehash(run_dir, e["artifact"])
    write_json(run_dir / "splits.json", splits)
    prov.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    _rehash(run_dir, "splits.json")
    _rehash(run_dir, "provenance.jsonl")

    result = evaluate(CLEAN, run_dir)

    assert result.outcome is not Outcome.NO_VIOLATION_FOUND
    assert result.outcome is Outcome.INCONCLUSIVE
    ef = _by_id(result)["split.evaluation_folds_nonempty"]
    assert ef.status is Status.NOT_ASSESSED
    assert ef.reason is Reason.EMPTY_EVALUATION
