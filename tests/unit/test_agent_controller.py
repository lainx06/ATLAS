"""T-06 slice 2: the bounded controller with fixture model replies (offline).

Most tests use a recording executor, so they test the controller's decisions, not execution.
`test_end_to_end_through_the_slice_1_executor` drives the real slice 1 executor with the fake
Docker harness of tests/unit/test_candidate_reevaluation.py; the real-Docker version is in
tests/integration/test_agent_fixture_docker.py. The original is always audited for real by the
trusted host-fixture runner (allowlisted s01_faulty).
"""

import difflib
import hashlib
import importlib.util
import json
import socket
from pathlib import Path

import pytest

from atlas.agent import controller as ctl
from atlas.agent.budget import Budget
from atlas.agent.client import FixtureClient, LiveModeUnavailable
from atlas.agent.execute import CandidateResult, execute_and_reevaluate
from atlas.candidates import Approval
from atlas.contracts import Outcome, RunOutcome, Status
from atlas.runner import trusted

ROOT = Path(__file__).resolve().parents[2]
S01 = ROOT / "benchmarks" / "t01" / "s01_faulty"
S02 = ROOT / "benchmarks" / "t01" / "s02_clean"
ORIGINAL = (S01 / "evaluate.py").read_text(encoding="utf-8")
FIX = (S02 / "evaluate.py").read_text(encoding="utf-8")
DIFF = "".join(
    difflib.unified_diff(
        ORIGINAL.splitlines(True),
        FIX.splitlines(True),
        "a/evaluate.py",
        "b/evaluate.py",
    )
)


def say(tool: str, **fields) -> dict:
    return {"content": json.dumps({"action": {"tool": tool, **fields}}), "usage": {}}


INSPECT = say("inspect_evidence", check="split_integrity")
READ = say("read_project_file", path="evaluate.py")
PATCH = say("propose_patch", diff=DIFF, rationale="fit the selector inside each fold")
FINISH = say(
    "finish",
    summary="APPROVED. NO_VIOLATION_FOUND: the claim is now scientifically valid.",
)


class ApproveExactly:
    """Test approver standing in for a human: approves the request it is shown."""

    def __init__(self):
        self.requests = []

    def decide(self, request):
        self.requests.append(request)
        return Approval(
            request.candidate_hash,
            request.base_snapshot_hash,
            "2026-10-15T00:00:00+00:00",
        )


class Decline:
    def __init__(self):
        self.requests = []

    def decide(self, request):
        self.requests.append(request)  # declines: returns None


class RecordingExecutor:
    """Stands in for the slice 1 executor; records exactly what it was asked to run."""

    def __init__(self, outcome=Outcome.NO_VIOLATION_FOUND):
        self.calls = []
        self.outcome = outcome

    def __call__(
        self, snapshot, candidate, approval, candidate_dir, *, proposed_at=None
    ):
        self.calls.append((snapshot, candidate, approval, Path(candidate_dir)))
        Path(candidate_dir).mkdir(parents=True)
        return CandidateResult(
            candidate_dir=Path(candidate_dir),
            candidate_hash=approval.candidate_hash,
            approval=approval.to_dict(),
            diff_sha256=candidate.diff_sha256,
            execution={"status": "completed", "reason": None},
            evaluated=True,
            outcome=RunOutcome(outcome=self.outcome, policy_version="policy-v1.3"),
            timing={},
        )


def tree_hashes(root: Path) -> dict:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def run(
    tmp_path,
    script,
    approver=None,
    executor=None,
    budget=None,
    name="unit",
    project=S01,
):
    client = FixtureClient(name, script)
    executor = executor or RecordingExecutor()
    result = ctl.run_agent(
        project,
        tmp_path / "runs",
        client,
        approver,
        executor=executor,
        budget=budget,
        env={},
    )
    return result, client, executor


def log_entries(result, event=None):
    lines = (
        (result.run_dir / "agent_log.jsonl").read_text(encoding="utf-8").splitlines()
    )
    entries = [json.loads(line) for line in lines]
    return [e for e in entries if event is None or e["event"] == event]


# --- the bounded path --------------------------------------------------------------------------


