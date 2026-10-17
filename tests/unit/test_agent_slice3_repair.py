"""T-06 slice 3 repair pass 1 (Codex review `runs/s3v/review.md`), offline only.

Regressions for the reviewed defects, each with a valid control:

1. reported usage is validated before accounting, logging or any action (P2-1), including
   the other provider-reported values on the same path (request ID, served model, finish
   reason);
2. partially known usage keeps every known component's cost and holds the unknown one at its
   ceiling (P2-2);
3. the client configuration is validated before any SDK object exists (P2-3);
4. report prose follows observed execution, not the selected runner (P3-1).

No real request is made: the client uses an `httpx2.MockTransport` handler under the fixture
network guard, and Docker is faked with the slice 1 harness. The helpers come from the slice 3
test module. The host baseline here is test-only, written so that this file also runs against
the pre-repair commit for the red demonstration.
"""

import dataclasses
import importlib.util
import io
import json
import sys
from decimal import Decimal
from pathlib import Path

import httpx2
import pytest

from atlas import cli
from atlas.agent import controller as ctl
from atlas.agent.budget import CostLedger
from atlas.agent.client import FixtureClient, ModelError, ModelRequest
from atlas.agent.nebius import NebiusClient
from atlas.agent.network import deny_network
from atlas.audit import audit
from atlas.contracts import Outcome
from atlas.runner import trusted


