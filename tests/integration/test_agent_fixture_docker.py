"""T-06 integration (slices 2-3): fixture-driven agent runs through the real isolated runner.

    ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_agent_fixture_docker.py

Fixture model replies (no model, no network) on the s01_faulty development fixture (not
independent benchmark evidence). Since slice 3 the unmodified original and the candidate both
run in Docker, each after an explicit approval bound to its hash, and the same trusted evaluator
judges both. The second test drives the complete local path from the CLI, with the approvals
typed at a (simulated) terminal.
"""

import difflib
import io
import json
import os
import re
import sys
from pathlib import Path

import pytest

from atlas import cli
from atlas.agent import controller as ctl
from atlas.agent.client import FixtureClient
from atlas.candidates import Approval
from atlas.contracts import Outcome
from atlas.runner import docker as dr

ROOT = Path(__file__).resolve().parents[2]
S01 = ROOT / "benchmarks" / "t01" / "s01_faulty"
S02 = ROOT / "benchmarks" / "t01" / "s02_clean"
REQUIRE_DOCKER = os.environ.get("ATLAS_REQUIRE_DOCKER") == "1"
DIFF = "".join(
    difflib.unified_diff(
        (S01 / "evaluate.py").read_text(encoding="utf-8").splitlines(True),
        (S02 / "evaluate.py").read_text(encoding="utf-8").splitlines(True),
        "a/evaluate.py",
        "b/evaluate.py",
    )
)
SCRIPT = [
    {"content": json.dumps({"action": {"tool": "inspect_evidence", "check": "split_integrity"}})},
    {"content": json.dumps({"action": {"tool": "propose_patch", "diff": DIFF, "rationale": "fold-local selection, grouped folds"}})},
    {"content": json.dumps({"action": {"tool": "finish", "summary": "done"}})},
]  # fmt: skip


@pytest.fixture(scope="module")
def isolation():
    cap = dr.probe()
    if cap.state != dr.CAPABILITY_AVAILABLE:
        message = f"isolated runner unavailable: {cap.reason}"
        if REQUIRE_DOCKER:
            pytest.fail(message)
        pytest.skip(message)
    return cap


class ApproveExactly:
    def __init__(self):
        self.requests = []

    def decide(self, request):
        self.requests.append(request)
        return Approval(
            request.candidate_hash,
            request.base_snapshot_hash,
            "2026-10-16T00:00:00+00:00",
        )


def test_original_and_candidate_run_in_docker(isolation, tmp_path):
    approver = ApproveExactly()
    result = ctl.run_agent(
        S01, tmp_path / "runs", FixtureClient("s01-docker", SCRIPT), approver, env={}
    )

    assert result.terminal_state == ctl.REPORT, result.reason
    assert [r.kind for r in approver.requests] == ["original", "candidate"]
    original = result.original
    assert original.runner == "docker_isolated"
    assert original.execution["status"] == "completed"
    assert original.execution["container_removed"] is True
    assert original.outcome.outcome is Outcome.VIOLATION_FOUND
    (candidate,) = result.candidates
    assert candidate.candidate_hash == approver.requests[1].candidate_hash
    assert candidate.execution["status"] == "completed"
    assert candidate.execution["container_removed"] is True
    assert candidate.outcome.outcome is Outcome.NO_VIOLATION_FOUND
    report = result.report
    assert (report["live"], report["model_id"]) == (False, "fixture:s01-docker")
    assert report["comparison"]["comparison_basis"].startswith(
        "Original and candidates all executed in the isolated Docker runner"
    )
    assert report["scientific_outcomes"] == {
        "source": "trusted evaluator only",
        "original": Outcome.VIOLATION_FOUND,
        "candidates": [Outcome.NO_VIOLATION_FOUND],
    }
    assert report["budget"]["used"]["attempts"] == 3


class TypedAtTerminal:
    """A terminal whose user types the first 12 characters of the hash shown on screen."""

    def __init__(self, screen: io.StringIO):
        self.screen = screen

    def isatty(self):
        return True

    def readline(self):
        shown = re.findall(r"Code hash:\s+([0-9a-f]{64})", self.screen.getvalue())
        return shown[-1][:12] + "\n"


