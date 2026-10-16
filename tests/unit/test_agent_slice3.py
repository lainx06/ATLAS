"""T-06 slice 3, offline: the Docker baseline, the terminal approval step, the production Nebius
client (mocked transport only) and the CLI.

No real Nebius request is made: every client test uses an `httpx2.MockTransport` handler, run
under the fixture network guard so that any real connection attempt would fail. Docker is faked
with the slice 1 harness (the runner's own host code runs for real); the evidence frames are
real adapter output from the trusted host runner on the allowlisted T-01 fixtures. The s01
fixture is a development fixture, not independent benchmark evidence.
"""

import difflib
import importlib.util
import io
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

import httpx2
import pytest

from atlas import cli
from atlas.agent import controller as ctl
from atlas.agent.approval import ApprovalUnavailable, TerminalApprover, inert
from atlas.agent.budget import Budget
from atlas.agent.client import (
    FixtureClient,
    LiveModeUnavailable,
    ModelError,
    ModelRequest,
    ModelTimeout,
    TransientModelError,
)
from atlas.agent.nebius import NebiusClient, NebiusConfig, load_api_key
from atlas.agent.network import deny_network
from atlas.audit import audit
from atlas.candidates import Approval
from atlas.contracts import Outcome
from atlas.runner import docker as dr
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
KEY = "sk-test-SECRET-do-not-leak-0123456789"
HASH = re.compile(r"Code hash:\s+([0-9a-f]{64})")


def act(tool: str, **fields) -> str:
    return json.dumps({"action": {"tool": tool, **fields}})


FINISH = act("finish", summary="done")
PATCH = act("propose_patch", diff=DIFF, rationale="fold-local selection")