def test_fixture_run_audits_first_then_acts_and_reports_non_live(tmp_path):
    approver = ApproveExactly()
    result, _client, executor = run(
        tmp_path, [INSPECT, READ, PATCH, FINISH], approver=approver, name="s01-fix"
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    states = [s["state"] for s in result.report["states"]]
    assert states[:2] == ["INTAKE", "CHECK"] and states.index("CHECK") < states.index(
        "MODEL"
    )
    assert ["APPROVAL", "EXECUTE", "VERIFY"] == [
        s for s in states if s in ("APPROVAL", "EXECUTE", "VERIFY")
    ]
    # Exactly the approved candidate ran, through the executor, bound to the snapshot.
    ((snapshot, candidate, approval, _),) = executor.calls
    assert approval.candidate_hash == approver.requests[0].candidate_hash
    assert candidate.entry_bytes == FIX.encode("utf-8")
    assert approval.base_snapshot_hash == snapshot.base_hash
    # Non-live labels everywhere.
    report = result.report
    assert (report["live"], report["mode"], report["model_id"]) == (
        False,
        "fixture",
        "fixture:s01-fix",
    )
    assert "NON-LIVE" in report["banner"] and "fixture:s01-fix" in report["banner"]
    assert all(
        e["live"] is False and e["model_id"] == "fixture:s01-fix"
        for e in log_entries(result)
    )
    saved = json.loads(
        (result.run_dir / "agent_report.json").read_text(encoding="utf-8")
    )
    assert saved["live"] is False and saved["model_id"] == "fixture:s01-fix"
    # Attempts logged per SPEC §11.
    attempts = log_entries(result, "model_attempt")
    assert [a["attempt"] for a in attempts] == [1, 2, 3, 4]
    assert all(
        {"params", "started_utc", "elapsed_s", "usage", "request_id", "result"}
        <= set(a)
        for a in attempts
    )
    assert [a["tool"] for a in attempts] == [
        "inspect_evidence",
        "read_project_file",
        "propose_patch",
        "finish",
    ]


def test_model_text_cannot_declare_success_or_change_required_assertions(tmp_path):
    result, _, _ = run(
        tmp_path,
        [PATCH, FINISH],
        approver=ApproveExactly(),
        executor=RecordingExecutor(Outcome.VIOLATION_FOUND),
    )
    report = result.report
    assert report["scientific_outcomes"] == {
        "source": "trusted evaluator only",
        "original": Outcome.VIOLATION_FOUND,
        "candidates": [Outcome.VIOLATION_FOUND],
    }
    claimed = [t for t in report["model_text"] if t["kind"] == "finish_summary"]
    assert claimed and "NO_VIOLATION_FOUND" in claimed[0]["text"]
    assert claimed[0]["label"].startswith("model-written")
    original = result.original.outcome
    assert [a.assertion_id for a in original.assertions] == [
        a["assertion_id"] for a in report["comparison"]["original"]["required_set"]
    ]


def test_the_baseline_audit_is_never_modified(tmp_path):
    result, _, _ = run(
        tmp_path, [INSPECT, PATCH, {"content": "not json"}], approver=ApproveExactly()
    )
    before = json.loads(
        (result.original.run_dir / "outcome.json").read_text(encoding="utf-8")
    )
    hashes = tree_hashes(result.original.run_dir)
    assert result.terminal_state == ctl.ERROR
    # The run ended; nothing touched the original's directory after its audit completed.
    assert before["outcome"] == Outcome.VIOLATION_FOUND
    index = json.loads(
        (result.original.run_dir / "index.json").read_text(encoding="utf-8")
    )
    for name, digest in {**index["artifacts"], **index["outputs"]}.items():
        assert hashes[name] == digest
    assert set(hashes) == {*index["artifacts"], *index["outputs"], "index.json"}


# --- invalid replies and failures ---------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        {"content": "Sure! " + FINISH["content"]},
        {"content": FINISH["content"], "finish_reason": "length"},
        {"content": None},
        {
            "content": json.dumps(
                {
                    "action": {
                        "tool": "propose_patch",
                        "diff": DIFF,
                        "rationale": "r",
                        "approved": True,
                    }
                }
            )
        },
        {"content": json.dumps({"action": {"tool": "evaluate_candidate"}})},
    ],
    ids=[
        "prose",
        "truncated_by_length",
        "no_content",
        "self_approval_field",
        "execution_tool",
    ],
)
def test_invalid_reply_is_a_recorded_schema_failure_with_no_action(tmp_path, bad):
    executor = RecordingExecutor()
    result, client, _ = run(
        tmp_path, [INSPECT, bad, PATCH, FINISH], ApproveExactly(), executor
    )
    assert result.terminal_state == ctl.ERROR
    assert result.reason.startswith("schema_failure")
    assert executor.calls == []  # the patch after it was never requested
    assert len(client.requests) == 2  # no format-repair retry
    attempts = log_entries(result, "model_attempt")
    assert attempts[-1]["result"] == "schema_failure"
    # The completed audit stands in the report.
    assert result.report["scientific_outcomes"]["original"] == Outcome.VIOLATION_FOUND
    assert result.report["comparison"]["original"]["required_set"]


