"""T-06 slice 4f, offline: a failing candidate's bounded error summary goes back to the model,
and a fixed adapter reference is part of the model's context.

Live run 4 (`runs/live4/agent-s01_faulty-8dcf4c7b3c37/`): both revisions read
`X['subject_id']`, but `adapter.load_table()` returns only the feature columns. Each exited 1
with `KeyError: 'subject_id'`, captured by the in-container supervisor in its frame header
(`supervisor.candidate_output_tail`; the child's stderr is merged into its stdout there), while
the record's `stderr_tail` is the docker CLI's own stderr and was empty. The evaluate_candidate
result carried no output, so the model repeated the error.

Here the summary (the exception line plus at most the last 20 lines of the final traceback, at
most 2,000 characters, control characters escaped, host paths, host environment values and the
key redacted) is labelled "candidate output (untrusted)", returned in the evaluate_candidate
result and persisted in the candidate's report entry. The adapter reference is derived from
`atlas.adapter` itself.

Fixture replies, or the production client over an `httpx2.MockTransport` under the network
guard; scripted executors stand in for the runner (the Docker replay is in
tests/integration/test_agent_fixture_docker.py).
"""

import ast
import hashlib
import importlib
import importlib.util
import inspect
import json
from pathlib import Path

import pytest

from atlas import adapter
from atlas.agent import controller as ctl
from atlas.agent.client import FixtureClient
from atlas.contracts import Outcome, RunOutcome


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name.removesuffix(".py"), Path(__file__).with_name(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _load("test_agent_slice3.py")
S01, KEY = S.S01, S.KEY
ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
FINISH = S.FINISH
# Live run 4's first revision, byte for byte, and its candidate's captured output.
C1_SOURCE = (FIXTURES / "live4_r1_new_source.txt").read_text(encoding="utf-8")
C1_OUTPUT = (FIXTURES / "live4_c1_candidate_output.txt").read_text(encoding="utf-8")
C1 = S.act("propose_patch", new_source=C1_SOURCE, rationale="grouped folds")
LABEL = "candidate output (untrusted)"


def failure():
    """Imported per test, so each one fails on its own before the module exists."""
    return importlib.import_module("atlas.agent.failure")


def content_chars(summary: dict) -> int:
    return len(summary["exception"] or "") + len(summary["traceback"])


def test_the_fixtures_are_live_run_4s_bytes():
    digest = hashlib.sha256(C1_SOURCE.encode("utf-8")).hexdigest()
    assert digest == "c0739c8ce22c768b795d9b9b38a53ee48951b627637ad567c3d088d96ab1cde5"
    digest = hashlib.sha256(C1_OUTPUT.encode("utf-8")).hexdigest()
    assert digest == "e88c0a80cb323cdb510948125547ff26de6ed9376518b8979dcbf4f9542cf0bd"


# =============================================================================================
# 1. The failure summary
# =============================================================================================


def test_live_run_4s_failure_is_summarized():
    summary = failure().summarize(C1_OUTPUT)
    assert summary["label"] == LABEL
    assert summary["exception"] == "KeyError: 'subject_id'"
    lines = summary["traceback"].split("\n")
    assert len(lines) <= 20
    # The last traceback (the direct cause shown by the chained exception), ending with the
    # exception line, including the project's own frame.
    assert lines[0] == "Traceback (most recent call last):"
    assert lines[-1] == "KeyError: 'subject_id'"
    assert "    groups = X['subject_id']" in lines
    assert (
        'File "/work/project/evaluate.py", line 12, in <module>' in summary["traceback"]
    )
    assert summary["truncated"] is False
    assert content_chars(summary) <= 2000


def test_the_summary_is_bounded_and_keeps_the_end():
    frames = "".join(
        f'  File "/work/project/m{i}.py", line {i}, in f{i}\n    f{i + 1}()\n'
        for i in range(200)
    )
    output = (
        "Traceback (most recent call last):\n" + frames + "ValueError: " + "x" * 5000
    )
    summary = failure().summarize(output)
    assert content_chars(summary) <= 2000
    assert len(summary["traceback"].split("\n")) <= 20
    assert summary["exception"].startswith("ValueError: x")
    assert summary["traceback"].endswith("x")
    assert summary["truncated"] is True


def test_output_without_a_traceback_keeps_its_last_lines():
    output = "".join(f"line {i}\n" for i in range(50)) + "fatal: no model\n"
    summary = failure().summarize(output)
    assert summary["exception"] is None
    lines = summary["traceback"].split("\n")
    assert len(lines) == 20 and lines[-1] == "fatal: no model"
    assert summary["truncated"] is True


@pytest.mark.parametrize("output", [None, ""], ids=["none", "empty"])
def test_no_output_gives_an_empty_summary(output):
    summary = failure().summarize(output)
    assert summary == {
        "label": LABEL,
        "exception": None,
        "traceback": "",
        "truncated": False,
    }


def test_host_paths_are_redacted_and_container_paths_kept(tmp_path):
    host = str(tmp_path / "runs" / "agent-x")
    output = (
        "Traceback (most recent call last):\n"
        '  File "/work/project/evaluate.py", line 3, in <module>\n'
        '  File "/opt/atlas/atlas_runner_entry.py", line 273, in child_main\n'
        f"    open({host!r})\n"
        "    open('C:\\\\Users\\\\someone\\\\secret\\\\notes.txt')\n"
        "    open('D:/data/private.csv')\n"
        "    open('\\\\\\\\fileserver\\\\share\\\\x')\n"
        f"OSError: cannot read {host}/table.csv or C:\\Users\\someone\\x.py"
    )
    summary = failure().summarize(output, host_strings=[str(tmp_path)])
    text = json.dumps(summary)
    for leaked in (str(tmp_path), "someone", "D:/data", "fileserver", "C:\\"):
        assert leaked not in text and leaked.replace("\\", "\\\\") not in text
    assert (
        "<host-path>" in summary["traceback"] and "<host-path>" in summary["exception"]
    )
    assert "/work/project/evaluate.py" in summary["traceback"]
    assert "/opt/atlas/atlas_runner_entry.py" in summary["traceback"]


@pytest.mark.parametrize(
    "output",
    [
        "//server/private/customer.csv",  # combined review 1, F1
        "\\\\server\\private\\customer.csv",
        "\\\\server/private/customer.csv",
        "/\\server\\private/customer.csv",
        "\\\\\\\\server\\\\private\\\\customer.csv",  # repr-doubled
        "\\\\server\\private share\\customer.csv",
        "OSError: cannot read //server/private share/customer.csv",
    ],
)
def test_unc_paths_are_redacted_in_every_slash_style(output):
    summary = failure().summarize(output, env={})
    assert "server" not in summary["traceback"]
    assert "customer" not in summary["traceback"]
    assert summary["traceback"].endswith("<host-path>")


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        # combined review 1, F1: the path's suffix after the space leaked
        ("C:\\Users\\Alice Smith\\private\\customer.csv", "<host-path>"),
        ("C:/Users/Alice Smith/private/customer.csv", "<host-path>"),
        (
            "OSError: cannot read C:/Users/Alice Smith/data.csv (mode r)",
            "OSError: cannot read <host-path>",
        ),
        (
            '  File "C:\\Users\\Alice Smith\\proj\\x.py", line 3, in <module>',
            '  File "<host-path>", line 3, in <module>',
        ),
        (
            "    open('C:/Users/Alice Smith/data.csv', 'rb')",
            "    open('<host-path>', 'rb')",
        ),
        (
            "    open('//server/my share/a b.csv') + x",
            "    open('<host-path>') + x",
        ),
    ],
)
def test_paths_with_spaces_are_redacted_whole(output, expected):
    assert failure().summarize(output, env={})["traceback"] == expected


