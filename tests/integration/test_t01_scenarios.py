"""T-01 acceptance scenarios (TASKS.md): expected assertion statuses, not only outcomes.

Each scenario is a trusted, repo-authored fixture under benchmarks/t01/, executed in a host
subprocess under the fixture hash allowlist (SPEC §10) and judged by the trusted evaluator.
"""

import json
import shutil
from pathlib import Path

import pytest

from atlas.audit import audit, evaluate, execute
from atlas.contracts import Manifest, Outcome, Reason, Status
from atlas.policy import required_assertions
from atlas.runner.trusted import UntrustedFixtureError

FIXTURES = Path(__file__).resolve().parents[2] / "benchmarks" / "t01"
P, F, N, E = Status.PASS, Status.FAIL, Status.NOT_ASSESSED, Status.ERROR
COLUMNS = [
    "split.no_row_overlap",  # RO
    "split.no_shared_source_observation",  # SO
    "split.no_group_overlap",  # GO
    "split.sampling_unit_disjoint",  # SU
    "split.repeated_measures_rule",  # RM
    "fit.state_dependencies_within_fold_train",  # SD
    "fit.coverage_complete",  # CC
    "metric.prediction_ids_match_eval_ids",  # PI
]
UNKNOWN = (N, Reason.UNKNOWN_ANCESTRY)
GAP = (N, Reason.COVERAGE_GAP)
ZERO = (N, Reason.ZERO_FIT)
MISSING = (N, Reason.MISSING_METADATA)

# scenario directory -> (RO, SO, GO, SU, RM, SD, CC, PI), other required assertions, outcome
EXPECTED = {
    "s01_faulty": ((P, P, F, F, F, F, P, P), {}, Outcome.VIOLATION_FOUND),
    "s02_clean": ((P, P, P, P, P, P, P, P), {}, Outcome.NO_VIOLATION_FOUND),
    "s03a_rebuilt_frame": ((P, P, P, P, P, UNKNOWN, GAP, P), {}, Outcome.INCONCLUSIVE),
    "s03b_inplace_mutation": (
        (P, P, P, P, P, UNKNOWN, GAP, P),
        {},
        Outcome.INCONCLUSIVE,
    ),
    "s04_zero_fit": ((P, P, P, P, P, ZERO, ZERO, P), {}, Outcome.INCONCLUSIVE),
    "s05a_contaminated_reuse": ((P, P, P, P, P, F, P, P), {}, Outcome.VIOLATION_FOUND),
    "s05b_benign_reuse": ((P, P, P, P, P, P, P, P), {}, Outcome.NO_VIOLATION_FOUND),
    "s06_missing_metadata": (
        (P, P, MISSING, MISSING, MISSING, P, P, P),
        {},
        Outcome.INCONCLUSIVE,
    ),
    # policy-v1.3: the window assertion is implemented. Under policy-v1.2 this fixture was
    # NOT_ASSESSED(unimplemented_assertion) and INCONCLUSIVE; that historical result stands.
    "s07_unimplemented_window": (
        (P, P, P, P, P, P, P, P),
        {"split.no_window_overlap": P},
        Outcome.NO_VIOLATION_FOUND,
    ),
    "s10a_identical_values_with_ids": (
        (P, P, P, P, P, P, P, P),
        {},
        Outcome.NO_VIOLATION_FOUND,
    ),
    "s10b_identical_values_no_ids": (
        (P, (N, Reason.UNRESOLVED_DUPLICATE_CANDIDATES), P, P, P, P, P, P),
        {},
        Outcome.INCONCLUSIVE,
    ),
    "s10c_known_duplicate": ((P, F, P, P, P, P, P, P), {}, Outcome.VIOLATION_FOUND),
}


def _assert_status(result, expected):
    status, reason = expected if isinstance(expected, tuple) else (expected, None)
    assert result.status is status, (
        f"{result.assertion_id}: {result.status} {result.reason} != {status} {reason}"
    )
    if reason is not None:
        assert result.reason is reason, (
            f"{result.assertion_id}: reason {result.reason} != {reason}"
        )


