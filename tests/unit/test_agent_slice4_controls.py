"""T-06 slice 4, prepared offline: the prompt budget and the spending controls for a live run.

No request leaves the process: the production client runs over an `httpx2.MockTransport`
handler under the fixture network guard, and the original is a test-only host baseline. The
token ceilings and amounts used here are the lead's Gate 2 decisions (`budget.DECIDED_SLICE4`,
DECISIONS.md "T-06 slice 4 live-run decisions (lead)"); passing tests authorize nothing.

Interfaces that are new in this slice are imported defensively, so the file also runs at the
parent commit for the red demonstration (new-interface tests then fail by design).
"""

import dataclasses
import importlib.util
import inspect
import json
from decimal import Decimal
from pathlib import Path

import pytest

from atlas.agent import controller as ctl
from atlas.agent.client import LiveModeUnavailable, ModelRequest
from atlas.agent.nebius import NebiusConfig
from atlas.agent.network import deny_network

try:  # new in slice 4 (the decided values replaced the proposal at Gate 2)
    from atlas.agent.budget import DECIDED_SLICE4, SpendLimits, SpendRefused
except ImportError:  # an earlier commit (red demonstration)
    DECIDED_SLICE4 = {
        "max_input_tokens": 12_000, "max_completion_tokens": 8_000,
        "template_overhead_tokens": 16, "context_length_tokens": 262_144,
        "price_input_per_token": Decimal("0.0000003"),
        "price_output_per_token": Decimal("0.0000009"),
        "estimate_cap_usd": Decimal("0.0648"), "authorized_usd": Decimal("0.51"),
    }  # fmt: skip
    SpendLimits = SpendRefused = None


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace(".py", ""), Path(__file__).with_name(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load("test_agent_slice3_repair.py")
S = R.S
FINISH, S01 = S.FINISH, S.S01
CONFIG_FIELDS = {f.name for f in dataclasses.fields(NebiusConfig)}
TOKENS = ("max_input_tokens", "max_completion_tokens", "template_overhead_tokens")
USAGE = '{"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200}'
READ_TABLE = S.act("read_project_file", path="table.csv")  # 13,371 bytes
CEILING = Decimal("0.0108")  # 12,000 x 0.0000003 + 8,000 x 0.0000009


# Token, price and context values only: the test client keeps its synthetic base URL and model.
DECIDED_CONFIG_KEYS = (
    "max_input_tokens",
    "max_completion_tokens",
    "template_overhead_tokens",
    "context_length_tokens",
    "price_input_per_token",
    "price_output_per_token",
)


def proposed(**overrides):
    """The decided token, price and context values (those this commit's NebiusConfig has)."""
    values = {
        k: DECIDED_SLICE4[k]
        for k in DECIDED_CONFIG_KEYS
        if k in DECIDED_SLICE4 and k in CONFIG_FIELDS
    }
    values.update(overrides)
    return values


def limits(authorized="0.51", cap="0.0648"):
    if SpendLimits is None:  # the parent commit: no spending limits exist
        return None
    return SpendLimits(
        authorized_usd=Decimal(authorized), estimate_cap_usd=Decimal(cap)
    )


def live(tmp_path, script, spend="proposed", original=None, **config):
    c, transport = R.raw_client(script, **proposed(**config))
    executor = S.RecordingExecutor()
    kwargs = {}
    if "spend" in inspect.signature(ctl.run_agent).parameters:
        kwargs["spend"] = limits() if spend == "proposed" else spend
    with deny_network():
        result = ctl.run_agent(
            S01, tmp_path / "runs", c, S.ApproveExactly(), executor=executor,
            original=original or R.host_baseline, live_authorized=True, env={},
            **kwargs,
        )  # fmt: skip
    log = (result.run_dir / "agent_log.jsonl").read_text(encoding="utf-8")
    return result, transport, executor, log


def estimate(request_body: dict, overhead=16) -> int:
    return sum(
        len(m["content"].encode("utf-8")) + overhead for m in request_body["messages"]
    )


# =============================================================================================
# 1. The proposal's arithmetic matches the code (proposed values; nothing is authorized)
# =============================================================================================


def test_the_proposed_figures_follow_from_the_code():
    c, _ = R.raw_client([], **proposed())
    assert c.ceiling_cost() == CEILING
    assert (
        6 * c.ceiling_cost() == DECIDED_SLICE4["estimate_cap_usd"] == Decimal("0.0648")
    )
    assert c.worst_case_request_cost() == Decimal("0.0834432")
    worst_run = 6 * c.worst_case_request_cost()
    assert worst_run == Decimal("0.5006592") <= DECIDED_SLICE4["authorized_usd"]
    assert c.user_message_budget(ctl.SYSTEM_PROMPT) == 12_000 - 489 - 16 - 16 == 11_479


def test_the_decided_values_are_never_a_default():
    """Only the CLI live path and the pre-run script read the decided constant."""
    assert inspect.signature(ctl.run_agent).parameters["spend"].default is None
    for module in ("controller.py", "nebius.py", "client.py", "preflight.py"):
        path = Path(ctl.__file__).parent / module
        if path.exists():
            source = path.read_text(encoding="utf-8")
            assert "DECIDED_SLICE4" not in source and "PROPOSED_SLICE4" not in source


# =============================================================================================
# 2. The prompt budget keeps live prompts inside the pre-send estimate
# =============================================================================================


def test_live_prompts_stay_within_the_estimate_as_history_grows(tmp_path):
    script = [(R.raw_body(READ_TABLE, USAGE), {})] * 5 + [
        (R.raw_body(FINISH, USAGE), {})
    ]
    result, transport, _, _ = live(tmp_path, script)
    assert result.terminal_state == ctl.REPORT, result.reason
    bodies = [json.loads(r.content) for r in transport.requests]
    assert len(bodies) == 6
    assert all(estimate(b) <= 12_000 for b in bodies)  # never refused before sending
    users = [b["messages"][1]["content"] for b in bodies]
    assert all(len(u.encode("utf-8")) <= 11_479 for u in users)
    assert any(json.loads(u).get("history_truncated") for u in users)  # older dropped
    budget = result.report["prompt_budget"]
    assert budget == {"user_message_bytes": 11_479, "tool_result_chars": 5_739}


def test_fixture_runs_keep_the_existing_limits(tmp_path):
    client = S.FixtureClient("s4", [{"content": FINISH}])
    result = ctl.run_agent(
        S01, tmp_path / "runs", client, S.ApproveExactly(),
        executor=S.RecordingExecutor(), original=R.host_baseline, env={},
    )  # fmt: skip
    assert result.report["prompt_budget"] == {
        "user_message_bytes": ctl.MAX_PROMPT_CHARS,
        "tool_result_chars": ctl.MAX_TOOL_RESULT_CHARS,
    }
    assert result.report["spending"]["applicable"] is False


def test_a_base_context_that_cannot_fit_is_refused_before_sending(tmp_path):
    result, transport, _, _ = live(
        tmp_path, [(R.raw_body(FINISH, USAGE), {})], max_input_tokens=700
    )
    assert (result.terminal_state, result.reason) == (ctl.ERROR, "input_over_ceiling")
    assert transport.requests == [] and result.report["budget"]["used"]["attempts"] == 0


@pytest.mark.parametrize(
    ("max_input", "overhead", "expected"),
    [(12_000, 16, 11_479), (12_000, 0, 11_511), (600, 100, 0), (505 + 16, 0, 32)],
)
def test_the_user_message_budget_formula(max_input, overhead, expected):
    c, _ = R.raw_client(
        [], **proposed(max_input_tokens=max_input, template_overhead_tokens=overhead)
    )
    system = "x" * 489
    assert c.user_message_budget(system) == expected
    request = ModelRequest(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": "y" * expected},
        ],
        {},
    )
    if expected:
        c.check_request(request)  # a user message of exactly the budget passes


