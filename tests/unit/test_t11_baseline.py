"""T-11 leg (b), Nemotron alone: exact reply validation, the request cap, the input-estimate
refusal and the live machinery's order (offline).

No request leaves the process: fixture clients make no network access, and the production
client is driven over an `httpx2.MockTransport` under the fixture network guard. The key is a
synthetic marker; the repository `.env` is never read.
"""

import json
from decimal import Decimal

import httpx2
import pytest

from atlas.agent import budget as budget_module
from atlas.agent.budget import SpendLimits
from atlas.agent.client import FixtureClient, LiveModeUnavailable
from atlas.agent.nebius import NebiusClient
from atlas.agent.network import deny_network
from atlas.cli import _decided_config
from atlas.evaluation import baseline as B
from atlas.evaluation import load_cases, load_definitions

KEY = "sk-test-SECRET-t11-do-not-leak-0123456789"
CASES = {c.case_id: c for c in load_cases()}
S01, S02, HAR = CASES["s01_faulty"], CASES["s02_clean"], CASES["har_flawed"]
DEFS = load_definitions()
CONFIG = _decided_config()
LIMITS = SpendLimits(authorized_usd=Decimal("0.51"), estimate_cap_usd=Decimal("0.0648"))
GOOD = json.dumps({"violated": ["split.no_group_overlap"], "rationale": "r"})
USAGE = {"prompt_tokens": 3000, "completion_tokens": 400, "total_tokens": 3400}


def reply(content, finish="stop"):
    return {"content": content, "finish_reason": finish}


def fixture_run(tmp_path, entries, case=S01):
    client = FixtureClient("t11-test", entries)
    record = B.run_case(case, client, tmp_path, config=CONFIG, definitions=DEFS, env={})
    return record, client


# =============================================================================================
# Exact validation
# =============================================================================================

INVALID = [
    ('{"violated": [], "violated": [], "rationale": "r"}', "duplicate_key"),
    ('{"violated": [], "rationale": "r", "confidence": 1}', "extra_field"),
    ('{"violated": ["split.made_up"], "rationale": "r"}', "unknown_id"),
    (
        (
            '{"violated": ["split.no_group_overlap", "split.no_group_overlap"], '
            '"rationale": "r"}'
        ),
        "duplicate_id",
    ),
    ("The evaluation violates split.no_group_overlap.", "not_json"),
    ("", "empty"),
    ("   \n", "empty"),
    ('```json\n{"violated": [], "rationale": "r"}\n```', "not_json"),
    ('{"violated": [], "rationale": "r",}', "not_json"),
    ('{"violated": [], "rationale": "r"} {"violated": []}', "not_json"),
    ('{"violated": [NaN], "rationale": "r"}', "not_json"),
    ('[{"violated": [], "rationale": "r"}]', "not_an_object"),
    ('{"violated": []}', "missing_field"),
    ('{"rationale": "r"}', "missing_field"),
    ('{"violated": "split.no_group_overlap", "rationale": "r"}', "wrong_type"),
    ('{"violated": [1], "rationale": "r"}', "wrong_type"),
    ('{"violated": [], "rationale": null}', "wrong_type"),
    (json.dumps({"violated": [], "rationale": "x" * 601}), "rationale_too_long"),
    (None, "missing_content"),
    ("x" * (128 * 1024 + 1), "too_large"),
]


@pytest.mark.parametrize(
    ("content", "code"), INVALID, ids=[f"{i}-{c}" for i, (_, c) in enumerate(INVALID)]
)
def test_invalid_replies_get_a_fixed_code(content, code):
    with pytest.raises(B.InvalidReply) as info:
        B.validate_reply(content, S01.canonical)
    assert info.value.code == code
    assert code in B.INVALID_CODES


def test_valid_replies():
    assert B.validate_reply(GOOD, S01.canonical).violated == ["split.no_group_overlap"]
    empty = B.validate_reply('{"violated": [], "rationale": ""}', S02.canonical)
    assert empty.violated == []
    at_limit = json.dumps({"violated": [], "rationale": "x" * 600})
    assert B.validate_reply(at_limit, S01.canonical).rationale == "x" * 600
    # JSON allows surrounding whitespace; nothing else is tolerated
    assert B.validate_reply(f"\n {GOOD} \n", S01.canonical).violated


