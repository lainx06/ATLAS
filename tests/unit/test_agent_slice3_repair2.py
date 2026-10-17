"""T-06 slice 3 repair pass 2 (Codex verification `runs/s3w/review.md`), offline only.

Regressions for the three remaining defects, each with valid controls:

1. invalid usage attached to an error (transient or not) ends the run before any retry
   decision, logging of provider values or action, keeping the valid known cost;
2. no response identifier reaches a log unchecked: the reply's model ID is never logged (only
   the trusted configured ID and whether it matched), error codes are fixed shapes, and
   request ID / served model are logged only when the client checked them against its
   credential;
3. money arithmetic is exact and independent of the ambient `decimal` context, with an
   explicit supported range checked before any client exists.

Synthetic secret markers only (`KEY` is a made-up string); no real credential is inspected and
no request leaves the process: clients are in-process fakes or the production client over an
`httpx2.MockTransport` handler. This file uses only interfaces that also exist at the parent
commit, so it can run there for the red demonstration.
"""

import decimal
import importlib.util
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from atlas.agent import controller as ctl
from atlas.agent.budget import CostLedger
from atlas.agent.client import ModelError, ModelReply, TransientModelError
from atlas.agent.network import deny_network


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace(".py", ""), Path(__file__).with_name(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load("test_agent_slice3_repair.py")
S = R.S
KEY, FINISH, PATCH, S01 = S.KEY, S.FINISH, S.PATCH, S.S01
P_IN, P_OUT = R.P_IN, R.P_OUT
CEIL_IN, CEIL_OUT, CEILING = R.CEIL_IN, R.CEIL_OUT, R.CEILING
RLO = chr(0x202E)  # right-to-left override
MARKERS = (KEY, "\x1b[2J", RLO)


class Scripted:
    """An in-process client: each script entry is an exception to raise or a reply."""

    def __init__(self, script, *, live=False, model_id="fixture:other", priced=None):
        self.script, self.calls = list(script), 0
        self.live, self.model_id = live, model_id
        if priced is not None:  # a priced fake (live): its own cost figures
            self.config = SimpleNamespace(max_completion_tokens=8000)
            self.ceiling_cost = lambda: priced["ceiling"]
            self.component_ceilings = lambda: priced["ceilings"]
            self.component_costs = priced["costs"]

    def complete(self, request):
        self.calls += 1
        entry = self.script.pop(0)
        if isinstance(entry, BaseException):
            raise entry
        return entry


def reply(content=FINISH, **fields):
    values = {"finish_reason": "stop", "model_id": "fixture:other", "live": False}
    values.update(fields)
    return ModelReply(content=content, **values)


def run(tmp_path, client, *, live=False):
    executor = S.RecordingExecutor()
    with deny_network():
        result = ctl.run_agent(
            S01,
            tmp_path / "runs",
            client,
            S.ApproveExactly(),
            executor=executor,
            original=R.host_baseline,
            live_authorized=live,
            env={},
        )
    log = (result.run_dir / "agent_log.jsonl").read_text(encoding="utf-8")
    text = log + json.dumps(result.report, default=str)
    return result, executor, log, text


def no_markers(text):
    return not any(m in text for m in MARKERS)


# =============================================================================================
# 1. Invalid usage on an error ends the run before any retry (P2, controller.py:574)
# =============================================================================================


def test_invalid_usage_on_a_transient_error_ends_the_run_without_retry(tmp_path):
    bad = TransientModelError(
        "x", usage={"prompt_tokens": -5, "completion_tokens": KEY}
    )
    client = Scripted([bad, reply(PATCH), reply(FINISH)])
    result, executor, log, text = run(tmp_path, client)
    assert (result.terminal_state, result.reason) == (ctl.ERROR, "invalid_usage")
    assert client.calls == 1 and executor.calls == []  # no second request, no action
    assert result.report["budget"]["used"]["attempts"] == 1
    (attempt,) = R.attempts(log)
    assert attempt["invalid_usage_fields"] == ["completion_tokens", "prompt_tokens"]
    assert attempt["error"] == "transport_error" and attempt.get("transient") is True
    assert no_markers(text)
    assert result.original.outcome.outcome is R.Outcome.VIOLATION_FOUND  # baseline kept


def test_a_transient_error_with_valid_usage_is_still_retried(tmp_path):
    ok = TransientModelError("x", usage={"prompt_tokens": 5, "completion_tokens": 0})
    client = Scripted([ok, reply(FINISH)])
    result, _, _, _ = run(tmp_path, client)
    assert result.terminal_state == ctl.REPORT and client.calls == 2  # control


def test_invalid_usage_on_a_permanent_error_is_reported_as_invalid_usage(tmp_path):
    bad = ModelError("x", usage={"prompt_tokens": 1.5})
    client = Scripted([bad, reply(FINISH)])
    result, executor, _, text = run(tmp_path, client)
    assert (result.terminal_state, result.reason) == (ctl.ERROR, "invalid_usage")
    assert client.calls == 1 and executor.calls == [] and no_markers(text)


def test_invalid_usage_on_a_priced_error_keeps_the_valid_known_cost(tmp_path):
    c, transport = R.raw_client([])
    calls = []

    def failing(request):
        calls.append(request)
        raise TransientModelError(
            "x", usage={"prompt_tokens": 1000, "completion_tokens": -1}
        )

    c.complete = failing
    result, executor, _, text = run(tmp_path, c, live=True)
    assert (result.terminal_state, result.reason) == (ctl.ERROR, "invalid_usage")
    assert len(calls) == 1 and executor.calls == [] and transport.requests == []
    cost = result.report["cost"]
    (entry,) = cost["entries"]
    assert entry["status"] == "partial_usage"
    assert Decimal(entry["known_usd"]) == 1000 * P_IN  # the valid count is kept
    assert (
        Decimal(cost["estimated_total_usd"]) == CEILING
    )  # never below the reservation
    assert no_markers(text)


# =============================================================================================
# 2. No unchecked response identifier reaches a log (P2, controller.py:625)
# =============================================================================================


@pytest.mark.parametrize(
    "model_id",
    ["nvidia/" + KEY, KEY, "fixture:other\x1b[2J", "fixture:other" + RLO],
    ids=["key-in-path", "key", "escape", "bidi"],
)
def test_a_mismatched_reply_model_id_is_never_logged(tmp_path, model_id):
    client = Scripted([reply(FINISH, model_id=model_id)])
    result, _, log, text = run(tmp_path, client)
    assert (result.terminal_state, result.reason) == (
        ctl.ERROR,
        "schema_failure: mislabelled",
    )
    (attempt,) = R.attempts(log)
    assert attempt["reply_model_id"] is None and attempt["reply_identity"] == "mismatch"
    assert no_markers(text)


def test_a_non_boolean_live_label_is_rejected_and_not_logged(tmp_path):
    client = Scripted([reply(FINISH, live="no " + KEY)])
    result, _, log, text = run(tmp_path, client)
    assert result.reason == "schema_failure: mislabelled"
    (attempt,) = R.attempts(log)
    assert attempt["reply_live"] is None and no_markers(text)


def test_a_matching_reply_identity_is_recorded_from_configuration(tmp_path):
    result, _, log, _ = run(tmp_path, Scripted([reply(FINISH)]))
    assert result.terminal_state == ctl.REPORT  # control
    (attempt,) = R.attempts(log)
    assert (attempt["reply_model_id"], attempt["reply_identity"]) == (
        "fixture:other",
        "match",
    )


def test_unchecked_request_id_and_served_model_are_withheld(tmp_path):
    client = Scripted([reply(FINISH, request_id=KEY, served_model="nvidia/" + KEY)])
    result, _, log, text = run(tmp_path, client)
    assert result.terminal_state == ctl.REPORT
    (attempt,) = R.attempts(log)
    assert attempt["request_id"] is None and attempt["served_model"] is None
    assert attempt["withheld_fields"] == ["request_id", "served_model"]
    assert no_markers(text)


def test_checked_identifiers_from_the_production_client_are_logged(tmp_path):
    usage = '{"prompt_tokens": 10, "completion_tokens": 5}'
    c, _ = R.raw_client([(R.raw_body(FINISH, usage), {"x-request-id": "req-7"})])
    result, _, log, _ = run(tmp_path, c, live=True)
    assert result.terminal_state == ctl.REPORT  # control
    (attempt,) = R.attempts(log)
    assert (attempt["request_id"], attempt["served_model"]) == (
        "req-7",
        "nvidia/test-model",
    )


@pytest.mark.parametrize("transient", [False, True], ids=["permanent", "transient"])
def test_client_error_codes_are_fixed_shapes(tmp_path, transient):
    kind = TransientModelError if transient else ModelError
    error = kind("x", code=KEY)
    client = Scripted([error, reply(FINISH), reply(FINISH)])
    result, _, log, text = run(tmp_path, client)
    attempts = R.attempts(log)
    assert attempts[0]["result"] == "unrecognized_error"
    if transient:  # retried once, then finished
        assert result.terminal_state == ctl.REPORT and client.calls == 2
    else:
        assert (result.terminal_state, result.reason) == (
            ctl.ERROR,
            "unrecognized_error",
        )
    assert no_markers(text)


def test_a_known_error_code_is_kept(tmp_path):
    client = Scripted([ModelError("x", code="http_400")])
    result, _, _, _ = run(tmp_path, client)
    assert result.reason == "http_400"  # control


# =============================================================================================
# 3. Exact money, independent of the ambient decimal context (P2, budget.py:207)
# =============================================================================================


def test_a_small_unknown_hold_survives_a_huge_known_cost():
    c, _ = R.raw_client([])
    ledger = CostLedger(c)
    ledger.reserve(1)
    ledger.settle(1, {"prompt_tokens": 10**40, "completion_tokens": None}, True)
    (entry,) = ledger.summary()["entries"]
    assert entry["status"] == "partial_usage"
    assert Decimal(entry["known_usd"]) == Decimal(10**40) * P_IN
    assert Decimal(entry["unresolved_usd"]) == CEIL_OUT  # not rounded away
    assert entry["unresolved_usd"] == "0.0072000"


def test_a_huge_known_cost_in_a_live_run_keeps_the_hold(tmp_path):
    usage = '{"prompt_tokens": 10000000000000000000000000000000000000000}'
    c, _ = R.raw_client([(R.raw_body(PATCH, usage), {})])
    result, executor, _, _ = run(tmp_path, c, live=True)
    assert result.reason == "usage_over_ceiling" and executor.calls == []
    (entry,) = result.report["cost"]["entries"]
    assert Decimal(entry["unresolved_usd"]) == CEIL_OUT


AMBIENT = {
    "prec=1": {"prec": 1},
    "prec=3, round up": {"prec": 3, "rounding": decimal.ROUND_UP},
    "Emax=9, overflow untrapped": {"Emax": 9, "traps": []},
    "every signal trapped": {
        "traps": [
            decimal.Inexact,
            decimal.Rounded,
            decimal.Overflow,
            decimal.InvalidOperation,
            decimal.Clamped,
        ]
    },
    "prec=2, nothing trapped": {"prec": 2, "traps": []},
}

CASES = {
    "complete": {"prompt_tokens": 1000, "completion_tokens": 200},
    "complete_low": {"prompt_tokens": 10, "completion_tokens": 5},
    "partial": {"prompt_tokens": 1000, "completion_tokens": None},
    "huge_partial": {"prompt_tokens": 10**40, "completion_tokens": None},
    "unknown": {},
}


def ledger_summary(**config):
    c, transport = R.raw_client([], **config)
    ledger = CostLedger(c)
    for attempt, usage in enumerate(CASES.values(), start=1):
        ledger.reserve(attempt)
        ledger.settle(attempt, usage, True)
    assert transport.requests == []
    return ledger.summary()


@pytest.mark.parametrize("ambient", sorted(AMBIENT))
def test_accounting_ignores_the_ambient_decimal_context(ambient):
    expected = ledger_summary()  # computed in the default context
    with decimal.localcontext() as ctx:
        for name, value in AMBIENT[ambient].items():
            if name == "traps":
                ctx.clear_traps()
                for signal in value:
                    ctx.traps[signal] = True
            else:
                setattr(ctx, name, value)
        got = ledger_summary()
    assert got == expected
    by_status = [e["status"] for e in got["entries"]]
    assert by_status == [
        "settled",
        "settled",
        "partial_usage",
        "partial_usage",
        "unknown_usage",
    ]
    complete, low = got["entries"][:2]
    assert Decimal(complete["known_usd"]) == 1000 * P_IN + 200 * P_OUT
    assert Decimal(low["known_usd"]) == Decimal("0.0000075")  # below the reservation
    assert Decimal(low["unresolved_usd"]) == 0
    assert all(Decimal(x).is_finite() for x in R.amounts(got))


@pytest.mark.parametrize(
    "bad",
    [
        {"price_input_per_token": Decimal("1e999999")},
        {"price_output_per_token": Decimal("1e101")},
        {"price_input_per_token": Decimal("1e-31")},
        {"price_input_per_token": Decimal("-0")},
        {"max_input_tokens": 10**100 + 1},
        {"template_overhead_tokens": 10**100 + 1},
        {"timeout_s": 10**400},
        {"timeout_s": 86_401},
    ],
    ids=lambda bad: f"{next(iter(bad))}",
)
def test_configurations_outside_the_supported_range_are_rejected(bad):
    with pytest.raises(ValueError):
        S.config(**bad)  # a ValueError before any client (or SDK object) exists


@pytest.mark.parametrize("trapped", [True, False], ids=["traps", "no-traps"])
def test_an_overflowing_price_is_rejected_whatever_the_ambient_traps(trapped):
    with decimal.localcontext() as ctx:
        ctx.traps[decimal.Overflow] = trapped
        with pytest.raises(ValueError):
            S.config(price_input_per_token=Decimal("1e999999"))


def test_the_supported_range_boundaries_are_accepted():
    c, _ = R.raw_client(
        [],
        price_input_per_token=Decimal("1e100"),
        price_output_per_token=Decimal("1e-30"),
        max_input_tokens=10**100,
        max_completion_tokens=10**100,
        timeout_s=86_400,
    )
    ledger = CostLedger(c)
    ledger.reserve(1)
    ledger.settle(1, {"prompt_tokens": 10**100, "completion_tokens": None}, True)
    (entry,) = ledger.summary()["entries"]
    assert Decimal(entry["known_usd"]) == Decimal("1e200")
    assert Decimal(entry["unresolved_usd"]) == Decimal("1e70")  # 10**100 x 1e-30, kept
    S.config(price_input_per_token=Decimal(0), price_output_per_token=Decimal(0))


def test_a_reported_count_outside_the_range_is_invalid_usage(tmp_path):
    usage = '{"prompt_tokens": 1' + "0" * 101 + ', "completion_tokens": 1}'
    c, _ = R.raw_client([(R.raw_body(PATCH, usage), {})])
    result, executor, log, _ = run(tmp_path, c, live=True)
    assert (result.terminal_state, result.reason) == (ctl.ERROR, "invalid_usage")
    assert executor.calls == []
    (attempt,) = R.attempts(log)
    assert attempt["invalid_usage_fields"] == ["prompt_tokens"]


def priced(costs, ceiling=Decimal("0.0672")):
    return {
        "ceiling": ceiling,
        "ceilings": (Decimal("0.06"), Decimal("0.0072")),
        "costs": costs,
    }


def test_an_unrepresentable_amount_is_never_settled(tmp_path):
    client = Scripted(
        [reply(PATCH, live=True, model_id="fake:priced")],
        live=True,
        model_id="fake:priced",
        priced=priced(lambda usage: (Decimal("Infinity"), Decimal(0))),
    )
    result, executor, _, _ = run(tmp_path, client, live=True)
    assert (result.terminal_state, result.reason) == (ctl.ERROR, "cost_unrepresentable")
    assert executor.calls == []
    cost = result.report["cost"]
    (entry,) = cost["entries"]
    assert entry["status"] == "unrepresentable" and entry["known_usd"] is None
    assert cost["estimated_total_usd"] is None  # withheld, not "Infinity"
    assert "Infinity" not in json.dumps(cost)


def test_an_unrepresentable_ceiling_is_rejected_before_any_request(tmp_path):
    client = Scripted(
        [reply(FINISH, live=True, model_id="fake:priced")],
        live=True,
        model_id="fake:priced",
        priced=priced(lambda usage: (None, None), ceiling=Decimal("Infinity")),
    )
    with pytest.raises(ValueError), deny_network():
        ctl.run_agent(
            S01, tmp_path / "runs", client, S.ApproveExactly(),
            executor=S.RecordingExecutor(), original=R.host_baseline,
            live_authorized=True, env={},
        )  # fmt: skip
    assert client.calls == 0 and not (tmp_path / "runs").exists()


def test_only_an_explicit_not_sent_releases_a_reservation():
    c, _ = R.raw_client([])
    ledger = CostLedger(c)
    for attempt, dispatched in enumerate([False, "no", None, 0], start=1):
        ledger.reserve(attempt)
        ledger.settle(attempt, None, dispatched)
    statuses = [e["status"] for e in ledger.summary()["entries"]]
    assert statuses == ["released", "unknown_usage", "unknown_usage", "unknown_usage"]