def test_a_path_split_across_lines_is_redacted_only_on_its_first_line():
    """The documented limit: redaction is per line and best-effort, so text the candidate
    deliberately splits across lines keeps its later lines (SPEC §11)."""
    output = "C:\\Users\\Alice Smith\nprivate\\customer.csv"
    lines = failure().summarize(output, env={})["traceback"].split("\n")
    assert lines[0] == "<host-path>"
    assert lines[1] == "private\\customer.csv"


def test_urls_floor_division_and_container_paths_are_kept():
    output = (
        "see https://example.org/a/b and file x//2 or (a)//2\n"
        '  File "/work/project/evaluate.py", line 3, in <module>'
    )
    assert failure().summarize(output, env={})["traceback"] == output


def test_host_environment_values_and_the_key_are_redacted():
    env = {"SOME_TOKEN": "tok-0123456789abcdef", "SHORT": "ab", "EMPTY": ""}
    output = (
        "Traceback (most recent call last):\n"
        f"    print('tok-0123456789abcdef', {KEY!r})\n"
        f"RuntimeError: leaked tok-0123456789abcdef and {KEY} (ab)"
    )
    summary = failure().summarize(output, env=env, secrets=[KEY])
    text = json.dumps(summary)
    assert "tok-0123456789abcdef" not in text and KEY not in text
    assert summary["exception"] == (
        "RuntimeError: leaked <env-redacted> and <redacted> (ab)"
    )