def test_ids_are_judged_against_the_cases_own_canonical_set():
    # split.no_window_overlap is required for the HAR claim, not for s01's
    content = json.dumps({"violated": ["split.no_window_overlap"], "rationale": "r"})
    assert B.validate_reply(content, HAR.canonical).violated
    with pytest.raises(B.InvalidReply) as info:
        B.validate_reply(content, S01.canonical)
    assert info.value.code == "unknown_id"


@pytest.mark.parametrize(
    ("content", "code"),
    [
        ('{"violated": [], "violated": [], "rationale": "r"}', "duplicate_key"),
        ('{"violated": [], "rationale": "r", "extra": 1}', "extra_field"),
        ('{"violated": ["split.made_up"], "rationale": "r"}', "unknown_id"),
        (
            (
                '{"violated": ["fit.coverage_complete", "fit.coverage_complete"], '
                '"rationale": "r"}'
            ),
            "duplicate_id",
        ),
        ("not json at all", "not_json"),
        ("", "empty"),
    ],
)
def test_an_invalid_reply_is_recorded_and_never_retried(tmp_path, content, code):
    record, client = fixture_run(
        tmp_path, [reply(content), reply(GOOD), reply(GOOD), reply(GOOD)]
    )
    first, second, third = record.trials
    assert (first["status"], first["code"]) == (B.INVALID_REPLY, code)
    assert "violated" not in first and "rationale" not in first
    # the next trial is the next repetition, not a retry: three requests in all
    assert [second["status"], third["status"]] == [B.VALID, B.VALID]
    assert len(client.requests) == 3
    assert [t["attempt"] for t in record.trials] == [1, 2, 3]


def test_a_reply_cut_off_or_mislabelled_is_invalid(tmp_path):
    record, _ = fixture_run(
        tmp_path, [reply(GOOD, finish="length"), reply(GOOD), reply(GOOD)]
    )
    assert (record.trials[0]["status"], record.trials[0]["code"]) == (
        B.INVALID_REPLY,
        "incomplete",
    )

    class Liar(FixtureClient):
        def complete(self, request):
            r = super().complete(request)
            r.model_id = "someone-else"
            return r

    client = Liar("t11-liar", [reply(GOOD)] * 3)
    record = B.run_case(S01, client, tmp_path / "liar", config=CONFIG,
                        definitions=DEFS, env={})  # fmt: skip
    assert {t["code"] for t in record.trials} == {"mislabelled"}


def test_raw_replies_are_stored_as_received_and_labelled(tmp_path):
    fenced = '```json\n{"violated": [], "rationale": "r"}\n```'
    record, _ = fixture_run(tmp_path, [reply(fenced), reply(GOOD), reply(None)])
    stored = record.trials[0]["reply"]
    assert (tmp_path / stored["path"]).read_bytes() == fenced.encode("utf-8")
    assert stored["label"] == B.REPLY_LABEL and stored["redacted"] is False
    assert record.trials[2]["reply"]["path"] is None
    assert record.trials[2]["code"] == "missing_content"


# =============================================================================================
# Fresh requests, the cap, the estimate refusal
# =============================================================================================


def test_each_trial_is_a_fresh_identical_request(tmp_path):
    _record, client = fixture_run(tmp_path, [reply(GOOD)] * 3)
    first, second, third = (r.messages for r in client.requests)
    assert first == second == third
    assert first is not second and first[1] is not second[1]
    assert first[0] == {"role": "system", "content": B.SYSTEM_PROMPT}
    assert GOOD not in json.dumps(second)  # nothing from an earlier trial is carried
    body = json.loads(first[1]["content"])
    assert set(body) == {"claim", "project_files", "assertions"}
    assert [a["assertion_id"] for a in body["assertions"]] == list(S01.canonical)
    assert body["project_files"][1]["untrusted_project_content"] == S01.entry_text
    assert client.requests[0].params == {"max_completion_tokens": 8000, "n": 1}