# =============================================================================================
# 3. Spending limits: required, checked before anything runs, and enforced per request
# =============================================================================================


def test_a_live_run_without_spending_limits_is_refused(tmp_path):
    c, transport = R.raw_client([(R.raw_body(FINISH, USAGE), {})], **proposed())
    with pytest.raises(LiveModeUnavailable):
        ctl.run_agent(
            S01, tmp_path / "runs", c, S.ApproveExactly(), original=R.host_baseline,
            live_authorized=True, env={},
        )  # fmt: skip
    assert transport.requests == [] and not (tmp_path / "runs").exists()


class Tripwire:
    def __init__(self):
        self.calls = 0

    def __call__(self, run):
        self.calls += 1
        raise AssertionError("the original ran although the spend check refused")


@pytest.mark.parametrize(
    ("authorized", "cap"),
    [("0.50", "0.0648"), ("0.51", "0.0107")],
    ids=["authorized-below-worst-case", "cap-below-one-ceiling"],
)
def test_insufficient_limits_refuse_before_anything_runs(tmp_path, authorized, cap):
    tripwire = Tripwire()
    with pytest.raises(SpendRefused):
        live(
            tmp_path,
            [(R.raw_body(FINISH, USAGE), {})],
            spend=limits(authorized, cap),
            original=tripwire,
        )
    assert tripwire.calls == 0 and not (tmp_path / "runs").exists()