def test_control_characters_are_escaped():
    output = (
        "Traceback (most recent call last):\n"
        "    print('\x1b[31mred\x1b[0m\r\x00\u202eevil\u200b')\n"
        "ValueError: bad\x07 \x7f\u0085value\tend"
    )
    summary = failure().summarize(output)
    text = summary["exception"] + summary["traceback"]
    for raw in (
        "\x1b",
        "\r",
        "\x00",
        "\u202e",
        "\u200b",
        "\x07",
        "\x7f",
        "\u0085",
        "\t",
    ):
        assert raw not in text
    assert (
        "\\x1b[31mred" in summary["traceback"] and "\\u202eevil" in summary["traceback"]
    )
    assert summary["exception"] == "ValueError: bad\\x07 \\x7f\\x85value\\x09end"
    assert summary["traceback"].count("\n") == 2  # only the line separators remain


# =============================================================================================
# 2. The summary reaches the model and the report
# =============================================================================================


class FailingExecutor:
    """A candidate that ran and exited 1 with `output` captured by the supervisor."""

    def __init__(self, output, status="failed"):
        self.output, self.status, self.calls = output, status, []

    def __call__(
        self, snapshot, candidate, approval, candidate_dir, *, proposed_at=None
    ):
        from atlas.agent.execute import CandidateResult

        self.calls.append(Path(candidate_dir))
        Path(candidate_dir).mkdir(parents=True)
        return CandidateResult(
            candidate_dir=Path(candidate_dir),
            candidate_hash=approval.candidate_hash,
            approval=approval.to_dict(),
            diff_sha256=candidate.diff_sha256,
            execution={"status": self.status, "reason": "candidate exited with 1"},
            evaluated=True,
            outcome=RunOutcome(
                outcome=Outcome.INCONCLUSIVE, policy_version="policy-v1.3"
            ),
            timing={},
            candidate_output=self.output,
        )


@pytest.fixture
def host_baseline(monkeypatch):
    monkeypatch.setattr(ctl, "docker_original", S.host_fixture_original)


def fixture_run(tmp_path, replies, executor):
    client = FixtureClient("s4f", [{"content": r} for r in replies])
    result = ctl.run_agent(
        S01, tmp_path / "runs", client, S.ApproveExactly(), executor=executor, env={}
    )
    return result, client


def evaluations(request) -> list[dict]:
    (user,) = [m for m in request.messages if m["role"] == "user"]
    history = json.loads(user["content"])["history"]
    return [h["result"] for h in history if h["tool"] == "evaluate_candidate"]


def test_the_failure_summary_is_returned_to_the_model_and_reported(
    tmp_path, host_baseline
):
    executor = FailingExecutor(C1_OUTPUT)
    result, client = fixture_run(tmp_path, [C1, FINISH], executor)
    assert result.terminal_state == ctl.REPORT, result.reason
    assert len(executor.calls) == 1
    (seen,) = evaluations(client.requests[1])
    summary = seen["failure_summary"]
    assert summary == failure().summarize(C1_OUTPUT)
    assert (
        summary["label"] == LABEL and summary["exception"] == "KeyError: 'subject_id'"
    )
    assert seen["execution_status"] == "failed"
    (entry,) = result.report["comparison"]["candidates"]
    assert entry["failure_summary"] == summary
    # The raw output itself is never reported.
    report = json.dumps(result.report)
    assert "candidate_output" not in report and "joblib" not in report


def test_a_completed_candidate_has_no_failure_summary(tmp_path, host_baseline):
    result, client = fixture_run(tmp_path, [C1, FINISH], S.RecordingExecutor())
    assert result.terminal_state == ctl.REPORT
    (seen,) = evaluations(client.requests[1])
    assert "failure_summary" not in seen
    assert result.report["comparison"]["candidates"][0]["failure_summary"] is None


def test_the_run_directory_never_reaches_the_model(tmp_path, host_baseline):
    runs = tmp_path / "runs"
    output = (
        "Traceback (most recent call last):\n"
        f'  File "{runs}\\agent\\evaluate.py", line 1\n'
        f"FileNotFoundError: {runs}/agent/table.csv"
    )
    _, client = fixture_run(tmp_path, [C1, FINISH], FailingExecutor(output))
    sent = json.dumps(client.requests[1].messages)
    assert str(tmp_path) not in sent and str(tmp_path).replace("\\", "\\\\") not in sent
    assert "<host-path>" in sent


