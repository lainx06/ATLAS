"""T-12 step 1: hosted mode in the engine (offline; mocked Nebius transport).

`run_agent(..., hosted=True)` reuses the agent loop: the original comes from the bundled
recorded run (re-verified by hash, refused on a mismatch), the executor is NotExecutedHere
(a validated proposal is "not executed here", no approval asked), and each live request is
reserved in the server-side store before it is sent. No request leaves the process.
"""

import json
import shutil
from decimal import Decimal
from pathlib import Path

import hosted_helpers as H
import httpx2
import pytest

from atlas.agent import controller as ctl
from atlas.agent.budget import Budget
from atlas.agent.client import FixtureClient, LiveModeUnavailable
from atlas.agent.network import deny_network
from atlas.hosted import bundle
from atlas.ui import recorded as RR


def hosted_run(tmp_path, provider, reservations=None, original=None, approver=None,
               executor=None):  # fmt: skip
    reservations = (
        reservations
        if reservations is not None
        else H.FakeReservations(provider=provider)
    )
    with deny_network():
        result = ctl.run_agent(
            H.S01, tmp_path / "runs", H.client(provider), approver or H.SpyApprover(),
            executor=executor, budget=Budget(max_attempts=6),
            original=original or bundle.live_original(), live_authorized=True,
            spend=H.decided_limits(), hosted=True, reservations=reservations,
        )  # fmt: skip
    return result, reservations


def log_events(result):
    text = (result.run_dir / "agent_log.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def test_hosted_happy_path(tmp_path):
    provider = H.live6_provider()
    approver = H.SpyApprover()
    result, store = hosted_run(tmp_path, provider, approver=approver)

    assert result.terminal_state == ctl.REPORT, result.reason
    assert (
        approver.requests == []
    )  # no approval asked, for the original or the revision
    assert (
        result.candidates == []
    )  # nothing executed (NotExecutedHere raises if called)
    assert len(provider.posts()) == 4
    # The original: from the recorded run, verified, labelled per SPEC §13.
    report = result.report
    label = "computed by ATLAS's trusted evaluation functions (recorded 2026-10-18)"
    assert result.original.runner == ctl.RECORDED_RUNNER
    assert report["hosted"]["original"]["label"] == label
    assert report["hosted"]["original"]["verified_items"] == 49
    assert report["scientific_outcomes"]["original"] == "VIOLATION_FOUND"
    assert report["scientific_outcomes"]["original_source"] == label
    assert report["comparison"]["original"]["recorded"]["label"] == label
    events = log_events(result)
    recorded = [e for e in events if e["event"] == "recorded_original"]
    assert recorded == [recorded[0]] and recorded[0]["result"] == "intact"
    # The proposal: validated by validate_diff, "not executed here", never approved.
    (proposal,) = report["proposals"]
    assert proposal["outcome"] == "not_executed_here"
    assert proposal["validation"] == "passes ATLAS validation"
    assert proposal["execution"] == "not executed here"
    assert proposal["candidate_hash"] and proposal["code"] is None
    assert not any(e["event"] == "approval" for e in events)
    assert not any(
        s["state"] in ("APPROVAL", "EXECUTE", "VERIFY") for s in report["states"]
    )
    assert report["hosted"]["candidates"]["label"] == "not executed here"
    assert "not executed here" in report["banner"]
    assert any("passed ATLAS validation and not executed here" in x
               for x in report["limitations"])  # fmt: skip
    assert not any(
        "validates the diff" in x and "not" not in x for x in report["limitations"]
    )
    # The model was told, in a fixed line, that nothing runs.
    tool = [t for t in result.transcript if t["tool"] == "propose_patch"]
    assert tool[0]["result"]["executed"] is False
    assert tool[0]["result"]["next_step"] == ctl.HOSTED_PROPOSAL_NOTE
    # Every request was reserved and marked dispatched before it was sent, then settled.
    names = store.names()
    assert names == ["reserve", "dispatched", "settle"] * 4
    for call in store.calls:
        if call[0] == "reserve":
            assert call[2] == Decimal("0.0108")
    sent_before = [c[-1] for c in store.calls if c[0] in ("reserve", "dispatched")]
    assert sent_before == [0, 0, 1, 1, 2, 2, 3, 3]  # nothing sent until reserved
    settled = [c[2] for c in store.calls if c[0] == "settle"]
    assert settled == [H.USAGE_USD] * 4  # exact Decimal known usage
    # The viewer verifies the hosted run itself, including the copied recorded original.
    assert RR.intact(RR.verify(result.run_dir, report))


def test_the_request_body_is_the_decided_one(tmp_path):
    provider = H.live6_provider()
    hosted_run(tmp_path, provider)
    for request in provider.posts():
        body = json.loads(request.content)
        assert set(body) == {"model", "messages", "max_completion_tokens", "n"}
        assert body["model"] == H.MODEL
        assert body["max_completion_tokens"] == 8000 and body["n"] == 1
        assert body["messages"][0] == {"role": "system", "content": ctl.SYSTEM_PROMPT}
        assert request.url.host == "api.tokenfactory.nebius.com"


def tamper(tmp_path, rel):
    copy = tmp_path / "bundle" / "agent-s01_faulty-877f8245a8a2"
    shutil.copytree(H.LIVE6, copy)
    path = copy / rel
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))
    return bundle.recorded_original(copy, "tampered")


