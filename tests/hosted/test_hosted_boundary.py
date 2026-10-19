"""T-12 fix pass 1: the hosted environment executes nothing, whichever way it is entered.

Review 1 (runs/t12r/review.md, P2) showed that with ATLAS_HOSTED=1 a local `run_agent` call
(`hosted=False`) still reached the executor. Every execution entry point now calls
`hosted.refuse_if_hosted` first. These tests are offline: tripwires replace the executor,
`subprocess.run`/`Popen` and the Docker probe, so no container or subprocess is started.

Also the judge access code's minimum length (lead hardening decision): a configured code
shorter than 32 characters disables the judge route.
"""

import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace

import hosted_helpers as H
import pytest

from atlas import cli
from atlas.agent import controller as ctl
from atlas.agent import execute as ex
from atlas.agent.budget import Budget
from atlas.agent.client import FixtureClient
from atlas.agent.network import deny_network
from atlas.candidates import Approval, Candidate, approve, build_snapshot, sha256_bytes
from atlas.hosted import HostedExecutionRefused, access, bundle, refuse_if_hosted
from atlas.hosted.budget_store import JUDGE, PUBLIC
from atlas.runner import docker as dr
from atlas.runner import trusted
from atlas.ui import worker

NOT_HOSTED = ["0", "", "true", " 1", None]  # anything but exactly "1"; None means unset


class Tripwire(AssertionError):
    """An execution step was reached."""


@pytest.fixture
def reached(monkeypatch):
    """Replace subprocess.run and subprocess.Popen with tripwires; returns what reached them."""
    calls = []

    def trip(name):
        def call(*args, **kwargs):
            calls.append(name)
            raise Tripwire(f"{name} reached")

        return call

    monkeypatch.setattr(subprocess, "run", trip("subprocess.run"))
    monkeypatch.setattr(subprocess, "Popen", trip("subprocess.Popen"))
    return calls