def test_a_live_run_never_sends_the_key_from_candidate_output(tmp_path):
    output = f"Traceback (most recent call last):\nRuntimeError: {KEY}\n"
    result, transport = S.live_run(
        tmp_path,
        [(200, S.ok_body(C1, S.USAGE)), (200, S.ok_body(FINISH, S.USAGE))],
        S.ApproveExactly(),
        FailingExecutor(output),
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    sent = transport.requests[1].content.decode("utf-8")
    assert "RuntimeError: <redacted>" in sent and KEY not in sent
    assert KEY not in json.dumps(result.report)


# =============================================================================================
# 3. The adapter reference
# =============================================================================================


def public_adapter_functions() -> dict:
    return {
        name: fn
        for name, fn in inspect.getmembers(adapter, inspect.isfunction)
        if fn.__module__ == adapter.__name__ and not name.startswith("_")
    }


def test_the_adapter_reference_matches_the_module():
    reference = ctl.ADAPTER_REFERENCE
    functions = public_adapter_functions()
    listed = [f["name"] for f in reference["functions"]]
    # Every public function, except the harness-only session the runner installs.
    assert set(listed) | set(ctl.ADAPTER_HARNESS_ONLY) == set(functions)
    assert set(ctl.ADAPTER_HARNESS_ONLY) == {"session"}
    assert {"load_table", "load_metadata", "declare_split", "take", "write_predictions"} <= set(listed)  # fmt: skip
    tree = ast.parse(Path(adapter.__file__).read_text(encoding="utf-8"))
    order = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert listed == [n for n in order if n in listed]  # the module's own order
    text = ctl.ADAPTER_REFERENCE_TEXT
    for entry in reference["functions"]:
        fn = functions[entry["name"]]
        assert entry["contract"] == inspect.getdoc(fn).splitlines()[0]
        assert entry["signature"].startswith(f"adapter.{entry['name']}(")
        for p in inspect.signature(fn).parameters:
            assert p in entry["signature"]
        assert f"- {entry['signature']}: {entry['contract']}" in text.splitlines()
    assert "adapter.take" in reference["rule"] and reference["rule"] in text


def test_the_adapter_reference_ends_the_system_prompt():
    """It is part of the system prompt, so the user-message budget derived from the system
    prompt (and the per-result limit, half of it) already accounts for it."""
    separator = chr(10) * 2  # one blank line
    assert (
        ctl.SYSTEM_PROMPT
        == ctl.SYSTEM_INSTRUCTIONS + separator + ctl.ADAPTER_REFERENCE_TEXT
    )
    c, _ = S.client([], max_input_tokens=12_000, template_overhead_tokens=16)
    system = len(ctl.SYSTEM_PROMPT.encode("utf-8"))
    assert c.user_message_budget(ctl.SYSTEM_PROMPT) == 12_000 - system - 2 * 16


def test_the_adapter_reference_is_generic_and_the_same_everywhere(
    tmp_path, host_baseline
):
    text = ctl.ADAPTER_REFERENCE_TEXT
    for hint in (
        "s01",
        "s02",
        "subject",
        "evaluate.py",
        "SelectKBest",
        "GroupKFold",
        "HAR",
    ):
        assert hint not in text
    seen = []
    for name in ("s01_faulty", "s02_clean"):
        client = FixtureClient("s4f", [{"content": FINISH}])
        ctl.run_agent(
            S01.parent / name, tmp_path / name, client, S.ApproveExactly(),
            executor=S.RecordingExecutor(), env={},
        )  # fmt: skip
        (system,) = [m for m in client.requests[0].messages if m["role"] == "system"]
        seen.append(system["content"])
    assert seen[0] == seen[1] == ctl.SYSTEM_PROMPT
    assert seen[0].endswith(text)


def test_the_prompt_budget_holds_with_a_maximal_history(tmp_path):
    """At the decided input estimate, five large reads fill the history: every request keeps
    the reference, stays within the user-message budget and drops old results; the fixed
    context still leaves room for one whole result at the per-result limit."""
    read = S.act("read_project_file", path="table.csv")  # 13,371 bytes, over a result
    script = [(200, S.ok_body(read, S.USAGE))] * 5 + [(200, S.ok_body(FINISH, S.USAGE))]
    result, transport = S.live_run(
        tmp_path, script, S.ApproveExactly(), max_input_tokens=12_000
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    figures = result.report["prompt_budget"]
    budget, per_result = figures["user_message_bytes"], figures["tool_result_chars"]
    assert budget == 12_000 - len(ctl.SYSTEM_PROMPT.encode("utf-8")) - 2 * 16
    assert per_result == min(ctl.MAX_TOOL_RESULT_CHARS, budget // 2)
    sizes, users = [], []
    for request in transport.requests:
        messages = json.loads(request.content)["messages"]
        assert messages[0] == {"role": "system", "content": ctl.SYSTEM_PROMPT}
        (user,) = [m["content"] for m in messages if m["role"] == "user"]
        sizes.append(len(user.encode("utf-8")))
        users.append(json.loads(user))
    assert len(sizes) == 6 and max(sizes) <= budget
    assert users[0]["history"] == [] and users[-1].get("history_truncated") is True
    # Room after the fixed context (the first request: no history) for one whole result,
    # its history envelope included.
    envelope = len(json.dumps(users[1]["history"][-1], sort_keys=True).encode("utf-8"))
    assert budget - sizes[0] >= envelope
    for later in users[1:]:
        newest = later["history"][-1]
        assert newest["tool"] == "read_project_file" and "text" in newest["result"]