def _slice3():
    spec = importlib.util.spec_from_file_location(
        "slice3_helpers", Path(__file__).with_name("test_agent_slice3.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _slice3()
KEY, FINISH, PATCH, S01 = S.KEY, S.FINISH, S.PATCH, S.S01
P_IN, P_OUT = Decimal("0.0000003"), Decimal("0.0000009")
CEIL_IN, CEIL_OUT = 200_000 * P_IN, 8_000 * P_OUT  # S.config(): 200,000 / 8,000 tokens
CEILING = CEIL_IN + CEIL_OUT


def host_baseline(run):
    """TEST-ONLY host-fixture baseline (production runs the original in Docker)."""
    run.enter("CHECK", "test-only host-fixture baseline")
    result = audit(run.project, run.runs_root)
    names = {f.name for f in dataclasses.fields(ctl.OriginalRun)}
    extra = {"executed": True} if "executed" in names else {}
    return ctl.OriginalRun(
        run_dir=result.run_dir,
        outcome=result.outcome,
        runner=trusted.RUNNER_NAME,
        **extra,
    )


class RawTransport:
    """Scripted responses with a raw JSON body (so NaN and Infinity can be sent) and headers."""

    def __init__(self, script):
        self.script, self.requests = list(script), []

    def __call__(self, request):
        self.requests.append(request)
        body, headers = self.script.pop(0)
        return httpx2.Response(
            200,
            content=body.encode("utf-8"),
            headers={"content-type": "application/json", **headers},
        )


def raw_body(content, usage_json="null", finish="stop", model="nvidia/test-model"):
    """A chat completion body; `usage_json` is inserted verbatim."""
    return (
        '{"id": "cmpl-1", "object": "chat.completion", "created": 0, '
        f'"model": {json.dumps(model)}, "choices": [{{"index": 0, '
        f'"finish_reason": {json.dumps(finish)}, "message": {{"role": "assistant", '
        f'"content": {json.dumps(content)}}}}}], "usage": {usage_json}}}'
    )


def raw_client(script, **overrides):
    transport = RawTransport(script)
    c = NebiusClient(
        S.config(**overrides),
        KEY,
        http_client=httpx2.Client(transport=httpx2.MockTransport(transport)),
    )
    return c, transport


def live(tmp_path, client, executor=None):
    executor = executor or S.RecordingExecutor()
    with deny_network():
        result = ctl.run_agent(
            S01,
            tmp_path / "runs",
            client,
            S.ApproveExactly(),
            executor=executor,
            original=host_baseline,
            live_authorized=True,
            spend=S.GENEROUS,
            env={},
        )
    log = (result.run_dir / "agent_log.jsonl").read_text(encoding="utf-8")
    return result, executor, log


def attempts(log):
    return [
        e
        for e in (json.loads(line) for line in log.splitlines())
        if e.get("event") == "model_attempt"
    ]


def amounts(cost):
    """Every money figure in the cost summary, as Decimal."""
    figures = [cost["known_usd"], cost["unresolved_usd"], cost["estimated_total_usd"]]
    for e in cost["entries"]:
        figures += [e["known_usd"], e["unresolved_usd"]]
    return [Decimal(x) for x in figures]


# =============================================================================================
# 1. Usage is validated before accounting, logging or action (P2-1)
# =============================================================================================

INVALID = {
    "negative": ('{"prompt_tokens": -1000, "completion_tokens": 0}', "prompt_tokens"),
    "fraction": (
        '{"prompt_tokens": 1000, "completion_tokens": 9000.5}',
        "completion_tokens",
    ),
    "integral_float": (
        '{"prompt_tokens": 1000.0, "completion_tokens": 10}',
        "prompt_tokens",
    ),
    "boolean": ('{"prompt_tokens": true, "completion_tokens": 10}', "prompt_tokens"),
    "text": ('{"prompt_tokens": 10, "completion_tokens": "lots"}', "completion_tokens"),
    "key_echo": (
        f'{{"prompt_tokens": {json.dumps(KEY)}, "completion_tokens": 1}}',
        "prompt_tokens",
    ),
    "nan": ('{"prompt_tokens": NaN, "completion_tokens": 1}', "prompt_tokens"),
    "infinity": ('{"prompt_tokens": 1, "completion_tokens": Infinity}', "completion_tokens"),
    "object": ('{"prompt_tokens": {"n": 1}, "completion_tokens": 1}', "prompt_tokens"),
}  # fmt: skip


@pytest.mark.parametrize("case", sorted(INVALID))
def test_invalid_usage_fails_closed_at_the_client(case):
    usage_json, field = INVALID[case]
    c, t = raw_client([(raw_body(FINISH, usage_json), {})])
    with deny_network(), pytest.raises(ModelError) as raised:
        c.complete(ModelRequest(S.MESSAGES, {}))
    exc = raised.value
    assert exc.code == "invalid_usage" and exc.dispatched is True
    assert field in exc.invalid_fields and exc.usage[field] is None
    assert len(t.requests) == 1
    for text in (str(exc), repr(exc.args), json.dumps(exc.usage)):
        assert KEY not in text and "lots" not in text


@pytest.mark.parametrize(
    ("usage_json", "expected"),
    [
        (
            '{"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200}',
            {"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200},
        ),
        (
            '{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}',
            {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        ),
        (
            '{"prompt_tokens": 1000, "completion_tokens": null}',
            {"prompt_tokens": 1000, "completion_tokens": None, "total_tokens": None},
        ),
        (
            "null",
            {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None},
        ),
    ],
    ids=["complete", "zero", "one_missing", "absent"],
)
def test_valid_and_missing_usage_controls(usage_json, expected):
    c, _ = raw_client([(raw_body(FINISH, usage_json), {"x-request-id": "req-1"})])
    with deny_network():
        reply = c.complete(ModelRequest(S.MESSAGES, {}))
    assert reply.usage == expected and reply.request_id == "req-1"


@pytest.mark.parametrize("case", ["negative", "fraction", "key_echo", "nan"])
def test_invalid_usage_authorizes_no_action_and_reaches_no_log(tmp_path, case):
    usage_json, field = INVALID[case]
    c, t = raw_client(
        [(raw_body(PATCH, usage_json), {}), (raw_body(FINISH, "null"), {})]
    )
    result, executor, log = live(tmp_path, c)
    assert (result.terminal_state, result.reason) == (ctl.ERROR, "invalid_usage")
    assert len(t.requests) == 1 and executor.calls == []  # the patch was not consumed
    assert result.original.outcome.outcome is Outcome.VIOLATION_FOUND  # baseline kept
    (attempt,) = attempts(log)
    assert attempt["invalid_usage_fields"] == [field]
    assert attempt["usage"][field] is None
    report = json.dumps(result.report, default=str)
    assert KEY not in log + report and "9000.5" not in log + report
    cost = result.report["cost"]
    assert all(x >= 0 for x in amounts(cost))
    assert Decimal(cost["estimated_total_usd"]) >= CEILING  # conservatively held


def test_a_valid_reply_is_still_consumed(tmp_path):
    usage = '{"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200}'
    c, _ = raw_client([(raw_body(PATCH, usage), {}), (raw_body(FINISH, usage), {})])
    result, executor, _ = live(tmp_path, c)
    assert result.terminal_state == ctl.REPORT and len(executor.calls) == 1


def test_any_clients_usage_is_validated_by_the_controller(tmp_path):
    """The controller does not rely on the client: a fixture reply's usage is checked too."""
    bad = FixtureClient(
        "bad-usage",
        [{"content": PATCH, "usage": {"prompt_tokens": -5, "completion_tokens": KEY}}],
    )
    executor = S.RecordingExecutor()
    result = ctl.run_agent(
        S01, tmp_path / "bad", bad, S.ApproveExactly(), executor=executor,
        original=host_baseline, env={},
    )  # fmt: skip
    log = (result.run_dir / "agent_log.jsonl").read_text(encoding="utf-8")
    assert (result.terminal_state, result.reason) == (ctl.ERROR, "invalid_usage")
    assert executor.calls == [] and KEY not in log
    (attempt,) = attempts(log)  # the raw -5 is not recorded; the count is unknown
    assert (
        attempt["usage"]["prompt_tokens"] is None and '"prompt_tokens": -5' not in log
    )
    good = FixtureClient(
        "good-usage",
        [
            {"content": PATCH, "usage": {"prompt_tokens": 5, "completion_tokens": 7}},
            {"content": FINISH},
        ],
    )
    control = ctl.run_agent(
        S01, tmp_path / "good", good, S.ApproveExactly(), executor=S.RecordingExecutor(),
        original=host_baseline, env={},
    )  # fmt: skip
    assert control.terminal_state == ctl.REPORT


def test_the_ledger_itself_ignores_invalid_counts():
    c, _ = raw_client([])
    ledger = CostLedger(c)
    ledger.reserve(1)
    # A caller passing raw counts directly: the negative one is unknown, never a refund.
    ledger.settle(1, {"prompt_tokens": -(10**9), "completion_tokens": 0}, True)
    ledger.reserve(2)
    ledger.settle(2, {"prompt_tokens": True, "completion_tokens": 9.5}, True)
    ledger.reserve(3)
    ledger.settle(3, {"prompt_tokens": 1000, "completion_tokens": 200}, True)  # control
    cost = ledger.summary()
    assert all(x >= 0 for x in amounts(cost))
    first, second, third = cost["entries"]
    assert first["status"] == "partial_usage"  # the valid zero output count is known
    assert Decimal(first["known_usd"]) + Decimal(first["unresolved_usd"]) == CEILING
    assert second["status"] == "unknown_usage"
    assert Decimal(second["unresolved_usd"]) == CEILING
    assert third["status"] == "settled"
    assert Decimal(third["known_usd"]) == 1000 * P_IN + 200 * P_OUT


# -- the adjacent provider-reported values on the same path -----------------------------------


def test_provider_identifiers_are_withheld_unless_plain_and_key_free(tmp_path):
    usage = '{"prompt_tokens": 10, "completion_tokens": 5}'
    c, _ = raw_client(
        [(raw_body(FINISH, usage, model="nvidia/" + KEY), {"x-request-id": KEY})]
    )
    result, _, log = live(tmp_path, c)
    assert result.terminal_state == ctl.REPORT
    (attempt,) = attempts(log)
    assert attempt["served_model"] is None and attempt["request_id"] is None
    assert attempt["withheld_fields"] == ["request_id", "served_model"]
    assert KEY not in log + json.dumps(result.report, default=str)
    c, _ = raw_client(
        [(raw_body(FINISH, usage), {"x-request-id": "req id; with spaces"})]
    )
    with deny_network():
        reply = c.complete(ModelRequest(S.MESSAGES, {}))
    assert reply.request_id is None and reply.withheld == ("request_id",)
    assert (
        reply.served_model == "nvidia/test-model"
    )  # control: a plain identifier is kept


def test_an_unknown_finish_reason_is_recorded_as_unrecognized(tmp_path):
    odd = "stop" + chr(0x202E) + KEY
    c, _ = raw_client([(raw_body(FINISH, "null", finish=odd), {})])
    result, _, log = live(tmp_path, c)
    assert result.terminal_state == ctl.ERROR and result.reason.startswith(
        "schema_failure"
    )
    (attempt,) = attempts(log)
    assert attempt["finish_reason"] == "unrecognized" and KEY not in log


# =============================================================================================
# 2. Partially known usage (P2-2)
# =============================================================================================


def test_a_known_component_above_the_whole_reservation_is_kept(tmp_path):
    usage = '{"prompt_tokens": 1000000, "completion_tokens": null}'
    c, t = raw_client([(raw_body(PATCH, usage), {})])
    result, executor, _ = live(tmp_path, c)
    assert (result.terminal_state, result.reason) == (ctl.ERROR, "usage_over_ceiling")
    assert len(t.requests) == 1 and executor.calls == []  # over the ceiling: work stops
    (entry,) = result.report["cost"]["entries"]
    assert entry["status"] == "partial_usage"
    assert Decimal(entry["known_usd"]) == 1_000_000 * P_IN == Decimal("0.3")
    assert Decimal(entry["unresolved_usd"]) == CEIL_OUT  # the missing output count
    assert (
        Decimal(result.report["cost"]["estimated_total_usd"])
        == Decimal("0.3") + CEIL_OUT
    )


def test_known_output_above_its_ceiling_with_unknown_input(tmp_path):
    usage = '{"prompt_tokens": null, "completion_tokens": 9000}'
    c, _ = raw_client([(raw_body(FINISH, usage), {})])
    result, _, _ = live(tmp_path, c)
    assert result.reason == "usage_over_ceiling"
    (entry,) = result.report["cost"]["entries"]
    assert (
        Decimal(entry["known_usd"]) == 9000 * P_OUT
    )  # not capped at the 8,000 ceiling
    assert Decimal(entry["known_usd"]) + Decimal(entry["unresolved_usd"]) == max(
        CEILING, 9000 * P_OUT + CEIL_IN
    )


def test_a_small_known_component_never_lowers_the_reservation(tmp_path):
    usage = '{"prompt_tokens": 1000, "completion_tokens": null}'
    c, _ = raw_client([(raw_body(FINISH, usage), {})])
    result, _, _ = live(tmp_path, c)
    assert result.terminal_state == ctl.REPORT
    cost = result.report["cost"]
    (entry,) = cost["entries"]
    assert entry["status"] == "partial_usage" and cost["unknown_usage_attempts"] == 1
    assert Decimal(entry["known_usd"]) == 1000 * P_IN
    assert Decimal(cost["estimated_total_usd"]) == CEILING  # the original reservation
    assert "not a guaranteed maximum" in cost["unresolved_note"]


# =============================================================================================
# 3. Configuration is validated before any SDK object exists (P2-3)
# =============================================================================================


@pytest.mark.parametrize(
    "bad",
    [
        {"timeout_s": float("inf")},
        {"timeout_s": float("nan")},
        {"timeout_s": True},
        {"timeout_s": -1.0},
        {"timeout_s": "5"},
        {"price_input_per_token": Decimal(-1)},
        {"price_output_per_token": Decimal("NaN")},
        {"price_input_per_token": Decimal("sNaN")},
        {"price_output_per_token": Decimal("Infinity")},
        {"price_input_per_token": 0.3},
        {"max_input_tokens": 0},
        {"max_completion_tokens": 0},
        {"max_input_tokens": True},
        {"max_completion_tokens": 8000.0},
        {"template_overhead_tokens": -1},
        {"template_overhead_tokens": False},
        {"base_url": "http://tokenfactory.invalid/v1/"},
        {"model_id": " "},
    ],
    ids=lambda bad: f"{next(iter(bad))}={next(iter(bad.values()))!r}",
)
def test_invalid_configuration_is_rejected(bad):
    with pytest.raises((TypeError, ValueError)) as raised:
        S.config(**bad)
    assert KEY not in str(raised.value)


def test_a_configuration_altered_after_validation_builds_no_client():
    cfg = S.config()
    object.__setattr__(cfg, "timeout_s", float("inf"))  # bypasses the frozen dataclass
    transport = RawTransport([])
    with pytest.raises(ValueError):
        NebiusClient(
            cfg,
            KEY,
            http_client=httpx2.Client(transport=httpx2.MockTransport(transport)),
        )
    assert transport.requests == []


def test_valid_configuration_controls():
    S.config(price_input_per_token=Decimal(0), price_output_per_token=Decimal(0))
    S.config(template_overhead_tokens=0, timeout_s=5, max_input_tokens=1)
    c, _ = raw_client([], timeout_s=600.0)
    assert c.ceiling_cost() == CEILING


# =============================================================================================
# 4. Report prose follows observed execution (P3-1)
# =============================================================================================


@pytest.fixture(scope="module")
def evidence(tmp_path_factory):
    base = tmp_path_factory.mktemp("evidence")
    run = base / "faulty"
    run.mkdir()
    assert trusted.run_trusted_fixture(S01, "evaluate.py", run)["returncode"] == 0
    return {"faulty": S.H.collected(run, base / "faulty-out")}


@pytest.fixture
def no_host_runner(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("project code reached the host runner")

    monkeypatch.setattr(trusted, "run_trusted_fixture", refuse)
    monkeypatch.setattr("atlas.audit.run_trusted_fixture", refuse)


class TamperOn(S.ApproveExactly):
    """Approves exactly, then changes the snapshot's entry point after approving `kind`."""

    def __init__(self, runs, kind):
        super().__init__()
        self.runs, self.kind = runs, kind

    def decide(self, request):
        decision = super().decide(request)
        if request.kind == self.kind:
            (entry,) = self.runs.glob("agent-*/snapshot/evaluate.py")
            entry.write_bytes(entry.read_bytes() + b"\n# changed after approval\n")
        return decision


def _not_executed_prose(result, status):
    report = result.report
    limitations = report["limitations"]
    text = " ".join(limitations)
    assert f"The original was not executed (execution status: {status})" in text
    assert not any(x.startswith("The original executed") for x in limitations)
    assert "candidate" not in text.lower()  # no candidate existed
    assert "Container evidence" not in text  # nothing executed
    comparison = report["comparison"]
    assert comparison["comparison_basis"].startswith("The original was not executed")
    assert "host trusted-fixture" not in comparison["comparison_basis"].lower()
    assert comparison["original"]["executed"] is False


def test_no_docker_prose_says_nothing_ran(tmp_path, monkeypatch, no_host_runner):
    S.fake_docker(monkeypatch, [], available=False)
    client = FixtureClient("s3r", [{"content": FINISH}])
    result = ctl.run_agent(S01, tmp_path / "runs", client, S.ApproveExactly(), env={})
    assert result.terminal_state == ctl.ERROR and client.requests == []
    _not_executed_prose(result, "not_executed")


def test_a_refused_original_prose_says_nothing_ran(
    tmp_path, monkeypatch, no_host_runner
):
    S.fake_docker(monkeypatch, [], available=True)
    runs = tmp_path / "runs"
    client = FixtureClient("s3r", [{"content": FINISH}])
    result = ctl.run_agent(S01, runs, client, TamperOn(runs, "original"), env={})
    assert (
        result.reason
        == "original_not_executed: refused: base_snapshot_changed; no host fallback"
    )
    assert client.requests == []
    _not_executed_prose(result, "refused")


def test_a_refused_candidate_is_not_described_as_executed(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    S.fake_docker(monkeypatch, [evidence["faulty"]])
    runs = tmp_path / "runs"
    client = FixtureClient("s3r", [{"content": PATCH}, {"content": FINISH}])
    result = ctl.run_agent(S01, runs, client, TamperOn(runs, "candidate"), env={})
    assert result.terminal_state == ctl.REPORT, result.reason
    (candidate,) = result.candidates
    assert candidate.evaluated is False
    limitations = result.report["limitations"]
    assert (
        "The original executed in the isolated Docker runner after explicit "
        "authorization." in limitations
    )
    assert any(x.startswith("0 of 1 candidates executed") for x in limitations)
    assert not any("Every candidate" in x for x in limitations)
    basis = result.report["comparison"]["comparison_basis"]
    assert "0 of 1 candidates executed" in basis
    assert not basis.startswith("Original and candidates all executed")


def test_cli_prints_not_executed_for_an_unexecuted_original(
    tmp_path, monkeypatch, no_host_runner
):
    S.fake_docker(monkeypatch, [], available=False)
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stdin", S.FakeStdin(["<prefix>"], out=out))
    script = tmp_path / "script.json"
    script.write_text(
        json.dumps({"name": "cli", "replies": [{"content": FINISH}]}), encoding="utf-8"
    )
    code = cli.main(
        ["audit", str(S01), "--mode", "agent", "--fixture-script", str(script),
         "--runs-dir", str(tmp_path / "runs")]
    )  # fmt: skip
    assert code == 1
    assert "original: INCONCLUSIVE (not executed)" in out.getvalue()
    assert "(docker_isolated)" not in out.getvalue()