def harness():
    spec = importlib.util.spec_from_file_location(
        "slice1_harness", Path(__file__).with_name("test_candidate_reevaluation.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H = harness()


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


class RecordingExecutor:
    def __init__(self):
        self.calls = []

    def __call__(
        self, snapshot, candidate, approval, candidate_dir, *, proposed_at=None
    ):
        from atlas.agent.execute import CandidateResult
        from atlas.contracts import RunOutcome

        self.calls.append(Path(candidate_dir))
        Path(candidate_dir).mkdir(parents=True)
        return CandidateResult(
            candidate_dir=Path(candidate_dir),
            candidate_hash=approval.candidate_hash,
            approval=approval.to_dict(),
            diff_sha256=candidate.diff_sha256,
            execution={"status": "completed"},
            evaluated=True,
            outcome=RunOutcome(
                outcome=Outcome.NO_VIOLATION_FOUND, policy_version="policy-v1.3"
            ),
            timing={},
        )


def host_fixture_original(run):
    """TEST-ONLY baseline for client-level tests (production runs the original in Docker)."""
    run.enter("CHECK", "test-only host-fixture baseline")
    result = audit(run.project, run.runs_root)
    return ctl.OriginalRun(
        run_dir=result.run_dir,
        outcome=result.outcome,
        runner=trusted.RUNNER_NAME,
        executed=True,
    )


# =============================================================================================
# 1. The terminal approval step
# =============================================================================================


class FakeStdin:
    def __init__(self, lines, tty=True, out=None):
        self.lines, self.tty, self.out = list(lines), tty, out

    def isatty(self):
        return self.tty

    def readline(self):
        if not self.lines:
            return ""
        line = self.lines.pop(0)
        if line == "<prefix>":  # what a person reads off the screen
            return HASH.findall(self.out.getvalue())[-1][:12] + "\n"
        return line


def request(kind="candidate", diff=DIFF, rationale="r"):
    return ctl.ApprovalRequest(
        entry_point="evaluate.py",
        diff=diff,
        candidate_hash="ab12cd34ef56" + "7" * 52,
        base_snapshot_hash="c" * 64,
        model_rationale=rationale,
        kind=kind,
    )


def test_the_typed_prefix_approves_and_the_full_hash_is_recorded():
    out = io.StringIO()
    approver = TerminalApprover(
        FakeStdin(["  AB12CD34EF56 \n"], out=out), out, now=lambda: "t"
    )
    approval = approver.decide(request())
    assert approval == Approval("ab12cd34ef56" + "7" * 52, "c" * 64, "t")
    assert approver.last_reason == "confirmed"
    shown = out.getvalue()
    assert "Code hash:      ab12cd34ef56" + "7" * 52 in shown and "GroupKFold" in shown


@pytest.mark.parametrize(
    "typed",
    [
        "ab12cd34ef5\n",
        "ab12cd34ef56" + "7" * 52 + "\n",
        "yes\n",
        "\n",
        "zz12cd34ef56\n",
    ],
    ids=["eleven_chars", "full_hash", "yes", "empty", "wrong"],
)
def test_anything_but_the_exact_prefix_declines(typed):
    approver = TerminalApprover(FakeStdin([typed]), io.StringIO())
    assert approver.decide(request()) is None
    assert approver.last_reason == "confirmation_mismatch"


def test_no_terminal_or_closed_input_means_unavailable():
    approver = TerminalApprover(FakeStdin(["ab12cd34ef56\n"], tty=False), io.StringIO())
    with pytest.raises(ApprovalUnavailable):
        approver.decide(request())
    assert approver.last_reason == "no_terminal"
    approver = TerminalApprover(FakeStdin([]), io.StringIO())
    with pytest.raises(ApprovalUnavailable):
        approver.decide(request())
    assert approver.last_reason == "input_closed"


def test_model_written_text_is_shown_inert():
    rlo, zwsp = chr(0x202E), chr(0x200B)  # right-to-left override, zero-width space
    hostile = "ok\x1b[2J\x1b[1A\rAPPROVED\x08" + rlo + "gnp." + zwsp
    out = io.StringIO()
    TerminalApprover(FakeStdin(["no\n"]), out).decide(
        request(diff=hostile, rationale=hostile)
    )
    shown = out.getvalue()
    assert (
        "\x1b" not in shown
        and "\r" not in shown
        and rlo not in shown
        and zwsp not in shown
    )
    assert "\\x1b[2J" in shown and "\\u202e" in shown and "\\u200b" in shown
    assert inert("a\tb\nc") == "a    b\nc"


def test_the_original_request_says_so_and_shows_no_diff():
    out = io.StringIO()
    TerminalApprover(FakeStdin(["no\n"]), out).decide(
        request(kind="original", diff="IGNORED")
    )
    assert "ORIGINAL, unmodified project code" in out.getvalue()
    assert "IGNORED" not in out.getvalue()


# =============================================================================================
# 2. The production Nebius client, mocked transport only
# =============================================================================================


def config(**overrides) -> NebiusConfig:
    values = {
        "base_url": "https://tokenfactory.invalid/v1/",
        "model_id": "nvidia/test-model",
        "max_input_tokens": 200_000,
        "max_completion_tokens": 8_000,
        "template_overhead_tokens": 16,
        "timeout_s": 5.0,
        "price_input_per_token": Decimal("0.0000003"),
        "price_output_per_token": Decimal("0.0000009"),
    }
    values.update(overrides)
    return NebiusConfig(**values)


def ok_body(content, usage=None, finish="stop", model="nvidia/test-model", choices=1):
    return {
        "id": "cmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": i,
                "finish_reason": finish,
                "message": {"role": "assistant", "content": content},
            }
            for i in range(choices)
        ],
        **({"usage": usage} if usage is not None else {}),
    }