@pytest.mark.parametrize(
    "rel", ["original/outcome.json", "original/checks/split_integrity.json",
            "agent_log.jsonl", "original/candidate.json"],
)  # fmt: skip
def test_a_changed_recorded_original_is_refused(tmp_path, rel):
    provider = H.live6_provider()
    store = H.FakeReservations(provider=provider)
    result, _ = hosted_run(tmp_path, provider, store, original=tamper(tmp_path, rel))
    assert result.terminal_state == ctl.ERROR
    assert result.reason.startswith("recorded_original_changed: evidence changed")
    assert (
        provider.requests == [] and store.calls == []
    )  # nothing sent, nothing reserved
    assert result.report["proposals"] == []


def test_a_recorded_original_of_other_code_is_refused(tmp_path):
    provider = H.live6_provider()
    other = H.ROOT / "benchmarks" / "t01" / "s02_clean"
    with deny_network():
        result = ctl.run_agent(
            other, tmp_path / "runs", H.client(provider), H.SpyApprover(),
            original=bundle.live_original(), live_authorized=True, spend=H.decided_limits(),
            hosted=True, reservations=H.FakeReservations(),
        )  # fmt: skip
    assert result.terminal_state == ctl.ERROR
    assert result.reason.startswith("recorded_original_mismatch")
    assert provider.requests == []


def test_a_store_refusal_sends_nothing(tmp_path):
    provider = H.live6_provider()
    store = H.FakeReservations(refuse_at=1, provider=provider)
    result, _ = hosted_run(tmp_path, provider, store)
    assert result.terminal_state == ctl.BUDGET_EXHAUSTED
    assert result.reason.startswith("hosted_budget: public_daily")
    assert provider.posts() == []
    assert result.report["budget"]["used"]["attempts"] == 0  # not an attempt
    assert store.names() == ["reserve"]


def test_a_refusal_mid_session_keeps_the_completed_findings(tmp_path):
    provider = H.live6_provider()
    store = H.FakeReservations(refuse_at=3, provider=provider)
    result, _ = hosted_run(tmp_path, provider, store)
    assert result.terminal_state == ctl.BUDGET_EXHAUSTED
    assert len(provider.posts()) == 2
    assert result.report["scientific_outcomes"]["original"] == "VIOLATION_FOUND"