def set_hosted(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("ATLAS_HOSTED", raising=False)
    else:
        monkeypatch.setenv("ATLAS_HOSTED", value)


def snapshot_and_approval(tmp_path):
    snap = build_snapshot(H.S01, tmp_path / "snapshot")
    entry = (snap.root / snap.entry_point).read_bytes()
    code = Candidate(snap.entry_point, entry, sha256_bytes(b""))
    return snap, code, approve(snap, code)


class BoundApprover:
    """Approves exactly the requested code and snapshot (a correctly bound approval)."""

    def decide(self, req):
        return Approval(
            req.candidate_hash, req.base_snapshot_hash, datetime.now(UTC).isoformat()
        )


def local_agent_run(tmp_path, executor):
    return ctl.run_agent(
        H.S01,
        tmp_path / "runs",
        FixtureClient("review", []),
        BoundApprover(),
        executor=executor,
    )


# -- guard 1: run_agent with hosted=False (Codex's review scenario, promoted) -----------------


def test_hosted_environment_refuses_a_local_agent_run(monkeypatch, tmp_path, reached):
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    monkeypatch.setenv("ATLAS_MODEL_MODE", "fixture")
    executed = []

    def executor(*args, **kwargs):
        executed.append(True)
        raise Tripwire("execution boundary reached; no code executed")

    with pytest.raises(HostedExecutionRefused):
        local_agent_run(tmp_path, executor)
    assert executed == [], "ATLAS_HOSTED=1 reached the local executor"
    assert reached == []
    assert not (tmp_path / "runs").exists()  # no run directory


def test_hosted_in_the_given_env_also_refuses_a_local_agent_run(monkeypatch, tmp_path):
    monkeypatch.delenv("ATLAS_HOSTED", raising=False)
    with pytest.raises(HostedExecutionRefused):
        ctl.run_agent(
            H.S01, tmp_path / "runs", FixtureClient("review", []), BoundApprover(),
            env={"ATLAS_HOSTED": "1", "ATLAS_MODEL_MODE": "fixture"},
        )  # fmt: skip
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("value", NOT_HOSTED)
def test_other_values_leave_the_local_agent_run_unchanged(monkeypatch, tmp_path, value):
    set_hosted(monkeypatch, value)
    monkeypatch.setenv("ATLAS_MODEL_MODE", "fixture")
    executed = []

    def executor(*args, **kwargs):
        executed.append(True)
        raise Tripwire("execution boundary reached; no code executed")

    with pytest.raises(Tripwire):
        local_agent_run(tmp_path, executor)
    assert executed == [True]  # the local path reaches the executor as before


def test_hosted_mode_still_runs_with_the_hosted_environment(monkeypatch, tmp_path):
    """hosted=True with ATLAS_HOSTED=1 is the hosted happy path, unchanged."""
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    provider = H.live6_provider()
    approver = H.SpyApprover()
    with deny_network():
        result = ctl.run_agent(
            H.S01, tmp_path / "runs", H.client(provider), approver,
            budget=Budget(max_attempts=6), original=bundle.live_original(),
            live_authorized=True, spend=H.decided_limits(), hosted=True,
            reservations=H.FakeReservations(provider=provider),
        )  # fmt: skip
    assert result.terminal_state == ctl.REPORT, result.reason
    assert approver.requests == []
    assert result.candidates == []
    assert len(provider.posts()) == 4
    assert result.report["hosted"]


# -- guard 2: the Docker runner's entry -------------------------------------------------------


def test_hosted_environment_refuses_a_docker_execution(monkeypatch, tmp_path, reached):
    snap, code, approval = snapshot_and_approval(tmp_path)
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    resolved = []
    monkeypatch.setattr(
        dr, "resolve_docker_cli", lambda *a, **k: resolved.append(True) or None
    )
    with pytest.raises(HostedExecutionRefused):
        dr.run_candidate(snap, code, approval, tmp_path / "exec")
    assert resolved == [] and reached == []
    assert not (tmp_path / "exec").exists()


@pytest.mark.parametrize("value", NOT_HOSTED)
def test_other_values_leave_the_docker_entry_unchanged(monkeypatch, tmp_path, value):
    snap, code, approval = snapshot_and_approval(tmp_path)
    set_hosted(monkeypatch, value)

    def probe(*args, **kwargs):
        raise Tripwire("the Docker capability probe was reached")

    monkeypatch.setattr(dr, "probe", probe)
    with pytest.raises(Tripwire):
        dr.run_candidate(snap, code, approval, tmp_path / "exec")
    assert (tmp_path / "exec" / "execution.json").is_file()  # the record, as before


# -- guard 3: the trusted-fixture host subprocess ---------------------------------------------


def test_hosted_environment_refuses_a_trusted_fixture_run(
    monkeypatch, tmp_path, reached
):
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    with pytest.raises(HostedExecutionRefused):
        trusted.run_trusted_fixture(H.S01, "evaluate.py", tmp_path / "out")
    assert reached == []
    assert not (tmp_path / "out").exists()


# -- guard 4: execute_and_reevaluate and docker_original (defense in depth) -------------------


def test_hosted_environment_refuses_execute_and_reevaluate(
    monkeypatch, tmp_path, reached
):
    snap, code, approval = snapshot_and_approval(tmp_path)
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    runner = []
    monkeypatch.setattr(dr, "run_candidate", lambda *a, **k: runner.append(True))
    with pytest.raises(HostedExecutionRefused):
        ex.execute_and_reevaluate(snap, code, approval, tmp_path / "candidate")
    assert runner == [] and reached == []
    assert not (tmp_path / "candidate").exists()


def test_hosted_environment_refuses_docker_original(monkeypatch, reached):
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    called = []
    run = SimpleNamespace(_docker_original=lambda: called.append(True))
    with pytest.raises(HostedExecutionRefused):
        ctl.docker_original(run)
    assert called == [] and reached == []


# -- guard 5: the local UI's worker process ---------------------------------------------------


def test_hosted_environment_refuses_a_local_ui_run(monkeypatch, tmp_path, reached):
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    monkeypatch.setenv(worker.RUNS_ENV, str(tmp_path / "ui-runs"))
    registry = worker.Registry()
    with pytest.raises(HostedExecutionRefused):
        registry.start("s01_faulty", worker.AUDIT, None)
    assert reached == [] and registry.started == 0 and registry.current() is None
    assert not (tmp_path / "ui-runs").exists()


# -- guard 6: the command line ----------------------------------------------------------------


@pytest.mark.parametrize(
    "extra",
    [
        ["--mode", "audit"],
        ["--mode", "agent", "--fixture-script", "replies.json"],
        ["--mode", "agent", "--live", "--authorize-spend-usd", "0.51"],
        ["--mode", "agent+memory"],
    ],
)
def test_the_cli_refuses_every_mode_in_the_hosted_environment(
    monkeypatch, tmp_path, capsys, reached, extra
):
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    monkeypatch.setenv("ATLAS_MODEL_MODE", "live" if "--live" in extra else "fixture")
    runs = tmp_path / "runs"
    code = cli.main(["audit", str(H.S01), "--runs-dir", str(runs), *extra])
    out = capsys.readouterr()
    assert code == cli.REFUSED_EXIT == 2
    assert out.err == f"{cli.HOSTED_REFUSAL} Nothing was run.\n"
    assert out.out == ""
    assert reached == []
    assert not runs.exists()


# -- the guard itself -------------------------------------------------------------------------


def test_the_refusal_names_what_and_no_environment_value():
    env = {"ATLAS_HOSTED": "1", "NEBIUS_API_KEY": H.KEY, "DATABASE_URL": "postgres://x"}
    with pytest.raises(HostedExecutionRefused) as info:
        refuse_if_hosted("a test execution", env)
    message = str(info.value)
    assert isinstance(info.value, RuntimeError)
    assert message.startswith("a test execution refused")
    assert H.KEY not in message and "postgres" not in message


@pytest.mark.parametrize("value", NOT_HOSTED)
def test_the_guard_ignores_other_values(value):
    refuse_if_hosted(
        "a test execution", {} if value is None else {"ATLAS_HOSTED": value}
    )


# -- judge access code length -----------------------------------------------------------------

CODE_31 = "J" * 15 + "-" + "k" * 15
CODE_32 = "J" * 16 + "-" + "k" * 15


def route_and_events(typed, expected):
    events = []
    route = access.select_route(typed, expected, lambda r, e: events.append((r, e)))
    return route, events


def test_a_31_character_code_disables_the_judge_route():
    assert len(CODE_31) == 31
    route, events = route_and_events(CODE_31, CODE_31)  # even the exact code
    assert route == PUBLIC
    assert events == [(JUDGE, access.TOO_SHORT)] == [("judge", "judge_code_too_short")]
    assert CODE_31 not in str(events) and "31" not in str(events)
    assert access.code_matches(CODE_31, CODE_31) is False


def test_a_32_character_code_selects_the_judge_route():
    assert len(CODE_32) == 32
    route, events = route_and_events(CODE_32, CODE_32)
    assert route == JUDGE
    assert events == [(JUDGE, access.ACCEPTED)]


def test_a_wrong_code_still_uses_the_public_route():
    route, events = route_and_events("x" + CODE_32[1:], CODE_32)
    assert route == PUBLIC
    assert events == [(JUDGE, access.REJECTED)]
    assert CODE_32 not in str(events)


def test_no_typed_code_records_nothing_even_with_a_short_code():
    assert route_and_events("", CODE_31) == (PUBLIC, [])
    assert route_and_events(None, "short") == (PUBLIC, [])


def test_the_operations_doc_gives_the_generation_command():
    text = (H.ROOT / "docs" / "HOSTED_OPERATIONS.md").read_text(encoding="utf-8")
    assert (
        'uv run --locked python -c "import secrets; print(secrets.token_urlsafe(32))"'
        in text
    )


def test_a_generated_code_is_long_enough():
    import secrets

    assert access.usable_code(secrets.token_urlsafe(32))