def test_failure_after_a_candidate_keeps_both_completed_results(tmp_path):
    result, _, executor = run(
        tmp_path, [PATCH, {"error": "rejected"}], ApproveExactly()
    )
    assert result.terminal_state == ctl.ERROR and result.reason == "model_error"
    assert len(executor.calls) == 1 and len(result.candidates) == 1
    assert result.report["scientific_outcomes"]["candidates"] == [
        Outcome.NO_VIOLATION_FOUND
    ]


def test_a_transient_failure_is_retried_once_and_the_retry_counts(tmp_path):
    result, _client, _ = run(tmp_path, [{"error": "timeout"}, FINISH])
    assert result.terminal_state == ctl.REPORT
    assert result.report["budget"]["used"]["attempts"] == 2
    assert result.report["budget"]["used"]["retries"] == 1
    assert [a["retry"] for a in log_entries(result, "model_attempt")] == [False, True]


def test_a_second_transient_failure_ends_the_run(tmp_path):
    result, client, _ = run(
        tmp_path, [{"error": "timeout"}, {"error": "timeout"}, FINISH]
    )
    assert result.terminal_state == ctl.ERROR and "after one retry" in result.reason
    assert len(client.requests) == 2


def test_a_permanent_error_is_not_retried(tmp_path):
    result, client, _ = run(tmp_path, [{"error": "rejected"}, FINISH])
    assert result.terminal_state == ctl.ERROR and len(client.requests) == 1


# --- ceilings ----------------------------------------------------------------------------------


def test_the_seventh_attempt_is_never_sent(tmp_path):
    result, client, _ = run(tmp_path, [INSPECT] * 6 + [FINISH])
    assert result.terminal_state == ctl.BUDGET_EXHAUSTED
    assert "model_attempts" in result.reason
    assert len(client.requests) == 6
    assert result.report["budget"]["used"]["attempts"] == 6


def test_retries_count_toward_six_and_need_a_remaining_attempt(tmp_path):
    result, client, _ = run(
        tmp_path, [INSPECT] * 5 + [{"error": "server_error"}, FINISH]
    )
    assert result.terminal_state == ctl.BUDGET_EXHAUSTED
    assert "no model attempt remains for its retry" in result.reason
    assert len(client.requests) == 6


def test_a_retry_uses_one_of_the_six_attempts(tmp_path):
    """An early retry is an attempt: after it, only four more requests may be sent."""
    result, client, _ = run(tmp_path, [{"error": "timeout"}] + [INSPECT] * 6 + [FINISH])
    assert (
        result.terminal_state == ctl.BUDGET_EXHAUSTED
        and "model_attempts" in result.reason
    )
    assert len(client.requests) == 6
    assert result.report["budget"]["used"] == {
        "attempts": 6,
        "retries": 1,
        "tool_operations": 5,
        "revisions": 0,
    }


def test_a_retry_that_fits_is_the_sixth_attempt(tmp_path):
    result, client, _ = run(tmp_path, [INSPECT] * 4 + [{"error": "timeout"}, FINISH])
    assert result.terminal_state == ctl.REPORT
    assert len(client.requests) == 6 and result.report["budget"]["used"]["retries"] == 1