@pytest.mark.parametrize("stage", ["reserve", "dispatched"])
@pytest.mark.parametrize("error", [RuntimeError, OSError, TimeoutError])
def test_a_store_failure_before_sending_sends_nothing(tmp_path, stage, error):
    provider = H.live6_provider()
    store = H.FakeReservations(fail={stage: error}, provider=provider)
    result, _ = hosted_run(tmp_path, provider, store)
    assert result.terminal_state == ctl.ERROR
    assert result.reason.startswith("hosted_store_unavailable")
    assert provider.posts() == []
    if stage == "dispatched":  # the reservation is given back; it was never sent
        assert store.names() == ["reserve", "dispatched", "release"]


def test_a_settle_failure_keeps_the_amount_held_and_is_recorded(tmp_path):
    provider = H.live6_provider()
    store = H.FakeReservations(fail={"settle": RuntimeError}, provider=provider)
    result, _ = hosted_run(tmp_path, provider, store)
    events = [e for e in log_events(result) if e["event"] == "hosted_budget"]
    assert any(e["action"] == "store_error" for e in events)
    assert result.terminal_state == ctl.REPORT


def test_unknown_usage_is_held(tmp_path):
    replies = [H.completion(c, usage=None) for c in [*H.LIVE6_REPLIES, H.FINISH]]
    provider = H.Provider(replies)
    _, store = hosted_run(tmp_path, provider)
    assert "settle" not in store.names()
    assert store.names().count("hold") == 4


def test_a_timeout_is_held_not_released(tmp_path):
    provider = H.Provider([httpx2.ReadTimeout, httpx2.ReadTimeout])
    result, store = hosted_run(tmp_path, provider)
    assert result.terminal_state == ctl.ERROR
    assert store.names() == ["reserve", "dispatched", "hold"] * 2
    assert "release" not in store.names()


def test_hosted_mode_arguments_are_checked(tmp_path):
    provider = H.live6_provider()
    live = H.client(provider)
    common = {"live_authorized": True, "spend": H.decided_limits()}
    with pytest.raises(ValueError, match="recorded original"):
        ctl.run_agent(H.S01, tmp_path, live, hosted=True,
                      reservations=H.FakeReservations(), **common)  # fmt: skip
    with pytest.raises(LiveModeUnavailable, match="budget store"):
        ctl.run_agent(H.S01, tmp_path, live, hosted=True,
                      original=bundle.live_original(), **common)  # fmt: skip
    with pytest.raises(ValueError, match="NotExecutedHere"):
        ctl.run_agent(H.S01, tmp_path, live, hosted=True, executor=lambda *a, **k: None,
                      original=bundle.live_original(),
                      reservations=H.FakeReservations(), **common)  # fmt: skip
    with pytest.raises(ValueError, match="hosted mode only"):
        ctl.run_agent(H.S01, tmp_path, live, executor=ctl.NotExecutedHere(), **common)
    with pytest.raises(ValueError, match="hosted mode only"):
        ctl.run_agent(
            H.S01, tmp_path, live, reservations=H.FakeReservations(), **common
        )
    fixture = FixtureClient("t12", [])
    with pytest.raises(ValueError, match="live client"):
        ctl.run_agent(H.S01, tmp_path, fixture, hosted=True, env={},
                      original=bundle.live_original(),
                      reservations=H.FakeReservations())  # fmt: skip
    assert provider.requests == [] and not any(Path(tmp_path).iterdir())


def test_not_executed_here_never_executes():
    with pytest.raises(AssertionError):
        ctl.NotExecutedHere()(None, None, None, None)


def test_a_local_run_has_no_hosted_labels(tmp_path):
    """The local paths are unchanged: no hosted section, banner or proposal outcome."""

    report = H.local_fixture_run(tmp_path)
    assert "hosted" not in report
    assert not report["banner"].startswith("HOSTED")
    assert all(p["outcome"] != "not_executed_here" for p in report["proposals"])
    assert "recorded" not in report["comparison"]["original"]
