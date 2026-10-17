"""T-06 slice 4, Gate 1 repair (`runs/g1-1016/review.md`), offline only.

P2-1: the history truncation marker must be inside the final size check, so a prompt that
fits never grows past the budget when the marker is added.
P2-2: a truncated tool result is bounded as it is actually embedded in the prompt (escaped
again inside a JSON string), and the newest result is shortened to fit rather than dropped
when a useful prefix fits.

The production client runs over a mock transport under the fixture network guard; no request
leaves the process. Apart from the last (helper-property) test, this file uses interfaces that
also exist at `96f6fc6`, so it can run there for the red demonstration.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from atlas.agent import controller as ctl
from atlas.agent.client import ModelRequest


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace(".py", ""), Path(__file__).with_name(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


T = _load("test_agent_slice4_controls.py")
FINISH, USAGE = T.FINISH, T.USAGE
MARKER = ', "history_truncated": true'  # 27 bytes in the sorted serialization


def utf8(text: str) -> int:
    return len(text.encode("utf-8"))


def captured_run(tmp_path, **config):
    """A finished live run (mock transport) whose run object can build further prompts."""
    runs = []

    def original(run):
        runs.append(run)
        return T.R.host_baseline(run)

    result, _, _, _ = T.live(
        tmp_path, [(T.R.raw_body(FINISH, USAGE), {})], original=original, **config
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    return runs[0]


def user_message(run) -> str:
    messages = run._messages()
    run.client.check_request(
        ModelRequest(messages, {})
    )  # the whole prompt fits the estimate
    return messages[1]["content"]


def item(text: str) -> dict:
    return {"tool": "inspect_evidence", "args": {}, "result": {"text": text}}


# =============================================================================================
# P2-1: the truncation marker is part of the final size check
# =============================================================================================


def test_the_marker_never_pushes_a_live_run_over_the_estimate(tmp_path):
    """Codex's end-to-end reproduction: two inspections then finish, at an input estimate
    chosen so that the marker used to push the third prompt over the budget."""
    action = T.S.act("inspect_evidence", check="split_integrity")
    script = [(T.R.raw_body(action, USAGE), {})] * 2 + [
        (T.R.raw_body(FINISH, USAGE), {})
    ]
    control, transport, _, _ = T.live(tmp_path / "control", script)
    assert control.terminal_state == ctl.REPORT
    second = json.loads(transport.requests[1].content)["messages"][1]["content"]
    limit = utf8(second) + 10 + utf8(ctl.SYSTEM_PROMPT) + 32
    result, transport, _, _ = T.live(
        tmp_path / "boundary", script, max_input_tokens=limit
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    bodies = [json.loads(r.content) for r in transport.requests]
    assert len(bodies) == 3 and all(T.estimate(b) <= limit for b in bodies)


@pytest.mark.parametrize("spare", [0, 1, 26, 27, 28, 40])
def test_the_marker_is_budgeted_at_the_decided_ceiling(tmp_path, spare):
    """At the decided 12,000 estimate: two recent results fill the budget up to `spare`
    bytes; an older one must then be dropped, and the marker must still fit."""
    run = captured_run(tmp_path)
    assert run.prompt_budget == 11_479
    run.transcript = [item("x" * 3000), item("")]
    pad = run.prompt_budget - utf8(user_message(run)) - spare
    assert 0 < pad < run.tool_result_chars - 40
    run.transcript[1]["result"]["text"] = "y" * pad
    assert utf8(user_message(run)) == run.prompt_budget - spare  # all fits, no marker
    newest = run.transcript[1]
    run.transcript.insert(0, item("old" * 1000))
    final = user_message(run)
    assert utf8(final) <= run.prompt_budget
    history = json.loads(final)["history"]
    assert json.loads(final)["history_truncated"] is True
    assert history[-1] == newest  # the newest result is never the one dropped
    # The two recent results stay together exactly when the marker also fits.
    assert len(history) == (2 if spare >= len(MARKER) else 1)


def test_no_marker_when_everything_fits_exactly(tmp_path):
    run = captured_run(tmp_path)
    run.transcript = [item("x" * 3000), item("")]
    pad = run.prompt_budget - utf8(user_message(run))
    run.transcript[1]["result"]["text"] = "y" * pad
    final = user_message(run)
    assert utf8(final) == run.prompt_budget  # an exact fit is a fit
    assert "history_truncated" not in json.loads(final)


# =============================================================================================
# P2-2: tool results are bounded as embedded, and the newest survives when space permits
# =============================================================================================

CONTENT = {
    "plain": "x",
    "quotes": '"',
    "backslashes": "\\",
    "quote-backslash": '\\"',
    "accented": "\u00e9",  # 6 bytes as \\u00e9
    "emoji": "\U0001f600",  # 12 bytes as a surrogate pair
    "controls": "\n\t\x01",
    "mixed": 'a"\\\u00e9\U0001f600\n',
}


@pytest.mark.parametrize("kind", sorted(CONTENT))
def test_a_large_read_is_bounded_as_embedded_and_kept(tmp_path, kind):
    run = captured_run(tmp_path)
    content = CONTENT[kind] * run.tool_result_chars
    original = {
        "untrusted_project_content": content,
        "bytes": len(content),
        "truncated": True,
    }
    run._record_tool(1, "read_project_file", {"path": "evaluate.py"}, original)
    stored = run.transcript[-1]["result"]
    full = json.dumps(original, sort_keys=True)
    assert stored["truncated"] is True and full.startswith(stored["text"])
    embedded = utf8(json.dumps(stored, sort_keys=True))
    assert embedded <= run.tool_result_chars  # escaping and the envelope included
    assert len(stored["text"]) > 0
    final = user_message(run)
    assert utf8(final) <= run.prompt_budget
    (kept,) = json.loads(final)["history"]
    assert kept["result"] == stored  # the newest (only) result survives whole


def test_codex_quote_heavy_read_shape(tmp_path):
    """Codex's reproduction: the exact `_read` shape with 5,739 quote characters."""
    run = captured_run(tmp_path)
    n = run.tool_result_chars
    run._record_tool(
        1, "read_project_file", {"path": "evaluate.py"},
        {"untrusted_project_content": '"' * n, "bytes": n, "truncated": False},
    )  # fmt: skip
    assert utf8(json.dumps(run.transcript[-1]["result"], sort_keys=True)) <= n
    assert json.loads(user_message(run))["history"]  # not discarded