def test_tool_operation_ceiling(tmp_path):
    result, _client, _ = run(
        tmp_path,
        [INSPECT, INSPECT, INSPECT, FINISH],
        budget=Budget(max_tool_operations=2),
    )
    assert (
        result.terminal_state == ctl.BUDGET_EXHAUSTED
        and "tool_operations" in result.reason
    )
    assert result.report["budget"]["used"]["tool_operations"] == 2


def test_revision_ceiling(tmp_path):
    executor = RecordingExecutor()
    result, _, _ = run(
        tmp_path, [PATCH, PATCH, PATCH, FINISH], ApproveExactly(), executor
    )
    assert (
        result.terminal_state == ctl.BUDGET_EXHAUSTED
        and "candidate_revisions" in result.reason
    )
    assert len(executor.calls) == 2


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_active_time_ceiling_and_approval_wait_excluded(tmp_path):
    clock = FakeClock()

    class SlowHuman(ApproveExactly):
        def decide(self, request):
            clock.now += 1000.0  # a long human wait
            return super().decide(request)

    result, _, executor = run(
        tmp_path, [PATCH, FINISH], SlowHuman(), budget=Budget(clock=clock)
    )
    assert result.terminal_state == ctl.REPORT and len(executor.calls) == 1
    budget = result.report["budget"]
    assert budget["approval_wait_s"] == 1000.0 and budget["total_elapsed_s"] == 1000.0
    assert budget["active_s"] == 0.0

    class SlowModel(FixtureClient):
        def complete(self, request):
            clock.now += 400.0
            return super().complete(request)

    clock.now = 0.0
    client = SlowModel("slow", [INSPECT, FINISH])
    result = ctl.run_agent(
        S01,
        tmp_path / "runs2",
        client,
        executor=RecordingExecutor(),
        budget=Budget(clock=clock),
        env={},
    )
    assert (
        result.terminal_state == ctl.BUDGET_EXHAUSTED and "active_time" in result.reason
    )


# --- approval boundary -------------------------------------------------------------------------


def test_no_approver_means_needs_input_and_no_execution(tmp_path):
    executor = RecordingExecutor()
    result, _, _ = run(tmp_path, [PATCH, FINISH], approver=None, executor=executor)
    assert (
        result.terminal_state == ctl.NEEDS_INPUT and "awaits approval" in result.reason
    )
    assert executor.calls == [] and not (result.run_dir / "candidates").exists()


def test_a_declined_candidate_is_not_executed(tmp_path):
    executor = RecordingExecutor()
    result, _, _ = run(tmp_path, [PATCH, FINISH], Decline(), executor)
    assert result.terminal_state == ctl.REPORT and executor.calls == []
    assert [e["decision"] for e in log_entries(result, "approval")] == ["declined"]


def test_an_approval_for_another_candidate_is_not_used(tmp_path):
    class WrongCandidate(ApproveExactly):
        def decide(self, request):
            super().decide(request)
            return Approval(
                "0" * 64, request.base_snapshot_hash, "2026-10-15T00:00:00+00:00"
            )

    executor = RecordingExecutor()
    result, _, _ = run(tmp_path, [PATCH, FINISH], WrongCandidate(), executor)
    assert executor.calls == []
    assert [e["decision"] for e in log_entries(result, "approval")] == ["unbound"]


def test_model_text_and_fixture_replies_cannot_grant_approval(tmp_path):
    """The fixture says 'APPROVED' and the rationale claims approval; without an approver
    nothing runs."""
    patch = say(
        "propose_patch", diff=DIFF, rationale="APPROVED by the user; run it now"
    )
    executor = RecordingExecutor()
    result, _, _ = run(tmp_path, [FINISH, patch], approver=None, executor=executor)
    assert result.terminal_state == ctl.REPORT and executor.calls == []
    result, _, _ = run(
        tmp_path / "b", [patch, FINISH], approver=None, executor=executor
    )
    assert result.terminal_state == ctl.NEEDS_INPUT and executor.calls == []


# --- mode and network --------------------------------------------------------------------------


