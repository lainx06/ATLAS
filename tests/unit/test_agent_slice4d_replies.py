"""T-06 slice 4d, offline: persisted raw replies, one corrective turn after a schema failure,
and the stricter reply prompt.

Live run 2 (`runs/live2/agent-s01_faulty-93583d9e48b5/`) ended ERROR on one `not_json` reply
whose text was never stored. Here every reply is written to `<run>/replies/a<N>.txt` before it
is parsed, and a schema failure from `parse_reply` gets one corrective turn within the
6-request budget. `parse_reply` is unchanged: the reply text is never altered, unfenced or
re-parsed leniently.

Fixture replies, or the production client over an `httpx2.MockTransport` under the network
guard: no real request is made. The original is the test-only host-fixture baseline of the
allowlisted s01 fixture (the Docker version is in tests/integration/test_agent_fixture_docker.py).
"""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from atlas.agent import budget as budget_module
from atlas.agent import controller as ctl
from atlas.agent.client import FixtureClient
from atlas.agent.schemas import MAX_REPLY_BYTES, ReplyRejected, parse_reply


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name.removesuffix(".py"), Path(__file__).with_name(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _load("test_agent_slice3.py")
S01, FIX, KEY = S.S01, S.FIX, S.KEY
FINISH = S.FINISH
READ = S.act("read_project_file", path="evaluate.py")
NEW_SOURCE = S.act(
    "propose_patch", new_source=FIX, rationale="fold-local, grouped folds"
)

# Three malformed replies, each with a marker that must never reach a later request.
FENCED = "```json\n" + S.act("read_project_file", path="FENCE-MARKER.py") + "\n```"
PROSE = "PROSE-MARKER: here is my action. " + READ
UNESCAPED = (  # the complete file pasted raw into the JSON string: real newlines and quotes
    '{"action": {"tool": "propose_patch", "new_source": "# NEWLINE-MARKER\n'
    + FIX
    + '", "rationale": "r"}}'
)
BAD = {"fenced": FENCED, "prose_before": PROSE, "unescaped_newline": UNESCAPED}
MARKERS = ("FENCE-MARKER", "PROSE-MARKER", "NEWLINE-MARKER")


@pytest.fixture(autouse=True)
def host_fixture_baseline(monkeypatch):
    monkeypatch.setattr(ctl, "docker_original", S.host_fixture_original)


def run(tmp_path, replies, approver=None, budget=None):
    """`replies`: reply strings, or full fixture entries (dicts)."""
    script = [r if isinstance(r, dict) else {"content": r} for r in replies]
    client = FixtureClient("s4d", script)
    executor = S.RecordingExecutor()
    result = ctl.run_agent(
        S01,
        tmp_path / "runs",
        client,
        approver or S.ApproveExactly(),
        executor=executor,
        budget=budget,
        env={},
    )
    return result, client, executor


def events(result, kind=None) -> list[dict]:
    lines = (
        (result.run_dir / "agent_log.jsonl").read_text(encoding="utf-8").splitlines()
    )
    entries = [json.loads(line) for line in lines]
    return [e for e in entries if kind is None or e["event"] == kind]


def user_message(request) -> dict:
    (user,) = [m for m in request.messages if m["role"] == "user"]
    return json.loads(user["content"])


def corrections(request) -> list[dict]:
    return [
        h for h in user_message(request)["history"] if h["tool"] == ctl.CORRECTION_TOOL
    ]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# =============================================================================================
# 1. A schema failure, persisted byte for byte, then one bounded correction
# =============================================================================================


@pytest.mark.parametrize("bad", list(BAD.values()), ids=list(BAD))
def test_a_malformed_reply_is_stored_corrected_once_and_the_run_continues(
    tmp_path, bad
):
    with pytest.raises(ReplyRejected) as info:  # unchanged parse_reply behaviour
        parse_reply(bad)
    assert info.value.code == "not_json"

    result, client, executor = run(tmp_path, [bad, NEW_SOURCE, FINISH])

    assert result.terminal_state == ctl.REPORT, result.reason
    assert len(client.requests) == 3 and len(executor.calls) == 1
    # The raw reply, exactly as received.
    stored = result.run_dir / "replies" / "a1.txt"
    assert stored.read_bytes() == bad.encode("utf-8")
    # The next request carries the bounded correction, and nothing of the reply.
    assert corrections(client.requests[0]) == []
    (fix,) = corrections(client.requests[1])
    assert fix["args"] == {"attempt": 1}
    assert fix["result"]["schema_failure"] == "not_json"
    assert fix["result"]["explanation"] == ctl.CORRECTION_EXPLANATIONS["not_json"]
    assert fix["result"]["parser_message"] == str(info.value)
    second = json.dumps(client.requests[1].messages)
    assert not any(marker in second for marker in MARKERS)
    # Recorded: the failure, its correction, and the limitation line.
    report = result.report
    assert report["schema_failures"] == [
        {"attempt": 1, "code": "not_json", "corrected": True}
    ]
    assert (
        "1 reply failed validation; 1 corrected on the next turn"
        in report["limitations"]
    )
    (correction,) = events(result, "correction")
    assert (correction["attempt"], correction["schema_failure"]) == (1, "not_json")
    attempts = events(result, "model_attempt")
    assert [a["result"] for a in attempts] == ["schema_failure", "ok", "ok"]
    assert report["proposals"][0]["outcome"] == "executed"


def test_every_reply_file_matches_the_log_and_the_report(tmp_path):
    result, _, _ = run(tmp_path, [PROSE, READ, FINISH])
    attempts = events(result, "model_attempt")
    replies = result.report["replies"]
    assert [r["attempt"] for r in replies] == [1, 2, 3]
    for logged, reported in zip(attempts, replies, strict=True):
        data = (result.run_dir / reported["path"]).read_bytes()
        assert reported["path"] == f"replies/a{reported['attempt']}.txt"
        assert logged["reply_sha256"] == reported["sha256"] == sha(data)
        assert logged["reply_bytes"] == reported["bytes"] == len(data)
        assert logged["reply_truncated"] is reported["truncated"] is False
        assert reported["label"] == ctl.REPLY_LABEL
    assert ctl.REPLY_LABEL == "model-written (untrusted); never evidence"
    assert (result.run_dir / "replies" / "a3.txt").read_bytes() == FINISH.encode()


def test_the_reply_is_written_before_it_is_parsed(tmp_path, monkeypatch):
    seen = []
    real = ctl.parse_reply

    def parse(content):
        run_dir = next((tmp_path / "runs").glob("agent-*"))
        files = sorted(p.name for p in (run_dir / "replies").glob("*.txt"))
        seen.append(files)
        return real(content)

    monkeypatch.setattr(ctl, "parse_reply", parse)
    result, _, _ = run(tmp_path, [READ, FINISH])
    assert result.terminal_state == ctl.REPORT
    assert seen == [["a1.txt"], ["a1.txt", "a2.txt"]]


def test_an_oversized_reply_is_stored_truncated_and_marked(tmp_path):
    big = "x" * (MAX_REPLY_BYTES + 10)
    result, _, _ = run(tmp_path, [big, FINISH])
    assert result.terminal_state == ctl.REPORT
    data = (result.run_dir / "replies" / "a1.txt").read_bytes()
    assert data == big.encode()[:MAX_REPLY_BYTES]
    first = result.report["replies"][0]
    assert first["truncated"] is True and first["bytes"] == MAX_REPLY_BYTES
    assert first["received_bytes"] == MAX_REPLY_BYTES + 10
    assert result.report["schema_failures"][0]["code"] == "too_large"


def test_a_reply_without_text_has_no_file_and_is_corrected(tmp_path):
    result, client, _ = run(tmp_path, [{"content": None}, FINISH])
    assert result.terminal_state == ctl.REPORT
    assert not (result.run_dir / "replies" / "a1.txt").exists()
    assert result.report["replies"][0]["path"] is None
    (fix,) = corrections(client.requests[1])
    assert fix["result"]["schema_failure"] == "missing_content"


# =============================================================================================
# 2. When the run still ends: consecutive failures, the final attempt
# =============================================================================================


def test_three_consecutive_schema_failures_end_the_run(tmp_path):
    """Since slice 4g two consecutive failures are corrected; the third ends the run."""
    script = [READ, PROSE, FENCED, UNESCAPED, NEW_SOURCE, FINISH]
    result, client, executor = run(tmp_path, script)
    assert (result.terminal_state, result.reason) == (
        ctl.ERROR,
        "schema_failure: not_json",
    )
    assert len(client.requests) == 4 and executor.calls == []
    assert result.report["schema_failures"] == [
        {"attempt": 2, "code": "not_json", "corrected": False},
        {"attempt": 3, "code": "not_json", "corrected": False},
        {"attempt": 4, "code": "not_json", "corrected": False},
    ]
    assert (
        "3 replies failed validation; 0 corrected on the next turn"
        in (result.report["limitations"])
    )
    assert result.report["scientific_outcomes"]["original"] == "VIOLATION_FOUND"


def test_a_schema_failure_on_the_final_attempt_ends_the_run(tmp_path):
    result, client, _ = run(tmp_path, [READ] * 5 + [PROSE, FINISH])
    assert (result.terminal_state, result.reason) == (
        ctl.ERROR,
        "schema_failure: not_json",
    )
    assert (
        len(client.requests) == 6 and result.report["budget"]["used"]["attempts"] == 6
    )
    assert events(result, "correction") == []


def test_failure_valid_failure_is_not_consecutive(tmp_path):
    result, client, _ = run(tmp_path, [PROSE, READ, FENCED, FINISH])
    assert result.terminal_state == ctl.REPORT, result.reason
    assert len(client.requests) == 4
    assert [f["corrected"] for f in result.report["schema_failures"]] == [True, True]
    assert (
        "2 replies failed validation; 2 corrected on the next turn"
        in (result.report["limitations"])
    )


@pytest.mark.parametrize(
    "entry, code",
    [
        ({"content": READ, "finish_reason": "length"}, "incomplete"),
    ],
    ids=["incomplete"],
)
def test_reply_metadata_failures_still_end_the_run_at_once(tmp_path, entry, code):
    """Control: only parse_reply's content failures are corrected. A reply that did not end
    normally is not a formatting problem the model can fix by being told."""
    result, client, _ = run(tmp_path, [entry, FINISH])
    assert (result.terminal_state, result.reason) == (
        ctl.ERROR,
        f"schema_failure: {code}",
    )
    assert len(client.requests) == 1 and events(result, "correction") == []


# =============================================================================================
# 3. The budget: corrective turns are attempts like any other
# =============================================================================================


def test_corrective_turns_count_and_six_requests_is_the_most(tmp_path):
    script = [PROSE, READ, FENCED, READ, PROSE, READ, READ, FINISH]
    result, client, _ = run(tmp_path, script)
    assert result.terminal_state == ctl.BUDGET_EXHAUSTED
    assert len(client.requests) == 6
    assert result.report["budget"]["used"]["attempts"] == 6
    assert len(result.report["schema_failures"]) == 3


def test_each_corrective_turn_is_reserved_before_it_is_dispatched(
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

    client = Recording("s4d", [{"content": r} for r in (PROSE, READ, FINISH)])
    result = ctl.run_agent(
        S01, tmp_path / "runs", client, S.ApproveExactly(),
        executor=S.RecordingExecutor(), env={},
    )  # fmt: skip
    assert result.terminal_state == ctl.REPORT
    expected = []
    for n in (1, 2, 3):
        expected += [("attempt", n), ("ledger", n), ("dispatch", n)]
    assert order == expected


# =============================================================================================
# 4. What the correction may contain, and what a stored reply never contains
# =============================================================================================


def test_the_correction_quotes_at_most_200_characters_of_the_parser_message(tmp_path):
    long_key = "K" * 300
    bad = (
        '{"action": {"tool": "finish", "summary": "SUMMARY-MARKER"}, '
        f'"{long_key}": 1, "{long_key}": 2}}'
    )
    with pytest.raises(ReplyRejected) as info:
        parse_reply(bad)
    assert info.value.code == "duplicate_key" and len(str(info.value)) > 200

    _, client, _ = run(tmp_path, [bad, FINISH])
    (fix,) = corrections(client.requests[1])
    assert fix["result"]["parser_message"] == str(info.value)[:200]
    assert set(fix["result"]) == {
        "schema_failure",
        "explanation",
        "parser_message",
        "note",
    }
    shown = json.dumps(fix)
    assert "SUMMARY-MARKER" not in shown and long_key not in shown
    assert len(shown) <= 1000


def test_every_parse_reply_code_has_a_fixed_explanation():
    codes = {
        "missing_content", "too_large", "empty", "not_json", "duplicate_key",
        "not_an_object", "schema",
    }  # fmt: skip
    # Plus one reply-metadata code since slice 4e: an empty reply cut off by the output limit.
    assert set(ctl.CORRECTION_EXPLANATIONS) == codes | {"incomplete_length"}
    assert all(0 < len(text) <= 300 for text in ctl.CORRECTION_EXPLANATIONS.values())


def test_a_live_run_stores_replies_without_the_key_or_headers(tmp_path):
    result, transport = S.live_run(
        tmp_path,
        [(200, S.ok_body(PROSE, S.USAGE)), (200, S.ok_body(FINISH, S.USAGE))],
        S.ApproveExactly(),
    )
    assert result.terminal_state == ctl.REPORT and len(transport.requests) == 2
    folder = result.run_dir / "replies"
    assert sorted(p.name for p in folder.iterdir()) == ["a1.txt", "a2.txt"]
    assert (folder / "a1.txt").read_bytes() == PROSE.encode()
    for path in folder.iterdir():
        text = path.read_text(encoding="utf-8")
        assert KEY not in text and "Authorization" not in text and "req-" not in text
    sent = transport.requests[1].content.decode("utf-8")
    assert "PROSE-MARKER" not in sent and KEY not in sent
    assert result.report["replies"][0]["label"] == ctl.REPLY_LABEL


# =============================================================================================
# 5. The prompt
# =============================================================================================


def test_the_prompt_asks_for_one_raw_object_with_a_valid_example():
    prompt = ctl.SYSTEM_PROMPT
    assert ctl.PROMPT_EXAMPLE in prompt
    assert parse_reply(ctl.PROMPT_EXAMPLE).action.tool == "read_project_file"
    assert "code fences" in prompt and "before or after" in prompt
    assert '"diff"' in prompt and '"new_source"' in prompt
    assert "escape" in prompt and "adapter" in prompt
    # Generic: no benchmark hints in the instructions. Since slice 4f the prompt also ends
    # with the adapter reference, whose API names `fold` itself (tested in slice 4f).
    for hint in ("s01", "evaluate.py", "SelectKBest", "GroupKFold", "subject", "fold"):
        assert hint not in ctl.SYSTEM_INSTRUCTIONS


def test_the_prompt_budget_figures_follow_the_new_prompt(tmp_path):
    """The live user-message budget is the decided input estimate minus the system prompt and
    two template allowances; a single tool result gets at most half of it. Derived from the
    prompt and the decided values, never pinned, and checked against the run's own report."""
    decided = budget_module.DECIDED_SLICE4
    overhead = decided["template_overhead_tokens"]
    system = len(ctl.SYSTEM_PROMPT.encode("utf-8"))
    expected = decided["max_input_tokens"] - system - 2 * overhead
    result, _ = S.live_run(
        tmp_path,
        [(200, S.ok_body(FINISH, S.USAGE))],
        S.ApproveExactly(),
        max_input_tokens=decided["max_input_tokens"],
        template_overhead_tokens=overhead,
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    assert result.report["prompt_budget"] == {
        "user_message_bytes": expected,
        "tool_result_chars": min(ctl.MAX_TOOL_RESULT_CHARS, expected // 2),
    }
