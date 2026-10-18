"""T-06 slice 4e, offline: an optional bounded rationale on every action, and one corrective turn
for a reply that hit the output limit before writing anything.

Live run 3b (`runs/live3b/agent-s01_faulty-7de5564eab88/`) ended ERROR: its second reply was
valid JSON for `list_project_files` plus a `rationale` (then an undeclared field, so `schema`),
and its third hit the 8,000-token output limit with no content (`incomplete`). Here a rationale
is accepted on every action, recorded as model-written text and never changes what the action
does; an empty `length` reply gets the one corrective turn (`incomplete_length`). Validation is
otherwise exact: other undeclared fields, a null rationale and an over-long one are rejected, a
`length` reply with content still ends the run, and so does every other metadata failure.

Fixture replies, or the production client over an `httpx2.MockTransport` under the network
guard: no real request is made. The original is the test-only host-fixture baseline of the
allowlisted s01 fixture (the Docker replay is in tests/integration/test_agent_fixture_docker.py).
"""

import dataclasses
import importlib.util
import json
from pathlib import Path

import pytest

from atlas.agent import budget as budget_module
from atlas.agent import controller as ctl
from atlas.agent.client import FixtureClient
from atlas.agent.schemas import (
    MAX_TEXT_CHARS,
    ReplyRejected,
    parse_reply,
    schema_text,
)


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name.removesuffix(".py"), Path(__file__).with_name(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _load("test_agent_slice3.py")
S01, FIX = S.S01, S.FIX
FINISH = S.FINISH
READ = S.act("read_project_file", path="evaluate.py")
NEW_SOURCE = S.act(
    "propose_patch", new_source=FIX, rationale="fold-local, grouped folds"
)

# Live run 3b's first two replies, byte for byte (`replies/a1.txt`, `replies/a2.txt`).
LIVE3B_A1 = '\n{\n    "action": {\n        "tool": "read_project_file",\n        "path": "evaluate.py"\n    }\n}'  # fmt: skip
LIVE3B_A2_RATIONALE = (
    "Need to see what other files exist (e.g., data, metadata) to understand column names "
    "and structure before proposing a patch."
)
LIVE3B_A2 = '\n{\n  "action": {\n    "tool": "list_project_files",\n    "rationale": "' + LIVE3B_A2_RATIONALE + '"\n  }\n}'  # fmt: skip

# A reply that hit the output limit before any content was written.
EMPTY_LENGTH = {"content": None, "finish_reason": "length"}
EXPLANATION = (
    "The reply hit the output limit before any action was written. Reason briefly and reply "
    "with one short JSON object."
)

ACTIONS = {
    "list_project_files": {},
    "read_project_file": {"path": "evaluate.py"},
    "inspect_evidence": {"check": "split_integrity"},
    "propose_patch": {"new_source": "x = 1\n"},
    "finish": {"summary": "done"},
}


@pytest.fixture(autouse=True)
def host_fixture_baseline(monkeypatch):
    monkeypatch.setattr(ctl, "docker_original", S.host_fixture_original)


def run(tmp_path, replies, client_class=FixtureClient):
    """`replies`: reply strings, or full fixture entries (dicts)."""
    script = [r if isinstance(r, dict) else {"content": r} for r in replies]
    client = client_class("s4e", script)
    executor = S.RecordingExecutor()
    result = ctl.run_agent(
        S01, tmp_path / "runs", client, S.ApproveExactly(), executor=executor, env={}
    )
    return result, client, executor


def events(result, kind=None) -> list[dict]:
    lines = (
        (result.run_dir / "agent_log.jsonl").read_text(encoding="utf-8").splitlines()
    )
    entries = [json.loads(line) for line in lines]
    return [e for e in entries if kind is None or e["event"] == kind]


def corrections(request) -> list[dict]:
    (user,) = [m for m in request.messages if m["role"] == "user"]
    history = json.loads(user["content"])["history"]
    return [h for h in history if h["tool"] == ctl.CORRECTION_TOOL]


def action(tool, **fields) -> str:
    return json.dumps({"action": {"tool": tool, **ACTIONS[tool], **fields}})


# =============================================================================================
# 1. The rationale: optional on every action, bounded, never null, never another field
# =============================================================================================


@pytest.mark.parametrize("tool", list(ACTIONS))
def test_a_rationale_is_accepted_on_every_action(tool):
    parsed = parse_reply(action(tool, rationale="because")).action
    assert parsed.tool == tool and parsed.rationale == "because"


@pytest.mark.parametrize("tool", [t for t in ACTIONS if t != "propose_patch"])
def test_the_rationale_is_optional_except_on_propose_patch(tool):
    assert parse_reply(action(tool)).action.rationale is None
    with pytest.raises(ReplyRejected) as info:
        parse_reply(action("propose_patch"))
    assert info.value.code == "schema"


@pytest.mark.parametrize("tool", list(ACTIONS))
@pytest.mark.parametrize(
    "fields",
    [
        {"rationale": "r" * (MAX_TEXT_CHARS + 1)},
        {"rationale": None},
        {"rationale": 7},
        {"rationale": ["r"]},
        {"rationale": "r", "reason": "r"},
        {"rationale": "r", "approved": True},
    ],
    ids=["over_bound", "null", "number", "list", "other_field", "approval_field"],
)
def test_an_invalid_rationale_or_any_other_field_is_still_rejected(tool, fields):
    with pytest.raises(ReplyRejected) as info:
        parse_reply(action(tool, **fields))
    assert info.value.code == "schema"


@pytest.mark.parametrize("tool", list(ACTIONS))
def test_a_rationale_at_the_bound_is_accepted(tool):
    text = "r" * MAX_TEXT_CHARS
    assert parse_reply(action(tool, rationale=text)).action.rationale == text


def test_the_shown_schema_offers_an_optional_non_null_rationale_on_every_action():
    schema = json.loads(schema_text())
    defs = {d["properties"]["tool"]["const"]: d for d in schema["$defs"].values()}
    assert set(defs) == set(ACTIONS)
    for tool, definition in defs.items():
        prop = definition["properties"]["rationale"]
        assert prop == {
            "maxLength": MAX_TEXT_CHARS,
            "title": "Rationale",
            "type": "string",
        }
        assert "null" not in json.dumps(prop) and "default" not in prop
        required = "rationale" in definition["required"]
        assert required is (tool == "propose_patch")
        assert definition["additionalProperties"] is False


def test_a_rationale_is_recorded_as_model_written_and_changes_nothing(tmp_path):
    plain, _, _ = run(tmp_path / "a", [action("list_project_files"), READ, FINISH])
    reasoned, _, _ = run(
        tmp_path / "b",
        [
            action("list_project_files", rationale="LIST-WHY"),
            action("read_project_file", rationale="READ-WHY"),
            action("finish", rationale="FINISH-WHY"),
        ],
    )
    assert plain.terminal_state == reasoned.terminal_state == ctl.REPORT
    # The same tools ran with the same arguments and results; the rationale is not an argument.
    tools = [(e["tool"], e["args"], e["result_sha256"]) for e in events(plain, "tool")]
    assert tools == [
        (e["tool"], e["args"], e["result_sha256"]) for e in events(reasoned, "tool")
    ]
    assert all("rationale" not in e["args"] for e in events(reasoned, "tool"))
    label = "model-written text; not evidence and not an outcome"
    assert plain.report["model_text"] == [
        {"kind": "finish_summary", "text": "done", "label": label}
    ]
    assert reasoned.report["model_text"] == [
        {"kind": "action_rationale", "tool": "list_project_files", "text": "LIST-WHY", "label": label},
        {"kind": "action_rationale", "tool": "read_project_file", "text": "READ-WHY", "label": label},
        {"kind": "action_rationale", "tool": "finish", "text": "FINISH-WHY", "label": label},
        {"kind": "finish_summary", "text": "done", "label": label},
    ]  # fmt: skip


def test_a_patch_rationale_is_recorded_once(tmp_path):
    result, _, executor = run(tmp_path, [NEW_SOURCE, FINISH])
    assert result.terminal_state == ctl.REPORT and len(executor.calls) == 1
    kinds = [t["kind"] for t in result.report["model_text"]]
    assert kinds == ["patch_rationale", "finish_summary"]


# =============================================================================================
# 2. Live run 3b replayed
# =============================================================================================


def test_the_live_run_3b_replies_are_now_accepted_and_the_run_continues(tmp_path):
    result, client, executor = run(tmp_path, [LIVE3B_A1, LIVE3B_A2, NEW_SOURCE, FINISH])
    assert result.terminal_state == ctl.REPORT, result.reason
    assert len(client.requests) == 4 and len(executor.calls) == 1
    assert [a["result"] for a in events(result, "model_attempt")] == ["ok"] * 4
    assert [e["tool"] for e in events(result, "tool")] == [
        "read_project_file",
        "list_project_files",
        "propose_patch",
        "evaluate_candidate",
    ]
    assert result.report["schema_failures"] == []
    assert (result.run_dir / "replies" / "a2.txt").read_bytes() == LIVE3B_A2.encode()
    assert result.report["model_text"][0] == {
        "kind": "action_rationale",
        "tool": "list_project_files",
        "text": LIVE3B_A2_RATIONALE,
        "label": "model-written text; not evidence and not an outcome",
    }
    assert result.report["proposals"][0]["outcome"] == "executed"


# =============================================================================================
# 3. An empty reply cut off by the output limit: one corrective turn
# =============================================================================================


@pytest.mark.parametrize("content", [None, "", " \n "], ids=["none", "empty", "blank"])
def test_an_empty_length_reply_is_corrected_once_and_the_run_continues(
    tmp_path, content
):
    entry = {"content": content, "finish_reason": "length"}
    result, client, executor = run(tmp_path, [entry, NEW_SOURCE, FINISH])
    assert result.terminal_state == ctl.REPORT, result.reason
    assert len(client.requests) == 3 and len(executor.calls) == 1
    assert corrections(client.requests[0]) == []
    (fix,) = corrections(client.requests[1])
    assert fix["args"] == {"attempt": 1}
    assert fix["result"]["schema_failure"] == "incomplete_length"
    assert fix["result"]["explanation"] == EXPLANATION
    assert len(fix["result"]["parser_message"]) <= ctl.MAX_PARSER_MESSAGE_CHARS
    assert result.report["schema_failures"] == [
        {"attempt": 1, "code": "incomplete_length", "corrected": True}
    ]
    assert (
        "1 reply failed validation; 1 corrected on the next turn"
        in result.report["limitations"]
    )
    attempts = events(result, "model_attempt")
    assert attempts[0]["schema_failure"] == "incomplete_length"
    assert attempts[0]["finish_reason"] == "length"


def test_the_incomplete_length_explanation_is_fixed():
    assert ctl.CORRECTION_EXPLANATIONS["incomplete_length"] == EXPLANATION
    assert "incomplete" not in ctl.CORRECTION_EXPLANATIONS
    assert "mislabelled" not in ctl.CORRECTION_EXPLANATIONS


def test_two_empty_length_replies_in_a_row_end_the_run(tmp_path):
    result, client, executor = run(tmp_path, [EMPTY_LENGTH, EMPTY_LENGTH, READ, FINISH])
    assert (result.terminal_state, result.reason) == (
        ctl.ERROR,
        "schema_failure: incomplete_length",
    )
    assert len(client.requests) == 2 and executor.calls == []
    assert [f["corrected"] for f in result.report["schema_failures"]] == [False, False]
    assert result.report["scientific_outcomes"]["original"] == "VIOLATION_FOUND"


def test_a_schema_failure_then_an_empty_length_reply_is_consecutive(tmp_path):
    result, client, _ = run(tmp_path, ["prose", EMPTY_LENGTH, READ, FINISH])
    assert (result.terminal_state, result.reason) == (
        ctl.ERROR,
        "schema_failure: incomplete_length",
    )
    assert len(client.requests) == 2


def test_an_empty_length_reply_on_the_final_attempt_ends_the_run(tmp_path):
    result, client, _ = run(tmp_path, [READ] * 5 + [EMPTY_LENGTH, FINISH])
    assert (result.terminal_state, result.reason) == (
        ctl.ERROR,
        "schema_failure: incomplete_length",
    )
    assert len(client.requests) == 6
    assert result.report["budget"]["used"]["attempts"] == 6
    assert events(result, "correction") == []


def test_a_length_reply_with_content_still_ends_the_run(tmp_path):
    """Unchanged: a reply that was cut off after writing something is not parsed or corrected,
    even when what it wrote happens to be a valid action."""
    for name, content in (("valid", READ), ("partial", READ[:20])):
        entry = {"content": content, "finish_reason": "length"}
        result, client, executor = run(tmp_path / name, [entry, FINISH])
        assert (result.terminal_state, result.reason) == (
            ctl.ERROR,
            "schema_failure: incomplete",
        )
        assert len(client.requests) == 1 and executor.calls == []
        assert events(result, "correction") == []
        assert (result.run_dir / "replies" / "a1.txt").read_bytes() == content.encode()


@pytest.mark.parametrize("finish_reason", ["content_filter", None, "tool_calls"])
def test_other_unfinished_replies_still_end_the_run_at_once(tmp_path, finish_reason):
    entry = {"content": None, "finish_reason": finish_reason}
    result, client, _ = run(tmp_path, [entry, FINISH])
    assert (result.terminal_state, result.reason) == (
        ctl.ERROR,
        "schema_failure: incomplete",
    )
    assert len(client.requests) == 1 and events(result, "correction") == []


class OtherModel(FixtureClient):
    """Every reply claims a different model than the configured one."""

    def complete(self, request):
        reply = super().complete(request)
        return dataclasses.replace(reply, model_id="fixture:other")


def test_a_mislabelled_empty_length_reply_ends_the_run_at_once(tmp_path):
    result, client, _ = run(tmp_path, [EMPTY_LENGTH, READ, FINISH], OtherModel)
    assert (result.terminal_state, result.reason) == (
        ctl.ERROR,
        "schema_failure: mislabelled",
    )
    assert len(client.requests) == 1 and events(result, "correction") == []


# =============================================================================================
# 4. The budget: corrective turns stay ordinary attempts
# =============================================================================================


def test_empty_length_corrections_count_and_six_requests_is_the_most(tmp_path):
    script = [EMPTY_LENGTH, READ, EMPTY_LENGTH, READ, EMPTY_LENGTH, READ, READ, FINISH]
    result, client, _ = run(tmp_path, script)
    assert result.terminal_state == ctl.BUDGET_EXHAUSTED
    assert len(client.requests) == 6
    assert result.report["budget"]["used"]["attempts"] == 6
    assert [f["code"] for f in result.report["schema_failures"]] == [
        "incomplete_length"
    ] * 3


def test_each_length_correction_is_reserved_before_it_is_dispatched(
    tmp_path, monkeypatch
):
    order = []
    reserve_attempt = budget_module.Budget.reserve_attempt
    ledger_reserve = budget_module.CostLedger.reserve

    def attempt(self, retry):
        n = reserve_attempt(self, retry)
        order.append(("attempt", n))
        return n

    def ledger(self, n):
        order.append(("ledger", n))
        return ledger_reserve(self, n)

    monkeypatch.setattr(budget_module.Budget, "reserve_attempt", attempt)
    monkeypatch.setattr(budget_module.CostLedger, "reserve", ledger)

    class Recording(FixtureClient):
        def complete(self, request):
            order.append(("dispatch", len(self.requests) + 1))
            return super().complete(request)

    result, _, _ = run(tmp_path, [EMPTY_LENGTH, READ, FINISH], Recording)
    assert result.terminal_state == ctl.REPORT
    expected = []
    for n in (1, 2, 3):
        expected += [("attempt", n), ("ledger", n), ("dispatch", n)]
    assert order == expected


def test_a_live_length_correction_keeps_the_decided_request_body(tmp_path):
    """Over the production client: the corrective request is the same body as any other
    (model, messages, max_completion_tokens, n), with no reasoning-control parameter."""
    result, transport = S.live_run(
        tmp_path,
        [
            (200, S.ok_body(None, S.USAGE, finish="length")),
            (200, S.ok_body(LIVE3B_A2, S.USAGE)),
            (200, S.ok_body(FINISH, S.USAGE)),
        ],
        S.ApproveExactly(),
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    assert len(transport.requests) == 3
    bodies = [json.loads(r.content) for r in transport.requests]
    for body in bodies:
        assert set(body) == {"model", "messages", "max_completion_tokens", "n"}
        assert (body["max_completion_tokens"], body["n"]) == (8000, 1)
    assert "incomplete_length" in bodies[1]["messages"][1]["content"]
    assert result.report["schema_failures"] == [
        {"attempt": 1, "code": "incomplete_length", "corrected": True}
    ]


# =============================================================================================
# 5. The prompt
# =============================================================================================


def test_the_prompt_asks_for_brief_reasoning_and_a_short_reply():
    prompt = ctl.SYSTEM_PROMPT
    assert "brief" in prompt and "short" in prompt
    for hint in ("s01", "evaluate.py", "SelectKBest", "GroupKFold", "subject", "fold"):
        assert hint not in prompt  # generic: no benchmark hints