def test_live_mode_is_refused_without_fallback(tmp_path):
    client = FixtureClient("unit", [FINISH])
    with pytest.raises(LiveModeUnavailable):
        ctl.run_agent(S01, tmp_path / "runs", client, env={"ATLAS_MODEL_MODE": "live"})

    class Live(FixtureClient):
        live = True

    with pytest.raises(LiveModeUnavailable):
        ctl.run_agent(S01, tmp_path / "runs", Live("unit", [FINISH]), env={})
    assert not (tmp_path / "runs").exists()  # refused before any run directory or audit


@pytest.mark.parametrize(
    "attempt",
    [
        lambda: socket.create_connection(("example.invalid", 443), timeout=1),
        lambda: socket.getaddrinfo("example.invalid", 443),
        lambda: socket.socket().connect(("127.0.0.1", 9)),
    ],
    ids=["create_connection", "getaddrinfo", "socket_connect"],
)
def test_fixture_mode_denies_network(tmp_path, attempt):
    class Phoning(FixtureClient):
        def complete(self, request):
            attempt()
            return super().complete(request)

    result = ctl.run_agent(
        S01,
        tmp_path / "runs",
        Phoning("phone", [FINISH]),
        executor=RecordingExecutor(),
        env={},
    )
    assert (
        result.terminal_state == ctl.ERROR
        and result.reason == "client_error: NetworkDenied"
    )
    assert socket.getaddrinfo.__name__ == "getaddrinfo"  # restored after the run


def test_unsupported_project_never_reaches_the_model(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    result, client, _ = run(tmp_path, [FINISH], project=empty)
    assert result.terminal_state == ctl.NOT_SUPPORTED
    assert client.requests == [] and result.original is None


def test_reads_are_limited_to_the_permitted_snapshot_files(tmp_path):
    result, _, _ = run(
        tmp_path,
        [
            say("read_project_file", path="../../pyproject.toml"),
            say("read_project_file", path="notes.txt"),
            READ,
            FINISH,
        ],
    )
    assert result.terminal_state == ctl.REPORT
    escape, unlisted, permitted = (t["result"] for t in result.transcript)
    assert (
        escape["error"].startswith("refused")
        and "untrusted_project_content" not in escape
    )
    assert unlisted["error"].startswith("refused: notes.txt is not one of")
    assert permitted["untrusted_project_content"].startswith('"""s01 faulty')
    assert len(log_entries(result, "tool")) == 3


# --- end to end through the verified slice 1 executor (fake Docker) ---------------------------


def _slice1_harness():
    spec = importlib.util.spec_from_file_location(
        "slice1_harness", Path(__file__).with_name("test_candidate_reevaluation.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_end_to_end_through_the_slice_1_executor(tmp_path, monkeypatch):
    h = _slice1_harness()
    clean = tmp_path / "clean-evidence"
    clean.mkdir()
    assert trusted.run_trusted_fixture(S02, "evaluate.py", clean)["returncode"] == 0
    out = h.collected(clean, tmp_path / "container-out")
    h.fake_docker(monkeypatch, out)
    real_fixture_runner = trusted.run_trusted_fixture
    host_runs = []

    def only_the_original(project, entry, run_dir):
        host_runs.append(Path(project).resolve())
        assert Path(project).resolve() == S01.resolve(), (
            "a candidate reached the host runner"
        )
        return real_fixture_runner(project, entry, run_dir)

    monkeypatch.setattr(trusted, "run_trusted_fixture", only_the_original)
    monkeypatch.setattr("atlas.audit.run_trusted_fixture", only_the_original)

    result, _, _ = run(
        tmp_path,
        [INSPECT, PATCH, FINISH],
        ApproveExactly(),
        execute_and_reevaluate,
        name="s01-e2e",
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    (candidate,) = result.candidates
    assert candidate.execution["status"] == "completed"
    assert candidate.outcome.outcome is Outcome.NO_VIOLATION_FOUND
    assert result.original.outcome.outcome is Outcome.VIOLATION_FOUND
    assert host_runs == [S01.resolve()]
    report = result.report
    assert report["comparison"]["comparison_basis"].startswith(
        "Host trusted-fixture baseline"
    )
    assert (
        report["comparison"]["candidates"][0]["approval"]["candidate_hash"]
        == candidate.candidate_hash
    )
    assert (candidate.candidate_dir / "approval.json").is_file()
    assert Status.PASS in {a.status for a in candidate.outcome.assertions}