def _manifest(name):
    return Manifest.model_validate_json(
        (FIXTURES / name / "atlas_manifest.json").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_scenario_assertion_statuses_and_outcome(name, tmp_path):
    row, others, outcome = EXPECTED[name]

    result = audit(FIXTURES / name, tmp_path).outcome

    by_id = {a.assertion_id: a for a in result.assertions}
    for aid, expected in zip(COLUMNS, row, strict=True):
        _assert_status(by_id[aid], expected)
    for aid, expected in others.items():
        _assert_status(by_id[aid], expected)
    assert result.outcome is outcome


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_every_required_assertion_is_listed_once_and_none_dropped(name, tmp_path):
    result = audit(FIXTURES / name, tmp_path).outcome

    listed = [a.assertion_id for a in result.assertions]
    assert listed == required_assertions(_manifest(name))
    for a in result.assertions:
        if a.status is Status.NOT_ASSESSED:
            assert a.reason is not None, a.assertion_id


def test_combined_claim_is_not_supported_and_nothing_executes(tmp_path):
    result = audit(FIXTURES / "s08a_combined_claim", tmp_path)

    assert result.outcome.outcome is Outcome.NOT_SUPPORTED
    assert result.outcome.assertions == []
    assert not (result.run_dir / "provenance.jsonl").exists()


def test_entry_point_without_adapter_is_not_supported_and_nothing_executes(tmp_path):
    result = audit(FIXTURES / "s08b_no_adapter", tmp_path)

    assert result.outcome.outcome is Outcome.NOT_SUPPORTED
    assert "adapter" in result.outcome.reason
    assert not (result.run_dir / "provenance.jsonl").exists()


def _corrupt(path: Path):
    data = path.read_bytes()
    path.write_bytes(data + b'{"type": "gap", "reason": "tampered"}\n')


def test_corrupted_provenance_keeps_the_independent_valid_fail(tmp_path):
    run_dir = execute(FIXTURES / "s01_faulty", tmp_path)
    _corrupt(run_dir / "provenance.jsonl")

    result = evaluate(FIXTURES / "s01_faulty", run_dir)

    by_id = {a.assertion_id: a for a in result.assertions}
    for aid, expected in zip(COLUMNS, (P, P, F, F, F, E, E, P), strict=True):
        _assert_status(by_id[aid], expected)
    assert result.outcome is Outcome.VIOLATION_FOUND
    assert set(result.incomplete_coverage) == {
        "fit.state_dependencies_within_fold_train",
        "fit.coverage_complete",
    }


def test_corrupted_provenance_alone_is_inconclusive(tmp_path):
    run_dir = execute(FIXTURES / "s02_clean", tmp_path)
    _corrupt(run_dir / "provenance.jsonl")

    result = evaluate(FIXTURES / "s02_clean", run_dir)

    by_id = {a.assertion_id: a for a in result.assertions}
    for aid, expected in zip(COLUMNS, (P, P, P, P, P, E, E, P), strict=True):
        _assert_status(by_id[aid], expected)
    assert result.outcome is Outcome.INCONCLUSIVE


def test_identical_value_candidates_are_reported_not_judged(tmp_path):
    result = audit(FIXTURES / "s10a_identical_values_with_ids", tmp_path).outcome

    so = next(
        a
        for a in result.assertions
        if a.assertion_id == "split.no_shared_source_observation"
    )
    assert any(so.observed["duplicate_candidates"].values())


def test_evidence_files_are_written_and_hashed(tmp_path):
    run_dir = audit(FIXTURES / "s02_clean", tmp_path).run_dir

    index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    for name in (
        "provenance.jsonl",
        "splits.json",
        "manifest.snapshot.json",
        "outcome.json",
        "report.json",
    ):
        assert (run_dir / name).exists(), name
    assert "provenance.jsonl" in index["artifacts"]
    outcome = json.loads((run_dir / "outcome.json").read_text(encoding="utf-8"))
    assert outcome["outcome"] == "NO_VIOLATION_FOUND"
    assert outcome["policy_version"] == "policy-v1.3"


def test_modified_fixture_is_refused_before_execution(tmp_path):
    copy = tmp_path / "s02_modified"
    shutil.copytree(FIXTURES / "s02_clean", copy)
    entry = copy / "evaluate.py"
    entry.write_text(
        entry.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8"
    )

    with pytest.raises(UntrustedFixtureError):
        execute(copy, tmp_path / "runs")
    assert not (tmp_path / "runs").exists() or not any(
        (tmp_path / "runs").rglob("provenance.jsonl")
    )


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_every_executed_scenario_has_nonempty_evaluation_folds(name, tmp_path):
    """policy-v1.2 prerequisite: all T-01 fixtures truthfully declare nonempty evaluation folds."""
    result = audit(FIXTURES / name, tmp_path).outcome

    ef = next(
        a
        for a in result.assertions
        if a.assertion_id == "split.evaluation_folds_nonempty"
    )
    assert ef.status is Status.PASS


def test_s07_window_pass_rests_on_disjoint_stream_membership(tmp_path):
    """Route D without bounds: every stream lies in one partition of every fold (policy-v1.3)."""
    result = audit(FIXTURES / "s07_unimplemented_window", tmp_path).outcome

    window = next(
        a for a in result.assertions if a.assertion_id == "split.no_window_overlap"
    )
    assert window.status is Status.PASS
    assert set(window.observed["established_by"].values()) == {
        "stream_membership_disjoint"
    }
    assert any("not proof of statistical independence" in x for x in window.limitations)