def test_at_most_three_requests_per_case_run(tmp_path):
    record, client = fixture_run(tmp_path, [reply(GOOD)] * 6)
    assert len(record.trials) == B.REPETITIONS == 3
    assert len(client.requests) == B.REQUESTS_PER_CASE == 3
    assert record.budget["limits"]["model_attempts"] == 3
    assert record.budget["used"]["attempts"] == 3


def test_a_transport_error_is_a_trial_without_an_answer_and_is_not_retried(tmp_path):
    record, client = fixture_run(
        tmp_path, [{"error": "server_error"}, reply(GOOD), reply(GOOD), reply(GOOD)]
    )
    assert record.trials[0]["status"] == B.MODEL_ERROR
    assert record.trials[0]["code"] == "transport_error"
    assert [t["status"] for t in record.trials[1:]] == [B.VALID, B.VALID]
    assert len(client.requests) == 3


def test_the_input_estimate_refuses_the_case_before_anything_is_sent(tmp_path):
    record, client = fixture_run(tmp_path, [reply(GOOD)] * 3, case=HAR)
    assert record.input_estimate > CONFIG.max_input_tokens == 12_000
    assert [(t["status"], t["code"], t["sent"]) for t in record.trials] == [
        (B.NOT_SENT, "input_over_ceiling", False)
    ] * 3
    assert client.requests == [] and record.budget["used"]["attempts"] == 0
    assert not (tmp_path / "replies").exists()


def test_the_estimate_is_the_production_clients_own(tmp_path):
    live = NebiusClient(CONFIG, KEY, http_client=httpx2.Client(transport=None))
    request = B.ModelRequest(B.messages(S01, DEFS), {})
    assert B.input_estimate(CONFIG, request) == live.input_bound(request)
    assert B.input_estimate(CONFIG, request) <= CONFIG.max_input_tokens


def test_fixture_runs_need_fixture_mode(tmp_path):
    with pytest.raises(LiveModeUnavailable):
        B.run_case(S01, FixtureClient("t", []), tmp_path, config=CONFIG,
                   definitions=DEFS, env={"ATLAS_MODEL_MODE": "live"})  # fmt: skip


# =============================================================================================
# The live machinery over a mocked transport (no network)
# =============================================================================================


def completion(content, usage=USAGE, finish="stop", model=CONFIG.model_id):
    body = {
        "id": "cmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [{"index": 0, "finish_reason": finish,
                     "message": {"role": "assistant", "content": content}}],
    }  # fmt: skip
    if usage is not None:
        body["usage"] = usage
    return body


class Provider:
    def __init__(self, script, events):
        self.script, self.events, self.requests = list(script), events, []

    def __call__(self, request):
        self.events.append("dispatch")
        self.requests.append(request)
        status, body = self.script.pop(0)
        return httpx2.Response(status, json=body, headers={"x-request-id": "req-1"})


@pytest.fixture
def events(monkeypatch):
    log = []
    Budget, Ledger = budget_module.Budget, budget_module.CostLedger
    reserve_attempt, reserve, settle = (
        Budget.reserve_attempt,
        Ledger.reserve,
        Ledger.settle,
    )

    def tracked_attempt(self, retry):
        log.append("reserve_attempt")
        return reserve_attempt(self, retry)

    def tracked_reserve(self, attempt):
        log.append("ledger_reserve")
        return reserve(self, attempt)

    def tracked_settle(self, attempt, usage, dispatched):
        log.append("settle")
        return settle(self, attempt, usage, dispatched)

    monkeypatch.setattr(Budget, "reserve_attempt", tracked_attempt)
    monkeypatch.setattr(Ledger, "reserve", tracked_reserve)
    monkeypatch.setattr(Ledger, "settle", tracked_settle)
    return log