def test_the_proposed_limits_are_accepted_and_reported(tmp_path):
    result, transport, _, _ = live(tmp_path, [(R.raw_body(FINISH, USAGE), {})])
    assert result.terminal_state == ctl.REPORT and len(transport.requests) == 1
    spending = result.report["spending"]
    assert (spending["authorized_usd"], spending["estimate_cap_usd"]) == (
        "0.51",
        "0.0648",
    )
    assert spending["provider_worst_case_run_usd"] == "0.5006592"
    assert "not a guaranteed charge" in spending["labels"]["estimate_cap_usd"]
    assert "has not verified" in spending["labels"]["provider_worst_case_run_usd"]


@pytest.mark.parametrize(
    "bad",
    [
        {"authorized_usd": Decimal("0.05"), "estimate_cap_usd": Decimal("0.0648")},
        {"authorized_usd": Decimal(-1), "estimate_cap_usd": Decimal(0)},
        {"authorized_usd": Decimal("NaN"), "estimate_cap_usd": Decimal(0)},
        {"authorized_usd": Decimal("Infinity"), "estimate_cap_usd": Decimal(0)},
        {"authorized_usd": 0.51, "estimate_cap_usd": Decimal(0)},
        {"authorized_usd": Decimal(1), "estimate_cap_usd": Decimal("-0")},
    ],
    ids=[
        "cap-above-authorized",
        "negative",
        "nan",
        "infinite",
        "float",
        "negative-zero",
    ],
)
def test_invalid_spending_limits_are_rejected(bad):
    with pytest.raises(ValueError):
        SpendLimits(**bad)


def test_the_estimate_cap_stops_before_sending(tmp_path):
    inspect_reply = S.act("inspect_evidence", check="split_integrity")
    script = [
        (R.raw_body(inspect_reply, "null"), {})
    ] * 5  # usage unknown: ceiling held
    result, transport, _, log = live(tmp_path, script, spend=limits("0.51", "0.0216"))
    assert result.terminal_state == ctl.BUDGET_EXHAUSTED
    assert result.reason.startswith("spend_cap")
    assert len(transport.requests) == 2  # 2 x 0.0108 held; a third could exceed 0.0216
    assert (
        result.report["budget"]["used"]["attempts"] == 2
    )  # the refusal is not an attempt
    refused = [json.loads(x) for x in log.splitlines() if '"spend_cap"' in x]
    assert refused and refused[0]["projected_usd"] == "0.0324000"


def test_the_estimate_cap_also_blocks_a_retry(tmp_path):
    import httpx2

    c, transport = S.client([httpx2.ReadTimeout, httpx2.ReadTimeout], **proposed())
    kwargs = {}
    if "spend" in inspect.signature(ctl.run_agent).parameters:
        kwargs["spend"] = limits("0.51", "0.0108")
    with deny_network():
        result = ctl.run_agent(
            S01, tmp_path / "runs", c, S.ApproveExactly(),
            executor=S.RecordingExecutor(), original=R.host_baseline,
            live_authorized=True, env={}, **kwargs,
        )  # fmt: skip
    # The timed-out request keeps its 0.0108 ceiling held, so the retry could exceed the cap.
    assert result.terminal_state == ctl.BUDGET_EXHAUSTED
    assert result.reason.startswith("spend_cap") and len(transport.requests) == 1


def test_known_small_usage_does_not_trip_the_cap(tmp_path):
    inspect_reply = S.act("inspect_evidence", check="split_integrity")
    script = [(R.raw_body(inspect_reply, USAGE), {})] * 2 + [
        (R.raw_body(FINISH, USAGE), {})
    ]
    result, transport, _, _ = live(tmp_path, script, spend=limits("0.51", "0.0216"))
    assert (
        result.terminal_state == ctl.REPORT and len(transport.requests) == 3
    )  # control


# =============================================================================================
# 4. The context length that the worst case relies on
# =============================================================================================


def test_the_ceilings_must_fit_the_context_length():
    with pytest.raises(ValueError):
        S.config(**proposed(context_length_tokens=19_999))  # 12,000 + 8,000 > 19,999
    S.config(**proposed(context_length_tokens=20_000))
    values = dict(proposed())
    values.pop("context_length_tokens")
    with pytest.raises(TypeError):
        NebiusConfig(**{**values, "base_url": "https://x.invalid/v1/", "model_id": "m",
                        "timeout_s": 5.0})  # fmt: skip


def test_the_worst_case_picks_the_dearer_token_kind():
    c, _ = R.raw_client(
        [],
        **proposed(
            price_input_per_token=Decimal("0.000001"),
            price_output_per_token=Decimal("0.0000001"),
        ),
    )
    assert c.worst_case_request_cost() == 262_144 * Decimal("0.000001")  # all input
