"""T-06 slice 4c, offline: full-source proposals, proposal records, the comparison's model label
and per-attempt cost.

Fixture replies, or the production client over an `httpx2.MockTransport` under the network
guard: no real request is made. Docker is faked with the slice 1 harness (the runner's own host
code runs for real); the evidence frames are real adapter output from the trusted host runner
on the allowlisted T-01 fixtures. Every candidate still passes `candidates.validate_diff`,
unchanged. The s01 fixture is a development fixture, not independent benchmark evidence.
"""

import hashlib
import importlib.util
import io
import json
import threading
import time
from decimal import Decimal
from pathlib import Path

import httpx2
import pytest
from pydantic import ValidationError

from atlas.agent import controller as ctl
from atlas.agent import proposals as P
from atlas.agent.approval import TerminalApprover
from atlas.agent.client import FixtureClient
from atlas.agent.network import deny_network
from atlas.agent.report import NO_MODEL, comparison_report
from atlas.agent.schemas import ProposePatch, ReplyRejected, parse_reply, schema_text
from atlas.candidates import MAX_DIFF_BYTES, MAX_ENTRY_BYTES, CandidateRejected
from atlas.contracts import Outcome
from atlas.runner import trusted


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name.removesuffix(".py"), Path(__file__).with_name(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _load("test_agent_slice3.py")
ORIGINAL, FIX, DIFF, S01, S02 = S.ORIGINAL, S.FIX, S.DIFF, S.S01, S.S02
FINISH = S.FINISH
NEW_SOURCE = S.act(
    "propose_patch", new_source=FIX, rationale="fold-local, grouped folds"
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def events(run_dir: Path) -> list[dict]:
    text = (run_dir / "agent_log.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def proposal_events(run_dir: Path) -> list[dict]:
    return [
        e
        for e in events(run_dir)
        if e["event"] == "tool" and e["tool"] == "propose_patch"
    ]


def miscounted(diff: str) -> str:
    """The same diff with its first hunk's new-side line count raised by one."""
    lines = diff.splitlines(True)
    i = next(n for n, line in enumerate(lines) if line.startswith("@@"))
    head, rest = lines[i].split(" @@", 1)
    old, new = head[3:].split(" ")
    start, count = new.split(",")
    lines[i] = f"@@ {old} {start},{int(count) + 1} @@{rest}"
    return "".join(lines)


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
        out[name] = S.H.collected(run, base / f"{name}-out")
    return out


@pytest.fixture
def no_host_runner(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("project code reached the host runner")

    monkeypatch.setattr(trusted, "run_trusted_fixture", refuse)
    monkeypatch.setattr("atlas.audit.run_trusted_fixture", refuse)


def fixture_run(tmp_path, replies, approver=None, executor=None):
    return ctl.run_agent(
        S01,
        tmp_path / "runs",
        FixtureClient("s4c", [{"content": r} for r in replies]),
        approver or S.ApproveExactly(),
        executor=executor,
        env={},
    )


# =============================================================================================
# 1. The reply schema: exactly one of diff or new_source
# =============================================================================================


def patch(**fields) -> str:
    return json.dumps({"action": {"tool": "propose_patch", **fields}})


def test_diff_only_and_new_source_only_are_accepted():
    a = parse_reply(patch(diff=DIFF, rationale="r")).action
    assert (a.diff, a.new_source, a.source_kind) == (DIFF, None, "diff")
    b = parse_reply(patch(new_source=FIX, rationale="r")).action
    assert (b.diff, b.new_source, b.source_kind) == (None, FIX, "new_source")


@pytest.mark.parametrize(
    "fields",
    [
        {"diff": DIFF, "new_source": FIX, "rationale": "r"},
        {"rationale": "r"},
        {"diff": None, "new_source": FIX, "rationale": "r"},
        {"new_source": None, "rationale": "r"},
        {"new_source": FIX, "rationale": "r", "approved": True},
        {"new_source": "", "rationale": "r"},
        {"new_source": FIX},
    ],
    ids=[
        "both",
        "neither",
        "null_diff_beside",
        "null_only",
        "extra",
        "empty",
        "no_why",
    ],
)
def test_anything_but_exactly_one_source_is_a_schema_failure(fields):
    with pytest.raises(ReplyRejected) as info:
        parse_reply(patch(**fields))
    assert info.value.code == "schema"


def test_a_duplicate_key_is_rejected():
    text = (
        '{"action": {"tool": "propose_patch", "new_source": "a\\n", '
        '"new_source": "b\\n", "rationale": "r"}}'
    )
    with pytest.raises(ReplyRejected) as info:
        parse_reply(text)
    assert info.value.code == "duplicate_key"


def test_one_action_per_reply_still_holds():
    two = '{"action": {"tool": "finish", "summary": "s"}, "second": {}}'
    with pytest.raises(ReplyRejected) as info:
        parse_reply(two)
    assert info.value.code == "schema"


def test_an_oversized_new_source_is_rejected():
    # Over the entry-point limit in UTF-8 bytes, though not in characters.
    wide = "é" * (MAX_ENTRY_BYTES // 2 + 1) + "\n"
    assert len(wide) < MAX_ENTRY_BYTES < len(wide.encode("utf-8"))
    with pytest.raises(ValidationError, match="new_source is"):
        ProposePatch.model_validate(
            {"tool": "propose_patch", "new_source": wide, "rationale": "r"}
        )
    with pytest.raises(ValidationError):
        ProposePatch.model_validate(
            {"tool": "propose_patch", "new_source": "x" * (MAX_ENTRY_BYTES + 1)}
        )
    # A whole reply is capped first (MAX_REPLY_BYTES is the tighter bound in practice).
    with pytest.raises(ReplyRejected) as info:
        parse_reply(patch(new_source="x" * (MAX_ENTRY_BYTES + 1), rationale="r"))
    assert info.value.code == "too_large"
    ok = "x" * (MAX_ENTRY_BYTES - 1) + "\n"
    assert (
        ProposePatch.model_validate(
            {"tool": "propose_patch", "new_source": ok, "rationale": "r"}
        ).new_source
        == ok
    )


def shown_schema() -> dict:
    """The propose_patch object exactly as the model is shown it (schema_text)."""
    return json.loads(schema_text())["$defs"]["ProposePatch"]


# The keywords the structural check below understands; the shown schema must use no others,
# so the check is complete for it (jsonschema is not a declared dependency).
CHECKED = {"type", "properties", "required", "additionalProperties", "oneOf", "const",
           "minLength", "maxLength", "title", "description"}  # fmt: skip


def conforms(schema: dict, value) -> bool:
    """A direct structural check of `value` against the keywords in CHECKED."""
    assert set(schema) <= CHECKED, set(schema) - CHECKED
    kind = schema.get("type")
    if kind == "object" and not isinstance(value, dict):
        return False
    if kind == "string" and not isinstance(value, str):
        return False
    if "const" in schema and value != schema["const"]:
        return False
    low, high = schema.get("minLength", 0), schema.get("maxLength")
    if isinstance(value, str) and not low <= len(value) <= (high or len(value)):
        return False
    if isinstance(value, dict):
        if not set(schema.get("required", ())) <= set(value):
            return False
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            return False
        if not all(
            conforms(properties[k], v) for k, v in value.items() if k in properties
        ):
            return False
        if "oneOf" in schema and sum(conforms(b, value) for b in schema["oneOf"]) != 1:
            return False
    return True


def test_the_shown_schema_states_exactly_one_non_null_source():
    schema = shown_schema()
    for name, limit in (("diff", MAX_DIFF_BYTES), ("new_source", MAX_ENTRY_BYTES)):
        prop = schema["properties"][name]
        assert (
            prop["type"] == "string" and "anyOf" not in prop and "default" not in prop
        )
        assert (prop["minLength"], prop["maxLength"]) == (1, limit)
    assert "null" not in json.dumps(schema["properties"])  # no null type or default
    assert schema["oneOf"] == [{"required": ["diff"]}, {"required": ["new_source"]}]
    # A set in JSON Schema; since slice 4e `rationale` is inherited, so it is listed first.
    assert sorted(schema["required"]) == ["rationale", "tool"]
    assert schema["additionalProperties"] is False


SHAPES = {
    "new_source": ({"new_source": "x = 1\n", "rationale": "r"}, True),
    "diff": ({"diff": DIFF, "rationale": "r"}, True),
    "both": ({"diff": DIFF, "new_source": "x = 1\n", "rationale": "r"}, False),
    "neither": ({"rationale": "r"}, False),
    "null_new_source": ({"new_source": None, "rationale": "r"}, False),
    "null_diff_beside": (
        {"diff": None, "new_source": "x = 1\n", "rationale": "r"},
        False,
    ),
    "empty": ({"new_source": "", "rationale": "r"}, False),
    "extra": ({"new_source": "x = 1\n", "rationale": "r", "approved": True}, False),
    "no_rationale": ({"new_source": "x = 1\n"}, False),
}


@pytest.mark.parametrize("name", list(SHAPES))
def test_the_shown_schema_and_the_runtime_agree(name):
    fields, accepted = SHAPES[name]
    action = {"tool": "propose_patch", **fields}
    assert conforms(shown_schema(), action) is accepted
    if accepted:
        assert (
            parse_reply(json.dumps({"action": action})).action.tool == "propose_patch"
        )
    else:
        with pytest.raises(ReplyRejected) as info:
            parse_reply(json.dumps({"action": action}))
        assert info.value.code == "schema"


def test_the_prompt_figures_are_unchanged_by_the_schema_fix():
    """The user-message budget derives from the system prompt only; the reply schema is part
    of the user message and so counts against that budget."""
    system = len(ctl.SYSTEM_PROMPT.encode("utf-8"))
    c, _ = S.client([], max_input_tokens=12_000, template_overhead_tokens=16)
    # Derived from the prompt, not pinned: the prompt changes (slice 4d), the rule does not.
    assert c.user_message_budget(ctl.SYSTEM_PROMPT) == 12_000 - system - 16 - 16
    # 2,915 since slice 4e (an optional rationale on every action); 2,619 at this fix, 2,650
    # before it.
    assert len(schema_text().encode("utf-8")) == 2915


# =============================================================================================
# 2. Diff generation and the newline rule
# =============================================================================================


def test_the_generated_diff_is_the_standard_unified_diff():
    generated = P.source_diff(ORIGINAL, FIX, "evaluate.py")
    assert generated == DIFF  # what difflib gives with a/ and b/ headers
    assert generated.startswith("--- a/evaluate.py\n+++ b/evaluate.py\n@@ ")
    assert P.source_diff(ORIGINAL, FIX, "evaluate.py") == generated  # deterministic


def test_the_newline_rule_never_alters_model_text():
    with pytest.raises(CandidateRejected) as info:
        P.source_diff(ORIGINAL, FIX.rstrip("\n"), "evaluate.py")
    assert info.value.code == "malformed_source"
    for bad in ("\r\n", "\x00"):
        with pytest.raises(CandidateRejected) as info:
            P.source_diff(ORIGINAL, FIX.replace("\n", bad, 1), "evaluate.py")
        assert info.value.code == "malformed_source"
    with pytest.raises(CandidateRejected) as info:
        P.source_diff(ORIGINAL, ORIGINAL, "evaluate.py")
    assert info.value.code == "no_change"


def test_an_original_without_a_final_newline_gets_the_standard_marker():
    generated = P.source_diff("a = 1\nb = 2", "a = 1\nb = 3\n", "m.py")
    assert generated.endswith("-b = 2\n\\ No newline at end of file\n+b = 3\n")


def test_the_detail_is_bounded_and_the_summary_counts_outcomes():
    long = CandidateRejected("malformed_diff", "x" * 500)
    assert P.bounded_detail(long) == "x" * P.DETAIL_CHARS
    assert P.bounded_detail(CandidateRejected("no_change")) is None
    records = [{"outcome": o} for o in ("rejected", "rejected", "declined", "executed")]
    assert (
        P.summary_line(records)
        == "4 proposals: 2 rejected by validation, 1 declined, 1 executed"
    )
    assert (
        P.summary_line([])
        == "0 proposals: 0 rejected by validation, 0 declined, 0 executed"
    )
    assert P.summary_line([{"outcome": "unavailable"}]).endswith(
        ", 1 unavailable (no approval possible)"
    )


# =============================================================================================
# 3. A full-source revision runs end to end
# =============================================================================================


def test_a_new_source_revision_is_validated_shown_executed_and_recorded(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    S.fake_docker(monkeypatch, [evidence["faulty"], evidence["clean"]])
    screen = io.StringIO()
    approver = TerminalApprover(
        S.FakeStdin(["<prefix>", "<prefix>"], out=screen), screen
    )
    result = fixture_run(tmp_path, [NEW_SOURCE, FINISH], approver)
    assert result.terminal_state == ctl.REPORT, result.reason

    # The approval panel shows the diff ATLAS generated, not the raw file.
    shown = screen.getvalue()
    panel = shown[shown.rindex("Proposed diff (untrusted") :]
    assert all(line in panel for line in DIFF.splitlines())

    # validate_diff passed and the candidate executed in (faked) Docker.
    (candidate,) = result.candidates
    assert candidate.execution["status"] == "completed"
    assert candidate.outcome.outcome is Outcome.NO_VIOLATION_FOUND
    assert candidate.diff_sha256 == sha(DIFF.encode("utf-8"))

    report = result.report
    (record,) = report["proposals"]
    assert record["revision"] == 1 and record["source_kind"] == "new_source"
    assert (record["outcome"], record["code"]) == ("executed", None)
    assert record["candidate_hash"] == candidate.candidate_hash
    assert record["execution_status"] == "completed"
    assert record["files_label"] == "model-written (untrusted)"
    assert record["detail_label"] == "validator message; may quote model text"
    run = result.run_dir
    assert (record["diff_path"], record["new_source_path"]) == (
        "proposals/r1.diff",
        "proposals/r1.new_source.py",
    )
    diff_bytes = (run / record["diff_path"]).read_bytes()
    source_bytes = (run / record["new_source_path"]).read_bytes()
    assert diff_bytes == DIFF.encode("utf-8")
    assert source_bytes == FIX.encode("utf-8")
    assert record["diff_sha256"] == sha(diff_bytes) == candidate.diff_sha256
    assert record["new_source_sha256"] == sha(source_bytes)

    (event,) = proposal_events(run)
    assert (event["outcome"], event["code"]) == ("executed", None)
    assert event["args"]["diff_sha256"] == record["diff_sha256"]
    assert (
        "1 proposal: 0 rejected by validation, 0 declined, 1 executed"
        in report["limitations"]
    )
    assert report["comparison"]["model"] == "fixture replies (non-live)"
    assert "full-source" not in ctl.SYSTEM_PROMPT  # generic guidance only
    assert "new_source" in ctl.SYSTEM_PROMPT and "adapter" in ctl.SYSTEM_PROMPT


def test_a_declined_revision_is_recorded_with_the_approvers_reason(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    S.fake_docker(monkeypatch, [evidence["faulty"]])
    screen = io.StringIO()
    approver = TerminalApprover(S.FakeStdin(["<prefix>", "no\n"], out=screen), screen)
    executor = S.RecordingExecutor()
    result = fixture_run(tmp_path, [NEW_SOURCE, FINISH], approver, executor)
    assert result.terminal_state == ctl.REPORT, result.reason
    assert [c.name for c in executor.calls] == ["original"]  # no candidate executed
    assert result.candidates == []
    (record,) = result.report["proposals"]
    assert (record["outcome"], record["code"]) == ("declined", "confirmation_mismatch")
    assert (result.run_dir / "proposals" / "r1.diff").read_text(
        encoding="utf-8"
    ) == DIFF
    (event,) = proposal_events(result.run_dir)
    assert (event["outcome"], event["code"]) == ("declined", "confirmation_mismatch")
    assert (
        "1 proposal: 0 rejected by validation, 1 declined, 0 executed"
        in result.report["limitations"]
    )


@pytest.mark.parametrize("typed", ["<snapshot>", "<SNAPSHOT>"], ids=["lower", "upper"])
def test_the_snapshot_hash_prefix_executes_nothing_at_the_terminal(
    tmp_path, monkeypatch, evidence, no_host_runner, typed
):
    """Combined review 1, F2: typing the shown snapshot hash's prefix declines the revision."""
    S.fake_docker(monkeypatch, [evidence["faulty"]])
    screen = io.StringIO()
    approver = TerminalApprover(S.FakeStdin(["<prefix>", typed], out=screen), screen)
    executor = S.RecordingExecutor()
    result = fixture_run(tmp_path, [NEW_SOURCE, FINISH], approver, executor)
    assert result.terminal_state == ctl.REPORT, result.reason
    assert [c.name for c in executor.calls] == ["original"]  # no candidate executed
    assert result.candidates == []
    (record,) = result.report["proposals"]
    assert (record["outcome"], record["code"]) == ("declined", "confirmation_mismatch")
    assert "Confirmation did not match: NOT approved." in screen.getvalue()


@pytest.mark.parametrize("upper", [False, True], ids=["lower", "upper"])
def test_the_snapshot_hash_prefix_executes_nothing_in_the_browser(
    tmp_path, monkeypatch, evidence, no_host_runner, upper
):
    """The same through the UI's BrowserApprover, answered as the page answers it."""
    from atlas.ui import approver as ch

    S.fake_docker(monkeypatch, [evidence["faulty"]])
    channel = tmp_path / "channel"
    channel.mkdir()
    ch.touch(channel)
    executor = S.RecordingExecutor()
    out = {}

    def run():
        out["result"] = fixture_run(
            tmp_path, [NEW_SOURCE, FINISH], ch.BrowserApprover(channel), executor
        )

    worker = threading.Thread(target=run)
    worker.start()
    for seq in (1, 2):  # the original's approval, then the revision's
        # Open pending.json only while the worker waits for this answer (it has recorded
        # every earlier decision): Windows refuses to delete or replace an open file.
        deadline = time.time() + 60
        pending = None
        while pending is None:
            assert worker.is_alive() and time.time() < deadline
            time.sleep(0.05)
            if len(ch.read_decisions(channel)) == seq - 1 and (
                (channel / ch.PENDING).exists()
            ):
                pending = ch.read_pending(channel)  # None while just being replaced
        assert pending["seq"] == seq
        if seq == 1:
            typed = pending["candidate_hash"][:12]
        else:
            typed = pending["base_snapshot_hash"][:12]
            assert typed != pending["candidate_hash"][:12]
            typed = typed.upper() if upper else typed
        ch.touch(channel)
        assert ch.answer(channel, seq, typed) is True
    worker.join(timeout=60)
    result = out["result"]
    assert result.terminal_state == ctl.REPORT, result.reason
    assert [c.name for c in executor.calls] == ["original"]  # no candidate executed
    assert result.candidates == []
    (record,) = result.report["proposals"]
    assert (record["outcome"], record["code"]) == ("declined", "confirmation_mismatch")
    assert ch.read_decisions(channel) == [
        {"kind": "original", "decision": "approved"},
        {"kind": "candidate", "decision": "declined"},
    ]


def test_an_unavailable_or_unbound_approval_is_recorded(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    S.fake_docker(monkeypatch, [evidence["faulty"]] * 2)
    screen = io.StringIO()
    closed = TerminalApprover(S.FakeStdin(["<prefix>"], out=screen), screen)
    executor = S.RecordingExecutor()
    result = fixture_run(tmp_path / "closed", [NEW_SOURCE, FINISH], closed, executor)
    assert result.terminal_state == ctl.NEEDS_INPUT
    assert result.candidates == []
    (record,) = result.report["proposals"]
    assert (record["outcome"], record["code"]) == ("unavailable", "needs_input")
    (event,) = proposal_events(result.run_dir)
    assert (event["outcome"], event["code"]) == ("unavailable", "needs_input")
    assert any(
        x.endswith("1 unavailable (no approval possible)")
        for x in result.report["limitations"]
    )

    class OtherCode(S.ApproveExactly):
        def decide(self, request):
            approval = super().decide(request)
            if request.kind == "original":
                return approval
            return ctl.Approval("0" * 64, request.base_snapshot_hash, "t")

    executor = S.RecordingExecutor()
    result = fixture_run(
        tmp_path / "unbound", [NEW_SOURCE, FINISH], OtherCode(), executor
    )
    assert result.terminal_state == ctl.REPORT and result.candidates == []
    (record,) = result.report["proposals"]
    assert (record["outcome"], record["code"]) == ("declined", "unbound")


# =============================================================================================
# 4. Rejected revisions are recorded and persisted; nothing executes
# =============================================================================================

BROKEN = FIX + "def broken(:\n"
REJECTED = {
    "unchanged": (
        S.act("propose_patch", new_source=ORIGINAL, rationale="r"),
        "no_change",
    ),
    "syntax": (
        S.act("propose_patch", new_source=BROKEN, rationale="r"),
        "syntax_error",
    ),
    "no_final_newline": (
        S.act("propose_patch", new_source=FIX.rstrip("\n"), rationale="r"),
        "malformed_source",
    ),
    "miscounted": (
        S.act("propose_patch", diff=miscounted(DIFF), rationale="r"),
        "malformed_diff",
    ),
}


@pytest.mark.parametrize("name", list(REJECTED))
def test_a_rejected_revision_is_recorded_and_never_executes(
    tmp_path, monkeypatch, evidence, no_host_runner, name
):
    reply, code = REJECTED[name]
    S.fake_docker(monkeypatch, [evidence["faulty"]])
    approver, executor = S.ApproveExactly(), S.RecordingExecutor()
    result = fixture_run(tmp_path, [reply, FINISH], approver, executor)
    assert result.terminal_state == ctl.REPORT, result.reason
    assert [r.kind for r in approver.requests] == ["original"]  # never asked to approve
    assert [c.name for c in executor.calls] == ["original"]  # no candidate executed
    assert result.candidates == []

    run = result.run_dir
    (record,) = result.report["proposals"]
    assert (record["outcome"], record["code"]) == ("rejected", code)
    assert record["detail"] is None or len(record["detail"]) <= P.DETAIL_CHARS
    assert record["detail_label"] == "validator message; may quote model text"
    action = json.loads(reply)["action"]
    if "new_source" in action:
        assert record["source_kind"] == "new_source"
        source = (run / "proposals" / "r1.new_source.py").read_bytes()
        assert source == action["new_source"].encode("utf-8")
        assert record["new_source_sha256"] == sha(source)
    if name in ("unchanged", "no_final_newline"):  # no diff could be generated
        assert (record["diff_path"], record["diff_sha256"]) == (None, None)
        assert not (run / "proposals" / "r1.diff").exists()
    else:
        persisted = (run / record["diff_path"]).read_bytes()
        assert record["diff_sha256"] == sha(persisted)
        if name == "miscounted":  # the supplied text, unchanged
            assert persisted == action["diff"].encode("utf-8")
            assert record["detail"] == "hunk line counts do not match"
        else:
            assert persisted == P.source_diff(ORIGINAL, BROKEN, "evaluate.py").encode()
    (event,) = proposal_events(run)
    assert (event["outcome"], event["code"]) == ("rejected", code)
    assert (
        "1 proposal: 1 rejected by validation, 0 declined, 0 executed"
        in result.report["limitations"]
    )


def test_two_rejected_revisions_are_both_recorded(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    """The live run's shape: both revisions fail validation; the reasons are now kept."""
    S.fake_docker(monkeypatch, [evidence["faulty"]])
    replies = [REJECTED["miscounted"][0], REJECTED["unchanged"][0], FINISH]
    result = fixture_run(tmp_path, replies)
    assert result.terminal_state == ctl.REPORT, result.reason
    records = result.report["proposals"]
    assert [(r["revision"], r["outcome"], r["code"]) for r in records] == [
        (1, "rejected", "malformed_diff"),
        (2, "rejected", "no_change"),
    ]
    assert [(e["outcome"], e["code"]) for e in proposal_events(result.run_dir)] == [
        ("rejected", "malformed_diff"),
        ("rejected", "no_change"),
    ]
    assert (
        "2 proposals: 2 rejected by validation, 0 declined, 0 executed"
        in result.report["limitations"]
    )


def test_an_oversized_generated_diff_is_rejected_and_not_stored(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    body = "".join(f"value_{i} = {i}  # {'z' * 60}\n" for i in range(1200))
    source = FIX + body
    assert len(source.encode("utf-8")) < MAX_ENTRY_BYTES
    reply = S.act("propose_patch", new_source=source, rationale="r")
    assert len(reply.encode("utf-8")) < 128 * 1024
    generated = P.source_diff(ORIGINAL, source, "evaluate.py").encode("utf-8")
    assert len(generated) > MAX_DIFF_BYTES
    S.fake_docker(monkeypatch, [evidence["faulty"]])
    result = fixture_run(tmp_path, [reply, FINISH])
    (record,) = result.report["proposals"]
    assert (record["outcome"], record["code"]) == ("rejected", "too_large")
    assert record["diff_sha256"] == sha(generated) and record["diff_path"] is None
    assert not (result.run_dir / "proposals" / "r1.diff").exists()
    assert (result.run_dir / "proposals" / "r1.new_source.py").exists()


# =============================================================================================
# 5. The comparison's model label and per-attempt cost
# =============================================================================================


def live(tmp_path, script):
    c, transport = S.client(script)
    with deny_network():  # any real connection attempt would fail
        result = ctl.run_agent(
            S01,
            tmp_path / "runs",
            c,
            S.ApproveExactly(),
            executor=S.RecordingExecutor(),
            live_authorized=True,
            spend=S.GENEROUS,
            env={},
        )
    return result, transport


def test_the_comparison_names_the_live_model(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    S.fake_docker(monkeypatch, [evidence["faulty"]])
    result, transport = live(
        tmp_path,
        [(200, S.ok_body(NEW_SOURCE, S.USAGE)), (200, S.ok_body(FINISH, S.USAGE))],
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    assert len(transport.requests) == 2
    report = result.report
    assert report["comparison"]["model"] == (
        "nvidia/test-model via the production client (live)"
    )
    assert report["proposals"][0]["outcome"] == "executed"


def test_without_a_model_client_the_slice_1_wording_stays(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    S.fake_docker(monkeypatch, [evidence["faulty"], evidence["clean"]])
    result = fixture_run(tmp_path, [NEW_SOURCE, FINISH])
    assert result.report["comparison"]["model"] == "fixture replies (non-live)"
    direct = comparison_report(
        result.original.run_dir, result.original.outcome, result.candidates
    )
    assert direct["model"] == NO_MODEL
    assert NO_MODEL.startswith("none (T-06 slice 1 has no model client")


def attempts(run_dir: Path) -> list[dict]:
    return [e for e in events(run_dir) if e["event"] == "model_attempt"]


def test_each_live_attempt_carries_its_ledger_entry(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    S.fake_docker(monkeypatch, [evidence["faulty"]])
    partial = {"prompt_tokens": 1000, "total_tokens": 1000}  # completion count unknown
    result, _ = live(
        tmp_path,
        [
            httpx2.ReadTimeout,  # transient: the ceiling stays held, then one retry
            (200, S.ok_body(S.act("list_project_files"), partial)),
            (200, S.ok_body(FINISH, S.USAGE)),
        ],
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    entries = result.report["cost"]["entries"]
    logged = attempts(result.run_dir)
    assert len(logged) == len(entries) == 3
    assert [a["cost"]["status"] for a in logged] == [
        "unknown_usage",
        "partial_usage",
        "settled",
    ]
    for event, entry in zip(logged, entries, strict=True):
        assert event["cost"] == entry
        for field in ("known_usd", "unresolved_usd"):
            assert Decimal(event["cost"][field]) == Decimal(entry[field])
    known = sum(Decimal(a["cost"]["known_usd"]) for a in logged)
    assert known == Decimal(result.report["cost"]["known_usd"])


def test_fixture_attempts_say_cost_is_not_applicable(
    tmp_path, monkeypatch, evidence, no_host_runner
):
    S.fake_docker(monkeypatch, [evidence["faulty"]])
    result = fixture_run(tmp_path, [S.act("list_project_files"), FINISH])
    logged = attempts(result.run_dir)
    assert len(logged) == 2
    assert all(a["cost"] == "not applicable (fixture)" for a in logged)
    assert result.report["cost"]["applicable"] is False