USAGE = {"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200}


class Transport:
    """A scripted mock transport: each entry is a status/body pair or an exception class."""

    def __init__(self, script):
        self.script, self.requests = list(script), []

    def __call__(self, request):
        self.requests.append(request)
        entry = self.script.pop(0)
        if isinstance(entry, type) and issubclass(entry, Exception):
            raise entry("mock failure " + KEY, request=request)
        status, body = entry
        return httpx2.Response(
            status, json=body, headers={"x-request-id": f"req-{len(self.requests)}"}
        )


def client(script, **overrides):
    transport = Transport(script)
    c = NebiusClient(
        config(**overrides),
        KEY,
        http_client=httpx2.Client(transport=httpx2.MockTransport(transport)),
    )
    return c, transport


MESSAGES = [{"role": "user", "content": "hello"}]


def test_request_shape_and_reply():
    c, t = client([(200, ok_body(FINISH, USAGE))])
    with deny_network():
        reply = c.complete(ModelRequest(MESSAGES, {}))
    (sent,) = t.requests
    body = json.loads(sent.content)
    assert sorted(body) == ["max_completion_tokens", "messages", "model", "n"]
    assert (body["model"], body["max_completion_tokens"], body["n"]) == (
        "nvidia/test-model",
        8000,
        1,
    )
    assert (
        sent.headers["authorization"] == f"Bearer {KEY}"
    )  # only in the outgoing header
    assert (reply.content, reply.finish_reason, reply.live) == (FINISH, "stop", True)
    assert reply.usage["completion_tokens"] == 200 and reply.request_id == "req-1"
    assert reply.served_model == "nvidia/test-model"


@pytest.mark.parametrize(
    ("entry", "error", "code", "transient"),
    [
        (httpx2.ReadTimeout, ModelTimeout, "model_timeout", True),
        (httpx2.ConnectError, TransientModelError, "transport_error", True),
        ((429, {"error": {"message": KEY}}), TransientModelError, "rate_limited", True),
        (
            (503, {"error": {"message": KEY}}),
            TransientModelError,
            "server_error_503",
            True,
        ),
        ((400, {"error": {"message": KEY}}), ModelError, "http_400", False),
        ((401, {"error": {"message": KEY}}), ModelError, "http_401", False),
    ],
    ids=["timeout", "connection", "429", "503", "400", "401"],
)
def test_errors_are_classified_once_without_retries_or_secrets(
    entry, error, code, transient
):
    c, t = client([entry, (200, ok_body(FINISH, USAGE))])
    with deny_network(), pytest.raises(error) as raised:
        c.complete(ModelRequest(MESSAGES, {}))
    exc = raised.value
    assert (exc.code, exc.transient, exc.dispatched) == (code, transient, True)
    assert len(t.requests) == 1  # the SDK did not retry
    assert exc.__cause__ is None and exc.__context__ is None  # no chained SDK exception
    for text in (str(exc), repr(exc), repr(exc.args)):
        assert KEY not in text and "mock failure" not in text
    assert KEY not in repr(c)


def test_the_input_ceiling_refuses_before_sending():
    c, t = client(
        [(200, ok_body(FINISH, USAGE))],
        max_input_tokens=20,
        template_overhead_tokens=16,
    )
    with pytest.raises(ModelError) as raised:
        c.complete(
            ModelRequest([{"role": "user", "content": "hello"}], {})
        )  # 5 + 16 > 20
    assert (raised.value.code, raised.value.dispatched) == ("input_over_ceiling", False)
    assert t.requests == []
    c.check_request(
        ModelRequest([{"role": "user", "content": "hi"}], {})
    )  # 2 + 16 <= 20


def test_usage_above_a_ceiling_fails_closed_with_the_usage():
    over = {"prompt_tokens": 10, "completion_tokens": 9_000, "total_tokens": 9_010}
    c, _ = client([(200, ok_body(FINISH, over))])
    with pytest.raises(ModelError) as raised:
        c.complete(ModelRequest(MESSAGES, {}))
    assert (
        raised.value.code == "usage_over_ceiling"
        and raised.value.usage["completion_tokens"] == 9_000
    )


def test_unexpected_choices_are_rejected_and_missing_usage_is_unknown():
    c, _ = client([(200, ok_body(FINISH, USAGE, choices=2))])
    with pytest.raises(ModelError) as raised:
        c.complete(ModelRequest(MESSAGES, {}))
    assert raised.value.code == "bad_response"
    c, _ = client([(200, ok_body(FINISH, None))])
    reply = c.complete(ModelRequest(MESSAGES, {}))
    assert set(reply.usage.values()) == {None}  # every count unknown
    assert c.usage_cost(reply.usage) is None
    assert c.component_costs(reply.usage) == (None, None)


def test_cost_figures_follow_the_configured_prices():
    c, _ = client([])
    assert c.ceiling_cost() == 200_000 * Decimal("0.0000003") + 8_000 * Decimal(
        "0.0000009"
    )
    assert c.usage_cost(USAGE) == 1000 * Decimal("0.0000003") + 200 * Decimal(
        "0.0000009"
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"max_input_tokens": -1},
        {"max_completion_tokens": True},
        {"template_overhead_tokens": 1.5},
        {"timeout_s": 0},
        {"price_input_per_token": 0.3},
    ],
)
def test_configuration_is_explicit_and_validated(bad):
    with pytest.raises((ValueError, TypeError)):
        config(**bad)