def test_a_small_result_is_stored_unchanged(tmp_path):
    run = captured_run(tmp_path)
    result = {"untrusted_project_content": 'a "b" \\c', "bytes": 9, "truncated": False}
    run._record_tool(1, "read_project_file", {"path": "evaluate.py"}, dict(result))
    assert run.transcript[-1]["result"] == result  # control: no envelope


def base_size(tmp_path) -> int:
    run = captured_run(tmp_path / "probe")
    run.transcript = []
    return utf8(user_message(run))


def config_for_budget(budget: int) -> dict:
    """An input estimate giving exactly this user-message budget (system prompt + 2 x 16)."""
    return {"max_input_tokens": budget + utf8(ctl.SYSTEM_PROMPT) + 32}


@pytest.mark.parametrize("kind", ["plain", "quotes", "emoji", "mixed"])
def test_the_newest_result_is_shortened_not_dropped(tmp_path, kind):
    """Space after the base context (~1,500 bytes) is below the per-result limit (about
    half the budget): the newest result must be cut to fit, not evicted."""
    base = base_size(tmp_path)
    budget = base + 1_500
    run = captured_run(tmp_path / "run", **config_for_budget(budget))
    assert run.prompt_budget == budget and run.tool_result_chars > 1_500
    content = CONTENT[kind] * 4_000
    original = {
        "untrusted_project_content": content,
        "bytes": len(content),
        "truncated": True,
    }
    run._record_tool(1, "read_project_file", {"path": "table.csv"}, original)
    final = user_message(run)
    assert utf8(final) <= budget
    (kept,) = json.loads(final)["history"]
    full = json.dumps(original, sort_keys=True)
    assert kept["result"]["truncated"] is True and full.startswith(
        kept["result"]["text"]
    )
    assert len(kept["result"]["text"]) >= ctl_min_prefix()


def ctl_min_prefix() -> int:
    return getattr(ctl, "MIN_TOOL_PREFIX_CHARS", 200)


def test_no_usable_space_drops_the_result_and_still_fits(tmp_path):
    base = base_size(tmp_path)
    budget = base + 100  # room for the marker, not for a useful prefix
    run = captured_run(tmp_path / "run", **config_for_budget(budget))
    run._record_tool(
        1, "read_project_file", {"path": "table.csv"}, {"text": "z" * 5_000}
    )
    final = user_message(run)
    assert utf8(final) <= budget
    message = json.loads(final)
    assert message["history"] == [] and message["history_truncated"] is True  # control


def test_a_shortened_older_result_keeps_the_newest_intact(tmp_path):
    """Several results: older ones are evicted whole, the newest is kept."""
    run = captured_run(tmp_path)
    for i in range(4):
        run._record_tool(
            i, "read_project_file", {"path": "table.csv"}, {"text": f"{i}" * 9_000}
        )
    final = user_message(run)
    assert utf8(final) <= run.prompt_budget
    message = json.loads(final)
    assert message["history"][-1] == run.transcript[-1]
    assert message["history_truncated"] is True


# =============================================================================================
# The bounding helper itself (new in the repair)
# =============================================================================================


@pytest.mark.parametrize("kind", sorted(CONTENT))
@pytest.mark.parametrize("limit", [0, 31, 32, 37, 50, 101, 1_000])
def test_the_bounded_envelope_is_maximal_and_within_the_limit(kind, limit):
    text = json.dumps({"c": CONTENT[kind] * 200}, sort_keys=True)
    envelope = ctl._bounded_envelope(text, limit)
    size = utf8(json.dumps(envelope, sort_keys=True))
    prefix = envelope["text"]
    assert text.startswith(prefix) and envelope["truncated"] is True
    if prefix:
        assert size <= limit
    if len(prefix) < len(text):  # one more character would not fit
        longer = {"text": text[: len(prefix) + 1], "truncated": True}
        assert utf8(json.dumps(longer, sort_keys=True)) > limit