def test_cli_complete_local_path(isolation, tmp_path, monkeypatch):
    script = tmp_path / "script.json"
    script.write_text(
        json.dumps({"name": "cli-docker", "replies": SCRIPT}), encoding="utf-8"
    )
    screen = io.StringIO()
    monkeypatch.setattr(sys, "stdout", screen)
    monkeypatch.setattr(sys, "stdin", TypedAtTerminal(screen))
    monkeypatch.setenv("ATLAS_MODEL_MODE", "fixture")

    code = cli.main(
        ["audit", str(S01), "--mode", "agent", "--fixture-script", str(script),
         "--runs-dir", str(tmp_path / "runs")]
    )  # fmt: skip

    out = screen.getvalue()
    assert code == 0, out
    assert out.count("APPROVAL REQUIRED") == 2
    assert "ORIGINAL, unmodified project code" in out
    assert "original: VIOLATION_FOUND (docker_isolated)" in out
    assert "execution completed, outcome NO_VIOLATION_FOUND" in out
    (report_path,) = (tmp_path / "runs").glob("agent-*/agent_report.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    approvals = [
        json.loads(line)
        for line in report_path.with_name("agent_log.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if '"event": "approval"' in line
    ]
    assert [a["approver_reason"] for a in approvals] == ["confirmed", "confirmed"]
    assert all(
        len(a["approval"]["candidate_hash"]) == 64 for a in approvals
    )  # full hash
    assert report["terminal_state"] == "REPORT"


def test_a_full_source_revision_runs_in_docker(isolation, tmp_path):
    """T-06 slice 4c: `new_source` (the complete s02 file) instead of a diff. ATLAS generates
    the diff, validate_diff passes it unchanged, and the candidate runs in the real runner."""
    fix = (S02 / "evaluate.py").read_text(encoding="utf-8")
    script = [
        {"content": json.dumps({"action": {"tool": "propose_patch", "new_source": fix, "rationale": "fold-local selection, grouped folds"}})},
        {"content": json.dumps({"action": {"tool": "finish", "summary": "done"}})},
    ]  # fmt: skip
    approver = ApproveExactly()
    result = ctl.run_agent(
        S01, tmp_path / "runs", FixtureClient("s4c-docker", script), approver, env={}
    )

    assert result.terminal_state == ctl.REPORT, result.reason
    assert approver.requests[1].diff == DIFF  # the generated diff is what is approved
    (candidate,) = result.candidates
    assert candidate.execution["status"] == "completed"
    assert candidate.execution["container_removed"] is True
    assert candidate.outcome.outcome is Outcome.NO_VIOLATION_FOUND
    (record,) = result.report["proposals"]
    assert (record["source_kind"], record["outcome"]) == ("new_source", "executed")
    run = result.run_dir
    assert (run / record["new_source_path"]).read_bytes() == fix.encode("utf-8")
    assert (run / record["diff_path"]).read_bytes() == DIFF.encode("utf-8")
    assert record["diff_sha256"] == candidate.diff_sha256


def test_a_corrected_malformed_revision_runs_in_docker(isolation, tmp_path):
    """T-06 slice 4d: inspect, then a new_source pasted raw into the JSON string (real
    newlines and quotes: not_json), then the same file properly escaped. The malformed reply
    is stored byte for byte and corrected once; the valid revision is approved by the test
    approver, executes in the real runner and is recorded as executed."""
    fix = (S02 / "evaluate.py").read_text(encoding="utf-8")
    malformed = (
        '{"action": {"tool": "propose_patch", "new_source": "'
        + fix
        + '", "rationale": "fold-local selection, grouped folds"}}'
    )
    script = [
        {"content": json.dumps({"action": {"tool": "read_project_file", "path": "evaluate.py"}})},
        {"content": malformed},
        {"content": json.dumps({"action": {"tool": "propose_patch", "new_source": fix, "rationale": "fold-local selection, grouped folds"}})},
        {"content": json.dumps({"action": {"tool": "finish", "summary": "done"}})},
    ]  # fmt: skip
    approver = ApproveExactly()
    client = FixtureClient("s4d-docker", script)
    result = ctl.run_agent(S01, tmp_path / "runs", client, approver, env={})

    assert result.terminal_state == ctl.REPORT, result.reason
    assert [r.kind for r in approver.requests] == ["original", "candidate"]
    assert approver.requests[1].diff == DIFF
    (candidate,) = result.candidates
    assert candidate.execution["status"] == "completed"
    assert candidate.execution["container_removed"] is True
    assert candidate.outcome.outcome is Outcome.NO_VIOLATION_FOUND
    (record,) = result.report["proposals"]
    assert (record["source_kind"], record["outcome"]) == ("new_source", "executed")
    run = result.run_dir
    assert (run / "replies" / "a2.txt").read_bytes() == malformed.encode("utf-8")
    assert result.report["schema_failures"] == [
        {"attempt": 2, "code": "not_json", "corrected": True}
    ]
    assert len(client.requests) == 4
    assert result.report["budget"]["used"]["attempts"] == 4


def test_the_live_run_3b_replay_runs_a_candidate_in_docker(isolation, tmp_path):
    """T-06 slice 4e: live run 3b's first two replies byte for byte (a read, then
    `list_project_files` with a rationale, now accepted), then a valid new_source revision. The
    test approver grants the exact original and candidate; the candidate executes in the real
    runner and is recorded as executed."""
    fix = (S02 / "evaluate.py").read_text(encoding="utf-8")
    a1 = '\n{\n    "action": {\n        "tool": "read_project_file",\n        "path": "evaluate.py"\n    }\n}'  # fmt: skip
    a2 = '\n{\n  "action": {\n    "tool": "list_project_files",\n    "rationale": "Need to see what other files exist (e.g., data, metadata) to understand column names and structure before proposing a patch."\n  }\n}'  # fmt: skip
    script = [
        {"content": a1},
        {"content": a2},
        {"content": json.dumps({"action": {"tool": "propose_patch", "new_source": fix, "rationale": "fold-local selection, grouped folds"}})},
        {"content": json.dumps({"action": {"tool": "finish", "summary": "done"}})},
    ]  # fmt: skip
    approver = ApproveExactly()
    client = FixtureClient("s4e-docker", script)
    result = ctl.run_agent(S01, tmp_path / "runs", client, approver, env={})

    assert result.terminal_state == ctl.REPORT, result.reason
    assert result.report["schema_failures"] == []
    assert [r.kind for r in approver.requests] == ["original", "candidate"]
    (candidate,) = result.candidates
    assert candidate.execution["status"] == "completed"
    assert candidate.execution["container_removed"] is True
    assert candidate.outcome.outcome is Outcome.NO_VIOLATION_FOUND
    (record,) = result.report["proposals"]
    assert (record["source_kind"], record["outcome"]) == ("new_source", "executed")
    assert (result.run_dir / "replies" / "a2.txt").read_bytes() == a2.encode("utf-8")
    assert len(client.requests) == 4
    assert result.report["budget"]["used"]["attempts"] == 4


def test_the_live_run_4_replay_feeds_the_error_back_and_the_fix_runs(
    isolation, tmp_path
):
    """T-06 slice 4f: live run 4's first revision byte for byte (it reads X['subject_id'],
    which load_table() does not return), executed in the real runner, fails; the next request's
    evaluate_candidate result carries the bounded, untrusted failure summary. The revision
    corrected to take the groups from adapter.load_metadata() then executes, and the trusted
    evaluator gives its outcome."""
    c1 = (ROOT / "tests" / "fixtures" / "live4_r1_new_source.txt").read_text(
        encoding="utf-8"
    )
    fixed = c1.replace(
        "groups = X['subject_id']",
        'groups = adapter.load_metadata().loc[X.index, "subject_id"]',
    )
    assert fixed != c1
    script = [
        {"content": json.dumps({"action": {"tool": "propose_patch", "new_source": c1, "rationale": "grouped folds"}})},
        {"content": json.dumps({"action": {"tool": "propose_patch", "new_source": fixed, "rationale": "groups from load_metadata"}})},
        {"content": json.dumps({"action": {"tool": "finish", "summary": "done"}})},
    ]  # fmt: skip
    approver = ApproveExactly()
    client = FixtureClient("s4f-docker", script)
    result = ctl.run_agent(S01, tmp_path / "runs", client, approver, env={})

    assert result.terminal_state == ctl.REPORT, result.reason
    assert [r.kind for r in approver.requests] == ["original", "candidate", "candidate"]
    first, second = result.candidates
    assert first.execution["status"] == "failed"
    assert first.outcome.outcome is Outcome.INCONCLUSIVE
    # What the model saw after the failing revision.
    (user,) = [m for m in client.requests[1].messages if m["role"] == "user"]
    history = json.loads(user["content"])["history"]
    (seen,) = [h["result"] for h in history if h["tool"] == "evaluate_candidate"]
    summary = seen["failure_summary"]
    assert summary["label"] == "candidate output (untrusted)"
    assert summary["exception"] == "KeyError: 'subject_id'"
    assert "groups = X['subject_id']" in summary["traceback"]
    assert len(summary["exception"]) + len(summary["traceback"]) <= 2000
    assert str(tmp_path) not in json.dumps(summary)
    entries = result.report["comparison"]["candidates"]
    assert entries[0]["failure_summary"] == summary
    assert entries[1]["failure_summary"] is None
    # The corrected revision ran in isolation and the trusted evaluator judged it.
    assert second.execution["status"] == "completed"
    assert second.execution["container_removed"] is True
    assert second.outcome.outcome is Outcome.NO_VIOLATION_FOUND, second.outcome.reason
    assert [p["outcome"] for p in result.report["proposals"]] == [
        "executed",
        "executed",
    ]
    assert len(client.requests) == 3
