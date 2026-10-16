"""T-06 slice 1 integration: real Docker, real candidates, trusted re-evaluation (SPEC §6, §9).

Acceptance command (fails instead of skipping when isolation is unavailable):
    ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_candidate_reevaluation_docker.py

Project: benchmarks/t01/s01_faulty (lead decision for T-06 integration acceptance). The original
is audited by the trusted host-fixture runner, so the comparison is labelled host baseline
versus Docker candidate; final agent acceptance requires Docker for both. Each candidate goes
through the full SPEC §9 path (snapshot -> unified diff -> validation -> approval -> hash-checked
staging -> container) and the image is confirmed by Docker itself during evaluation.
"""

import difflib
import json
import os
from pathlib import Path

import pytest

from atlas.agent.execute import execute_and_reevaluate
from atlas.agent.report import MIXED_BASIS, comparison_report
from atlas.audit import audit
from atlas.candidates import approve, build_snapshot, validate_diff
from atlas.contracts import Outcome, Status
from atlas.runner import docker as dr

ROOT = Path(__file__).resolve().parents[2]
S01 = ROOT / "benchmarks" / "t01" / "s01_faulty"
S02 = ROOT / "benchmarks" / "t01" / "s02_clean"
REQUIRE_DOCKER = os.environ.get("ATLAS_REQUIRE_DOCKER") == "1"
ORIGINAL = (S01 / "evaluate.py").read_text(encoding="utf-8")
CANDIDATES = {
    # Fold-local selection and grouped folds: the entry point of the clean fixture.
    "fold_local": (S02 / "evaluate.py").read_text(encoding="utf-8"),
    # Runs to completion, changes nothing that matters: the violation remains.
    "cosmetic": ORIGINAL + "# reviewed: no functional change\n",
    # Fails before any split, fit or prediction exists.
    "early_failure": 'raise SystemExit("stopped before any evidence")\n' + ORIGINAL,
    # Produces the complete faulty evidence, then fails.
    "late_failure": ORIGINAL + 'raise SystemExit("failed after writing evidence")\n',
}


@pytest.fixture(scope="module")
def isolation():
    cap = dr.probe()
    if cap.state != dr.CAPABILITY_AVAILABLE:
        message = f"isolated runner unavailable: {cap.reason}"
        if REQUIRE_DOCKER:
            pytest.fail(message)
        pytest.skip(message)
    return cap


@pytest.fixture(scope="module")
def original(tmp_path_factory):
    return audit(S01, tmp_path_factory.mktemp("original"))


@pytest.fixture(scope="module")
def results(isolation, tmp_path_factory):
    out = {}
    for name, source in CANDIDATES.items():
        base = tmp_path_factory.mktemp(name)
        snap = build_snapshot(S01, base / "snapshot")
        diff = "".join(
            difflib.unified_diff(
                ORIGINAL.splitlines(True),
                source.splitlines(True),
                "a/evaluate.py",
                "b/evaluate.py",
            )
        )
        cand = validate_diff(snap, diff)
        out[name] = execute_and_reevaluate(
            snap, cand, approve(snap, cand), base / "agent" / "c1"
        )
    return out


def _statuses(outcome):
    return {a.assertion_id: a.status for a in outcome.assertions}


def _record(result):
    path = result.candidate_dir / "exec" / "execution.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_every_container_was_removed(results):
    for name, result in results.items():
        record = _record(result)
        assert record["container_removed"] is True, name
        assert record["cleanup"]["status"] == dr.CLEANUP_CONFIRMED, name


def test_fold_local_candidate_completes_and_finds_no_violation(original, results):
    result = results["fold_local"]
    assert original.outcome.outcome is Outcome.VIOLATION_FOUND
    assert result.execution["status"] == "completed"
    assert result.outcome.outcome is Outcome.NO_VIOLATION_FOUND, result.outcome.reason
    assert [a.assertion_id for a in result.outcome.assertions] == [
        a.assertion_id for a in original.outcome.assertions
    ]


def test_completed_execution_can_still_show_the_violation(results):
    result = results["cosmetic"]
    assert result.execution["status"] == "completed"
    assert result.outcome.outcome is Outcome.VIOLATION_FOUND
    assert result.outcome.reason is None  # trusted, completed: the FAIL is the finding


def test_failure_before_evidence_is_inconclusive(results):
    result = results["early_failure"]
    assert result.execution["status"] == "failed"
    assert result.outcome.outcome is Outcome.INCONCLUSIVE
    assert not {Status.PASS, Status.FAIL} & set(_statuses(result.outcome).values())


def test_failure_after_evidence_keeps_the_violation(results):
    result = results["late_failure"]
    assert result.execution["status"] == "failed"
    assert result.outcome.outcome is Outcome.VIOLATION_FOUND
    assert Status.PASS not in _statuses(result.outcome).values()


def test_comparison_report_labels_the_mixed_runner_basis(original, results):
    report = comparison_report(
        original.run_dir, original.outcome, list(results.values())
    )
    assert report["comparison_basis"] == MIXED_BASIS
    outcomes = {
        (c["execution"]["status"], c["scientific_outcome"])
        for c in report["candidates"]
    }
    assert outcomes == {
        ("completed", Outcome.NO_VIOLATION_FOUND),
        ("completed", Outcome.VIOLATION_FOUND),
        ("failed", Outcome.INCONCLUSIVE),
        ("failed", Outcome.VIOLATION_FOUND),
    }