def live_run(tmp_path, script, events, *, case=S01, limits=LIMITS):
    provider = Provider(script, events)
    client = NebiusClient(
        CONFIG, KEY, http_client=httpx2.Client(transport=httpx2.MockTransport(provider))
    )
    with deny_network():
        record = B.run_case(case, client, tmp_path, config=CONFIG,
                            definitions=DEFS, spend=limits)  # fmt: skip
    return record, provider


def test_reservation_comes_before_every_dispatch(tmp_path, events):
    record, _provider = live_run(tmp_path, [(200, completion(GOOD))] * 3, events)
    assert events == ["reserve_attempt", "ledger_reserve", "dispatch", "settle"] * 3
    assert [t["status"] for t in record.trials] == [B.VALID] * 3
    assert record.cost["applicable"] is True
    assert [e["status"] for e in record.cost["entries"]] == ["settled"] * 3


def test_the_request_body_is_exactly_the_decided_one(tmp_path, events):
    _, provider = live_run(tmp_path, [(200, completion(GOOD))] * 3, events)
    for request in provider.requests:
        body = json.loads(request.content)
        assert set(body) == {"model", "messages", "max_completion_tokens", "n"}
        assert body["model"] == "nvidia/nemotron-3-super-120b-a12b"
        assert (body["max_completion_tokens"], body["n"]) == (8000, 1)


def test_invalid_usage_is_caught_before_accounting_and_stops_the_case(tmp_path, events):
    bad = {"prompt_tokens": -1, "completion_tokens": 400, "total_tokens": 3400}
    record, provider = live_run(
        tmp_path, [(200, completion(GOOD, usage=bad))] * 3, events
    )
    first = record.trials[0]
    assert (first["status"], first["code"]) == (B.MODEL_ERROR, "invalid_usage")
    assert first["invalid_usage_fields"] == ["prompt_tokens"]
    assert [t["code"] for t in record.trials[1:]] == ["case_stopped"] * 2
    assert len(provider.requests) == 1
    # the invalid count is unknown: held at its ceiling, never settled at a reported value
    assert record.cost["entries"][0]["status"] == "partial_usage"
    assert record.cost["entries"][0]["unresolved_usd"] != "0"


def test_the_estimate_cap_refuses_before_the_attempt_is_reserved(tmp_path, events):
    # unknown usage is held at the 0.0108 ceiling; a cap of two ceilings stops trial 3
    tight = SpendLimits(
        authorized_usd=Decimal("0.51"), estimate_cap_usd=Decimal("0.0216")
    )
    record, provider = live_run(
        tmp_path, [(200, completion(GOOD, usage=None))] * 3, events, limits=tight
    )
    assert [t["status"] for t in record.trials] == [B.VALID, B.VALID, B.NOT_SENT]
    assert record.trials[2]["code"] == "spend_cap" and record.stopped == "spend_cap"
    assert len(provider.requests) == 2 and events.count("reserve_attempt") == 2


def test_a_live_estimate_refusal_sends_and_reserves_nothing(tmp_path, events):
    record, provider = live_run(tmp_path, [], events, case=HAR)
    assert {t["code"] for t in record.trials} == {"input_over_ceiling"}
    assert provider.requests == [] and events == [] and record.cost["entries"] == []


def test_a_live_server_error_is_not_retried(tmp_path, events):
    record, provider = live_run(
        tmp_path,
        [(500, {"error": "x"}), (200, completion(GOOD)), (200, completion(GOOD))],
        events,
    )
    assert record.trials[0]["code"] == "server_error_500"
    assert len(provider.requests) == 3


def test_a_live_case_run_needs_spending_limits(tmp_path):
    client = NebiusClient(CONFIG, KEY)
    with pytest.raises(ValueError):
        B.run_case(S01, client, tmp_path, config=CONFIG, definitions=DEFS)


def test_the_key_never_reaches_a_record_or_a_file(tmp_path, events):
    echo = json.dumps({"violated": [], "rationale": f"echo {KEY}"})
    record, _ = live_run(
        tmp_path, [(200, completion(echo)), (200, completion(GOOD))] * 2, events
    )
    assert KEY not in json.dumps(record.to_dict(), default=str)
    assert record.trials[0]["reply"]["redacted"] is True
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes()