def test_the_key_comes_from_the_env_file_without_echo(tmp_path):
    env = tmp_path / ".env"
    env.write_text(f"NEBIUS_API_KEY={KEY}\n", encoding="utf-8")
    assert load_api_key(env) == KEY
    env.write_text("NEBIUS_API_KEY=\n", encoding="utf-8")
    with pytest.raises(ValueError) as raised:
        load_api_key(env)
    assert KEY not in str(raised.value)
    with pytest.raises(ValueError):
        NebiusClient(config(), "  ")


# =============================================================================================
# 3. The controller with the (mocked) production client
# =============================================================================================


def live_run(tmp_path, script, approver=None, executor=None, **overrides):
    c, t = client(script, **overrides)
    with deny_network():  # any real connection attempt would fail
        result = ctl.run_agent(
            S01,
            tmp_path / "runs",
            c,
            approver,
            executor=executor or RecordingExecutor(),
            original=host_fixture_original,
            live_authorized=True,
            env={},
        )
    return result, t


def test_a_live_client_is_refused_without_explicit_authorization(tmp_path):
    c, t = client([(200, ok_body(FINISH, USAGE))])
    with pytest.raises(LiveModeUnavailable):
        ctl.run_agent(S01, tmp_path / "runs", c, env={})
    assert t.requests == [] and not (tmp_path / "runs").exists()


def test_a_mocked_live_run_reports_live_and_settles_cost(tmp_path):
    approver = ApproveExactly()
    result, t = live_run(
        tmp_path,
        [(200, ok_body(PATCH, USAGE)), (200, ok_body(FINISH, USAGE))],
        approver,
    )
    assert result.terminal_state == ctl.REPORT and len(t.requests) == 2
    report = result.report
    assert (report["live"], report["mode"], report["model_id"]) == (
        True,
        "live",
        "nvidia/test-model",
    )
    cost = report["cost"]
    per = Decimal("0.0003") + Decimal("0.00018")
    assert Decimal(cost["known_usd"]) == Decimal(cost["estimated_total_usd"]) == 2 * per
    assert Decimal(cost["unresolved_usd"]) == 0 and cost["unknown_usage_attempts"] == 0
    assert "not a spending authorization" in cost["note"]
    attempts = [
        json.loads(x)
        for x in (result.run_dir / "agent_log.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert all(a["live"] is True for a in attempts)
    assert {a.get("request_id") for a in attempts if a["event"] == "model_attempt"} == {
        "req-1",
        "req-2",
    }
    text = (result.run_dir / "agent_log.jsonl").read_text(
        encoding="utf-8"
    ) + json.dumps(report)
    assert KEY not in text


def test_timeouts_keep_the_ceiling_reserved_and_end_after_one_retry(tmp_path):
    result, t = live_run(
        tmp_path,
        [httpx2.ReadTimeout, httpx2.ReadTimeout, (200, ok_body(FINISH, USAGE))],
    )
    assert (
        result.terminal_state == ctl.ERROR
        and result.reason == "model_timeout (after one retry)"
    )
    assert len(t.requests) == 2
    cost = result.report["cost"]
    ceiling = Decimal(cost["ceiling_per_request_usd"])
    assert cost["unknown_usage_attempts"] == 2
    assert Decimal(cost["unresolved_usd"]) == Decimal(cost["estimated_total_usd"])
    assert Decimal(cost["estimated_total_usd"]) == 2 * ceiling
    assert "not a guaranteed maximum" in cost["unresolved_note"]
    assert KEY not in json.dumps(result.report)


def test_retry_exhaustion_at_the_sixth_attempt(tmp_path):
    inspect = act("inspect_evidence", check="split_integrity")
    script = [(200, ok_body(inspect, USAGE))] * 5 + [httpx2.ReadTimeout]
    result, t = live_run(tmp_path, script)
    assert result.terminal_state == ctl.BUDGET_EXHAUSTED and len(t.requests) == 6
    assert result.report["cost"]["unknown_usage_attempts"] == 1


@pytest.mark.parametrize(
    "body",
    [
        ok_body("Sure! " + FINISH, USAGE),
        ok_body(FINISH, USAGE, finish="length"),
        ok_body(None, USAGE),
    ],
    ids=["prose", "length", "no_content"],
)
def test_invalid_live_replies_authorize_nothing(tmp_path, body):
    executor = RecordingExecutor()
    result, t = live_run(
        tmp_path,
        [(200, body), (200, ok_body(PATCH, USAGE))],
        ApproveExactly(),
        executor,
    )
    assert result.terminal_state == ctl.ERROR and result.reason.startswith(
        "schema_failure"
    )
    assert len(t.requests) == 1 and executor.calls == []


def test_an_oversized_prompt_is_never_sent_or_counted(tmp_path):
    result, t = live_run(
        tmp_path, [(200, ok_body(FINISH, USAGE))], max_input_tokens=100
    )
    assert result.terminal_state == ctl.ERROR and result.reason == "input_over_ceiling"
    assert t.requests == [] and result.report["budget"]["used"]["attempts"] == 0
    assert result.report["cost"]["entries"] == []


def test_usage_above_the_ceiling_ends_the_run_and_is_charged(tmp_path):
    over = {"prompt_tokens": 10, "completion_tokens": 9_000, "total_tokens": 9_010}
    result, _ = live_run(tmp_path, [(200, ok_body(FINISH, over))])
    assert result.terminal_state == ctl.ERROR and result.reason == "usage_over_ceiling"
    (entry,) = result.report["cost"]["entries"]
    assert entry["status"] == "settled"
    assert Decimal(entry["unresolved_usd"]) == 0 and Decimal(
        entry["known_usd"]
    ) == 10 * Decimal("0.0000003") + 9_000 * Decimal("0.0000009")


def test_a_reporting_failure_in_a_live_run_is_finalized(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("comparison " + KEY)

    monkeypatch.setattr(ctl, "comparison_report", broken)
    with pytest.raises(RuntimeError):
        live_run(tmp_path, [(200, ok_body(FINISH, USAGE))])
    (path,) = (tmp_path / "runs").glob("agent-*/agent_report.json")
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["terminal_state"] == "ERROR" and report["live"] is True
    assert KEY not in json.dumps(report)


# =============================================================================================
# 4. The Docker baseline (fake Docker; the runner's host code and the evaluator run for real)
# =============================================================================================


@pytest.fixture(scope="module")
def evidence(tmp_path_factory):
    base = tmp_path_factory.mktemp("evidence")
    out = {}
    for name, project in (("faulty", S01), ("clean", S02)):
        run = base / name
        run.mkdir()
        assert (
            trusted.run_trusted_fixture(project, "evaluate.py", run)["returncode"] == 0
        )
        out[name] = H.collected(run, base / f"{name}-out")
    return out


def fake_docker(monkeypatch, frames, available=True):
    """Docker 'available'; each container emits the next evidence directory in `frames`."""
    queue = list(frames)
    if available:
        cap = dr.Capability(dr.CAPABILITY_AVAILABLE, None, docker_cli="docker.exe",
                            image_id=H.FAKE_IMAGE, recipe_sha256=dr.recipe_sha256())  # fmt: skip
    else:
        cap = dr.Capability(
            dr.CAPABILITY_UNAVAILABLE, "unit: Docker daemon unreachable"
        )
    monkeypatch.setattr(
        dr, "probe", lambda image=dr.IMAGE_TAG, env=None, exclude=(): cap
    )
    monkeypatch.setattr(dr, "_spawn", lambda cli, args, env: H.FakeProcess())

    def bounded(proc, limits):
        stdout = H.frame(queue.pop(0))
        return {"stdout": bytearray(stdout), "stderr_tail": bytearray(),
                "counts": {"stdout": len(stdout), "stderr": 0}, "problems": [],
                "host_timed_out": False, "threads": []}  # fmt: skip

    monkeypatch.setattr(dr, "communicate_bounded", bounded)
    monkeypatch.setattr(dr, "_docker", H.gone)
    monkeypatch.setattr(dr.time, "sleep", lambda s: None)


@pytest.fixture
def no_host_runner(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("project code reached the host runner")

    monkeypatch.setattr(trusted, "run_trusted_fixture", refuse)
    monkeypatch.setattr("atlas.audit.run_trusted_fixture", refuse)


def test_original_and_candidate_both_run_in_docker_after_authorization(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    fake_docker(monkeypatch, [evidence["faulty"], evidence["clean"]])
    approver = ApproveExactly()
    result = ctl.run_agent(
        S01,
        tmp_path / "runs",
        FixtureClient("s3", [{"content": PATCH}, {"content": FINISH}]),
        approver,
        env={},
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    kinds = [r.kind for r in approver.requests]
    assert kinds == ["original", "candidate"]
    original_request = approver.requests[0]
    assert (
        original_request.diff == ""
        and original_request.base_snapshot_hash
        == approver.requests[1].base_snapshot_hash
    )
    assert result.original.runner == "docker_isolated"
    assert result.original.execution["status"] == "completed"
    assert result.original.outcome.outcome is Outcome.VIOLATION_FOUND
    (candidate,) = result.candidates
    assert candidate.outcome.outcome is Outcome.NO_VIOLATION_FOUND
    approval = json.loads(
        (result.original.run_dir / "approval.json").read_text(encoding="utf-8")
    )
    assert approval["candidate_hash"] == original_request.candidate_hash
    report = result.report
    assert report["comparison"]["comparison_basis"].startswith(
        "Original and candidates all executed"
    )
    limitations = report["limitations"]
    assert "The original executed in the isolated Docker runner" in " ".join(
        limitations
    )
    assert any("Every candidate (1) executed" in x for x in limitations)
    assert report["comparison"]["original"]["executed"] is True
    states = [s["state"] for s in report["states"]]
    assert states.index("APPROVAL") < states.index("CHECK") < states.index("MODEL")


@pytest.mark.parametrize("approver", [None, "decline", "unbound"])
def test_without_authorization_the_original_never_runs(
    tmp_path, monkeypatch, approver, no_host_runner
):
    class Decline:
        def decide(self, request):
            return None

    class Unbound:
        def decide(self, request):
            return Approval("0" * 64, request.base_snapshot_hash, "t")

    executor = RecordingExecutor()
    client = FixtureClient("s3", [{"content": FINISH}])
    chosen = {None: None, "decline": Decline(), "unbound": Unbound()}[approver]
    result = ctl.run_agent(
        S01, tmp_path / "runs", client, chosen, executor=executor, env={}
    )
    assert result.terminal_state == ctl.NEEDS_INPUT
    assert executor.calls == [] and client.requests == []
    assert result.original is None


def test_without_docker_the_original_is_not_executed_and_nothing_falls_back(
    tmp_path, monkeypatch, no_host_runner
):
    fake_docker(monkeypatch, [], available=False)
    client = FixtureClient("s3", [{"content": FINISH}])
    result = ctl.run_agent(S01, tmp_path / "runs", client, ApproveExactly(), env={})
    assert result.terminal_state == ctl.ERROR
    assert result.reason.startswith(
        "original_not_executed: not_executed: isolation unavailable"
    )
    assert client.requests == []  # no model request
    assert result.original.execution["status"] == "not_executed"
    assert result.report["scientific_outcomes"]["original"] == Outcome.INCONCLUSIVE


def test_the_post_authorization_time_check_refuses_the_original(
    tmp_path, monkeypatch, no_host_runner
):
    clock = H_clock = type(
        "Clock", (), {"now": 0.0, "__call__": lambda self: self.now}
    )()
    real_snapshot = ctl.build_snapshot

    def slow_snapshot(*args, **kwargs):
        value = real_snapshot(*args, **kwargs)
        clock.now += 301.0  # active work before the approval
        return value

    class SlowHuman(ApproveExactly):
        def decide(self, request):
            clock.now += 10_000.0  # excluded
            return super().decide(request)

    monkeypatch.setattr(ctl, "build_snapshot", slow_snapshot)
    executor = RecordingExecutor()
    result = ctl.run_agent(
        S01,
        tmp_path / "runs",
        FixtureClient("s3", [{"content": FINISH}]),
        SlowHuman(),
        executor=executor,
        budget=Budget(clock=H_clock),
        env={},
    )
    assert result.terminal_state == ctl.BUDGET_EXHAUSTED and executor.calls == []
    assert result.report["budget"]["approval_wait_s"] == 10_000.0


# =============================================================================================
# 5. The CLI
# =============================================================================================


def write_script(tmp_path, replies) -> Path:
    path = tmp_path / "script.json"
    path.write_text(
        json.dumps({"name": "cli", "replies": [{"content": r} for r in replies]}),
        encoding="utf-8",
    )
    return path


def run_cli(tmp_path, monkeypatch, replies, answers, tty=True):
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stdin", FakeStdin(answers, tty=tty, out=out))
    code = cli.main(
        ["audit", str(S01), "--mode", "agent", "--fixture-script", str(write_script(tmp_path, replies)),
         "--runs-dir", str(tmp_path / "runs")]
    )  # fmt: skip
    return code, out.getvalue()


def test_cli_agent_run_with_typed_approvals(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    fake_docker(monkeypatch, [evidence["faulty"], evidence["clean"]])
    code, out = run_cli(
        tmp_path, monkeypatch, [PATCH, FINISH], ["<prefix>", "<prefix>"]
    )
    assert code == 0, out
    assert "NON-LIVE agent run" in out and "terminal state: REPORT" in out
    assert "original: VIOLATION_FOUND (docker_isolated)" in out
    assert "execution completed, outcome NO_VIOLATION_FOUND" in out
    assert out.count("APPROVAL REQUIRED") == 2


def test_cli_wrong_confirmation_does_not_execute_the_candidate(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    fake_docker(monkeypatch, [evidence["faulty"]])
    code, out = run_cli(
        tmp_path, monkeypatch, [PATCH, FINISH], ["<prefix>", "000000000000\n"]
    )
    assert code == 0 and "Confirmation did not match: NOT approved." in out
    assert (
        "candidate " not in out.split("terminal state")[1]
    )  # no executed candidate listed


def test_cli_without_a_terminal_needs_input(tmp_path, monkeypatch, no_host_runner):
    code, out = run_cli(tmp_path, monkeypatch, [FINISH], [], tty=False)
    assert code == 3 and "terminal state: NEEDS_INPUT" in out
    assert not list((tmp_path / "runs").glob("agent-*/original"))


def test_cli_without_docker_reports_the_original_not_executed(
    tmp_path, monkeypatch, no_host_runner
):
    fake_docker(monkeypatch, [], available=False)
    code, out = run_cli(tmp_path, monkeypatch, [FINISH], ["<prefix>"])
    assert code == 1 and "original_not_executed" in out
    (log,) = (tmp_path / "runs").glob("agent-*/agent_log.jsonl")
    assert '"model_attempt"' not in log.read_text(encoding="utf-8")


def test_cli_refuses_live_mode_and_missing_scripts(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ATLAS_MODEL_MODE", "live")
    assert (
        cli.main(["audit", str(S01), "--mode", "agent", "--fixture-script", "x.json"])
        == 2
    )
    assert "not authorized" in capsys.readouterr().err
    monkeypatch.setenv("ATLAS_MODEL_MODE", "fixture")
    assert cli.main(["audit", str(S01), "--mode", "agent"]) == 2
    assert "--fixture-script" in capsys.readouterr().err
    assert cli.main(["audit", str(S01), "--mode", "agent+memory"]) == 2
    assert not Path("runs").joinpath("x").exists()
